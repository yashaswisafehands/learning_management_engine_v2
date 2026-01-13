from neomodel import (DateTimeProperty, FloatProperty, JSONProperty, One,
                      RelationshipFrom, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)


class ScreenData(StructuredNode):
    """Container node for screen data versions (e.g., 'Login Button')."""
    data_id = UniqueIdProperty()
    key = StringProperty(required=True, unique_index=True)  # e.g., "Login Button"
    
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    
    # Current version pointer (only one current version at a time)
    current_version = RelationshipTo("ScreenDataVersion", "CURRENT_VERSION")
    
    # All versions
    versions = RelationshipTo("ScreenDataVersion", "HAS_VERSION")
    
    # Link back to Language
    language = RelationshipFrom("app.models.languages.Language", "HAS_SCREEN_DATA", cardinality=One)


class ScreenDataVersion(StructuredNode):
    """Versioned content for screen data."""
    screen_data_version_id = UniqueIdProperty()
    data = JSONProperty()  # Stores the full screen data
    version = FloatProperty(default=1.0)
    status = StringProperty(
        index=True,
        choices={
            "draft": "draft",
            "active": "active",
            "superseded": "superseded",
            "archived": "archived",
        },
        default="draft"
    )
    
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    created_by = StringProperty(default="System")
    updated_by = StringProperty()
    
    # Relationship to Language is via container
    # language_version relationship removed
    
    # Link back to container
    screen_data = RelationshipFrom("ScreenData", "HAS_VERSION", cardinality=One)
    
    # Track assets used in this version's data (for referential integrity and graph queries)
    uses_assets = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
