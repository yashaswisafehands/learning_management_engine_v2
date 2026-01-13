from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      RelationshipTo, StringProperty, StructuredNode,
                      UniqueIdProperty)

from app.utils.sys_date import now


class Resource(StructuredNode):
    resource_id = UniqueIdProperty()
    title = StringProperty(required=True)
    slug = StringProperty(required=True, unique_index=True)
    is_deleted = BooleanProperty(default=False)
    tag = StringProperty(index=True, required=True)

    # Current pointers
    current_original_version = RelationshipTo("ResourceVersion", "CURRENT_ORIGINAL")
    current_adapted_versions = RelationshipTo("ResourceVersion", "CURRENT_ADAPTATION")
    current_translated_versions = RelationshipTo(
        "ResourceVersion", "CURRENT_TRANSLATION"
    )

    # All versions
    versions = RelationshipTo(
        "ResourceVersion", "HAS_VERSION"
    )  # All versions language_id + active


class ResourceVersion(StructuredNode):
    resource_version_id = UniqueIdProperty()
    title = StringProperty(required=True)
    description = StringProperty()

    content_type = StringProperty(
        required=True,
        index=True,
        choices={
            "original": "original",
            "adapted": "adapted",
            "translated": "translated",
        },
    )
    version = FloatProperty(default=1.0)
    status = StringProperty(
        required=True,
        index=True,
        choices={
            "draft": "draft",
            "active": "active",
            "superseded": "superseded",
            "reverted": "reverted",
            "archived": "archived",
            "review": "review",
        },
    )

    created_at = DateTimeProperty(default_now=now)
    created_by = StringProperty(default="System")

    # Derivation relationships
    derived_from = RelationshipTo("ResourceVersion", "DERIVED_FROM")

    # Language and region
    language = RelationshipTo(
        "app.models.languages.Language", "IN_LANGUAGE"
    )  # For translations
    region = StringProperty(index=True, default=None)  # For adaptations

    # Assets (icon, content)
    icon = RelationshipTo("app.models.assets.Asset", "USES_ICON")
    content = RelationshipTo("app.models.assets.Asset", "USES_CONTENT")
