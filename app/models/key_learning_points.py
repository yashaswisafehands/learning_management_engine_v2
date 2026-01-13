from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      IntegerProperty, RelationshipTo, StringProperty,
                      StructuredNode, UniqueIdProperty)

from app.utils.sys_date import now


class KeyLearningPoint(StructuredNode):
    """Container for Key Learning Point versions - following Resource pattern."""

    klp_id = UniqueIdProperty()
    title = StringProperty(required=True)
    slug = StringProperty(required=True, unique_index=True)
    is_deleted = BooleanProperty(default=False)
    level = StringProperty(index=True, required=True)

    # Current pointers (following Resource pattern)
    current_original_version = RelationshipTo(
        "KeyLearningPointVersion", "CURRENT_ORIGINAL"
    )
    current_adapted_versions = RelationshipTo(
        "KeyLearningPointVersion", "CURRENT_ADAPTATION"
    )
    current_translated_versions = RelationshipTo(
        "KeyLearningPointVersion", "CURRENT_TRANSLATION"
    )

    # All versions
    versions = RelationshipTo("KeyLearningPointVersion", "HAS_VERSION")

    # Module relationship
    module = RelationshipTo("app.models.modules.Module", "BELONGS_TO_MODULE")


class KeyLearningPointVersion(StructuredNode):
    """Versioned content for Key Learning Point - following ResourceVersion pattern."""

    klp_version_id = UniqueIdProperty()
    title = StringProperty(required=True)
    description = StringProperty()

    # Content type following Resource pattern
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
        default="draft",
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
    is_deleted = BooleanProperty(default=False)

    # Derivation relationships (following Resource pattern)
    derived_from = RelationshipTo("KeyLearningPointVersion", "DERIVED_FROM")

    # Language and region (following Resource pattern)
    language = RelationshipTo("app.models.languages.Language", "IN_LANGUAGE")
    language_id = StringProperty(index=True)
    region = StringProperty(index=True, default=None)

    # KLP specific: Questions instead of Assets
    questions = RelationshipTo("KLPQuestion", "HAS_QUESTION")

    # Parent relationship
    key_learning_point = RelationshipTo("KeyLearningPoint", "VERSION_OF")


class KLPQuestion(StructuredNode):
    """Question node - replaces Asset content in Resource pattern."""

    question_id = UniqueIdProperty()
    question = StringProperty(required=True)
    quizz_type = StringProperty(required=True)
    show_toggle = BooleanProperty(default=False)
    essential = BooleanProperty(default=False)
    description = StringProperty()
    order = IntegerProperty(default=0)

    # Question assets
    icon = RelationshipTo("app.models.assets.Asset", "USES_ICON")
    link = RelationshipTo("app.models.resources.Resource", "LINKS_TO")

    # Answers
    answers = RelationshipTo("KLPAnswer", "HAS_ANSWER")


class KLPAnswer(StructuredNode):
    """Answer options for KLP questions."""

    answer_id = UniqueIdProperty()
    value = StringProperty(required=True)
    correct = BooleanProperty(default=False)
    order = IntegerProperty(default=0)
