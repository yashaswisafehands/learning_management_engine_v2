from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks

from app.repositories.resources import ResourceRepository
from app.schemas.assets import AssetBaseSchema
from app.schemas.resources import (ResourceBaseSchema, ResourcePostRequestData,
                                   ResourceSchema, ResourceUpdateRequestData,
                                   ResourceVersionSchema)
from app.utils.executors import run_sync


def _pick_single(rel):
    """Return a single related node from a neomodel relationship or value.

    Tries in order: .single(), .first(), .one(), first of .all(), else returns rel itself.
    """
    if rel is None:
        return None
    # Relationship managers
    for attr in ("single", "first", "one"):
        func = getattr(rel, attr, None)
        if callable(func):
            try:
                node = func()
                if node is not None:
                    return node
            except Exception:
                pass
    all_func = getattr(rel, "all", None)
    if callable(all_func):
        try:
            seq = all_func()
            if isinstance(seq, (list, tuple)) and seq:
                return seq[0]
        except Exception:
            pass
    # Already a node or unsupported manager; return as-is
    return rel


def _extract_icon_id(source) -> Optional[str]:
    """Resolve icon identifier from either a model instance or schema."""
    if source is None:
        return None

    icon_attr = getattr(source, "icon", None)
    if isinstance(icon_attr, AssetBaseSchema):
        return icon_attr.asset_id
    if isinstance(icon_attr, str):
        return icon_attr

    resolved = _pick_single(icon_attr)
    if isinstance(resolved, AssetBaseSchema):
        return resolved.asset_id
    if resolved is not None:
        return getattr(resolved, "asset_id", None)
    return None


def _version_to_schema(rv) -> ResourceVersionSchema:
    lang = _pick_single(getattr(rv, "language", None))
    icon_asset = _pick_single(getattr(rv, "icon", None))
    content_asset = _pick_single(getattr(rv, "content", None))
    # Normalize created_at to ISO string (schema type is datetime but tests may expect serializable value)
    _created_at = getattr(rv, "created_at", None)
    if isinstance(_created_at, datetime):
        created_at_str = _created_at.isoformat()
    else:
        created_at_str = str(_created_at) if _created_at is not None else None

    return ResourceVersionSchema(
        resource_version_id=rv.resource_version_id,
        title=getattr(rv, "title", None),
        language_id=getattr(lang, "language_id", None),
        language_name=getattr(lang, "language_name", None),
        region=getattr(rv, "region", None),
        description=getattr(rv, "description", None),
        content_type=getattr(rv, "content_type", None),
        version=getattr(rv, "version", None),
        status=getattr(rv, "status", None),
        created_at=created_at_str,
        created_by=getattr(rv, "created_by", None) or "System",
        is_deleted=getattr(rv, "is_deleted", False),
        icon=(getattr(icon_asset, "asset_id", None) if icon_asset else None),
        content=(
            AssetBaseSchema.model_validate(content_asset, from_attributes=True)
            if content_asset
            else None
        ),
    )


def _resource_to_schema(
    resource,
    versions: Optional[list[ResourceVersionSchema]],
    orig,
    adapted: list,
    translated: list,
) -> ResourceSchema:
    # Derive a representative version for top-level title/description (prefer original current, else any version)
    representative = orig or (versions[0] if versions else None)
    title = getattr(representative, "title", None) if representative else None
    icon_id = _extract_icon_id(representative)
    return ResourceSchema(
        resource_id=getattr(resource, "resource_id", None),
        title=title or getattr(resource, "title", None) or "",
        description=(
            getattr(representative, "description", None) if representative else None
        ),
        icon=icon_id,
        slug=getattr(resource, "slug", None),
        tag=getattr(resource, "tag", None),
        versions=versions or [],
        current_original_version=_version_to_schema(orig) if orig else None,
        current_adapted_versions=[_version_to_schema(a) for a in (adapted or [])],
        current_translated_versions=[_version_to_schema(t) for t in (translated or [])],
    )


