from typing import Optional, Union
from fastapi import APIRouter, BackgroundTasks, Query, Depends
from app.core.auth import validate_token

from typing_extensions import Literal

from app.schemas.resources import (ResourceBaseSchema, ResourcePostRequestData,
                                   ResourceSchema, ResourceStatusUpdateRequest,
                                   ResourceUpdateRequestData,
                                   ResourceVersionSchema)
from app.services import resources as resources_service

router = APIRouter(prefix="/resources", tags=["Resources"], dependencies=[Depends(validate_token)])


@router.post("/{tag}/", response_model=ResourceSchema)
async def create_resource(
    tag: str,
    resource_data: ResourcePostRequestData,
    background_tasks: BackgroundTasks = None,
):
    return await resources_service.create_resource(resource_data, tag, background_tasks)


@router.get(
    "/",
    response_model=Union[list[ResourceBaseSchema], list[ResourceSchema]],
)
async def get_all_resources(
    content_type: Optional[Literal["original", "adapted", "translated"]] = Query(
        None,
        description=(
            "Filter by content type (original, adapted, translated). "
            "If None: prefer translated, then adapted, else original."
        ),
    ),
    language_id: Optional[str] = Query(None, description="Filter by language ID"),
    include_versions: bool = Query(
        False,
        description=(
            "When true, returns all versions for each resource (rich ResourceSchema)."
        ),
    ),
):
    return await resources_service.get_all_resources(
        content_type=content_type,
        language_id=language_id,
        include_versions=include_versions,
    )


@router.get("/{resource_id}", response_model=ResourceSchema)
async def get_resource_by_id(
    resource_id: str,
    language_id: Optional[str] = Query(
        None, description="Preferred language for content"
    ),
    region: Optional[str] = Query(None, description="Preferred region for content"),
):
    return await resources_service.get_resource_by_id(
        resource_id=resource_id, language_id=language_id, region=region
    )


@router.patch("/{resource_id}", response_model=ResourceSchema)
async def update_resource(
    resource_id: str,
    resource_data: ResourceUpdateRequestData,
    background_tasks: BackgroundTasks = None,
):
    return await resources_service.update_resource(
        resource_id=resource_id, data=resource_data, background_tasks=background_tasks
    )


@router.get("/{resource_id}/versions", response_model=list[ResourceSchema])
async def get_all_versions_by_resource_id(resource_id: str):
    """Get all versions of a resource irrespective of type or status"""
    return await resources_service.get_all_versions_by_resource_id(resource_id)


@router.patch("/version/{id}/status", response_model=ResourceVersionSchema)
async def update_resource_status(
    id: str,
    status_update: ResourceStatusUpdateRequest,
):
    return await resources_service.update_resource_status(id, status_update)
