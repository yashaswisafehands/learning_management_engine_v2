from typing import Optional

from fastapi import BackgroundTasks

from app.repositories.categories import CategoryRepository
from app.schemas.categories import (CategoryBaseSchema, CategoryCreateRequest,
                                    CategorySchema,
                                    CategoryStatusUpdateRequest,
                                    CategoryUpdateRequest,
                                    CategoryVersionSchema)
from app.schemas.modules import ModuleBaseSchema
from app.utils.executors import run_sync


def _category_version_to_version_schema(category_version) -> CategoryVersionSchema:
    """Map a CategoryVersion node to CategoryVersionSchema."""
    # Icon
    icon_asset = category_version.icon.single()
    icon_id = icon_asset.asset_id if icon_asset else None

    # Modules as ModuleBaseSchema
    modules: list[ModuleBaseSchema] = []
    for module_rel in category_version.modules.all():
        current_module_version = module_rel.current_version_rel.single()
        if current_module_version:
            modules.append(
                ModuleBaseSchema(
                    module_id=module_rel.module_id,
                    title=current_module_version.title,
                    slug=module_rel.slug,
                    description=current_module_version.description,
                    version=current_module_version.version,
                )
            )

    return CategoryVersionSchema(
        category_version_id=category_version.category_version_id,
        title=category_version.title,
        description=category_version.description,
        created_at=category_version.created_at,
        created_by=category_version.created_by or "System",
        is_deleted=category_version.is_deleted,
        version=category_version.version,
        status=getattr(category_version, "status", None) or "draft",
        icon=icon_id,
        modules=modules,
    )


def _category_version_to_base_schema(category_version) -> CategoryBaseSchema:
    """Create a flattened CategoryBaseSchema from a CategoryVersion + its parent Category."""
    parent_category = category_version.category.single()
    slug = (
        parent_category.slug
        if parent_category
        else f"cat-{category_version.title.lower().replace(' ', '-')}"
    )
    category_id = (
        parent_category.category_id
        if parent_category
        else category_version.category_version_id
    )

    ver_schema = _category_version_to_version_schema(category_version)
    return CategoryBaseSchema(
        category_id=category_id,
        title=ver_schema.title,
        slug=slug,
        description=ver_schema.description,
        version=ver_schema.version,
        icon=ver_schema.icon,
        modules=ver_schema.modules,
    )


def _category_to_schema(category) -> CategorySchema:
    """Create CategorySchema containing latest 'version' and 'current_version' fields."""
    versions = []
    try:
        versions = category.versions.all()
    except Exception:
        pass
    latest_version = max(versions, key=lambda v: v.version) if versions else None
    current_version = None
    try:
        current_version = category.current_version_rel.single()
    except Exception:
        pass
    # Return ALL versions, sorted by version number descending
    versions_list: list[CategoryVersionSchema] = [
        _category_version_to_version_schema(v) 
        for v in sorted(versions, key=lambda v: v.version, reverse=True)
    ]

    # Pick a source version for top-level fields
    source = latest_version or current_version
    icon_id = None
    if source is not None:
        try:
            icon_asset = source.icon.single()
            icon_id = getattr(icon_asset, "asset_id", None)
        except Exception:
            pass

    return CategorySchema(
        category_id=getattr(category, "category_id", None),
        slug=getattr(category, "slug", None),
        title=(
            getattr(source, "title", None) or getattr(category, "title", None) or ""
        ),
        description=(
            getattr(source, "description", None)
            or getattr(category, "description", None)
        ),
        icon=icon_id,
        version=(getattr(latest_version, "version", None) if latest_version else None),
        versions=versions_list or None,
        current_version=(
            _category_version_to_version_schema(current_version)
            if current_version
            else None
        ),
    )


# Using centralized run_sync from app.utils.executors


async def create_category(
    data: CategoryCreateRequest, background_tasks: BackgroundTasks
) -> CategorySchema:
    category_version = await run_sync(CategoryRepository.create_category, data)
    # For create/update we continue returning a flattened base view for the just-created version
    return _category_to_schema(category_version.category.single())


async def update_category(
    category_id: str, payload: CategoryUpdateRequest, background_tasks: BackgroundTasks
) -> CategorySchema:
    category_version = await run_sync(
        CategoryRepository.update_category, category_id, payload
    )
    return _category_to_schema(category_version.category.single())


async def list_categories(
    # Status filter now uses "active" instead of legacy "published".
    # Accepts: "active" (only active versions) or "all" (latest/current regardless of status)
    status_filter: str = "active",
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    include_versions: bool = False,
) -> list:
    items = await run_sync(
        CategoryRepository.get_categories,
        # Backward compatibility: if caller still sends 'published', treat as 'active'
        "active" if status_filter == "published" else status_filter,
        limit,
        offset,
        include_versions,
    )

    if include_versions:
        # items are Category nodes; map to CategorySchema with current/latest versions
        return [_category_to_schema(cat) for cat in items]
    else:
        # items are CategoryVersion nodes; map to flattened base schema
        return [_category_version_to_base_schema(cv) for cv in items]


async def get_category_by_id(category_id: str) -> CategorySchema:
    """Return the latest version of a category as CategorySchema.

    We reuse the repository's latest-version helper to avoid returning a raw Category node.
    """
    latest_version = await run_sync(
        CategoryRepository.get_latest_version_by_category_id, category_id
    )
    # Convert to full Category schema with current/latest versions
    parent_category = latest_version.category.single()
    return _category_to_schema(parent_category)


async def update_category_status(
    category_version_id: str, status_update: CategoryStatusUpdateRequest
) -> CategoryVersionSchema:
    version = await run_sync(
        CategoryRepository.update_category_status,
        category_version_id,
        status_update.status,
        status_update.updated_by,
    )
    return _category_version_to_version_schema(version)
