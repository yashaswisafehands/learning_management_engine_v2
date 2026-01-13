from fastapi import BackgroundTasks

from app.repositories.languages import LanguageRepository
from app.schemas.languages import (LanguageCreateRequest, LanguagesBaseSchema,
                                   LanguageSchema, LanguageStatusUpdateRequest,
                                   LanguageVersionSchema)
from app.utils.executors import run_sync
from app.utils.neo4j_rel import safe_relationship_all
from app.utils.slug import build_language_slug


def _extract_category_ids(language_version) -> list[str]:
    """Return ordered category ids for a language version."""

    categories = safe_relationship_all(
        getattr(language_version, "categories", None),
        "USES_CATEGORY",
    )
    output: list[str] = []
    for category in categories:
        if isinstance(category, str):
            output.append(category)
            continue
        if isinstance(category, dict):
            cid = category.get("category_id") or category.get("id")
            if cid:
                output.append(str(cid))
            continue
        cid = getattr(category, "category_id", None) or getattr(category, "id", None)
        if cid is not None:
            output.append(str(cid))
    return output


def _language_version_to_schema(language_version) -> LanguageVersionSchema:
    """Transform a LanguageVersion model instance to LanguageVersionSchema"""
    # Get icon asset_id
    icon_id = None
    icon_asset = language_version.icon.single()
    if icon_asset:
        icon_id = icon_asset.asset_id

    # Get the parent Language node for slug and language_name
    parent_language = language_version.language.single()
    if parent_language:
        slug = parent_language.slug or build_language_slug(
            language_version.country,
            parent_language.language_name,
        )
        language_name = parent_language.language_name or "Unknown Language"
    else:
        slug = build_language_slug(language_version.country, None)
        language_name = "Unknown Language"  # fallback

    category_ids = _extract_category_ids(language_version)

    return LanguageVersionSchema(
        language_version_id=language_version.language_version_id,
        slug=slug,
        language_name=language_name,
        autonym_script=language_version.autonym_script or "",
        learning_platform=bool(language_version.learning_platform),
        country=language_version.country or "Unknown Country",
        country_code=language_version.country_code or "",
        region=language_version.region or "",
        latitude=language_version.latitude,
        longitude=language_version.longitude,
        version=language_version.version,
        status=language_version.status,
        created_at=language_version.created_at,
        created_by=language_version.created_by or "System",
        is_deleted=language_version.is_deleted,
        icon=icon_id,
        categories=category_ids,
    )


def _language_to_languages_base_schema(language_version) -> LanguagesBaseSchema:
    """Transform a LanguageVersion model instance to LanguagesBaseSchema"""
    # Get icon asset
    icon_asset = None
    icon = language_version.icon.single()
    if icon:
        # For LanguagesBaseSchema, icon should be asset_id string, not AssetSchema
        icon_asset = icon.asset_id

    # Get the parent Language node for slug and language_name
    parent_language = language_version.language.single()
    if parent_language:
        language_id = parent_language.language_id
        slug = parent_language.slug or build_language_slug(
            language_version.country,
            parent_language.language_name,
        )
        language_name = parent_language.language_name or "Unknown Language"
    else:
        language_id = language_version.language_version_id
        slug = build_language_slug(language_version.country, None)
        language_name = "Unknown Language"  # fallback

    # Extract only category IDs
    category_ids = []
    category_ids = _extract_category_ids(language_version)

    return LanguagesBaseSchema(
        language_id=language_id,
        slug=slug,
        language_name=language_name,
        autonym_script=language_version.autonym_script or "",
        country=language_version.country or "Unknown Country",
        country_code=language_version.country_code or "",
        latitude=language_version.latitude,
        longitude=language_version.longitude,
        icon=icon_asset,
        categories=category_ids,
    )


# using centralized run_sync


