from neomodel.exceptions import DoesNotExist

from app.models.categories import Category, CategoryVersion
from app.models.modules import Module
from app.repositories.assets import AssetRepository
from app.schemas.categories import CategoryCreateRequest, CategoryUpdateRequest
from app.utils.lifecycle import (activate_version, deactivate_version,
                                 validate_status)
from app.utils.version_utils import increment_version


class CategoryRepository:
    @staticmethod
    def create_category(data: CategoryCreateRequest) -> CategoryVersion:
        slug = f'cat-{data.title.lower().replace(" ", "-")}'

        # Check if category with this slug already exists
        existing_categories = Category.nodes.filter(slug=slug)
        if existing_categories:
            raise ValueError(f"Category with slug '{slug}' already exists")

        # Create the Category node
        category = Category(
            slug=slug,
            title=data.title,
            current_version=1.0,  # Keep current_version = 1.0
        ).save()

        # Create the CategoryVersion node
        category_version = CategoryVersion(
            title=data.title,
            description=data.description,
            status="draft",
            version=1.0,
            created_by=data.created_by or "System",
        ).save()

        # Link icon to the version
        if data.icon:
            icon_asset = AssetRepository.get_asset_by_id(data.icon)
            category_version.icon.connect(icon_asset)

        # Link modules to the version (establish from Module -> CategoryVersion)
        for index, module_id in enumerate(data.modules):
            module_node = Module.nodes.get(module_id=module_id)
            module_node.categories.connect(category_version, {"order": index + 1})

        # Create relationships - link to versions only.
        # Note: current_version_rel is NOT set here - it will be set when a version becomes published
        category.versions.connect(category_version)

        return category_version

    @staticmethod
    def update_category(
        category_id: str, payload: CategoryUpdateRequest
    ) -> CategoryVersion:
        # Get the latest version for this category
        current_version = CategoryRepository.get_latest_version_by_category_id(
            category_id
        )

        # Get the parent Category node
        category = current_version.category.single()
        if not category:
            raise ValueError(
                f"No version found for this category '{current_version.category_version_id}'"
            )

        # Get the current_version and increment by 0.1 using utility function
        new_version = increment_version(category.current_version)

        # Create a new CategoryVersion node with updated data
        new_category_version = CategoryVersion(
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
                new_category_version.icon.connect(icon_asset)
        else:
            # Copy existing icon if no new icon provided
            existing_icon = current_version.icon.single()
            if existing_icon:
                new_category_version.icon.connect(existing_icon)

        # Handle modules update
        if payload.modules is not None:
            # Link new modules from Module -> CategoryVersion
            for index, module_id in enumerate(payload.modules):
                module_node = Module.nodes.get(module_id=module_id)
                module_node.categories.connect(
                    new_category_version, {"order": index + 1}
                )
        else:
            # Copy existing modules if no new modules provided
            for module_node in current_version.modules.all():
                rel = current_version.modules.relationship(module_node)
                module_node.categories.connect(
                    new_category_version, {"order": getattr(rel, "order", 1)}
                )

        # Update Category node - update current_version, don't change slug
        category.current_version = new_version
        category.save()

        # Update relationships - link new version to versions
        category.versions.connect(new_category_version)

        return new_category_version

    @staticmethod
    def get_latest_version_by_category_id(category_id: str) -> CategoryVersion:
        """Get the latest version for a category by its category_id"""
        try:
            category = Category.nodes.get(category_id=category_id)
            latest_version = category.current_version_rel.single()
            if latest_version:
                return latest_version
            # Fallback: if no current version set yet, return highest version
            versions = category.versions.all()
            if versions:
                return max(versions, key=lambda v: v.version)
            raise AttributeError("No versions found")
        except (DoesNotExist, AttributeError):
            raise ValueError(f"No latest version found for category '{category_id}'")

    @staticmethod
    def get_categories(
        status_filter: str = "active",
        limit: int | None = None,
        offset: int | None = None,
        include_versions: bool = False,
    ) -> list:
        from neomodel import db

        params = {
            "status": status_filter if status_filter != "all" else None,
        }

        if status_filter == "published":
            params["status"] = "active"

        if include_versions:
            query = """
                MATCH (c:Category)
                WHERE $status IS NULL OR (c)-[:CURRENT_VERSION]->(:CategoryVersion {status: $status})
                RETURN c
                ORDER BY c.title
            """
            if offset is not None:
                query += " SKIP $skip"
                params["skip"] = offset
            if limit is not None:
                query += " LIMIT $limit"
                params["limit"] = limit
            results, _ = db.cypher_query(query, params)
            return [Category.inflate(row[0]) for row in results]
        else:
            if status_filter == "all":
                query = """
                    MATCH (c:Category)
                    OPTIONAL MATCH (c)-[:HAS_VERSION]->(v:CategoryVersion)
                    WITH c, v ORDER BY coalesce(v.version, 0) DESC
                    WITH c, head(collect(v)) as latest_version
                    WHERE latest_version IS NOT NULL
                    RETURN latest_version
                    ORDER BY latest_version.title
                """
            else:
                query = """
                    MATCH (c:Category)-[:CURRENT_VERSION]->(cv:CategoryVersion {status: $status})
                    RETURN cv
                    ORDER BY cv.title
                """
            if offset is not None:
                query += " SKIP $skip"
                params["skip"] = offset
            if limit is not None:
                query += " LIMIT $limit"
                params["limit"] = limit

            results, _ = db.cypher_query(query, params)
            return [CategoryVersion.inflate(row[0]) for row in results]

    @staticmethod
    def get_category_by_id(category_id: str) -> Category:
        """Get a single category by ID"""
        try:
            return Category.nodes.get(category_id=category_id)
        except (DoesNotExist, AttributeError):
            raise ValueError(f"No category found with ID '{category_id}'")

    @staticmethod
    def update_category_status(
        category_version_id: str, status: str, updated_by: str = "System"
    ) -> CategoryVersion:
        """Update a category version's status using shared lifecycle helpers.

        Backward compatibility: incoming 'published' is treated as 'active'.
        """

        def _fetch(cat_ver_id: str) -> CategoryVersion:
            return CategoryVersion.nodes.get(
                category_version_id=cat_ver_id
            )  # pragma: no cover simple wrapper

        # In-memory test override path (used by unit tests to bypass DB)
        test_overrides = getattr(CategoryRepository, "_test_in_memory_versions", None)
        if isinstance(test_overrides, dict) and category_version_id in test_overrides:
            version = test_overrides[category_version_id]
        else:
            try:
                version = _fetch(category_version_id)
            except (
                Exception
            ):  # noqa: BLE001 - broad to allow test monkeypatching without neomodel
                # Attempt to gather existing IDs only if graph available; wrap in safe try
                existing_ids: list[str] = []
                try:  # pragma: no cover - defensive
                    existing_ids = [
                        v.category_version_id for v in CategoryVersion.nodes.all()
                    ]
                except Exception:  # noqa: BLE001
                    pass
                raise ValueError(
                    f"Category version with ID '{category_version_id}' does not exist. Existing IDs: {existing_ids}"
                )

        if status == "published":
            status = "active"
        validate_status(status)

        category = version.category.single()
        if not category:
            raise ValueError(
                f"No parent category found for version '{category_version_id}'"
            )

        all_versions = category.versions.all()

        class _PointerAdapter:
            def get_current(self):
                return category.current_version_rel.single()

            def connect(self, ver):
                category.current_version_rel.connect(ver)
                category.save()

            def disconnect(self, ver):
                category.current_version_rel.disconnect(ver)
                category.save()

        pointer = _PointerAdapter()

        if status == "active":
            return activate_version(
                parent=category,
                version=version,
                pointer=pointer,
                all_versions=all_versions,
                updated_by=updated_by,
                save_parent=lambda c: c.save(),
                save_version=lambda v: v.save(),
            )

        if getattr(version, "status", None) == "active" and status != "active":
            return deactivate_version(
                parent=category,
                version=version,
                pointer=pointer,
                all_versions=all_versions,
                new_status=status,
                updated_by=updated_by,
                save_parent=lambda c: c.save(),
                save_version=lambda v: v.save(),
            )

        version.status = status
        if updated_by:
            version.created_by = updated_by
        version.save()
        return version
