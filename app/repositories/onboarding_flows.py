from app.models.onboarding_flows import OnboardingFlow, OnboardingFlowVersion
from app.models.languages import Language
from app.models.assets import Asset
from app.schemas.onboarding_flows import OnboardingFlowVersionCreate, OnboardingFlowVersionResponse, OnboardingFlowUpdate
from app.utils.uuid import get_uid
from neomodel import db
from typing import Set, Union, List


def _ensure_question_ids(data: Union[dict, list, None]) -> Union[dict, list, None]:
    """
    Ensure each question in the onboarding flow data has a question_id.
    Auto-generates a UUID for questions that don't have one.
    
    Args:
        data: The onboarding flow data (list of questions or dict)
        
    Returns:
        The data with question_ids added where missing
    """
    if data is None:
        return data
    
    if isinstance(data, list):
        # List of questions
        for item in data:
            if isinstance(item, dict):
                # Add question_id if missing
                if 'question_id' not in item or not item['question_id']:
                    item['question_id'] = get_uid()
    elif isinstance(data, dict):
        # Single question or wrapper object
        if 'question_id' not in data or not data['question_id']:
            # Check if this looks like a question (has 'label' or 'answers')
            if 'label' in data or 'answers' in data:
                data['question_id'] = get_uid()
        
        # Handle nested questions list (e.g., {"questions": [...]})
        if 'questions' in data and isinstance(data['questions'], list):
            _ensure_question_ids(data['questions'])
    
    return data


def _extract_asset_ids_from_data(data: Union[dict, list, None]) -> Set[str]:
    """
    Recursively extract asset IDs from onboarding flow JSON data.
    Looks for 'content' fields in answers that contain asset IDs.
    
    Args:
        data: The onboarding flow data (list of questions or dict)
        
    Returns:
        Set of unique asset IDs found in the data
    """
    asset_ids: Set[str] = set()
    
    if data is None:
        return asset_ids
    
    if isinstance(data, list):
        for item in data:
            asset_ids.update(_extract_asset_ids_from_data(item))
    elif isinstance(data, dict):
        # Check for 'content' field (asset ID reference)
        if 'content' in data and data['content']:
            content = data['content']
            # Handle case where content might be "asset_id.extension"
            if isinstance(content, str):
                asset_id = content.split('.')[0] if '.' in content else content
                asset_ids.add(asset_id)
        
        # Recurse into nested structures
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                asset_ids.update(_extract_asset_ids_from_data(value))
    
    return asset_ids


def _link_assets_to_version(version: OnboardingFlowVersion, data: Union[dict, list, None]) -> List[str]:
    """
    Extract asset IDs from data and create USES_ASSET relationships.
    
    Args:
        version: The OnboardingFlowVersion node
        data: The onboarding flow JSON data
        
    Returns:
        List of asset IDs that were successfully linked
    """
    asset_ids = _extract_asset_ids_from_data(data)
    linked_ids = []
    
    for asset_id in asset_ids:
        asset = Asset.nodes.get_or_none(asset_id=asset_id)
        if asset:
            version.uses_assets.connect(asset)
            linked_ids.append(asset_id)
    
    return linked_ids


