from typing import Optional

from fastapi import BackgroundTasks

from app.repositories.modules import ModuleRepository
from app.schemas.modules import (ModuleBaseSchema, ModuleCreateRequest,
                                 ModuleSchema, ModuleStatusUpdateRequest,
                                 ModuleUpdateRequest, ModuleVersionSchema)
from app.schemas.resources import ResourceWithOrderSchema
from app.services.assets import _asset_to_schema, generate_container_sas_url
from app.utils.executors import run_sync
from app.utils.slug import build_slug


def _version_to_schema(
    module_version, 
    slug: str, 
    language_id: Optional[str] = None, 
    sas_token: Optional[str] = None
) -> ModuleVersionSchema:
    if module_version is None:
        raise ValueError("module_version cannot be None")

    icon_rel = getattr(module_version, "icon", None)
    icon = icon_rel.single() if icon_rel and hasattr(icon_rel, "single") else None
    icon_id = getattr(icon, "asset_id", None) if icon else None

    def _map_rel(rel_manager: str) -> list[ResourceWithOrderSchema]:
        manager = getattr(module_version, rel_manager, None)
        if manager is None or not hasattr(manager, "all"):
            return []
        try:
            relations = manager.all()
        except Exception:
            return []
        if not relations:
            return []

        ordered_items: list[tuple[float, ResourceWithOrderSchema]] = []
        for idx, res in enumerate(relations):
            # res is a Resource node
            rel = (
                manager.relationship(res) if hasattr(manager, "relationship") else None
            )
            order_attr = getattr(rel, "order", None) if rel else None
            sort_key = (
                float(order_attr)
                if isinstance(order_attr, (int, float))
                else float(idx + 1)
            )
            display_order = (
                int(order_attr) if isinstance(order_attr, (int, float)) else idx + 1
            )
            
            # Logic to find the best version for the language
            target_version = None
            
            # 1. Try to find an active translation for this language
            if language_id:
                # We need to filter manually or via python because we are in an object traversal
                # res.current_translated_versions is a relation
                try:
                    translations = res.current_translated_versions.all()
                    for t in translations:
                        # t is ResourceVersion
                        if t.status == 'active': # Ensure it is active
                            lang_rel = t.language.single()
                            if lang_rel and lang_rel.language_id == language_id:
                                target_version = t
                                break
                except Exception:
                    pass

            # 2. Fallback to current original version
            if not target_version:
                try:
                    target_version = res.current_original_version.single()
                except Exception:
                    pass
            
            # 3. If still nothing (e.g. no original set?), maybe use res metadata?
            # But we need asset content which is on Version.
            
            content_schema = None
            icon_schema = None
            description = getattr(res, "description", None)
            summary = getattr(res, "summary", None) # Resource might usually not have summary, mapped from desc
            version_val = None
            
            if target_version:
                title = getattr(target_version, "title", None) or getattr(res, "title", None)
                description = getattr(target_version, "description", None) or description
                version_val = getattr(target_version, "version", None)
                
                # Inflate Content Asset
                try:
                    content_asset_rel = getattr(target_version, "content", None)
                    content_asset = content_asset_rel.single() if content_asset_rel else None
                    if content_asset:
                        content_schema = _asset_to_schema(content_asset, sas_token=sas_token)
                except Exception:
                    pass
                    
                # Inflate Icon Asset
                try:
                    icon_asset_rel = getattr(target_version, "icon", None)
                    icon_asset = icon_asset_rel.single() if icon_asset_rel else None
                    if icon_asset:
                         icon_schema = _asset_to_schema(icon_asset, sas_token=sas_token)
                except Exception:
                    pass
            else:
                title = getattr(res, "title", None)

            ordered_items.append(
                (
                    sort_key,
                    ResourceWithOrderSchema(
                        resource_id=getattr(res, "resource_id", None),
                        title=title,
                        tag=getattr(res, "tag", None),
                        order=display_order,
                        summary=summary,
                        description=description,
                        version=version_val,
                        content=content_schema,
                        icon=icon_schema
                    ),
                )
            )
        ordered_items.sort(key=lambda item: item[0])
        return [schema for _, schema in ordered_items]

    def _map_klps():
        """Map key learning points to KeyLearningPointResponse objects"""
        from app.schemas.key_learning_points import KeyLearningPointResponse
        
        manager = getattr(module_version, "key_learning_points", None)
        if manager is None or not hasattr(manager, "all"):
            return []
        try:
            klps = manager.all()
        except Exception:
            return []
        if not klps:
            return []
        
        klp_schemas = []
        for klp in klps:
            # Get the KLP container to access the level
            container = klp.container.single() if hasattr(klp, "container") else None
            level = getattr(container, "level", None) if container else None
            
            # Get questions
            questions = []
            if hasattr(klp, "questions"):
                try:
                    from app.schemas.key_learning_points import KLPQuestionResponse, KLPAnswerResponse
                    for question in klp.questions.all():
                        answers = []
                        if hasattr(question, "answers"):
                            for answer in question.answers.all():
                                answers.append(KLPAnswerResponse(
                                    answer_id=answer.answer_id,
                                    value=getattr(answer, "value", ""),
                                    correct=getattr(answer, "correct", False),
                                    order=getattr(answer, "order", None),
                                ))
                        questions.append(KLPQuestionResponse(
                            question_id=question.question_id,
                            question=getattr(question, "question", ""),
                            quizz_type=getattr(question, "quizz_type", ""),
                            icon=getattr(question, "icon", None),
                            link=getattr(question, "link", None),
                            show_toggle=getattr(question, "show_toggle", False),
                            essential=getattr(question, "essential", False),
                            description=getattr(question, "description", None),
                            order=getattr(question, "order", None),
                            answers=answers,
                        ))
                except Exception:
                    pass
            
            klp_schemas.append(KeyLearningPointResponse(
                klp_id=getattr(klp, "klp_version_id", None) or getattr(klp, "klp_id", ""),
                title=getattr(klp, "title", None),
                version=getattr(klp, "version", None),
                level=level,
                description=getattr(klp, "description", None),
                questions=questions,
            ))
        return klp_schemas

    return ModuleVersionSchema(
        module_version_id=module_version.module_version_id,
        title=module_version.title,
        slug=slug,
        description=module_version.description,
        version=module_version.version,
        status=getattr(module_version, "status", None) or "draft",
        created_at=module_version.created_at,
        created_by=module_version.created_by or "System",
        is_deleted=module_version.is_deleted,
        icon=icon_id,
        videos=_map_rel("videos"),
        action_cards=_map_rel("action_cards"),
        practical_procedures=_map_rel("practical_procedures"),
        drugs=_map_rel("drugs"),
        key_learning_points=_map_klps()
    )


