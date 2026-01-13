from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      RelationshipFrom, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)

from app.models.module_resource_rel import ModuleResourceRel
from app.utils.sys_date import now


class Category(StructuredNode):
    category_id = UniqueIdProperty()
    title = StringProperty(required=True)
    slug = StringProperty(required=True)
    current_version = FloatProperty(default=1.0)

    versions = RelationshipTo("app.models.categories.CategoryVersion", "HAS_VERSION")
    current_version_rel = RelationshipTo(
        "app.models.categories.CategoryVersion", "CURRENT_VERSION"
    )


class CategoryVersion(StructuredNode):
    category_version_id = UniqueIdProperty()
    title = StringProperty(required=True)
    description = StringProperty()
    created_at = DateTimeProperty(default=now)
    created_by = StringProperty(default="System")
    is_deleted = BooleanProperty(default=False)
    version = FloatProperty(default=1.0)
    status = StringProperty(
        required=True,
        index=True,
        choices={
            "draft": "draft",
            "active": "active",  # previously "published"
            "superseded": "superseded",  # This version has been replaced by a newer one
            "reverted": "reverted",  # This version has been reverted to a previous one
            "archived": "archived",
            "review": "review",
        },
    )

    # Relationships
    captions = RelationshipTo("app.models.translations.Translation", "HAS_CAPTION")
    category = RelationshipFrom("app.models.categories.Category", "HAS_VERSION")
    icon = RelationshipTo("app.models.assets.Asset", "USES_ICON")
    modules = RelationshipFrom(
        "app.models.modules.Module", "INCLUDED_IN_CATEGORY", model=ModuleResourceRel
    )