class OnboardingFlowRepository:
    @staticmethod
    def create_onboarding_flow(language_id: str, data: OnboardingFlowVersionCreate) -> OnboardingFlowVersionResponse:
        """Create a new onboarding flow version.
        
        This creates a new version every time it's called. The version is created as 'draft'
        and needs to be manually set as current using set_current_version().
        """
        # Get Language directly
        language = Language.nodes.get_or_none(language_id=language_id)
        if not language:
            raise ValueError(f"Language {language_id} not found")

        # Define the monolithic key for this language's onboarding flow
        # This ensures one container per language
        key = f"onboarding_{language.language_id}"
        
        # Find or create OnboardingFlow container
        onboarding_flow = OnboardingFlow.nodes.get_or_none(key=key)
        if not onboarding_flow:
            onboarding_flow = OnboardingFlow(key=key).save()
        
        # Get the latest version number
        existing_versions = list(onboarding_flow.versions.all())
        if existing_versions:
            latest_version = max(v.version for v in existing_versions)
            new_version_number = latest_version + 0.1
        else:
            new_version_number = 1.0
        
        # Ensure all questions have IDs
        processed_data = _ensure_question_ids(data.data)
        
        # Create new OnboardingFlowVersion (as draft)
        version = OnboardingFlowVersion(
            data=processed_data,
            version=new_version_number,
            status="draft",
            created_by=data.updated_by or "System",
            updated_by=data.updated_by
        ).save()
        
        # Extract and link assets from the JSON data
        _link_assets_to_version(version, processed_data)
        
        # Link version to container
        onboarding_flow.versions.connect(version)
        
        # Link container to Language (only if not already connected)
        # This avoids cardinality violation when adding new versions to existing flow
        if not language.onboarding_flows.is_connected(onboarding_flow):
            language.onboarding_flows.connect(onboarding_flow)
        
        return OnboardingFlowVersionResponse(
            onboarding_flow_version_id=version.onboarding_flow_version_id,
            onboarding_flow_id=onboarding_flow.onboarding_flow_id,
            key=onboarding_flow.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at
        )
    
    @staticmethod
    def set_current_version(onboarding_flow_id: str, version_id: str) -> OnboardingFlowVersionResponse:
        """Set a specific version as the current version for an onboarding flow."""
        onboarding_flow = OnboardingFlow.nodes.get_or_none(onboarding_flow_id=onboarding_flow_id)
        if not onboarding_flow:
            raise ValueError(f"OnboardingFlow {onboarding_flow_id} not found")
        
        version = OnboardingFlowVersion.nodes.get_or_none(onboarding_flow_version_id=version_id)
        if not version:
            raise ValueError(f"OnboardingFlowVersion {version_id} not found")
        
        # Disconnect old current version
        onboarding_flow.current_version.disconnect_all()
        
        # Set new current version
        onboarding_flow.current_version.connect(version)
        
        # Update version status to active
        version.status = "active"
        version.save()
        
        return OnboardingFlowVersionResponse(
            onboarding_flow_version_id=version.onboarding_flow_version_id,
            onboarding_flow_id=onboarding_flow.onboarding_flow_id,
            key=onboarding_flow.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at
        )

    @staticmethod
    def get_onboarding_flow(onboarding_flow_id: str):
        """Get onboarding flow with all its versions."""
        onboarding_flow = OnboardingFlow.nodes.get_or_none(onboarding_flow_id=onboarding_flow_id)
        if not onboarding_flow:
            raise ValueError(f"OnboardingFlow {onboarding_flow_id} not found")
        
        current_version = onboarding_flow.current_version.single()
        all_versions = list(onboarding_flow.versions.all())
        
        return {
            "onboarding_flow_id": onboarding_flow.onboarding_flow_id,
            "key": onboarding_flow.key,
            "current_version": {
                "onboarding_flow_version_id": current_version.onboarding_flow_version_id,
                "data": current_version.data,
                "version": current_version.version,
                "status": current_version.status,
                "created_at": current_version.created_at,
                "updated_at": current_version.updated_at,
                "updated_by": current_version.updated_by
            } if current_version else None,
            "versions": [
                {
                    "onboarding_flow_version_id": v.onboarding_flow_version_id,
                    "data": v.data,
                    "version": v.version,
                    "status": v.status,
                    "created_at": v.created_at,
                    "updated_at": v.updated_at,
                    "updated_by": v.updated_by
                } for v in all_versions
            ]
            
        }

    @staticmethod
    def update_onboarding_flow_data(version_id: str, data: OnboardingFlowUpdate) -> OnboardingFlowVersionResponse:
        """Update the data content of an onboarding flow version."""
        version = OnboardingFlowVersion.nodes.get_or_none(onboarding_flow_version_id=version_id)
        if not version:
            raise ValueError(f"OnboardingFlowVersion {version_id} not found")
        
        if data.data is not None:
            # Ensure all questions have IDs
            processed_data = _ensure_question_ids(data.data)
            version.data = processed_data
            
            # Re-link assets: disconnect old, connect new
            version.uses_assets.disconnect_all()
            _link_assets_to_version(version, processed_data)
        
        if data.updated_by:
            version.updated_by = data.updated_by
            
        version.updated_at = version.updated_at  # Force update timestamp if handled by neomodel, or set explicitly if needed
        # Assuming DateTimeProperty(default_now=True) handles creation, for updates we might need manual set if not auto-updating on save
        # But typically we just save.
        version.save()
        
        # We need to traverse back to the container to return the full response structure if we wanted, 
        # but here we return a specific version response.
        # To get the container ID, we can traverse relationships.
        onboarding_flow = version.onboarding_flow.single()
        key = onboarding_flow.key if onboarding_flow else "unknown"
        flow_id = onboarding_flow.onboarding_flow_id if onboarding_flow else "unknown"

        return OnboardingFlowVersionResponse(
            onboarding_flow_version_id=version.onboarding_flow_version_id,
            onboarding_flow_id=flow_id,
            key=key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at
        )
