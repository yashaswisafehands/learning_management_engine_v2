from typing import Literal, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, HTTPException

from app.schemas.languages import (LanguageCreateRequest, LanguagesBaseSchema,
                                   LanguageSchema, LanguageStatusUpdateRequest,
                                   LanguageUpdateRequest,
                                   LanguageVersionSchema,
                                   ModuleEnableDisableRequest, DisabledModuleResponse,
                                   ResourceEnableDisableRequest, DisabledResourceResponse)
from app.schemas.settings_screen import ScreenDataVersionCreate, ScreenDataVersionResponse, ScreenDataUpdate
from app.schemas.transcriptions import (TranscriptionVersionCreate,
                                        TranscriptionVersionResponse, TranscriptionUpdate)
from app.schemas.modules import ModuleVersionSchema
from app.services import languages as languages_service
from app.services.settings_screen import ScreenDataService
from app.services.transcriptions import TranscriptionService
from app.services import modules as modules_service
from app.repositories.onboarding_flows import OnboardingFlowRepository
from app.schemas.onboarding_flows import (OnboardingFlowVersionCreate,
                                          OnboardingFlowVersionResponse, OnboardingFlowUpdate)

from app.core.auth import validate_token

router = APIRouter(prefix="/languages", tags=["Languages"], dependencies=[Depends(validate_token)])


@router.post("/", response_model=LanguagesBaseSchema)
async def create_language(
    data: LanguageCreateRequest, background_tasks: BackgroundTasks
) -> LanguagesBaseSchema:
    return await languages_service.create_language(data, background_tasks)


@router.get("/", response_model=Union[list[LanguagesBaseSchema], list[LanguageSchema]])
async def get_languages(
    status_filter: Literal["active", "all"] = "active",
    limit: Optional[int] = Query(
        None, ge=1, le=200, description="Max items to return (1-200)"
    ),
    offset: Optional[int] = Query(
        None,
        ge=0,
        description="Items to skip before starting to collect the result set",
    ),
    include_versions: bool = Query(
        False, description="When true, returns all versions for each language"
    ),
):
    """Get languages filtered by version status.

    Query parameters:
    - status_filter: "active" (default) - only languages with active versions
                    "all" - all languages regardless of version status
    """
    return await languages_service.get_languages(
        status_filter, limit=limit, offset=offset, include_versions=include_versions
    )


@router.get(
    "/all-versions", response_model=list[LanguageSchema], include_in_schema=False
)
async def get_all_languages_versions():
    """Get all languages with their versions"""
    return await languages_service.get_all_languages_versions()


@router.get("/{id}", response_model=LanguageSchema)
async def get_language_by_id(id: str):
    """Get a single language with all its versions by language ID"""
    return await languages_service.get_language_by_id(id)


@router.patch("/{id}", response_model=LanguageVersionSchema)
async def update_language(
    id: str,
    payload: LanguageUpdateRequest,
):
    """Update a language by creating a new version. The {id} should be the language_id from LanguageSchema."""
    return await languages_service.update_language(language_id=id, payload=payload)


@router.patch("/version/{id}/status", response_model=LanguageVersionSchema)
async def update_language_status(
    id: str,
    status_update: LanguageStatusUpdateRequest,
):
    """Update the status of a language version"""
    return await languages_service.update_language_status(
        language_version_id=id, status_update=status_update
    )


@router.post("/{language_id}/transcript", response_model=TranscriptionVersionResponse)
async def create_transcript(language_id: str, transcript_data: TranscriptionVersionCreate):
    """Create a new transcription version (as draft) for a language."""
    return TranscriptionService.create_transcription(
        language_id=language_id, data=transcript_data
    )


@router.patch("/transcript/{transcription_id}/version/{version_id}")
async def set_current_transcription_version(transcription_id: str, version_id: str):
    """Set a specific version as the current version for a transcription."""
    return TranscriptionService.set_current_version(transcription_id, version_id)


@router.patch("/transcript/version/{version_id}/data", response_model=TranscriptionVersionResponse)
async def update_transcription_data(version_id: str, data: TranscriptionUpdate):
    """Update the data content of a transcription version."""
    return TranscriptionService.update_transcription_data(version_id, data)


@router.post("/{language_id}/settings_screen_data", response_model=ScreenDataVersionResponse)
async def create_screendata(language_id: str, screen_data: ScreenDataVersionCreate):
    """Create a new screen data version (as draft) for a language."""
    return ScreenDataService.create_screen_data(
        language_id=language_id, data=screen_data
    )


@router.patch("/screen_data/{data_id}/version/{version_id}")
async def set_current_screen_data_version(data_id: str, version_id: str):
    """Set a specific version as the current version for screen data."""
    return ScreenDataService.set_current_version(data_id, version_id)


@router.patch("/screen_data/version/{version_id}/data", response_model=ScreenDataVersionResponse)
async def update_screen_data_data(version_id: str, data: ScreenDataUpdate):
    """Update the data content of a screen data version."""
    return ScreenDataService.update_screen_data_data(version_id, data)


