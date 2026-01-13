from typing import List, Union

from fastapi import APIRouter, BackgroundTasks, Body, Depends

from app.core.auth import validate_token
from app.schemas.categories import CategorySchema
from app.schemas.entities import (EntitiyResponseSchema, EntityCreateSchema,
                                  EntityPatchSchema)
from app.schemas.key_learning_points import KeyLearningPointSchema
from app.schemas.languages import LanguageSchema
from app.schemas.modules import ModuleSchema
from app.schemas.resources import ResourceSchema
from app.schemas.translations import TranslationSchema
from app.services.entities import (create_entity, list_entities,
                                   list_entities_by_kind, update_entity)

router = APIRouter(prefix="/entities", tags=["Entities"], dependencies=[Depends(validate_token)])


@router.get(
    "/",
    response_model=Union[
        List[EntitiyResponseSchema],
        List[LanguageSchema],
        List[ModuleSchema],
        List[CategorySchema],
        List[ResourceSchema],
        List[TranslationSchema],
        List[KeyLearningPointSchema],
    ],
)
async def get_entities(kind: str = None):
    if kind:
        return await list_entities_by_kind(kind=kind)
    return await list_entities()


@router.post("/", response_model=EntitiyResponseSchema)
async def post_entity(entity: EntityCreateSchema):
    return await create_entity(entity, BackgroundTasks)


@router.patch("/{id}", response_model=EntitiyResponseSchema)
async def patch_entities(
    id: str,
    payload: EntityPatchSchema = Body(...),
):
    return await update_entity(
        entity_id=id, payload=payload, background_tasks=BackgroundTasks
    )
