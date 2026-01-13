from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      IntegerProperty, RelationshipTo, RelationshipFrom, StringProperty,
                      StructuredNode, UniqueIdProperty)

from app.utils.sys_date import now


class AssetObject(StructuredNode):
    """Container for Asset versions (grouped by tag + original_filename)."""
    asset_object_id = UniqueIdProperty()
    tag = StringProperty(index=True)
    title = StringProperty(index=True)  # This will store the original_filename
    
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    
    # Relationships
    versions = RelationshipTo("Asset", "HAS_VERSION")
    current_version = RelationshipTo("Asset", "CURRENT_VERSION")


class Asset(StructuredNode):
    asset_id = UniqueIdProperty()
    filename = StringProperty(required=True)
    original_filename = StringProperty()
    tag = StringProperty()
    mime_type = StringProperty()
    extension = StringProperty()
    size_bytes = IntegerProperty()
    sha256 = StringProperty()
    file_url = StringProperty()
    container = StringProperty()
    created_at = DateTimeProperty(default=now())
    updated_at = DateTimeProperty(default=now())
    is_deleted = BooleanProperty(default=False)
    version = FloatProperty(default=1.0)
    status = StringProperty(
        choices={
            "draft": "draft",
            "active": "active",
            "superseded": "superseded",
            "archived": "archived",
        },
        default="draft",
        index=True
    )

    # Relationships
    linked_assets = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
    asset_object = RelationshipFrom("AssetObject", "HAS_VERSION")
    is_current_of = RelationshipFrom("AssetObject", "CURRENT_VERSION")
