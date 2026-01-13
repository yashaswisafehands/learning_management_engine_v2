from neomodel import (DateTimeProperty, FloatProperty, JSONProperty,
                      RelationshipTo, StringProperty, StructuredNode,
                      UniqueIdProperty, RelationshipFrom)

from app.utils.sys_date import now
from neomodel import One


class OnboardingFlow(StructuredNode):
    """Container node for onboarding flow versions."""
    onboarding_flow_id = UniqueIdProperty()
    key = StringProperty(required=True, unique_index=True)  # e.g., "onboarding_{lang_id}"
    
    created_at = DateTimeProperty(default_now=now)
    updated_at = DateTimeProperty(default_now=now)
    
    # Current version pointer
    current_version = RelationshipTo("OnboardingFlowVersion", "CURRENT_VERSION")
    
    # All versions
    versions = RelationshipTo("OnboardingFlowVersion", "HAS_VERSION")
    
    # Link back to Language
    language = RelationshipFrom("app.models.languages.Language", "HAS_ONBOARDING_FLOW", cardinality=One)


class OnboardingFlowVersion(StructuredNode):
    """Versioned content for an onboarding flow."""
    onboarding_flow_version_id = UniqueIdProperty()
    data = JSONProperty()  # Stores the full onboarding flow (list of questions)
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
    
    created_at = DateTimeProperty(default_now=now)
    updated_at = DateTimeProperty(default_now=now)
    created_by = StringProperty(default="System")
    updated_by = StringProperty()

    # Relationships
    # Link back to LanguageVersion is handled by LanguageVersion -> HAS_ONBOARDING_FLOW -> OnboardingFlowVersion
    
    # Link back to container
    onboarding_flow = RelationshipFrom("OnboardingFlow", "HAS_VERSION", cardinality=One)
    
    # Track assets used in this version's data (for referential integrity and graph queries)
    uses_assets = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