@router.post("/{language_id}/onboarding_flow", response_model=OnboardingFlowVersionResponse)
async def create_onboarding_flow(language_id: str, flow_data: OnboardingFlowVersionCreate):
    """Create a new onboarding flow version (as draft) for a language."""
    return OnboardingFlowRepository.create_onboarding_flow(
        language_id=language_id, data=flow_data
    )


@router.patch("/onboarding_flow/{flow_id}/version/{version_id}")
async def set_current_onboarding_flow_version(flow_id: str, version_id: str):
    """Set a specific version as the current version for onboarding flow."""
    return OnboardingFlowRepository.set_current_version(flow_id, version_id)


@router.patch("/onboarding_flow/version/{version_id}/data", response_model=OnboardingFlowVersionResponse)
async def update_onboarding_flow_data(version_id: str, data: OnboardingFlowUpdate):
    """Update the data content of an onboarding flow version."""
    return OnboardingFlowRepository.update_onboarding_flow_data(version_id, data)





@router.get("/{id}/transcriptions")
async def get_transcriptions(id: str):
    """Get all transcription versions for a language."""
    # 1. Get language to find the key
    language = await languages_service.get_language_by_id(id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    
    # 2. Construct key
    key = f"transcription_{id}"
    
    # 3. Find container
    from app.models.transcriptions import Transcription
    container = Transcription.nodes.get_or_none(key=key)
    if not container:
        return {"transcription_id": None, "key": key, "versions": []}
        
    # 4. Get versions
    return TranscriptionService.get_transcription(container.transcription_id)


@router.get("/{id}/settings_screen_data")
async def get_screen_data(id: str):
    """Get all screen data versions for a language."""
    # 1. Get language to find the key
    language = await languages_service.get_language_by_id(id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    
    # 2. Construct key
    key = f"screen_data_{id}"
    
    # 3. Find container
    from app.models.settings_screen import ScreenData
    container = ScreenData.nodes.get_or_none(key=key)
    if not container:
        return {"data_id": None, "key": key, "versions": []}
        
    # 4. Get versions
    return ScreenDataService.get_screen_data(container.data_id)


@router.get("/{id}/onboarding_flow")
async def get_onboarding_flow(id: str):
    """Get all onboarding flow versions for a language."""
    # 1. Get language to find the key
    language = await languages_service.get_language_by_id(id)
    if not language:
        raise HTTPException(status_code=404, detail="Language not found")
    
    # 2. Construct key
    key = f"onboarding_{id}"
    
    # 3. Find container
    from app.models.onboarding_flows import OnboardingFlow
    container = OnboardingFlow.nodes.get_or_none(key=key)
    if not container:
        return {"onboarding_flow_id": None, "key": key, "versions": []}
        
    # 4. Get versions
    return OnboardingFlowRepository.get_onboarding_flow(container.onboarding_flow_id)


@router.get("/{id}/modules", response_model=list[ModuleVersionSchema])
async def get_modules(id: str):
    """Get active modules for a language."""
    return await modules_service.get_modules_by_language(id)


@router.patch("/{language_id}/modules/{module_id}/status")
async def set_module_status(
    language_id: str, 
    module_id: str, 
    request: ModuleEnableDisableRequest
):
    """Enable or disable a module for a specific language.
    
    When a module is disabled for a language, it won't appear in that language's manifest.
    By default, all modules are enabled. Only explicitly disabled modules are filtered out.
    """
    return await languages_service.set_module_status_for_language(
        language_id=language_id,
        module_id=module_id,
        enabled=request.enabled,
        updated_by=request.updated_by or "System"
    )


@router.get("/{language_id}/disabled-modules", response_model=list[DisabledModuleResponse])
async def get_disabled_modules(language_id: str):
    """Get list of modules that are disabled for a specific language.
    
    Returns all modules that have been explicitly disabled for this language.
    These modules won't appear in the language's manifest.
    """
    return await languages_service.get_disabled_modules(language_id)


@router.patch("/{language_id}/resources/{resource_id}/status")
async def set_resource_status(
    language_id: str, 
    resource_id: str, 
    request: ResourceEnableDisableRequest
):
    """Enable or disable a resource for a specific language.
    
    When a resource is disabled for a language, it won't appear in that language's manifest.
    By default, all resources are enabled. Only explicitly disabled resources are filtered out.
    """
    return await languages_service.set_resource_status_for_language(
        language_id=language_id,
        resource_id=resource_id,
        enabled=request.enabled,
        updated_by=request.updated_by or "System"
    )


@router.get("/{language_id}/disabled-resources", response_model=list[DisabledResourceResponse])
async def get_disabled_resources(language_id: str):
    """Get list of resources that are disabled for a specific language.
    
    Returns all resources that have been explicitly disabled for this language.
    These resources won't appear in the language's manifest.
    """
    return await languages_service.get_disabled_resources(language_id)

