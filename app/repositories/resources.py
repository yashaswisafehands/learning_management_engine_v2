from typing import List, Optional, Tuple

from neomodel import db
from neomodel.exceptions import DoesNotExist

from app.models.assets import Asset  # noqa: F401
from app.models.languages import Language
from app.models.resources import Resource, ResourceVersion
from app.repositories.assets import AssetRepository
from app.schemas.resources import (ResourcePostRequestData,
                                   ResourceUpdateRequestData)
from app.utils.neo4j_rel import (relationship_type_exists,
                                 safe_relationship_all,
                                 safe_relationship_first)
from app.utils.slug import build_slug
from app.utils.version_utils import increment_version


class ResourceRepository:
    # ---------------------- Internal helpers ---------------------- #

    @staticmethod
    def _determine_creation_dimensions(
        data: ResourcePostRequestData,
    ) -> tuple[str, str]:
        """Return (content_type, region) for a new resource version.

        Rules:
        - If data.content_type explicitly provided -> trust but validate combinations.
        - If not provided: infer
            * no language_id & no region -> original
            * region & no language_id -> adapted
            * language_id present -> translated
        - Region defaults to 'GLOBAL' for original & adapted when not passed.
        - Translated versions do not force a region (keep passed region or None).
        Validation:
        - translated requires language_id
        - adapted optionally supplies region (defaults to GLOBAL)
        - original must not include language_id
        """
        explicit = getattr(data, "content_type", None)
        language_id = getattr(data, "language_id", None)
        region = getattr(data, "region", None)

        if explicit:
            if explicit not in {"original", "adapted", "translated"}:
                raise ValueError(
                    f"Invalid content_type '{explicit}'. Must be one of original|adapted|translated"
                )
            if explicit == "translated" and not language_id:
                raise ValueError("language_id is required for translated resources")
            if explicit == "original" and language_id:
                raise ValueError(
                    "language_id should not be set when creating an original resource"
                )
            if explicit == "adapted" and not region:
                region = "GLOBAL"
            if explicit in {"original", "adapted"} and not region:
                # normalize missing region to GLOBAL for these types
                region = "GLOBAL"
            return explicit, region

        # Infer content_type
        if not language_id and not region:
            return "original", "GLOBAL"
        if region and not language_id:
            return "adapted", region or "GLOBAL"
        # language_id present -> translated
        if language_id:
            return "translated", region  # region may be None for translated
        # Fallback (should not trigger)
        return "original", "GLOBAL"

    @staticmethod
    def get_resource_by_id(
        resource_id: str,
        language_id: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Resource:
        try:
            resource = Resource.nodes.get(resource_id=resource_id)
            return resource
        except DoesNotExist:
            raise ValueError(f"Resource with ID '{resource_id}' not found")

    @staticmethod
    def get_best_fit_version(
        resource_id: str,
        language_id: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Optional[ResourceVersion]:
        """Return best-fit active version: translated > adapted > original.

        This implementation relies on the current pointer relationships instead of issuing
        broad MATCH queries, drastically reducing the number of database round-trips on
        hot paths. When ``language_id`` is provided but ``region`` is not, we attempt to
        derive the relevant region from the language's current version.
        """

        def _is_active(version: Optional[ResourceVersion]) -> bool:
            return bool(version) and getattr(version, "status", None) == "active"

        def _language_matches(version: ResourceVersion, expected_id: str) -> bool:
            rel = getattr(version, "language", None)
            if not rel:
                return False
            try:
                lang = rel.single() if hasattr(rel, "single") else None
            except Exception:
                lang = None
            if lang is None:
                return False
            return getattr(lang, "language_id", None) == expected_id

        def _derive_region(lang_id: Optional[str]) -> Optional[str]:
            if not lang_id:
                return None
            try:
                lang = Language.nodes.get(language_id=lang_id)
                current_lv = lang.current_version_rel.single()
                if current_lv:
                    return getattr(current_lv, "region", None)
            except Language.DoesNotExist:  # type: ignore[attr-defined]
                return None
            except Exception:
                return None
            return None

        try:
            resource = ResourceRepository.get_resource_by_id(resource_id)
        except ValueError:
            return None
        derived_region = region if region is not None else _derive_region(language_id)

        current_original, current_adapted, current_translated = (
            ResourceRepository.get_current_versions(resource)
        )

        # Prioritise translated version that matches the requested language
        if language_id:
            translated_candidates = [
                version
                for version in (current_translated or [])
                if _is_active(version) and _language_matches(version, language_id)
            ]
            if translated_candidates:
                return max(
                    translated_candidates,
                    key=lambda v: getattr(v, "version", 0.0) or 0.0,
                )

        # Fall back to adapted version with matching region (or GLOBAL when requested)
        adapted_candidates: List[ResourceVersion] = []
        if current_adapted:
            target_region = derived_region or "GLOBAL"
            for version in current_adapted:
                if not _is_active(version):
                    continue
                region_value = getattr(version, "region", None) or "GLOBAL"
                if (
                    derived_region is None
                    or target_region == "GLOBAL"
                    or region_value == target_region
                ):
                    adapted_candidates.append(version)
        if adapted_candidates:
            return max(
                adapted_candidates,
                key=lambda v: getattr(v, "version", 0.0) or 0.0,
            )

        # Finally, return the current original version when active
        if _is_active(current_original):
            return current_original

        return None

    @staticmethod
    def get_current_versions(
        resource: Resource,
    ) -> Tuple[Optional[ResourceVersion], List[ResourceVersion], List[ResourceVersion]]:
        orig = safe_relationship_first(
            resource.current_original_version, "CURRENT_ORIGINAL"
        )
        adapted = safe_relationship_all(
            resource.current_adapted_versions, "CURRENT_ADAPTATION"
        )
        translated = safe_relationship_all(
            resource.current_translated_versions, "CURRENT_TRANSLATION"
        )
        return orig, adapted or [], translated

    @staticmethod
    def create_resource(data: ResourcePostRequestData, tag: str) -> Resource:
        slug = build_slug("res", tag, data.title)

        existing_resources = Resource.nodes.filter(slug=slug)
        if existing_resources:
            raise ValueError(f"Resource with slug '{slug}' already exists")

        resource = Resource(
            title=data.title,
            slug=slug,
            tag=tag,
            is_deleted=False,
        ).save()

        # Determine content_type & region per new schema fields
        content_type, region = ResourceRepository._determine_creation_dimensions(data)

        resource_version = ResourceVersion(
            title=data.title,
            description=data.description,
            content_type=content_type,
            region=region,
            status="draft",
            version=1.0,
            created_by=getattr(data, "created_by", None) or "System",
        ).save()

        # Link icon/content assets to version
        if data.icon:
            icon_asset = AssetRepository.get_asset_by_id(data.icon)
            resource_version.icon.connect(icon_asset)
        if data.content:
            content_asset = AssetRepository.get_asset_by_id(data.content)
            resource_version.content.connect(content_asset)

        # Link language relation when translated
        if content_type == "translated" and getattr(data, "language_id", None):
            try:
                lang = Language.nodes.get(language_id=data.language_id)
                resource_version.language.connect(lang)
            except Language.DoesNotExist:  # type: ignore[attr-defined]
                raise ValueError(
                    f"Language with ID '{data.language_id}' does not exist"
                )

        # Link version to resource (HAS_VERSION)
        resource.versions.connect(resource_version)

        return resource

    @staticmethod
    def update_resource(resource_id: str, data: ResourceUpdateRequestData) -> Resource:
        resource = ResourceRepository.get_resource_by_id(resource_id)

        # Determine content type
        content_type = getattr(data, "content_type", None)
        if not content_type:
            if not data.language_id and not data.region:
                content_type = "original"
            elif data.region and not data.language_id:
                content_type = "adapted"
            else:
                content_type = "translated"

        # Compute new version number based on existing versions of same type/dimension
        params = {
            "rid": resource.resource_id,
            "ct": content_type,
            "region": data.region or "GLOBAL",
        }
        if content_type == "translated":
            params["language_id"] = data.language_id
            version_query = """
                MATCH (r:Resource {resource_id:$rid})-[:HAS_VERSION]->(rv:ResourceVersion)
                OPTIONAL MATCH (rv)-[:IN_LANGUAGE]->(lang:Language)
                WHERE rv.content_type=$ct AND (lang.language_id = $language_id)
                RETURN rv
                ORDER BY rv.version DESC
                LIMIT 1
                """
        elif content_type == "adapted":
            version_query = """
                MATCH (r:Resource {resource_id:$rid})-[:HAS_VERSION]->(rv:ResourceVersion)
                WHERE rv.content_type=$ct AND rv.region=$region
                RETURN rv
                ORDER BY rv.version DESC
                LIMIT 1
                """
        else:
            version_query = """
                MATCH (r:Resource {resource_id:$rid})-[:HAS_VERSION]->(rv:ResourceVersion)
                WHERE rv.content_type=$ct
                RETURN rv
                ORDER BY rv.version DESC
                LIMIT 1
                """
        vres, _ = db.cypher_query(version_query, params)
        last_version = ResourceVersion.inflate(vres[0][0]) if vres else None
        if last_version:
            new_version = increment_version(last_version.version)
        else:
            new_version = 1.0

        source_version = last_version
        if source_version is None:
            try:
                source_version = resource.current_original_version.single()
            except Exception:
                source_version = None
            if source_version is None:
                existing_versions = resource.versions.all()
                if existing_versions:
                    source_version = existing_versions[0]

        title_value = (
            data.title
            if data.title is not None
            else (
                getattr(source_version, "title", None) or getattr(resource, "title", "")
            )
        )
        if not title_value:
            raise ValueError("Title is required for resource versions")

        if data.title:
            resource.title = data.title

        description_value = (
            data.description
            if data.description is not None
            else getattr(source_version, "description", None)
        )

        if content_type == "translated":
            region_value = (
                data.region
                if data.region is not None
                else getattr(last_version, "region", None)
            )
        else:
            region_value = (
                data.region
                if data.region is not None
                else getattr(last_version, "region", None)
            )
            if not region_value and source_version is not None:
                region_value = getattr(source_version, "region", None)
            if not region_value:
                region_value = "GLOBAL"

        resource_version = ResourceVersion(
            title=title_value,
            description=description_value,
            content_type=content_type,
            region=region_value,
            status="draft",
            version=new_version,
            created_by=data.__dict__.get("created_by", "System") or "System",
        ).save()

        # Link language for translated
        if content_type == "translated" and data.language_id:
            try:
                lang = Language.nodes.get(language_id=data.language_id)
                resource_version.language.connect(lang)
            except Language.DoesNotExist:  # type: ignore[attr-defined]
                raise ValueError(
                    f"Language with ID '{data.language_id}' does not exist"
                )

        # Handle icon/content assets on version
        if data.icon:
            icon_asset = AssetRepository.get_asset_by_id(data.icon)
            resource_version.icon.connect(icon_asset)
        if data.content:
            content_asset = AssetRepository.get_asset_by_id(data.content)
            resource_version.content.connect(content_asset)

        # Derivation link
        if data.derived_from_id:
            try:
                base = ResourceVersion.nodes.get(
                    resource_version_id=data.derived_from_id
                )
                resource_version.derived_from.connect(base)
            except ResourceVersion.DoesNotExist:  # type: ignore[attr-defined]
                pass

        resource.versions.connect(resource_version)
        resource.save()
        return resource, resource_version

    @staticmethod
    def get_resources(
        filter: Optional[str] = None,
        language_id: Optional[str] = None,
        _region: Optional[str] = None,
    ) -> list[Resource]:
        """Return resources, optionally filtered by having versions of a content_type."""
        params = {
            "language_id": language_id,
            "ct": filter,
        }

        if language_id:
            query = """
                MATCH (r:Resource)
                WHERE r.is_deleted=false
                  AND EXISTS {
                    MATCH (r)-[:HAS_VERSION]->(rv:ResourceVersion {content_type:'translated', status:'active'})
                    -[:IN_LANGUAGE]->(:Language {language_id:$language_id})
                  }
                RETURN DISTINCT r
            """
        elif filter:
            query = """
                MATCH (r:Resource)
                WHERE r.is_deleted=false
                  AND EXISTS {
                    MATCH (r)-[:HAS_VERSION]->(:ResourceVersion {content_type:$ct})
                  }
                RETURN DISTINCT r
            """
        else:
            query = """
                MATCH (r:Resource {is_deleted:false})
                RETURN r
            """

        results, _ = db.cypher_query(query, params)
        return [Resource.inflate(row[0]) for row in results]

    @staticmethod
    def get_all_versions_by_resource_id(resource_id: str) -> list[ResourceVersion]:
        """Get all versions for a resource by its resource_id, irrespective of type or status"""
        query = """
            MATCH (r:Resource {resource_id: $resource_id})
            -[:HAS_VERSION]->(rv:ResourceVersion)
            RETURN rv
            ORDER BY rv.created_at DESC
        """
        results, _ = db.cypher_query(query, {"resource_id": resource_id})
        return [ResourceVersion.inflate(row[0]) for row in results]

    @staticmethod
    def get_resources_with_versions(
        resource_ids: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        language_id: Optional[str] = None,
    ) -> List[dict]:
        """Batch-fetch resources with their versions and current pointers.

        Returns a list of dictionaries containing:
        - ``resource``: inflated :class:`Resource`
        - ``current_original_ids`` / ``current_adapted_ids`` /
          ``current_translated_ids``: Lists of resource_version_ids
        - ``versions``: List of dict snapshots for each relevant version with
          essential scalar fields (title, version, assets, etc.)
        """

        params = {
            "resource_ids": resource_ids,
            "content_type": content_type,
            "language_id": language_id,
        }

        has_current_original = relationship_type_exists("CURRENT_ORIGINAL")
        has_current_adaptation = relationship_type_exists("CURRENT_ADAPTATION")
        has_current_translation = relationship_type_exists("CURRENT_TRANSLATION")

        query_parts = [
            """
            MATCH (r:Resource)
            WHERE r.is_deleted = false
              AND ($resource_ids IS NULL OR r.resource_id IN $resource_ids)
            WITH r, $content_type AS content_type, $language_id AS language_id
            """
        ]

        if has_current_original:
            query_parts.append(
                """
            OPTIONAL MATCH (r)-[:CURRENT_ORIGINAL]->(co:ResourceVersion)
            WITH r, content_type, language_id,
                 collect(DISTINCT co.resource_version_id) AS current_original_ids
                """
            )
        else:
            query_parts.append(
                """
            WITH r, content_type, language_id, [] AS current_original_ids
                """
            )

        if has_current_adaptation:
            query_parts.append(
                """
            OPTIONAL MATCH (r)-[:CURRENT_ADAPTATION]->(ca:ResourceVersion)
            WITH r, content_type, language_id, current_original_ids,
                 collect(DISTINCT ca.resource_version_id) AS current_adapted_ids
                """
            )
        else:
            query_parts.append(
                """
            WITH r, content_type, language_id, current_original_ids, [] AS current_adapted_ids
                """
            )

        if has_current_translation:
            query_parts.append(
                """
            OPTIONAL MATCH (r)-[:CURRENT_TRANSLATION]->(ct:ResourceVersion)
            WITH r, content_type, language_id, current_original_ids, current_adapted_ids,
                 collect(DISTINCT ct.resource_version_id) AS current_translated_ids
                """
            )
        else:
            query_parts.append(
                """
            WITH r, content_type, language_id, current_original_ids, current_adapted_ids,
                 [] AS current_translated_ids
                """
            )

        query_parts.append(
            """
            OPTIONAL MATCH (r)-[:HAS_VERSION]->(rv:ResourceVersion)
            WHERE rv IS NULL
               OR content_type IS NULL
               OR rv.content_type = content_type
               OR rv.resource_version_id IN current_original_ids
               OR rv.resource_version_id IN current_adapted_ids
               OR rv.resource_version_id IN current_translated_ids
            OPTIONAL MATCH (rv)-[:IN_LANGUAGE]->(lang:Language)
            WITH r, content_type, language_id,
                 current_original_ids, current_adapted_ids, current_translated_ids,
                 rv, lang
            WHERE rv IS NULL
               OR language_id IS NULL
               OR lang IS NULL
               OR lang.language_id = language_id
            OPTIONAL MATCH (rv)-[:USES_ICON]->(icon:Asset)
            WITH r, current_original_ids, current_adapted_ids, current_translated_ids,
                 rv, lang, head(collect(DISTINCT icon)) AS icon
            OPTIONAL MATCH (rv)-[:USES_CONTENT]->(content:Asset)
            WITH r, current_original_ids, current_adapted_ids, current_translated_ids,
                 rv, lang, icon, head(collect(DISTINCT content)) AS content
            WITH r, current_original_ids, current_adapted_ids, current_translated_ids,
                 collect(
                    CASE
                        WHEN rv IS NULL THEN NULL
                        ELSE {
                            resource_version_id: rv.resource_version_id,
                            title: rv.title,
                            description: rv.description,
                            content_type: rv.content_type,
                            version: rv.version,
                            status: rv.status,
                            region: rv.region,
                            created_at: rv.created_at,
                            created_by: rv.created_by,
                            is_deleted: coalesce(rv.is_deleted, false),
                            language_id: CASE WHEN lang IS NULL THEN NULL ELSE lang.language_id END,
                            language_name: CASE WHEN lang IS NULL THEN NULL ELSE lang.language_name END,
                            icon_id: CASE WHEN icon IS NULL THEN NULL ELSE icon.asset_id END,
                            icon_filename: CASE WHEN icon IS NULL THEN NULL ELSE icon.filename END,
                            content_id: CASE WHEN content IS NULL THEN NULL ELSE content.asset_id END,
                            content_filename: CASE WHEN content IS NULL THEN NULL ELSE content.filename END
                        }
                    END
                 ) AS version_rows
            WITH r, current_original_ids, current_adapted_ids, current_translated_ids,
                 [row IN version_rows WHERE row IS NOT NULL] AS filtered_versions
            RETURN r, current_original_ids, current_adapted_ids, current_translated_ids, filtered_versions
            """
        )

        query = "".join(query_parts)

        results, _ = db.cypher_query(query, params)

        def _unique(values: List[Optional[str]]) -> List[str]:
            seen = set()
            ordered: List[str] = []
            for value in values or []:
                if value and value not in seen:
                    seen.add(value)
                    ordered.append(value)
            return ordered

        payload: List[dict] = []
        for row in results:
            resource_node, orig_ids, adapted_ids, translated_ids, version_rows = row
            payload.append(
                {
                    "resource": Resource.inflate(resource_node),
                    "current_original_ids": _unique(orig_ids),
                    "current_adapted_ids": _unique(adapted_ids),
                    "current_translated_ids": _unique(translated_ids),
                    "versions": version_rows or [],
                }
            )

        return payload

    @staticmethod
    def update_resource_status(
        resource_version_id: str, status: str, updated_by: str = "System"
    ) -> ResourceVersion:
        """Update status and manage current pointers per content type.

                - For 'active': connect as current for its dimension; mark previous current
                    as superseded/reverted based on version number.
        - For non-active: if this version was current, disconnect pointer.
        """
        try:
            version = ResourceVersion.nodes.get(resource_version_id=resource_version_id)
        except ResourceVersion.DoesNotExist:  # type: ignore[attr-defined]
            raise ValueError(f"Resource version '{resource_version_id}' not found")

        # Find parent resource via HAS_VERSION
        query = """
            MATCH (r:Resource)-[:HAS_VERSION]->(rv:ResourceVersion {resource_version_id:$id})
            RETURN r LIMIT 1
        """
        rows, _ = db.cypher_query(query, {"id": resource_version_id})
        if not rows:
            raise ValueError(
                f"No parent resource found for version '{resource_version_id}'"
            )
        resource = Resource.inflate(rows[0][0])

        valid_statuses = [
            "draft",
            "active",
            "superseded",
            "reverted",
            "archived",
            "review",
        ]
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
            )

        ctype = version.content_type
        old_status = getattr(version, "status", None)

        if status == "active":
            if ctype == "original":
                current = safe_relationship_first(
                    resource.current_original_version, "CURRENT_ORIGINAL"
                )
                if current and current.resource_version_id != resource_version_id:
                    if version.version > current.version:
                        current.status = "superseded"
                    elif version.version < current.version:
                        current.status = "reverted"
                    current.save()
                    resource.current_original_version.disconnect(current)
                version.status = "active"
                version.created_by = updated_by or version.created_by
                version.save()
                resource.current_original_version.connect(version)
            elif ctype == "adapted":
                region = getattr(version, "region", None) or "GLOBAL"
                current_adapted = safe_relationship_all(
                    resource.current_adapted_versions, "CURRENT_ADAPTATION"
                )
                for cur in current_adapted:
                    cur_region = getattr(cur, "region", None) or "GLOBAL"
                    if region != cur_region:
                        continue
                    if version.version > cur.version:
                        cur.status = "superseded"
                    elif version.version < cur.version:
                        cur.status = "reverted"
                    cur.save()
                    resource.current_adapted_versions.disconnect(cur)
                version.status = "active"
                version.created_by = updated_by or version.created_by
                version.save()
                resource.current_adapted_versions.connect(version)
            elif ctype == "translated":
                lang_rel = getattr(version, "language", None)
                lang = None
                if lang_rel:
                    try:
                        lang = lang_rel.single()
                    except Exception:
                        lang = None
                lang_id = getattr(lang, "language_id", None)
                current_translated = safe_relationship_all(
                    resource.current_translated_versions, "CURRENT_TRANSLATION"
                )
                for cur in current_translated:
                    cur_lang_rel = getattr(cur, "language", None)
                    cur_lang = None
                    if cur_lang_rel:
                        try:
                            cur_lang = cur_lang_rel.single()
                        except Exception:
                            cur_lang = None
                    cur_lang_id = getattr(cur_lang, "language_id", None)
                    if lang_id and cur_lang_id != lang_id:
                        continue
                    if version.version > cur.version:
                        cur.status = "superseded"
                    elif version.version < cur.version:
                        cur.status = "reverted"
                    cur.save()
                    resource.current_translated_versions.disconnect(cur)
                version.status = "active"
                version.created_by = updated_by or version.created_by
                version.save()
                resource.current_translated_versions.connect(version)
        else:
            # Non-active -> if currently pointed, disconnect
            if old_status == "active":
                if ctype == "original":
                    cur = safe_relationship_first(
                        resource.current_original_version, "CURRENT_ORIGINAL"
                    )
                    if cur and cur.resource_version_id == resource_version_id:
                        resource.current_original_version.disconnect(cur)
                elif ctype == "adapted":
                    if relationship_type_exists("CURRENT_ADAPTATION"):
                        resource.current_adapted_versions.disconnect(version)
                elif ctype == "translated":
                    if relationship_type_exists("CURRENT_TRANSLATION"):
                        resource.current_translated_versions.disconnect(version)
            version.status = status
            version.created_by = updated_by or version.created_by
            version.save()

        return version