async def get_languages(
    status_filter: str = "active",
    *,
    limit: int | None = None,
    offset: int | None = None,
    include_versions: bool = False,
):
    """Get languages list.

    - When include_versions is False (default): returns summary list (LanguagesBaseSchema)
    - When include_versions is True: returns full LanguageSchema per language (all versions)
    """
    if include_versions:
        # Delegate to existing all-versions aggregation and let repository build per-language payloads
        return await get_all_languages_versions()

    # Summary list flow (original behavior)
    if limit is None and offset is None:
        languages = await run_sync(LanguageRepository.get_languages, status_filter)
    else:
        languages = await run_sync(
            LanguageRepository.get_languages, status_filter, limit, offset
        )
    return [_language_to_languages_base_schema(lang) for lang in languages]


async def create_language(
    data: LanguageCreateRequest, background_tasks: BackgroundTasks
) -> LanguagesBaseSchema:
    language = await run_sync(LanguageRepository.create_language, data)
    return _language_to_languages_base_schema(language)


async def get_all_languages_versions() -> list[LanguageSchema]:
    """Get all languages with their versions"""
    return await run_sync(LanguageRepository.get_all_languages_versions)


async def get_language_by_id(language_id: str) -> LanguageSchema:
    """Get a single language with all its versions by language ID"""
    return await run_sync(LanguageRepository.get_language_by_id, language_id)


async def update_language(
    language_id: str, payload: LanguageCreateRequest
) -> LanguageVersionSchema:
    language = await run_sync(LanguageRepository.update_language, language_id, payload)
    return _language_version_to_schema(language)


async def update_language_status(
    language_version_id: str, status_update: LanguageStatusUpdateRequest
) -> LanguageVersionSchema:
    """Update the status of a language version"""
    language_version = await run_sync(
        LanguageRepository.update_language_status,
        language_version_id,
        status_update.status,
        status_update.updated_by,
    )
    return _language_version_to_schema(language_version)


async def set_module_status_for_language(
    language_id: str, module_id: str, enabled: bool, updated_by: str = "System"
) -> dict:
    """Enable or disable a module for a specific language.
    
    Args:
        language_id: The language ID
        module_id: The module ID
        enabled: True to enable (remove from blacklist), False to disable (add to blacklist)
        updated_by: User who made the change
        
    Returns:
        Dict with status of the operation
    """
    if enabled:
        result = await run_sync(
            LanguageRepository.enable_module_for_language, language_id, module_id
        )
        action = "enabled"
        message = "Module was already enabled" if not result else "Module enabled successfully"
    else:
        result = await run_sync(
            LanguageRepository.disable_module_for_language, language_id, module_id, updated_by
        )
        action = "disabled"
        message = "Module was already disabled" if not result else "Module disabled successfully"
    
    return {
        "language_id": language_id,
        "module_id": module_id,
        "enabled": enabled,
        "action": action,
        "changed": result,
        "message": message
    }


async def get_disabled_modules(language_id: str) -> list[dict]:
    """Get list of disabled modules for a language."""
    return await run_sync(
        LanguageRepository.get_disabled_modules_for_language, language_id
    )


async def set_resource_status_for_language(
    language_id: str, resource_id: str, enabled: bool, updated_by: str = "System"
) -> dict:
    """Enable or disable a resource for a specific language.
    
    Args:
        language_id: The language ID
        resource_id: The resource ID
        enabled: True to enable (remove from blacklist), False to disable (add to blacklist)
        updated_by: User who made the change
        
    Returns:
        Dict with status of the operation
    """
    if enabled:
        result = await run_sync(
            LanguageRepository.enable_resource_for_language, language_id, resource_id
        )
        action = "enabled"
        message = "Resource was already enabled" if not result else "Resource enabled successfully"
    else:
        result = await run_sync(
            LanguageRepository.disable_resource_for_language, language_id, resource_id, updated_by
        )
        action = "disabled"
        message = "Resource was already disabled" if not result else "Resource disabled successfully"
    
    return {
        "language_id": language_id,
        "resource_id": resource_id,
        "enabled": enabled,
        "action": action,
        "changed": result,
        "message": message
    }


async def get_disabled_resources(language_id: str) -> list[dict]:
    """Get list of disabled resources for a language."""
    return await run_sync(
        LanguageRepository.get_disabled_resources_for_language, language_id
    )

