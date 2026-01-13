from typing import Literal, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Query, Depends

from app.core.auth import validate_token
from app.schemas.modules import (ModuleBaseSchema, ModuleCreateRequest,
                                 ModuleSchema, ModuleStatusUpdateRequest,
                                 ModuleUpdateRequest, ModuleVersionSchema)
from app.services import modules as modules_service

router = APIRouter(prefix="/modules", tags=["Modules"], dependencies=[Depends(validate_token)])


@router.post("/", response_model=ModuleSchema)
async def create_module(
    module_data: ModuleCreateRequest,
    background_tasks: BackgroundTasks = None,
):
    return await modules_service.create_module(module_data, background_tasks)


@router.get("/", response_model=Union[list[ModuleSchema], list[ModuleBaseSchema]])
async def get_modules(
    status_filter: Literal["active", "all"] = "active",
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: Optional[int] = Query(None, ge=0),
    include_versions: bool = Query(
        False, description="When true, returns all versions for each module"
    ),
):
    return await modules_service.list_modules(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        include_versions=include_versions,
    )


@router.patch("/{id}", response_model=ModuleSchema)
async def update_module(
    id: str,
    module_data: ModuleUpdateRequest,
    background_tasks: BackgroundTasks = None,
):
    return await modules_service.update_module(
        module_id=id, data=module_data, background_tasks=background_tasks
    )


@router.get("/{id}", response_model=ModuleSchema)
async def get_module_by_id(
    id: str,
    language_id: Optional[str] = Query(None, description="Language ID for localized resources"),
):
    return await modules_service.get_module_by_id(module_id=id, language_id=language_id)


@router.patch("/version/{id}/status", response_model=ModuleVersionSchema)
async def update_module_status(
    id: str,
    status_update: ModuleStatusUpdateRequest,
):
    return await modules_service.update_module_status(id, status_update)
