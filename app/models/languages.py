from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      RelationshipFrom, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)

from app.models.language_category_rel import LanguageCategoryRel
from app.models.language_module_rel import LanguageModuleRel
from app.models.language_resource_rel import LanguageResourceRel


class Language(StructuredNode):
    language_id = UniqueIdProperty()
    slug = StringProperty()
    current_version = FloatProperty(default=1.0)
    language_name = StringProperty()
    versions = RelationshipTo("app.models.languages.LanguageVersion", "HAS_VERSION")
    current_version_rel = RelationshipTo(
        "app.models.languages.LanguageVersion", "CURRENT_VERSION"
    )
    onboarding_questions = RelationshipTo(
        "app.models.onboarding_flows.OnboardingFlow", "HAS_ONBOARDING"
    )
    transcriptions = RelationshipTo(
        "app.models.transcriptions.Transcription", "HAS_TRANSCRIPTION"
    )
    screen_data = RelationshipTo("app.models.settings_screen.ScreenData", "HAS_SCREEN_DATA")
    onboarding_flows = RelationshipTo("app.models.onboarding_flows.OnboardingFlow", "HAS_ONBOARDING_FLOW")
    
    # Disabled modules for this language (blacklist approach)
    disabled_modules = RelationshipTo(
        "app.models.modules.Module", "DISABLED_MODULE", model=LanguageModuleRel
    )

    # Disabled resources for this language (blacklist approach)
    disabled_resources = RelationshipTo(
        "app.models.resources.Resource", "DISABLED_RESOURCE", model=LanguageResourceRel
    )



class LanguageVersion(StructuredNode):
    language_version_id = UniqueIdProperty()
    autonym_script = StringProperty()
    learning_platform = BooleanProperty()
    country = StringProperty()
    country_code = StringProperty(index=True)
    region = StringProperty()
    latitude = FloatProperty()
    longitude = FloatProperty()
    version = FloatProperty(default=1.0)
    status = StringProperty(
        required=True,
        index=True,
        choices={
            "draft": "draft",
            "active": "active",  # This is the current active version
            "superseded": "superseded",  # This version has been replaced by a newer one
            "reverted": "reverted",  # This version has been reverted to a previous one
            "archived": "archived",  # This version is archived and not in use
            "review": "review",  # This version is under review
        },
    )

    created_at = DateTimeProperty(default_now=True)
    created_by = StringProperty(default="System")
    is_deleted = BooleanProperty(default=False)

    # Relationships
    language = RelationshipFrom("app.models.languages.Language", "HAS_VERSION")
    icon = RelationshipTo("app.models.assets.Asset", "USES_ICON")
    assets = RelationshipTo("app.models.assets.Asset", "USES_ASSET")
    categories = RelationshipTo("app.models.categories.Category", "USES_CATEGORY", model=LanguageCategoryRel)
