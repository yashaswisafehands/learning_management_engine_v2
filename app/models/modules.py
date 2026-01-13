from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      RelationshipFrom, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)

from app.models.module_resource_rel import ModuleResourceRel


class Module(StructuredNode):
    module_id = UniqueIdProperty()
    title = StringProperty(required=True)
    slug = StringProperty()
    current_version = FloatProperty(default=1.0)

    versions = RelationshipTo("app.models.modules.ModuleVersion", "HAS_VERSION")
    current_version_rel = RelationshipTo(
        "app.models.modules.ModuleVersion", "CURRENT_VERSION"
    )

    # Categories this module is included in (establish relationship from module side)
    categories = RelationshipTo(
        "app.models.categories.CategoryVersion",
        "INCLUDED_IN_CATEGORY",
        model=ModuleResourceRel,
    )


class ModuleVersion(StructuredNode):
    module_version_id = UniqueIdProperty()
    title = StringProperty(required=True)
    version = FloatProperty(default=1.0)
    description = StringProperty()
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

    created_at = DateTimeProperty(default_now=True)
    is_deleted = BooleanProperty(default=False)
    created_by = StringProperty(default="System")

    # Relationships
    module = RelationshipFrom("app.models.modules.Module", "HAS_VERSION")
    icon = RelationshipTo("app.models.assets.Asset", "USES_ICON")

    videos = RelationshipTo(
        "app.models.resources.Resource", "HAS_VIDEO", model=ModuleResourceRel
    )

    action_cards = RelationshipTo(
        "app.models.resources.Resource", "HAS_ACTION_CARD", model=ModuleResourceRel
    )

    practical_procedures = RelationshipTo(
        "app.models.resources.Resource",
        "HAS_PRACTICAL_PROCEDURE",
        model=ModuleResourceRel,
    )

    drugs = RelationshipTo(
        "app.models.resources.Resource", "HAS_DRUG", model=ModuleResourceRel
    )

    key_learning_points = RelationshipTo(
        "app.models.key_learning_points.KeyLearningPoint",
        "HAS_KEY_LEARNING_POINT",
    )