def _version_to_base(module_version) -> ModuleBaseSchema:
    module_rel = getattr(module_version, "module", None)
    parent = (
        module_rel.single() if module_rel and hasattr(module_rel, "single") else None
    )
    slug = (
        parent.slug
        if parent
        else build_slug("mod", getattr(module_version, "title", None))
    )
    module_id = (
        parent.module_id if parent else getattr(module_version, "module_version_id", "")
    )
    icon_rel = getattr(module_version, "icon", None)
    icon = icon_rel.single() if icon_rel and hasattr(icon_rel, "single") else None
    icon_id = getattr(icon, "asset_id", None) if icon else None
    return ModuleBaseSchema(
        module_id=module_id,
        title=module_version.title,
        slug=slug,
        description=module_version.description,
        version=module_version.version,
        icon=icon_id,
    )


def _module_to_schema(
    module, 
    language_id: Optional[str] = None, 
    sas_token: Optional[str] = None
) -> ModuleSchema:
    versions = module.versions.all()
    versions_sorted = sorted(
        versions, key=lambda v: getattr(v, "version", 0), reverse=True
    )
    versions_schema = [
        _version_to_schema(version, module.slug, language_id=language_id, sas_token=sas_token) 
        for version in versions_sorted
    ]

    current_version = None
    try:
        current_version = module.current_version_rel.single()
    except Exception:
        current_version = None
    current_schema = (
        _version_to_schema(current_version, module.slug, language_id=language_id, sas_token=sas_token) 
        if current_version else None
    )

    source_version = current_version or (
        versions_sorted[0] if versions_sorted else None
    )

    icon_id = None
    if source_version is not None:
        icon_rel = getattr(source_version, "icon", None)
        if icon_rel and hasattr(icon_rel, "single"):
            icon_asset = icon_rel.single()
            icon_id = getattr(icon_asset, "asset_id", None)

    description = (
        getattr(source_version, "description", None)
        if source_version is not None
        else None
    )

    title = (
        getattr(source_version, "title", None) or getattr(module, "title", None) or ""
    )

    return ModuleSchema(
        module_id=module.module_id,
        title=title,
        slug=module.slug,
        description=description,
        icon=icon_id,
        versions=versions_schema,
        current_version=current_schema,
    )


# Using centralized run_sync from app.utils.executors


async def create_module(
    data: ModuleCreateRequest, background_tasks: BackgroundTasks
) -> ModuleSchema:
    version = await run_sync(ModuleRepository.create_module, data)
    parent = version.module.single()
    return _module_to_schema(parent)


async def list_modules(
    status_filter: str = "published",
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    include_versions: bool = False,
) -> list:
    items = await run_sync(
        ModuleRepository.get_modules, status_filter, limit, offset, include_versions
    )
    if include_versions:
        return [_module_to_schema(m) for m in items]
    return [_version_to_base(v) for v in items]


async def get_module_by_id(module_id: str, language_id: Optional[str] = None) -> ModuleSchema:
    # Use latest version to ensure we capture current pointer semantics and satisfy tests
    latest_version = await run_sync(
        ModuleRepository.get_latest_version_by_module_id, module_id
    )
    parent = latest_version.module.single()
    
    # Generate SAS token for full access
    sas_token = await generate_container_sas_url(only_token=True)
    
    return _module_to_schema(parent, language_id=language_id, sas_token=sas_token)


async def update_module(
    module_id: str, data: ModuleUpdateRequest, background_tasks: BackgroundTasks
) -> ModuleSchema:
    version = await run_sync(ModuleRepository.update_module, module_id, data)
    parent = version.module.single()
    return _module_to_schema(parent)


async def update_module_status(
    module_version_id: str, status_update: ModuleStatusUpdateRequest
) -> ModuleVersionSchema:
    version = await run_sync(
        ModuleRepository.update_module_status,
        module_version_id,
        status_update.status,
        status_update.updated_by,
    )
    parent = version.module.single()
    slug = parent.slug if parent else build_slug("mod", getattr(version, "title", None))
    return _version_to_schema(version, slug)


async def get_modules_by_language(language_id: str) -> list[ModuleVersionSchema]:
    """Get active modules for a language."""
    versions = await run_sync(ModuleRepository.get_modules_by_language_id, language_id)
    
    # Generate SAS token
    sas_token = await generate_container_sas_url(only_token=True)
    
    results = []
    for v in versions:
        # We need the parent module to get the slug
        module_rel = getattr(v, "module", None)
        parent = module_rel.single() if module_rel and hasattr(module_rel, "single") else None
        slug = parent.slug if parent else build_slug("mod", getattr(v, "title", None))
        results.append(_version_to_schema(v, slug, language_id=language_id, sas_token=sas_token))
        
    return results
