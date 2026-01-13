from typing import Literal, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Query, Depends

from app.core.auth import validate_token
from app.schemas.key_learning_points import (
    KeyLearningPointBaseSchema, KeyLearningPointCreateRequest,
    KeyLearningPointSchema, KeyLearningPointStatusUpdateRequest,
    KeyLearningPointUpdateRequest, KeyLearningPointVersionSchema)
from app.services import key_learning_points as klp_service

router = APIRouter(prefix="/klps", tags=["Key Learning Points"], dependencies=[Depends(validate_token)])


@router.post("/", response_model=KeyLearningPointSchema)
async def create_klp(
    klp_data: KeyLearningPointCreateRequest,
    background_tasks: BackgroundTasks = None,
):
    """Create a new Key Learning Point."""
    return await klp_service.create_klp(klp_data, background_tasks)


@router.get(
    "/",
    response_model=Union[
        list[KeyLearningPointSchema], list[KeyLearningPointBaseSchema]
    ],
)
async def get_klps(
    status_filter: Literal["active", "all"] = "active",
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: Optional[int] = Query(None, ge=0),
    include_containers: bool = Query(
        False, description="When true, returns full container objects with all versions"
    ),
):
    """Get list of Key Learning Points."""
    return await klp_service.list_klps(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        include_containers=include_containers,
    )


@router.get("/{id}", response_model=KeyLearningPointSchema)
async def get_klp_by_id(id: str):
    """Get a specific Key Learning Point by ID."""
    return await klp_service.get_klp_by_id(klp_id=id)


@router.patch("/{id}", response_model=KeyLearningPointSchema)
async def update_klp(
    id: str,
    klp_data: KeyLearningPointUpdateRequest,
    background_tasks: BackgroundTasks = None,
):
    """Update a Key Learning Point (creates new version)."""
    return await klp_service.update_klp(
        klp_id=id, data=klp_data, background_tasks=background_tasks
    )


@router.patch("/versions/{id}/status", response_model=KeyLearningPointVersionSchema)
async def update_klp_status(
    id: str,
    status_update: KeyLearningPointStatusUpdateRequest,
):
    """Update the status of a specific KLP version."""
    return await klp_service.update_klp_status(id, status_update)