def _resource_to_base_schema(resource, best_fit) -> ResourceBaseSchema:
    """Project a minimal ResourceBaseSchema from a Resource and its best-fit version.

    - resource_id, slug, tag come from the Resource node
    - version comes from best_fit.version (defaults to 1.0 when absent)
    - icon is the asset_id string from best_fit.icon relation
    - content is AssetBaseSchema built from best_fit.content relation
    """
    icon_id: Optional[str] = None
    content_schema: Optional[AssetBaseSchema] = None
    version_value: float = 1.0

    if best_fit is None:
        pass
    elif isinstance(best_fit, ResourceVersionSchema):
        version_value = best_fit.version or 1.0
        icon_id = best_fit.icon
        content_schema = best_fit.content
    elif isinstance(best_fit, dict):
        version_value = float(best_fit.get("version", 1.0) or 1.0)
        icon_id = best_fit.get("icon_id")
        content_id = best_fit.get("content_id")
        content_filename = best_fit.get("content_filename")
        if content_id and content_filename:
            content_schema = AssetBaseSchema(
                asset_id=content_id,
                filename=content_filename,
            )
    else:
        icon_asset = _pick_single(getattr(best_fit, "icon", None))
        if icon_asset:
            icon_id = getattr(icon_asset, "asset_id", None)
        content_asset = _pick_single(getattr(best_fit, "content", None))
        if content_asset:
            content_schema = AssetBaseSchema.model_validate(
                content_asset,
                from_attributes=True,
            )
        version_value = getattr(best_fit, "version", 1.0) or 1.0

    if not icon_id:
        icon_asset = _pick_single(getattr(resource, "icon", None))
        if icon_asset:
            icon_id = getattr(icon_asset, "asset_id", None)

    return ResourceBaseSchema(
        resource_id=resource.resource_id,
        slug=resource.slug,
        tag=getattr(resource, "tag", None),
        version=version_value,
        icon=icon_id,
        content=content_schema,
    )


def _version_snapshot_to_schema(snapshot: Dict[str, Any]) -> ResourceVersionSchema:
    created_at = snapshot.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            created_at = datetime.utcnow()
    elif created_at is None:
        created_at = datetime.utcnow()

    content_asset = None
    if snapshot.get("content_id") and snapshot.get("content_filename"):
        content_asset = AssetBaseSchema(
            asset_id=snapshot["content_id"],
            filename=snapshot["content_filename"],
        )

    return ResourceVersionSchema(
        resource_version_id=snapshot["resource_version_id"],
        title=snapshot.get("title") or "",
        language_id=snapshot.get("language_id"),
        language_name=snapshot.get("language_name"),
        region=snapshot.get("region"),
        description=snapshot.get("description"),
        content_type=snapshot.get("content_type") or "original",
        version=float(snapshot.get("version") or 0.0),
        status=snapshot.get("status") or "draft",
        created_at=created_at,
        created_by=snapshot.get("created_by") or "System",
        is_deleted=bool(snapshot.get("is_deleted", False)),
        icon=snapshot.get("icon_id"),
        content=content_asset,
    )


def _compose_resource_schema_from_snapshot(
    resource, snapshot: Dict[str, Any]
) -> ResourceSchema:
    version_schemas = [
        _version_snapshot_to_schema(row) for row in snapshot.get("versions", []) if row
    ]

    version_schemas.sort(key=lambda v: v.version, reverse=True)

    by_id = {version.resource_version_id: version for version in version_schemas}

    def _collect(order_ids: list[str]) -> list[ResourceVersionSchema]:
        result: list[ResourceVersionSchema] = []
        for version_id in order_ids or []:
            version = by_id.get(version_id)
            if version and version not in result:
                result.append(version)
        return result

    current_original = next(
        (
            by_id.get(version_id)
            for version_id in snapshot.get("current_original_ids", [])
            if version_id in by_id
        ),
        None,
    )
    current_adapted = _collect(snapshot.get("current_adapted_ids", []))
    current_translated = _collect(snapshot.get("current_translated_ids", []))

    representative = current_original or (
        version_schemas[0] if version_schemas else None
    )

    title = (
        representative.title
        if representative and representative.title
        else getattr(resource, "title", None) or ""
    )
    description = representative.description if representative else None
    icon = representative.icon if representative else None

    return ResourceSchema(
        resource_id=resource.resource_id,
        title=title,
        description=description,
        icon=icon,
        slug=resource.slug,
        tag=getattr(resource, "tag", None),
        versions=version_schemas,
        current_original_version=current_original,
        current_adapted_versions=current_adapted,
        current_translated_versions=current_translated,
    )


