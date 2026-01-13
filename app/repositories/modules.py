from neomodel.exceptions import DoesNotExist

from app.models.modules import Module, ModuleVersion
from app.repositories.assets import AssetRepository
from app.repositories.resources import ResourceRepository
from app.schemas.modules import ModuleCreateRequest, ModuleUpdateRequest
from app.utils.lifecycle import (activate_version, deactivate_version,
                                 validate_status)
from app.utils.slug import build_slug
from app.utils.version_utils import increment_version
from app.repositories.key_learning_points import KeyLearningPointRepository

class ModuleRepository:

    @staticmethod
    def create_module(data: ModuleCreateRequest) -> ModuleVersion:
        slug = build_slug("mod", data.title)

        # Check if module with this slug already exists
        existing_modules = Module.nodes.filter(slug=slug)
        if existing_modules:
            raise ValueError(f"Module with slug '{slug}' already exists")

        # if data.key_learning_points:
        #     raise ValueError(
        #         "Setting key learning points during module creation is not supported yet"
        #     )

        # Create the Module node
        module = Module(
            title=data.title,
            slug=slug,
            current_version=1.0,  # Keep current_version = 1.0
        ).save()

        # Create the ModuleVersion node
        module_version = ModuleVersion(
            title=data.title,
            description=data.description,
            status="draft",
            version=1.0,
            created_by=data.created_by or "System",
        ).save()

        # Link icon to the version
        if data.icon:
            icon_asset = AssetRepository.get_asset_by_id(data.icon)
            module_version.icon.connect(icon_asset)

        # Link videos to the version
        for index, resource_id in enumerate(data.videos):
            resource = ResourceRepository.get_resource_by_id(resource_id)
            module_version.videos.connect(resource, {"order": index + 1})

        # Link action cards to the version
        for index, resource_id in enumerate(data.action_cards):
            resource = ResourceRepository.get_resource_by_id(resource_id)
            module_version.action_cards.connect(resource, {"order": index + 1})

        # Link practical procedures to the version
        for index, resource_id in enumerate(data.practical_procedures):
            resource = ResourceRepository.get_resource_by_id(resource_id)
            module_version.practical_procedures.connect(resource, {"order": index + 1})

        # Link drugs to the version
        for index, resource_id in enumerate(data.drugs):
            resource = ResourceRepository.get_resource_by_id(resource_id)
            module_version.drugs.connect(resource, {"order": index + 1})

        # Link KLPs to the version
        for klp_id in data.key_learning_points:
            klp = KeyLearningPointRepository.get_klp_by_id(klp_id)
            module_version.key_learning_points.connect(klp)

        # Create relationships - link version only. Do NOT set CURRENT_VERSION here.
        # The pointer must only be established when a version becomes active via
        # update_module_status (activation flow).
        module.versions.connect(module_version)

        return module_version

    @staticmethod
    def get_modules(
        status_filter: str = "active",
        limit: int | None = None,
        offset: int | None = None,
        include_versions: bool = False,
    ) -> list:
        from neomodel import db

        params = {
            "status": status_filter if status_filter != "all" else None,
        }

        if include_versions:
            # Return Module nodes
            query = """
                MATCH (m:Module)
                WHERE ($status IS NULL OR (m)-[:CURRENT_VERSION]->(:ModuleVersion {status: $status}))
                RETURN m
                ORDER BY m.title
            """
        else:
            # Return ModuleVersion nodes
            if status_filter == "all":
                # For "all", get the latest version of each module
                query = """
                    MATCH (m:Module)
                    OPTIONAL MATCH (m)-[:HAS_VERSION]->(v:ModuleVersion)
                    WITH m, v ORDER BY coalesce(v.version, 0) DESC
                    WITH m, head(collect(v)) as latest_version
                    WHERE latest_version IS NOT NULL
                    RETURN latest_version
                    ORDER BY latest_version.title
                """
            else:
                # For a specific status, get the current version with that status
                query = """
                    MATCH (m:Module)-[:CURRENT_VERSION]->(mv:ModuleVersion {status: $status})
                    RETURN mv
                    ORDER BY mv.title
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
        
        if include_versions:
            return [Module.inflate(row[0]) for row in results]
        else:
            return [ModuleVersion.inflate(row[0]) for row in results]

    @staticmethod
    def get_modules_by_language_id(language_id: str, status_filter: str = "active") -> list[ModuleVersion]:
        """
        Get all active module versions available in the specified language.
        Path: Language -> (current) LanguageVersion -> (uses) Category -> (current) CategoryVersion <- (included in) Module -> (current) ModuleVersion
        """
        from neomodel import db

        query = """
            MATCH (l:Language {language_id: $language_id})
            MATCH (l)-[:CURRENT_VERSION]->(lv:LanguageVersion)
            MATCH (lv)-[:USES_CATEGORY]->(c:Category)
            MATCH (c)-[:CURRENT_VERSION]->(cv:CategoryVersion)
            MATCH (m:Module)-[:INCLUDED_IN_CATEGORY]->(cv)
            MATCH (m)-[:CURRENT_VERSION]->(mv:ModuleVersion)
            WHERE mv.status = $status
            RETURN DISTINCT mv
            ORDER BY mv.title
        """
        
        params = {
            "language_id": language_id,
            "status": status_filter
        }

        results, _ = db.cypher_query(query, params)
        return [ModuleVersion.inflate(row[0]) for row in results]

    @staticmethod
    def get_modules_all_nodes() -> list[Module]:
        return Module.nodes.all()

    @staticmethod
    def get_module_by_id(module_id: str) -> Module:
        try:
            return Module.nodes.get(module_id=module_id)
        except DoesNotExist:
            raise ValueError(f"Module with id '{module_id}' not found")

    @staticmethod
    def get_latest_version_by_module_id(module_id: str) -> ModuleVersion:
        """Get the latest version for a module by its module_id"""
        try:
            module = Module.nodes.get(module_id=module_id)
        except DoesNotExist:
            raise ValueError(f"Module with id '{module_id}' not found")

        # First attempt: use CURRENT_VERSION pointer
        pointer_version = None
        try:
            pointer_version = module.current_version_rel.single()
        except Exception:  # pragma: no cover - protective
            pointer_version = None
        if pointer_version:
            return pointer_version

        # Fallback: compute latest by numeric version among HAS_VERSION relations
        versions = module.versions.all()
        if versions:
            latest = max(versions, key=lambda v: getattr(v, "version", 0))
            return latest
        raise ValueError(f"No latest version found for module '{module_id}'")

    @staticmethod
    def update_module(module_id: str, payload: ModuleUpdateRequest) -> ModuleVersion:
        # Get the latest version for this module
        current_version = ModuleRepository.get_latest_version_by_module_id(module_id)

        # Get the parent Module node
        module_rel = getattr(current_version, "module", None)
        module = (
            module_rel.single()
            if module_rel and hasattr(module_rel, "single")
            else None
        )
        if not module:
            raise ValueError(
                f"No parent module found for version '{current_version.module_version_id}'"
            )

        # Get the current_version and increment by 0.1 using utility function
        new_version = increment_version(module.current_version)

        # Create a new ModuleVersion node with updated data
        new_module_version = ModuleVersion(
            title=(
                payload.title if payload.title is not None else current_version.title
            ),
            description=(
                payload.description
                if payload.description is not None
                else current_version.description
            ),
            status="draft",
            version=new_version,
            created_by=(
                payload.created_by
                if payload.created_by is not None
                else current_version.created_by
            ),
        ).save()

        # Handle icon linking
        if payload.icon is not None:
            if payload.icon:
                icon_asset = AssetRepository.get_asset_by_id(payload.icon)
                new_module_version.icon.connect(icon_asset)
        else:
            # Copy existing icon if no new icon provided
            existing_icon = current_version.icon.single()
            if existing_icon:
                new_module_version.icon.connect(existing_icon)

        # Handle videos update
        if payload.videos is not None:
            # Link new videos
            for index, resource_id in enumerate(payload.videos):
                resource = ResourceRepository.get_resource_by_id(resource_id)
                new_module_version.videos.connect(resource, {"order": index + 1})
        else:
            # Copy existing videos if no new videos provided
            for res in current_version.videos.all():
                rel = current_version.videos.relationship(res)
                new_module_version.videos.connect(res, {"order": rel.order})

        # Handle action cards update
        if payload.action_cards is not None:
            # Link new action cards
            for index, resource_id in enumerate(payload.action_cards):
                resource = ResourceRepository.get_resource_by_id(resource_id)
                new_module_version.action_cards.connect(resource, {"order": index + 1})
        else:
            # Copy existing action cards if no new action cards provided
            for res in current_version.action_cards.all():
                rel = current_version.action_cards.relationship(res)
                new_module_version.action_cards.connect(res, {"order": rel.order})

        # Handle practical procedures update
        if payload.practical_procedures is not None:
            # Link new practical procedures
            for index, resource_id in enumerate(payload.practical_procedures):
                resource = ResourceRepository.get_resource_by_id(resource_id)
                new_module_version.practical_procedures.connect(
                    resource, {"order": index + 1}
                )
        else:
            # Copy existing practical procedures if no new practical procedures provided
            for res in current_version.practical_procedures.all():
                rel = current_version.practical_procedures.relationship(res)
                new_module_version.practical_procedures.connect(
                    res, {"order": rel.order}
                )

        # Handle drugs update
        if payload.drugs is not None:
            # Link new drugs
            for index, resource_id in enumerate(payload.drugs):
                resource = ResourceRepository.get_resource_by_id(resource_id)
                new_module_version.drugs.connect(resource, {"order": index + 1})
        else:
            # Copy existing drugs if no new drugs provided
            for res in current_version.drugs.all():
                rel = current_version.drugs.relationship(res)
                new_module_version.drugs.connect(res, {"order": rel.order})

        # Handle key learning points update
        if payload.key_learning_points is not None:
            for klp_id in payload.key_learning_points:
                klp = KeyLearningPointRepository.get_klp_by_id(klp_id)
                new_module_version.key_learning_points.connect(klp)
        else:
            for klp in current_version.key_learning_points.all():
                new_module_version.key_learning_points.connect(klp)

        # Handle key learning points update
        # if payload.key_learning_points is not None:
        #     raise ValueError(
        #         "Updating key learning points on modules is not supported yet"
        #     )

        if payload.title is not None:
            module.title = payload.title

        # Update Module node - only update current_version, don't change slug
        module.current_version = new_version
        module.save()

        # Update relationships - link new version to versions; do not set current_version_rel here
        module.versions.connect(new_module_version)

        return new_module_version

    @staticmethod
    def update_module_status(
        module_version_id: str, status: str, updated_by: str = "System"
    ) -> ModuleVersion:
        """Update a module version's status using shared lifecycle helpers."""
        try:
            # In-memory override for tests
            test_overrides = getattr(ModuleRepository, "_test_in_memory_versions", None)
            if isinstance(test_overrides, dict) and module_version_id in test_overrides:
                version = test_overrides[module_version_id]
            else:
                version = ModuleVersion.nodes.get(module_version_id=module_version_id)
        except Exception:  # noqa: BLE001
            existing_ids: list[str] = []
            try:  # pragma: no cover
                existing_ids = [v.module_version_id for v in ModuleVersion.nodes.all()]
            except Exception:  # noqa: BLE001
                pass
            raise ValueError(
                f"Module version with ID '{module_version_id}' does not exist. Existing IDs: {existing_ids}"
            )

        # No legacy 'published' mapping; use provided status directly.
        validate_status(status)

        module = version.module.single()
        if not module:
            raise ValueError(
                f"No parent module found for version '{module_version_id}'"
            )

        all_versions = module.versions.all()

        class _PointerAdapter:
            def get_current(self):
                return module.current_version_rel.single()

            def connect(self, ver):
                module.current_version_rel.connect(ver)
                module.save()

            def disconnect(self, ver):
                module.current_version_rel.disconnect(ver)
                module.save()

        pointer = _PointerAdapter()

        if status == "active":
            return activate_version(
                parent=module,
                version=version,
                pointer=pointer,
                all_versions=all_versions,
                updated_by=updated_by,
                save_parent=lambda m: m.save(),
                save_version=lambda v: v.save(),
            )

        if getattr(version, "status", None) == "active" and status != "active":
            return deactivate_version(
                parent=module,
                version=version,
                pointer=pointer,
                all_versions=all_versions,
                new_status=status,
                updated_by=updated_by,
                save_parent=lambda m: m.save(),
                save_version=lambda v: v.save(),
            )

        version.status = status
        if updated_by:
            version.created_by = updated_by
        version.save()
        return version
