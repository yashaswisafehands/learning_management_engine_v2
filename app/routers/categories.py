from typing import Literal, Optional, Union

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.params import Query

from app.core.auth import validate_token
from app.schemas.categories import (CategoryBaseSchema, CategoryCreateRequest,
                                    CategorySchema,
                                    CategoryStatusUpdateRequest,
                                    CategoryUpdateRequest,
                                    CategoryVersionSchema)
from app.services import categories as categories_service

router = APIRouter(prefix="/categories", tags=["Categories"], dependencies=[Depends(validate_token)])


@router.post("/", response_model=CategorySchema)
async def create_category(
    category_data: CategoryCreateRequest,
    background_tasks: BackgroundTasks = None,
):
    return await categories_service.create_category(category_data, background_tasks)


@router.patch("/{id}/", response_model=CategorySchema)
async def update_category_modules(
    id: str,
    update_data: CategoryUpdateRequest,
):
    updated_category = await categories_service.update_category(
        category_id=id, payload=update_data, background_tasks=BackgroundTasks()
    )

    if updated_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return updated_category


@router.get("/", response_model=Union[list[CategorySchema], list[CategoryBaseSchema]])
async def get_categories(
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
        False, description="When true, returns all versions for each category"
    ),
):
    return await categories_service.list_categories(
        status_filter=status_filter,
        limit=limit,
        offset=offset,
        include_versions=include_versions,
    )


@router.get("/{id}/", response_model=CategorySchema)
async def get_category(id: str):
    category = await categories_service.get_category_by_id(id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.patch("/version/{id}/status", response_model=CategoryVersionSchema)
async def update_category_status(id: str, status_update: CategoryStatusUpdateRequest):
    return await categories_service.update_category_status(id, status_update)