# Using centralized run_sync from app.utils.executors


async def create_resource(
    resource_data: ResourcePostRequestData, tag: str, background_tasks: BackgroundTasks
) -> ResourceSchema:
    resource = await run_sync(ResourceRepository.create_resource, resource_data, tag)
    orig, adapted, translated = await run_sync(
        ResourceRepository.get_current_versions, resource
    )
    return _resource_to_schema(
        resource,
        [],
        orig,
        adapted,
        translated,
    )


async def get_all_resources(
    content_type: Optional[str] = None,
    language_id: Optional[str] = None,
    include_versions: bool = False,
):
    resources = await run_sync(
        ResourceRepository.get_resources, content_type, language_id, None
    )
    if include_versions:
        resource_ids = [r.resource_id for r in resources]
        if not resource_ids:
            return []
        snapshots = await run_sync(
            ResourceRepository.get_resources_with_versions,
            resource_ids,
            content_type,
            language_id,
        )
        snapshot_map = {item["resource"].resource_id: item for item in snapshots}
        aggregated: list[ResourceSchema] = []
        for r in resources:
            snapshot = snapshot_map.get(r.resource_id)
            if not snapshot:
                continue
            aggregated.append(_compose_resource_schema_from_snapshot(r, snapshot))
        return aggregated

    result: list[ResourceBaseSchema] = []
    for r in resources:
        # Project minimal ResourceBaseSchema using best-fit version
        best = await run_sync(
            ResourceRepository.get_best_fit_version,
            r.resource_id,
            language_id,
            None,
        )
        if not best:
            # If a language filter is requested, do not fallback to other types; skip this resource
            if language_id:
                continue
            # Fallback to latest available version (any status), optionally filtered by content_type
            snapshot = await run_sync(
                ResourceRepository.get_resources_with_versions,
                [r.resource_id],
                content_type,
                language_id,
            )
            if snapshot:
                versions = snapshot[0].get("versions", [])
                versions.sort(
                    key=lambda row: float(row.get("version", 0.0) or 0.0),
                    reverse=True,
                )
                best_row = versions[0] if versions else None
                best = _version_snapshot_to_schema(best_row) if best_row else None
        result.append(_resource_to_base_schema(r, best))
    return result


async def get_resource_by_id(
    resource_id: str, language_id: Optional[str] = None, region: Optional[str] = None
) -> ResourceSchema:
    resource = await run_sync(
        ResourceRepository.get_resource_by_id, resource_id, language_id, region
    )
    orig, adapted, translated = await run_sync(
        ResourceRepository.get_current_versions, resource
    )
    return _resource_to_schema(
        resource,
        [],
        orig,
        adapted,
        translated,
    )


async def update_resource(
    resource_id: str, data: ResourceUpdateRequestData, background_tasks: BackgroundTasks
) -> ResourceSchema:
    resource, new_version = await run_sync(ResourceRepository.update_resource, resource_id, data)
    orig, adapted, translated = await run_sync(
        ResourceRepository.get_current_versions, resource
    )
    new_version_schema = _version_to_schema(new_version) if new_version else None
    versions_list = [new_version_schema] if new_version_schema else []
    return _resource_to_schema(
        resource,
        versions_list,
        orig,
        adapted,
        translated,
    )


async def get_all_versions_by_resource_id(resource_id: str) -> list[ResourceSchema]:
    """Get all versions of a resource irrespective of type or status"""
    versions = await run_sync(
        ResourceRepository.get_all_versions_by_resource_id, resource_id
    )
    # Minimal projection for versions list: map each version to ResourceVersionSchema
    resource = await run_sync(ResourceRepository.get_resource_by_id, resource_id)
    return [
        ResourceSchema(
            resource_id=resource_id,
            title=getattr(v, "title", "") or getattr(resource, "title", "") or "Untitled",
            slug=resource.slug,
            tag=resource.tag,
            versions=[_version_to_schema(v)],
        )
        for v in versions
    ]


async def update_resource_status(resource_version_id: str, status_update):
    """Update resource version status and return the updated version schema"""
    updated = await run_sync(
        ResourceRepository.update_resource_status,
        resource_version_id,
        status_update.status,
        getattr(status_update, "updated_by", None) or "System",
    )
    return _version_to_schema(updated)
