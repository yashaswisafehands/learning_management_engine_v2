from neomodel import (BooleanProperty, DateTimeProperty, FloatProperty,
                      IntegerProperty, RelationshipFrom, RelationshipTo,
                      StringProperty, StructuredNode, UniqueIdProperty)

from app.utils.sys_date import now


class UserFeedback(StructuredNode):
    """Container node for user feedback flows with version support."""

    feedback_id = UniqueIdProperty()
    title = StringProperty(required=True)
    slug = StringProperty(required=True, unique_index=True)
    tag = StringProperty(index=True, required=True)
    is_deleted = BooleanProperty(default=False)

    current_original_version = RelationshipTo("UserFeedbackVersion", "CURRENT_ORIGINAL")
    current_adapted_versions = RelationshipTo(
        "UserFeedbackVersion", "CURRENT_ADAPTATION"
    )
    current_translated_versions = RelationshipTo(
        "UserFeedbackVersion", "CURRENT_TRANSLATION"
    )
    versions = RelationshipTo("UserFeedbackVersion", "HAS_VERSION")


class UserFeedbackVersion(StructuredNode):
    """Versioned node holding feedback question sets."""

    feedback_version_id = UniqueIdProperty()
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

    derived_from = RelationshipTo("UserFeedbackVersion", "DERIVED_FROM")
    language = RelationshipTo("app.models.languages.Language", "IN_LANGUAGE")
    region = StringProperty(index=True, default=None)

    questions = RelationshipTo("UserFeedbackQuestion", "HAS_QUESTION")
    feedback = RelationshipTo("UserFeedback", "VERSION_OF")


class UserFeedbackQuestion(StructuredNode):
    """Question node linked to a specific feedback version."""

    question_id = UniqueIdProperty()
    question_key = StringProperty(required=True)
    label = StringProperty(required=True)
    question_type = StringProperty(required=True)
    help_text = StringProperty()
    required = BooleanProperty(default=False)
    order = IntegerProperty(default=0)
    metadata = StringProperty()

    version = RelationshipFrom("UserFeedbackVersion", "HAS_QUESTION")
    answers = RelationshipTo("UserFeedbackAnswer", "HAS_ANSWER")


class UserFeedbackAnswer(StructuredNode):
    """Answer option node for a user feedback question."""

    answer_id = UniqueIdProperty()
    label = StringProperty(required=True)
    value = StringProperty(required=True)
    order = IntegerProperty(default=0)
    is_default = BooleanProperty(default=False)
    is_correct = BooleanProperty(default=False)
    metadata = StringProperty()

    question = RelationshipFrom("UserFeedbackQuestion", "HAS_ANSWER")


class UserFeedbackResponse(StructuredNode):
    """Captured response for a feedback question."""

    response_id = UniqueIdProperty()
    user_id = StringProperty()  # allow anonymous submissions
    language_id = StringProperty()
    region = StringProperty()
    question_key = StringProperty(required=True)
    answer_value = StringProperty()
    free_text = StringProperty()
    created_at = DateTimeProperty(default_now=now)

    version = RelationshipTo("UserFeedbackVersion", "RESPONSE_FOR_VERSION")
    question = RelationshipTo("UserFeedbackQuestion", "RESPONSE_FOR_QUESTION")
    answer = RelationshipTo("UserFeedbackAnswer", "SELECTED_ANSWER")
