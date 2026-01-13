import types
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from neomodel.exceptions import DoesNotExist

from app.schemas.user_feedbacks import (UserFeedbackAnswerSubmission,
                                        UserFeedbackSubmitRequest)
from app.services.user_feedbacks import (_feedback_to_base,
                                         _feedback_to_schema,
                                         _version_to_schema,
                                         get_questions_for_language,
                                         list_feedbacks, submit_feedback)


class DummyAnswer:
    def __init__(self, answer_id, label, value, order=0, is_default=False, is_correct=False, metadata=None):
        self.answer_id = answer_id
        self.label = label
        self.value = value
        self.order = order
        self.is_default = is_default
        self.is_correct = is_correct
        self.metadata = metadata


class DummyQuestion:
    def __init__(self, question_key, label, question_type, order=0, answers=None):
        self.question_key = question_key
        self.label = label
        self.question_type = question_type
        self.help_text = "Help"
        self.required = True
        self.order = order
        self.metadata = "meta"
        self.answers = types.SimpleNamespace(all=lambda: answers or [])


class DummyVersion:
    def __init__(self, feedback_version_id, content_type="original", status="draft", version=1.0, questions=None):
        self.feedback_version_id = feedback_version_id
        self.content_type = content_type
        self.status = status
        self.version = version
        self.title = "Feedback"
        self.description = "Description"
        self.created_at = datetime.utcnow()
        self.created_by = "tester"
        self.region = "GLOBAL"
        self.questions = types.SimpleNamespace(all=lambda: questions or [])
        self.language = types.SimpleNamespace(single=lambda: None)
        self.derived_from = types.SimpleNamespace(single=lambda: None)
        self.feedback = types.SimpleNamespace(single=lambda: None)


class DummyFeedback:
    def __init__(self, feedback_id="ufb-1", slug="ufb-sample", tag="sample"):
        self.feedback_id = feedback_id
        self.slug = slug
        self.title = "Feedback"
        self.tag = tag
        self.is_deleted = False
        self.current_original_version = types.SimpleNamespace(single=lambda: None)
        self.current_adapted_versions = types.SimpleNamespace(all=lambda: [])
        self.current_translated_versions = types.SimpleNamespace(all=lambda: [])
        self.versions = types.SimpleNamespace(all=lambda: [])


class FakeDoesNotExist(DoesNotExist):
    _model_class = object()


class MissingRelationship:
    def single(self):
        raise FakeDoesNotExist("no relationship")


@pytest.mark.parametrize(
    "answers",
    [
        [DummyAnswer("ans-1", "Yes", "yes", order=1, is_default=True)],
        [],
    ],
)
def test_version_to_schema_serialises_questions(answers):
    question = DummyQuestion("q-1", "How are you?", "single_choice", order=5, answers=answers)
    version = DummyVersion("ufbv-1", questions=[question])

    schema = _version_to_schema(version)

    assert schema.feedback_version_id == "ufbv-1"
    assert schema.questions[0].question_key == "q-1"
    assert len(schema.questions[0].answers) == len(answers)
    if answers:
        assert schema.questions[0].answers[0].answer_id == "ans-1"
        assert schema.questions[0].answers[0].is_default is True


def test_feedback_to_schema_includes_versions():
    original = DummyVersion("ufbv-1", status="active")
    adapted = DummyVersion("ufbv-2", content_type="adapted", version=2.0)
    translated = DummyVersion("ufbv-3", content_type="translated", version=3.0)

    feedback = DummyFeedback()
    feedback.current_original_version = types.SimpleNamespace(single=lambda: original)
    feedback.current_adapted_versions = types.SimpleNamespace(all=lambda: [adapted])
    feedback.current_translated_versions = types.SimpleNamespace(all=lambda: [translated])
    feedback.versions = types.SimpleNamespace(all=lambda: [translated, adapted, original])

    schema = _feedback_to_schema(feedback)

    assert schema.feedback_id == "ufb-1"
    assert schema.slug == "ufb-sample"
    assert schema.current_original_version.feedback_version_id == "ufbv-1"
    assert schema.current_adapted_versions[0].feedback_version_id == "ufbv-2"
    assert schema.current_translated_versions[0].feedback_version_id == "ufbv-3"


def test_feedback_to_base_uses_parent_metadata():
    version = DummyVersion("ufbv-1")
    parent = DummyFeedback()
    version.feedback = types.SimpleNamespace(single=lambda: parent)

    base = _feedback_to_base(version)

    assert base.feedback_id == "ufb-1"
    assert base.slug == "ufb-sample"
    assert base.tag == "sample"


def test_feedback_to_schema_handles_missing_current_original():
    feedback = DummyFeedback()
    feedback.current_original_version = MissingRelationship()
    feedback.versions = types.SimpleNamespace(all=lambda: [])

    schema = _feedback_to_schema(feedback)

    assert schema.current_original_version is None


@pytest.mark.asyncio
@patch("app.services.user_feedbacks.run_sync")
async def test_list_feedbacks_returns_base(mock_run_sync):
    version = DummyVersion("ufbv-1")
    mock_run_sync.return_value = [version]

    result = await list_feedbacks(include_containers=False)

    assert len(result) == 1
    assert result[0].feedback_id == "ufbv-1"
    mock_run_sync.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.user_feedbacks.UserFeedbackResponseRepository.save_responses")
async def test_submit_feedback_calls_repository(mock_save):
    mock_save.return_value = [MagicMock(), MagicMock()]

    payload = UserFeedbackSubmitRequest(
        language_id="en",
        user_id="user-1",
        answers=[
            UserFeedbackAnswerSubmission(
                question_id="q-1",
                answer_id="ans-1",
                answer_value="yes",
            )
        ],
    )

    response = await submit_feedback(payload)

    assert response.saved_count == 2
    mock_save.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.user_feedbacks.UserFeedbackRepository.get_active_questions")
@patch("app.services.user_feedbacks.run_sync")
async def test_get_questions_for_language(mock_run_sync, mock_repo):
    mock_repo.return_value = []
    mock_run_sync.return_value = []

    result = await get_questions_for_language("en")

    assert result == []
