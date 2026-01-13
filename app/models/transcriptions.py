from neomodel import (DateTimeProperty, FloatProperty, JSONProperty, One,
                      RelationshipFrom, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)


class Transcription(StructuredNode):
    """Container node for transcription versions (e.g., 'Settings', 'Login')."""
    transcription_id = UniqueIdProperty()
    key = StringProperty(required=True, unique_index=True)  # e.g., "Settings"
    
    created_at = DateTimeProperty(default_now=True)
    updated_at = DateTimeProperty(default_now=True)
    
    # Current version pointer (only one current version at a time)
    current_version = RelationshipTo("TranscriptionVersion", "CURRENT_VERSION")
    
    # All versions
    versions = RelationshipTo("TranscriptionVersion", "HAS_VERSION")
    
    # Link back to Language
    language = RelationshipFrom("app.models.languages.Language", "HAS_TRANSCRIPTION", cardinality=One)


class TranscriptionVersion(StructuredNode):
    """Versioned content for a transcription."""
    transcription_version_id = UniqueIdProperty()
    data = JSONProperty()  # Stores the full transcription data
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
    transcription = RelationshipFrom("Transcription", "HAS_VERSION", cardinality=One)
