from app.models.settings_screen import ScreenData, ScreenDataVersion
from app.models.languages import Language
from app.models.assets import Asset
from app.schemas.settings_screen import ScreenDataVersionCreate, ScreenDataVersionResponse, ScreenDataUpdate
from typing import Set, Union, List


def _extract_screen_data_asset_ids(data: Union[dict, list, None]) -> Set[str]:
    """
    Extract asset IDs from screen data JSON.
    Looks for 'content', 'translated_content', and 'icon' fields.
    
    Args:
        data: The screen data (list of items or dict)
        
    Returns:
        Set of unique asset IDs found in the data
    """
    asset_ids: Set[str] = set()
    
    if data is None:
        return asset_ids
    
    if isinstance(data, list):
        for item in data:
            asset_ids.update(_extract_screen_data_asset_ids(item))
    elif isinstance(data, dict):
        # Check for asset reference fields
        for field in ['content', 'translated_content', 'icon']:
            if field in data and data[field]:
                value = data[field]
                if isinstance(value, str):
                    # Extract asset_id (handle "asset_id.extension" format)
                    asset_id = value.split('.')[0] if '.' in value else value
                    asset_ids.add(asset_id)
        
        # Recurse into nested structures
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                asset_ids.update(_extract_screen_data_asset_ids(value))
    
    return asset_ids


def _link_screen_data_assets_to_version(version: ScreenDataVersion, data: Union[dict, list, None]) -> List[str]:
    """
    Extract asset IDs from data and create USES_ASSET relationships.
    
    Args:
        version: The ScreenDataVersion node
        data: The screen data JSON
        
    Returns:
        List of asset IDs that were successfully linked
    """
    asset_ids = _extract_screen_data_asset_ids(data)
    linked_ids = []
    
    for asset_id in asset_ids:
        asset = Asset.nodes.get_or_none(asset_id=asset_id)
        if asset:
            version.uses_assets.connect(asset)
            linked_ids.append(asset_id)
    
    return linked_ids


class ScreenDataRepository:
    @staticmethod
    def create_screen_data(language_id: str, data: ScreenDataVersionCreate) -> ScreenDataVersionResponse:
        """Create a new screen data version.
        
        This creates a new version every time it's called. The version is created as 'draft'
        and needs to be manually set as current using set_current_version().
        """
        # Get Language directly
        language = Language.nodes.get_or_none(language_id=language_id)
        if not language:
            raise ValueError(f"Language {language_id} not found")

        # Define the monolithic key for this language's screen data
        # This ensures one container per language
        key = f"screen_data_{language.language_id}"
        
        # Find or create ScreenData container
        screen_data = ScreenData.nodes.get_or_none(key=key)
        if not screen_data:
            screen_data = ScreenData(key=key).save()
        
        # Get the latest version number
        existing_versions = list(screen_data.versions.all())
        if existing_versions:
            latest_version = max(v.version for v in existing_versions)
            new_version_number = latest_version + 0.1
        else:
            new_version_number = 1.0
        
        # Create new ScreenDataVersion (as draft)
        version = ScreenDataVersion(
            data=data.data,
            version=new_version_number,
            status="draft",
            created_by=data.updated_by or "System",
            updated_by=data.updated_by
        ).save()
        
        # Extract and link assets from the JSON data
        _link_screen_data_assets_to_version(version, data.data)
        
        # Link version to container
        screen_data.versions.connect(version)
        
        # Link container to Language (only if not already connected)
        # This avoids cardinality violation when adding new versions to existing container
        if not language.screen_data.is_connected(screen_data):
            language.screen_data.connect(screen_data)
        
        return ScreenDataVersionResponse(
            screen_data_version_id=version.screen_data_version_id,
            data_id=screen_data.data_id,
            key=screen_data.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by
        )
    
    @staticmethod
    def set_current_version(data_id: str, version_id: str) -> ScreenDataVersionResponse:
        """Set a specific version as the current version for screen data."""
        screen_data = ScreenData.nodes.get_or_none(data_id=data_id)
        if not screen_data:
            raise ValueError(f"ScreenData {data_id} not found")
        
        version = ScreenDataVersion.nodes.get_or_none(screen_data_version_id=version_id)
        if not version:
            raise ValueError(f"ScreenDataVersion {version_id} not found")
        
        # Disconnect old current version
        screen_data.current_version.disconnect_all()
        
        # Set new current version
        screen_data.current_version.connect(version)
        
        # Update version status to active
        version.status = "active"
        version.save()
        
        return ScreenDataVersionResponse(
            screen_data_version_id=version.screen_data_version_id,
            data_id=screen_data.data_id,
            key=screen_data.key,
            data=version.data,
            version=version.version,
            status=version.status,
            created_at=version.created_at,
            updated_at=version.updated_at,
            updated_by=version.updated_by
        )

    @staticmethod
    def get_screen_data(data_id: str):
        """Get screen data with all its versions."""
        screen_data = ScreenData.nodes.get_or_none(data_id=data_id)
        if not screen_data:
            raise ValueError(f"ScreenData {data_id} not found")
        
        current_version = screen_data.current_version.single()
        all_versions = list(screen_data.versions.all())
        
        return {
            "data_id": screen_data.data_id,
            "key": screen_data.key,
            "current_version": {
                "screen_data_version_id": current_version.screen_data_version_id,
                "data": current_version.data,
                "version": current_version.version,
                "status": current_version.status,
                "created_at": current_version.created_at,
                "updated_at": current_version.updated_at,
                "updated_by": current_version.updated_by
            } if current_version else None,
            "versions": [
                {
                    "screen_data_version_id": v.screen_data_version_id,
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
    def update_screen_data_data(version_id: str, data: ScreenDataUpdate) -> ScreenDataVersionResponse:
        """Update the data content of a screen data version."""
        version = ScreenDataVersion.nodes.get_or_none(screen_data_version_id=version_id)
        if not version:
            raise ValueError(f"ScreenDataVersion {version_id} not found")
        
        if data.data is not None:
            version.data = data.data
            
            # Re-link assets: disconnect old, connect new
            version.uses_assets.disconnect_all()
            _link_screen_data_assets_to_version(version, data.data)
            
        if data.updated_by:
            version.updated_by = data.updated_by
            
        version.save()
        
        screen_data = version.screen_data.single()
        key = screen_data.key if screen_data else "unknown"
        data_id = screen_data.data_id if screen_data else "unknown"
        
        updated_by=version.updated_by
        

    @staticmethod
    def get_all_screen_data():
        """Get all screen data with all versions."""
        all_screen_data = ScreenData.nodes.all()
        
        result = []
        for screen_data in all_screen_data:
            current_version = screen_data.current_version.single()
            all_versions = list(screen_data.versions.all())
            
            result.append({
                "data_id": screen_data.data_id,
                "key": screen_data.key,
                "current_version": {
                    "screen_data_version_id": current_version.screen_data_version_id,
                    "data": current_version.data,
                    "version": current_version.version,
                    "status": current_version.status,
                    "created_at": current_version.created_at,
                    "updated_at": current_version.updated_at,
                    "updated_by": current_version.updated_by
                } if current_version else None,
                "versions": [
                    {
                        "screen_data_version_id": v.screen_data_version_id,
                        "data": v.data,
                        "version": v.version,
                        "status": v.status,
                        "created_at": v.created_at,
                        "updated_at": v.updated_at,
                        "updated_by": v.updated_by
                    } for v in all_versions
                ]
            })
        return result
