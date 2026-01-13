from neomodel import db

from app.models.languages import Language, LanguageVersion
from app.repositories.assets import AssetRepository
from app.schemas.languages import (LanguageCreateRequest, LanguageSchema,
                                   LanguageVersionSchema)
from app.utils.neo4j_rel import safe_relationship_all
from app.utils.slug import build_language_slug
from app.utils.version_utils import increment_version


class LanguageRepository:

    @staticmethod
    def get_languages(
        status_filter: str = "active",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LanguageVersion]:
        """Get languages based on version status filter."""
        params = {}
        
        if status_filter == "all":
            query = """
                MATCH (l:Language)
                OPTIONAL MATCH (l)-[:HAS_VERSION]->(v:LanguageVersion)
                WITH l, v ORDER BY coalesce(v.version, 0) DESC
                WITH l, collect(v) AS versions
                WITH versions[0] AS latest_version
                WHERE latest_version IS NOT NULL
                RETURN latest_version
                ORDER BY coalesce(latest_version.created_at, 0) DESC
            """
        else:  # "active"
            query = """
                MATCH (l:Language)-[:CURRENT_VERSION]->(lv:LanguageVersion)
                WHERE lv.status = 'active'
                RETURN lv
                ORDER BY lv.created_at DESC
            """
        
        # Only add SKIP if offset is provided
        if offset is not None:
            query += " SKIP $skip"
            params["skip"] = offset
        
        # Only add LIMIT if limit is provided
        if limit is not None:
            query += " LIMIT $limit"
            params["limit"] = limit

        results, _ = db.cypher_query(query, params)
        return [LanguageVersion.inflate(row[0]) for row in results if row[0]]

    @staticmethod
    def get_language_by_id(language_id: str) -> LanguageSchema:
        """Get a single language with all its versions by language ID"""
        query = """
            MATCH (lang:Language {language_id: $language_id})
            OPTIONAL MATCH (lang)-[:HAS_VERSION]->(v:LanguageVersion)
            OPTIONAL MATCH (lang)-[:CURRENT_VERSION]->(current_v:LanguageVersion)
            OPTIONAL MATCH (v)-[:HAS_ICON]->(icon:Asset)
            WITH lang, v, current_v, icon
            ORDER BY v.version DESC
            WITH lang, current_v, collect({
                language_version_id: v.language_version_id,
                slug: lang.slug,
                language_name: lang.language_name,
                autonym_script: v.autonym_script,
                learning_platform: v.learning_platform,
                country: v.country,
                country_code: v.country_code,
                region: v.region,
                latitude: v.latitude,
                longitude: v.longitude,
                version: v.version,
                status: v.status,
                created_at: v.created_at,
                created_by: v.created_by,
                is_deleted: v.is_deleted,
                icon: icon.asset_id
            }) AS versions
            RETURN lang, versions, current_v
        """
        results, _ = db.cypher_query(query, {"language_id": language_id})

        if not results:
            raise ValueError(f"Language with ID '{language_id}' does not exist")

        lang_node, version_data, current_version_node = results[0]
        language = Language.inflate(lang_node)

        version_schemas = [
            LanguageVersionSchema(**data)
            for data in version_data
            if data["language_version_id"]
        ]
        current_version_schema = None
        if current_version_node:
            current_version_inflated = LanguageVersion.inflate(current_version_node)
            current_version_data = next(
                (
                    v
                    for v in version_schemas
                    if v.language_version_id
                    == current_version_inflated.language_version_id
                ),
                None,
            )
            if current_version_data:
                current_version_schema = current_version_data

        return LanguageSchema(
            language_id=language.language_id,
            slug=language.slug,
            language_name=language.language_name or "Unknown Language",
            versions=version_schemas,
            current_version=current_version_schema,
        )

    @staticmethod
    def get_language_ids_by_country_codes(
        country_codes: list[str],
        *,
        status: str | None = "active",
    ) -> dict[str, list[str]]:
        """Return mapping of country_code to language_ids for active languages."""

        if not country_codes:
            return {}

        normalized_codes = list({code for code in country_codes if code})
        if not normalized_codes:
            return {}

        status_filter = None if status in (None, "all") else status

        query = """
            MATCH (lang:Language)-[:CURRENT_VERSION]->(lv:LanguageVersion)
            WHERE lv.country_code IN $codes
              AND ($status IS NULL OR lv.status = $status)
            RETURN lv.country_code AS country_code,
                   collect(DISTINCT lang.language_id) AS language_ids
        """
        rows, _ = db.cypher_query(
            query,
            {
                "codes": normalized_codes,
                "status": status_filter,
            },
        )
        mapping: dict[str, list[str]] = {}
        for country_code, language_ids in rows:
            mapping[country_code] = list(language_ids or [])
        # Ensure every requested code has an entry
        for code in normalized_codes:
            mapping.setdefault(code, [])
        return mapping

    @staticmethod
    def get_all_languages_versions() -> list[LanguageSchema]:
        """Get all languages with their versions using an efficient query."""
        query = """
            MATCH (lang:Language)
            OPTIONAL MATCH (lang)-[:HAS_VERSION]->(v:LanguageVersion)
            OPTIONAL MATCH (lang)-[:CURRENT_VERSION]->(current_v:LanguageVersion)
            OPTIONAL MATCH (v)-[:HAS_ICON]->(icon:Asset)
            WITH lang, v, current_v, icon
            ORDER BY v.version DESC
            WITH lang, current_v, collect({
                language_version_id: v.language_version_id,
                slug: lang.slug,
                language_name: lang.language_name,
                autonym_script: v.autonym_script,
                learning_platform: v.learning_platform,
                country: v.country,
                country_code: v.country_code,
                region: v.region,
                latitude: v.latitude,
                longitude: v.longitude,
                version: v.version,
                status: v.status,
                created_at: v.created_at,
                created_by: v.created_by,
                is_deleted: v.is_deleted,
                icon: icon.asset_id
            }) AS versions_data
            RETURN lang, versions_data, current_v
            ORDER BY lang.language_name
        """
        results, _ = db.cypher_query(query)

        result_schemas = []
        for lang_node, versions_data, current_v_node in results:
            lang = Language.inflate(lang_node)
            version_schemas = [
                LanguageVersionSchema(**data)
                for data in versions_data
                if data["language_version_id"]
            ]

            current_version_schema = None
            if current_v_node:
                current_v_inflated = LanguageVersion.inflate(current_v_node)
                current_version_schema = next(
                    (
                        vs
                        for vs in version_schemas
                        if vs.language_version_id
                        == current_v_inflated.language_version_id
                    ),
                    None,
                )

            result_schemas.append(
                LanguageSchema(
                    language_id=lang.language_id,
                    slug=lang.slug,
                    language_name=lang.language_name or "Unknown Language",
                    versions=version_schemas,
                    current_version=current_version_schema,
                )
            )

        return result_schemas

    @staticmethod
    def create_language(data: LanguageCreateRequest) -> LanguageVersion:
        slug = build_language_slug(data.country, data.language_name)

        # Check if language with this slug already exists
        existing_languages = Language.nodes.filter(slug=slug)
        if existing_languages:
            raise ValueError(f"Language with slug '{slug}' already exists")

        # Create the Language node
        language = Language(
            slug=slug,
            current_version=1.0,  # Keep current_version = 1.0
            language_name=data.language_name,
        ).save()

        # Create the LanguageVersion node
        language_version = LanguageVersion(
            autonym_script=data.autonym_script,
            learning_platform=(
                data.learning_platform if data.learning_platform is not None else True
            ),
            country=data.country,
            country_code=data.country_code,
            region=data.region,
            latitude=data.latitude,
            longitude=data.longitude,
            status="draft",
            version=1.0,
            created_by=data.created_by or "System",
        ).save()

        # Link icon to the version
        if data.icon:
            icon_asset = AssetRepository.get_asset_by_id(data.icon)
            language_version.icon.connect(icon_asset)

        # Create relationships - link to versions
        # Note: current_version_rel is NOT set here - it will be set when a version becomes published
        language.versions.connect(language_version)

        # Link Categories if provided
        if data.categories:
            from app.repositories.categories import CategoryRepository

            for index, category_id in enumerate(data.categories):
                category = CategoryRepository.get_category_by_id(category_id)
                if category:
                    language_version.categories.connect(category, {"order": index + 1})
                else:
                    raise ValueError(f"Category with ID '{category_id}' does not exist")

        return language_version

    @staticmethod
    def update_language(
        language_id: str, payload: LanguageCreateRequest
    ) -> LanguageVersion:
        # Get the Language node
        try:
            language = Language.nodes.get(language_id=language_id)
        except Language.DoesNotExist:
            raise ValueError(f"Language with ID '{language_id}' does not exist")

        # Get the latest version of this language (highest version number)
        versions = language.versions.all()
        if not versions:
            raise ValueError(f"No versions found for language '{language_id}'")

        current_version = max(versions, key=lambda v: v.version)

        # Get the current_version and increment by 0.1 using utility function
        new_version = increment_version(language.current_version)

        # Create a new LanguageVersion node with updated data
        new_language_version = LanguageVersion(
            autonym_script=(
                payload.autonym_script
                if payload.autonym_script is not None
                else current_version.autonym_script
            ),
            learning_platform=(
                payload.learning_platform
                if payload.learning_platform is not None
                else current_version.learning_platform
            ),
            country=(
                payload.country
                if payload.country is not None
                else current_version.country
            ),
            country_code=(
                payload.country_code
                if payload.country_code is not None
                else current_version.country_code
            ),
            region=(
                payload.region if payload.region is not None else current_version.region
            ),
            latitude=(
                payload.latitude
                if payload.latitude is not None
                else current_version.latitude
            ),
            longitude=(
                payload.longitude
                if payload.longitude is not None
                else current_version.longitude
            ),
            status="draft",
            version=new_version,
            created_by=(
                payload.created_by
                if payload.created_by is not None
                else current_version.created_by
            ),
        ).save()

        # Handle icon linking (inherit if not provided)
        if payload.icon:
            icon_asset = AssetRepository.get_asset_by_id(payload.icon)
            new_language_version.icon.connect(icon_asset)
        else:
            existing_icon = current_version.icon.single()
            if existing_icon:
                new_language_version.icon.connect(existing_icon)

        # Handle categories linking
        if payload.categories is not None:
            from app.repositories.categories import CategoryRepository

            # First, disconnect all existing categories
            existing_categories = safe_relationship_all(
                new_language_version.categories,
                "USES_CATEGORY",
            )
            for category in existing_categories:
                new_language_version.categories.disconnect(category)

            # Now, link the new categories
            for index, category_id in enumerate(payload.categories):
                category = CategoryRepository.get_category_by_id(category_id)
                if category:
                    new_language_version.categories.connect(
                        category, {"order": index + 1}
                    )
                else:
                    raise ValueError(f"Category with ID '{category_id}' does not exist")
        else:
            # inherit categories from current version
            existing_categories = safe_relationship_all(
                current_version.categories,
                "USES_CATEGORY",
            )
            for rel_index, category in enumerate(existing_categories, start=1):
                rel = current_version.categories.relationship(category)
                order = getattr(rel, "order", rel_index)
                new_language_version.categories.connect(category, {"order": order})

        # Update Language node - update current_version, language_name if provided, and regenerate slug if needed
        language.current_version = new_version
        slug_changed = False
        if payload.language_name is not None:
            language.language_name = payload.language_name
            slug_changed = True
        if payload.country is not None:
            slug_changed = True

        if slug_changed:
            # Regenerate slug using the new values or current values
            country_for_slug = (
                payload.country
                if payload.country is not None
                else current_version.country
            )
            language_name_for_slug = (
                payload.language_name
                if payload.language_name is not None
                else language.language_name
            )
            new_slug = build_language_slug(country_for_slug, language_name_for_slug)
            language.slug = new_slug

        language.save()

        # Update relationships - link new version to versions
        # Note: current_version_rel is NOT set here - it will be set when a version becomes published via status update
        language.versions.connect(new_language_version)

        return new_language_version

    @staticmethod
    def update_language_status(
        language_version_id: str, status: str, updated_by: str = "System"
    ) -> LanguageVersion:
        """Update the status of a language version.

        If setting to 'active':
        - Find the current active version (if any).
        - If activating.version > current.version -> mark current as 'superseded'.
        - If activating.version < current.version -> mark current as 'reverted'.
        - Disconnect current_version_rel from current and connect the activating version.
        If changing away from 'active' and it was current, disconnect current_version_rel (no auto-promotion).
        """
        # Get the existing language version
        try:
            language_version = LanguageVersion.nodes.get(
                language_version_id=language_version_id
            )
        except LanguageVersion.DoesNotExist:
            # Try to find all existing language versions for debugging
            all_versions = LanguageVersion.nodes.all()
            existing_ids = [v.language_version_id for v in all_versions]
            raise ValueError(
                f"Language version with ID '{language_version_id}' does not exist. "
                f"Existing language version IDs: {existing_ids}"
            )

        # Validate status
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

        # Get the parent language
        language = language_version.language.single()
        if not language:
            raise ValueError(
                f"No parent language found for version '{language_version_id}'"
            )

        old_status = getattr(language_version, "status", None)

        if status == "active":
            # Determine current active
            current_active = language.current_version_rel.single()
            if (
                current_active
                and current_active.language_version_id != language_version_id
            ):
                # Compare versions and mark current accordingly
                try:
                    if language_version.version > current_active.version:
                        current_active.status = "superseded"
                    elif language_version.version < current_active.version:
                        current_active.status = "reverted"
                    # if equal, leave status as-is
                    current_active.save()
                except Exception:
                    pass
                language.current_version_rel.disconnect(current_active)

            # Set this version active and connect
            language_version.status = "active"
            language_version.created_by = updated_by or language_version.created_by
            language_version.save()
            language.current_version_rel.connect(language_version)
        else:
            # Changing away from active
            if old_status == "active":
                current_rel = language.current_version_rel.single()
                if (
                    current_rel
                    and current_rel.language_version_id == language_version_id
                ):
                    language.current_version_rel.disconnect(current_rel)
            language_version.status = status
            language_version.created_by = updated_by or language_version.created_by
            language_version.save()

        return language_version

    @staticmethod
    def disable_module_for_language(
        language_id: str, module_id: str, disabled_by: str = "System"
    ) -> bool:
        """Disable a module for a specific language by creating DISABLED_MODULE relationship.
        
        Returns True if the module was disabled, False if it was already disabled.
        """
        from app.models.modules import Module
        
        # Get the language
        try:
            language = Language.nodes.get(language_id=language_id)
        except Language.DoesNotExist:
            raise ValueError(f"Language with ID '{language_id}' does not exist")
        
        # Get the module
        try:
            module = Module.nodes.get(module_id=module_id)
        except Module.DoesNotExist:
            raise ValueError(f"Module with ID '{module_id}' does not exist")
        
        # Check if already disabled
        if language.disabled_modules.is_connected(module):
            return False  # Already disabled
        
        # Create the DISABLED_MODULE relationship
        language.disabled_modules.connect(module, {"disabled_by": disabled_by})
        return True

    @staticmethod
    def enable_module_for_language(language_id: str, module_id: str) -> bool:
        """Enable a module for a language by removing DISABLED_MODULE relationship.
        
        Returns True if the module was enabled, False if it was not disabled.
        """
        from app.models.modules import Module
        
        # Get the language
        try:
            language = Language.nodes.get(language_id=language_id)
        except Language.DoesNotExist:
            raise ValueError(f"Language with ID '{language_id}' does not exist")
        
        # Get the module
        try:
            module = Module.nodes.get(module_id=module_id)
        except Module.DoesNotExist:
            raise ValueError(f"Module with ID '{module_id}' does not exist")
        
        # Check if disabled
        if not language.disabled_modules.is_connected(module):
            return False  # Not disabled
        
        # Remove the DISABLED_MODULE relationship
        language.disabled_modules.disconnect(module)
        return True

    @staticmethod
    def get_disabled_modules_for_language(language_id: str) -> list[dict]:
        """Get list of disabled modules for this language with metadata.
        
        Returns list of dicts with module_id, title, disabled_at, disabled_by.
        """
        query = """
            MATCH (lang:Language {language_id: $language_id})-[rel:DISABLED_MODULE]->(m:Module)
            OPTIONAL MATCH (m)-[:CURRENT_VERSION]->(mv:ModuleVersion)
            RETURN m.module_id as module_id, 
                   COALESCE(mv.title, m.title) as title,
                   rel.disabled_at as disabled_at,
                   rel.disabled_by as disabled_by
            ORDER BY title
        """
        results, _ = db.cypher_query(query, {"language_id": language_id})
        
        return [
            {
                "module_id": row[0],
                "title": row[1],
                "disabled_at": row[2],
                "disabled_by": row[3]
            }
            for row in results
        ]

    @staticmethod
    def disable_resource_for_language(
        language_id: str, resource_id: str, disabled_by: str = "System"
    ) -> bool:
        """Disable a resource for a specific language by creating DISABLED_RESOURCE relationship.
        
        Returns True if the resource was disabled, False if it was already disabled.
        """
        from app.models.resources import Resource
        
        # Get the language
        try:
            language = Language.nodes.get(language_id=language_id)
        except Language.DoesNotExist:
            raise ValueError(f"Language with ID '{language_id}' does not exist")
        
        # Get the resource
        try:
            resource = Resource.nodes.get(resource_id=resource_id)
        except Resource.DoesNotExist:
            raise ValueError(f"Resource with ID '{resource_id}' does not exist")
        
        # Check if already disabled
        if language.disabled_resources.is_connected(resource):
            return False  # Already disabled
        
        # Create the DISABLED_RESOURCE relationship
        language.disabled_resources.connect(resource, {"disabled_by": disabled_by})
        return True

    @staticmethod
    def enable_resource_for_language(language_id: str, resource_id: str) -> bool:
        """Enable a resource for a language by removing DISABLED_RESOURCE relationship.
        
        Returns True if the resource was enabled, False if it was not disabled.
        """
        from app.models.resources import Resource
        
        # Get the language
        try:
            language = Language.nodes.get(language_id=language_id)
        except Language.DoesNotExist:
            raise ValueError(f"Language with ID '{language_id}' does not exist")
        
        # Get the resource
        try:
            resource = Resource.nodes.get(resource_id=resource_id)
        except Resource.DoesNotExist:
            raise ValueError(f"Resource with ID '{resource_id}' does not exist")
        
        # Check if disabled
        if not language.disabled_resources.is_connected(resource):
            return False  # Not disabled
        
        # Remove the DISABLED_RESOURCE relationship
        language.disabled_resources.disconnect(resource)
        return True

    @staticmethod
    def get_disabled_resources_for_language(language_id: str) -> list[dict]:
        """Get list of disabled resources for this language with metadata.
        
        Returns list of dicts with resource_id, title, disabled_at, disabled_by.
        """
        query = """
            MATCH (lang:Language {language_id: $language_id})-[rel:DISABLED_RESOURCE]->(r:Resource)
            OPTIONAL MATCH (r)-[:CURRENT_ORIGINAL]->(rv:ResourceVersion)
            RETURN r.resource_id as resource_id, 
                   COALESCE(rv.title, r.title) as title,
                   rel.disabled_at as disabled_at,
                   rel.disabled_by as disabled_by
            ORDER BY title
        """
        results, _ = db.cypher_query(query, {"language_id": language_id})
        
        return [
            {
                "resource_id": row[0],
                "title": row[1],
                "disabled_at": row[2],
                "disabled_by": row[3]
            }
            for row in results
        ]

