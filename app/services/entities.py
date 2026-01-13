from typing import List, Union

from fastapi import BackgroundTasks

from app.repositories.entities import EntityRepository
from app.repositories.key_learning_points import KeyLearningPointRepository
from app.repositories.resources import ResourceRepository
from app.schemas.categories import CategorySchema
from app.schemas.entities import (EntitiyResponseSchema, EntityCreateSchema,
                                  EntityPatchSchema)
from app.schemas.key_learning_points import KeyLearningPointSchema
from app.schemas.languages import LanguageSchema
from app.schemas.modules import ModuleSchema
from app.schemas.resources import ResourceSchema
from app.schemas.transcriptions import TranscriptionResponse
from app.schemas.translations import TranslationSchema
from app.schemas.settings_screen import ScreenDataResponse
from app.services import categories as category_service
from app.services import languages as languages_service
from app.services import modules as modules_service
from app.services import resources as resources_service
from app.services import transcriptions as transcriptions_service
from app.services import translations as translations_service
from app.services import key_learning_points as key_learning_points_service
from app.services import settings_screen as settings_screen_service
from app.utils.executors import run_sync

async def list_entities() -> List[EntitiyResponseSchema]:
    return await run_sync(EntityRepository.get_entities)


async def create_entity(
    data: EntityCreateSchema, background_tasks: BackgroundTasks
) -> EntitiyResponseSchema:
    return await run_sync(EntityRepository.create_entity, data)


async def update_entity(
    entity_id: str, payload: EntityPatchSchema, background_tasks: BackgroundTasks
) -> EntitiyResponseSchema:
    return await run_sync(EntityRepository.patch_entity, entity_id, payload)


async def list_entities_by_kind(
    kind: str,
) -> Union[
    List[EntitiyResponseSchema],
    List[LanguageSchema],
    List[ModuleSchema],
    List[CategorySchema],
    List[ResourceSchema],
    List[TranslationSchema],
    List[KeyLearningPointSchema],
    List[TranscriptionResponse],
    List[ScreenDataResponse],
]:

    if kind == "language":
        return await languages_service.get_languages("all", include_versions=True)
    elif kind == "category":
        return await category_service.list_categories(
            status_filter="all", include_versions=True
        )
    elif kind == "module":
        return await modules_service.list_modules(
            status_filter="all", include_versions=True
        )
    elif kind == "resource":
        return await resources_service.get_all_resources(
            include_versions=True
        )
    elif kind == "transcription":
        return await transcriptions_service.get_all_transcriptions()
        
    elif kind == "translation":
        return await translations_service.get_translations(
            include_versions=True
        )
    elif kind == "key_learning_point":
        return await key_learning_points_service.get_key_learning_points(
            include_versions=True
        )
    elif kind == "settings_screen":
        return await settings_screen_service.get_settings_screens(
            include_versions=True
        )   
    else:
        return []
