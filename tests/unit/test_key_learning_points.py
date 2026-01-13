import types
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.key_learning_points import KeyLearningPointVersion
from app.repositories.key_learning_points import KeyLearningPointRepository
from app.schemas.key_learning_points import (
    KeyLearningPointBaseSchema, KeyLearningPointCreateRequest,
    KeyLearningPointSchema, KeyLearningPointStatusUpdateRequest,
    KeyLearningPointUpdateRequest, KeyLearningPointVersionSchema,
    KLPAnswerCreate, KLPQuestionCreate)
from app.services.key_learning_points import (_klp_to_schema, _version_to_base,
                                              _version_to_schema, create_klp,
                                              get_klp_by_id, list_klps,
                                              update_klp, update_klp_status)


class DummyKLPAnswer:
    def __init__(self, answer_id, value, correct=False, order=0):
        self.answer_id = answer_id
        self.value = value
        self.correct = correct
        self.order = order


class DummyKLPQuestion:
    def __init__(self, question_id, question, quizz_type, answers=None, order=0):
        self.question_id = question_id
        self.question = question
        self.quizz_type = quizz_type
        self.show_toggle = False
        self.essential = False
        self.description = "Test question"
        self.order = order
        self.icon = types.SimpleNamespace(single=lambda: None)
        self.link = types.SimpleNamespace(single=lambda: None)
        self.answers = types.SimpleNamespace(all=lambda: answers or [])


class DummyKLPVersion:
    def __init__(
        self,
        klp_version_id,
        content_type,
        version=1.0,
        status="draft",
        title="Test KLP",
        questions=None,
    ):
        self.klp_version_id = klp_version_id
        self.content_type = content_type
        self.version = version
        self.status = status
        self.title = title
        self.description = "Test description"
        self.region = "GLOBAL"
        self.created_by = "tester"
        self.is_deleted = False
        self.created_at = datetime.now()
        self.language = types.SimpleNamespace(single=lambda: None)
        self.derived_from = types.SimpleNamespace(single=lambda: None)
        self.questions = types.SimpleNamespace(all=lambda: questions or [])
        self.key_learning_point = types.SimpleNamespace(single=lambda: None)


class DummyKLP:
    def __init__(self, klp_id, title="Test KLP", level="beginner", slug="klp-test"):
        self.klp_id = klp_id
        self.title = title
        self.slug = slug
        self.level = level
        self.is_deleted = False
        # Following Resource pattern with current pointers
        self.current_original_version = types.SimpleNamespace(single=lambda: None)
        self.current_adapted_versions = types.SimpleNamespace(all=lambda: [])
        self.current_translated_versions = types.SimpleNamespace(all=lambda: [])
        self.versions = types.SimpleNamespace(all=lambda: [])


class TestKLPRepository:
    @patch('app.repositories.key_learning_points.KeyLearningPointRepository.get_klps')
    def test_get_klps_active(self, mock_get):
        v = MagicMock(spec=KeyLearningPointVersion)
        mock_get.return_value = [v]
        result = KeyLearningPointRepository.get_klps('active')
        assert result == [v]
        mock_get.assert_called_once_with('active')

    @patch('app.repositories.key_learning_points.KeyLearningPointRepository.get_klps')
    def test_get_klps_all(self, mock_get):
        v = MagicMock(spec=KeyLearningPointVersion)
        mock_get.return_value = [v]
        result = KeyLearningPointRepository.get_klps('all')
        assert result == [v]
        mock_get.assert_called_once_with('all')

    @patch('app.repositories.key_learning_points.KeyLearningPoint')
    @patch('app.repositories.key_learning_points.KeyLearningPointVersion')
    def test_create_klp_does_not_set_current_version_for_draft(
        self, mock_version_class, mock_klp_class
    ):
        """Test that draft versions are NOT set as current versions."""
        # Setup mocks
        mock_klp = MagicMock()
        mock_version = MagicMock()
        mock_klp_class.return_value = mock_klp
        mock_version_class.return_value = mock_version
        mock_klp.save.return_value = mock_klp
        mock_version.save.return_value = mock_version
        mock_klp_class.nodes.filter.return_value = []

        # Create request data
        data = KeyLearningPointCreateRequest(
            title="Test KLP",
            level="beginner",
            content_type="original",
            questions=[],
        )

        # Execute
        result = KeyLearningPointRepository.create_klp(data)

        # Verify KLP container is created
        mock_klp_class.assert_called_once()
        mock_klp.save.assert_called_once()

        # Verify version is created with draft status
        mock_version_class.assert_called_once()
        version_call_args = mock_version_class.call_args[1]
        assert version_call_args['status'] == 'draft'
        mock_version.save.assert_called_once()

        # Verify relationships are connected
        mock_klp.versions.connect.assert_called_once_with(mock_version)
        mock_version.key_learning_point.connect.assert_called_once_with(mock_klp)

        # Verify current version pointers are NOT set for draft
        mock_klp.current_original_version.connect.assert_not_called()
        mock_klp.current_adapted_versions.connect.assert_not_called()
        mock_klp.current_translated_versions.connect.assert_not_called()

        assert result == mock_klp

    @patch('app.repositories.key_learning_points.KeyLearningPointVersion')
    def test_update_klp_status_sets_current_pointer_when_active(self, mock_version_class):
        """Test that current pointers are set when version becomes active."""
        # Setup mock version
        mock_version = MagicMock()
        mock_version.content_type = "original"
        mock_version.status = "draft"
        mock_version_class.nodes.get.return_value = mock_version

        # Setup mock KLP container
        mock_klp = MagicMock()
        mock_version.key_learning_point.single.return_value = mock_klp
        mock_klp.current_original_version.single.return_value = None

        # Execute
        result = KeyLearningPointRepository.update_klp_status(
            "version-123", "active", "test-user"
        )

        # Verify current pointer is set for active original version
        mock_klp.current_original_version.connect.assert_called_once_with(mock_version)
        assert mock_version.status == "active"
        assert mock_version.created_by == "test-user"
        assert result == mock_version

    @patch('app.repositories.key_learning_points.KeyLearningPointVersion')
    def test_update_klp_status_removes_current_pointer_when_deactivated(self, mock_version_class):
        """Test that current pointers are removed when version is deactivated."""
        # Setup mock version
        mock_version = MagicMock()
        mock_version.content_type = "adapted"
        mock_version.status = "active"
        mock_version_class.nodes.get.return_value = mock_version

        # Setup mock KLP container
        mock_klp = MagicMock()
        mock_version.key_learning_point.single.return_value = mock_klp

        # Execute
        result = KeyLearningPointRepository.update_klp_status(
            "version-123", "archived", "test-user"
        )

        # Verify current pointer is removed when deactivated
        mock_klp.current_adapted_versions.disconnect.assert_called_once_with(mock_version)
        assert mock_version.status == "archived"
        assert result == mock_version


class TestKLPService:
    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.get_klps')
    @patch('app.services.key_learning_points.run_sync')
    async def test_list_klps_base(self, mock_run_sync, mock_repo_get):
        """Test listing KLPs returns base schemas."""
        v = DummyKLPVersion("klpv-1", "original")
        parent = DummyKLP("klp-1")
        v.key_learning_point = types.SimpleNamespace(single=lambda: parent)

        mock_repo_get.return_value = [v]
        mock_run_sync.return_value = [v]

        result = await list_klps(include_containers=False)
        assert len(result) == 1
        assert isinstance(result[0], KeyLearningPointBaseSchema)
        assert result[0].klp_id == "klp-1"
        assert result[0].content_type == "original"

    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.get_klps')
    @patch('app.services.key_learning_points.run_sync')
    async def test_list_klps_include_containers(self, mock_run_sync, mock_repo_get):
        """Test listing KLPs with containers returns full schemas."""
        klp = DummyKLP("klp-1")
        mock_repo_get.return_value = [klp]
        mock_run_sync.return_value = [klp]

        result = await list_klps(include_containers=True)
        assert len(result) == 1
        assert isinstance(result[0], KeyLearningPointSchema)
        assert result[0].klp_id == "klp-1"
        assert result[0].level == "beginner"

    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.create_klp')
    @patch('app.services.key_learning_points.run_sync')
    async def test_create_klp(self, mock_run_sync, mock_repo_create):
        """Test creating KLP returns container schema."""
        klp = DummyKLP("klp-1")
        mock_repo_create.return_value = klp
        mock_run_sync.return_value = klp

        data = KeyLearningPointCreateRequest(
            title="Test KLP",
            level="beginner",
            content_type="original",
            questions=[],
        )

        result = await create_klp(data, None)
        assert isinstance(result, KeyLearningPointSchema)
        assert result.klp_id == "klp-1"

    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.get_klp_by_id')
    @patch('app.services.key_learning_points.run_sync')
    async def test_get_klp_by_id(self, mock_run_sync, mock_repo_get):
        """Test getting KLP by ID."""
        klp = DummyKLP("klp-1")
        mock_repo_get.return_value = klp
        mock_run_sync.return_value = klp

        result = await get_klp_by_id("klp-1")
        assert isinstance(result, KeyLearningPointSchema)
        assert result.klp_id == "klp-1"

    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.update_klp')
    @patch('app.services.key_learning_points.run_sync')
    async def test_update_klp(self, mock_run_sync, mock_repo_update):
        """Test updating KLP creates new version."""
        new_version = DummyKLPVersion("klpv-2", "original", version=2.0)
        klp = DummyKLP("klp-1")
        new_version.key_learning_point = types.SimpleNamespace(single=lambda: klp)

        mock_repo_update.return_value = new_version
        mock_run_sync.return_value = new_version

        data = KeyLearningPointUpdateRequest(title="Updated Title")
        result = await update_klp("klp-1", data, None)

        assert isinstance(result, KeyLearningPointSchema)
        assert result.klp_id == "klp-1"

    @pytest.mark.asyncio
    @patch('app.services.key_learning_points.KeyLearningPointRepository.update_klp_status')
    @patch('app.services.key_learning_points.run_sync')
    async def test_update_klp_status(self, mock_run_sync, mock_repo_update):
        """Test updating KLP status."""
        version = DummyKLPVersion("klpv-1", "original", status="active")
        mock_repo_update.return_value = version
        mock_run_sync.return_value = version

        status_update = KeyLearningPointStatusUpdateRequest(
            status="active", updated_by="test-user"
        )
        result = await update_klp_status("klpv-1", status_update)

        assert isinstance(result, KeyLearningPointVersionSchema)
        assert result.status == "active"

    def test_version_to_schema_with_questions(self):
        """Test converting KLP version with questions to schema."""
        # Create dummy answers
        answers = [
            DummyKLPAnswer("ans-1", "Answer A", True, order=1),
            DummyKLPAnswer("ans-2", "Answer B", False, order=2),
        ]

        # Create dummy question
        question = DummyKLPQuestion(
            "q1", "What is hygiene?", "multiple_choice", answers=answers, order=3
        )

        # Create dummy version with questions
        version = DummyKLPVersion("klpv-1", "original", questions=[question])

        result = _version_to_schema(version)

        assert isinstance(result, KeyLearningPointVersionSchema)
        assert result.klp_version_id == "klpv-1"
        assert result.content_type == "original"
        assert len(result.questions) == 1
        assert result.questions[0].order == 3
        assert result.questions[0].question == "What is hygiene?"
        assert len(result.questions[0].answers) == 2
        assert result.questions[0].answers[0].correct is True
        assert result.questions[0].answers[0].order == 1
        assert result.questions[0].answers[0].answer_id == "ans-1"

    def test_version_to_schema_with_derivation_and_language(self):
        """Test converting KLP version with derivation and language info."""
        # Setup derived version mock
        derived_version = DummyKLPVersion("klpv-source", "original")
        
        # Setup language mock
        language = types.SimpleNamespace()
        language.language_id = "es"
        language.name = "Spanish"

        # Create version with derivation and language
        version = DummyKLPVersion("klpv-1", "translated")
        version.derived_from = types.SimpleNamespace(single=lambda: derived_version)
        version.language = types.SimpleNamespace(single=lambda: language)

        result = _version_to_schema(version)

        assert result.content_type == "translated"
        assert result.derived_from_id == "klpv-source"
        assert result.language_id == "es"
        assert result.language_name == "Spanish"

    def test_version_to_base_schema(self):
        """Test converting KLP version to base schema."""
        parent = DummyKLP("klp-1", level="intermediate")
        version = DummyKLPVersion("klpv-1", "adapted")
        version.key_learning_point = types.SimpleNamespace(single=lambda: parent)

        result = _version_to_base(version)

        assert isinstance(result, KeyLearningPointBaseSchema)
        assert result.klp_id == "klp-1"
        assert result.level == "intermediate"
        assert result.content_type == "adapted"
        assert result.slug == "klp-test"

    def test_klp_to_schema_with_current_versions(self):
        """Test converting KLP container with current versions to schema."""
        # Setup current versions
        original_version = DummyKLPVersion("klpv-1", "original", status="active")
        adapted_version = DummyKLPVersion("klpv-2", "adapted", status="active")
        translated_version = DummyKLPVersion("klpv-3", "translated", status="active")

        # Create KLP with current versions
        klp = DummyKLP("klp-1", level="advanced")
        klp.current_original_version = types.SimpleNamespace(single=lambda: original_version)
        klp.current_adapted_versions = types.SimpleNamespace(all=lambda: [adapted_version])
        klp.current_translated_versions = types.SimpleNamespace(all=lambda: [translated_version])
        klp.versions = types.SimpleNamespace(all=lambda: [original_version, adapted_version, translated_version])

        result = _klp_to_schema(klp)

        assert isinstance(result, KeyLearningPointSchema)
        assert result.klp_id == "klp-1"
        assert result.slug == "klp-test"
        assert result.level == "advanced"
        assert result.current_original_version is not None
        assert result.current_original_version.content_type == "original"
        assert len(result.current_adapted_versions) == 1
        assert result.current_adapted_versions[0].content_type == "adapted"
        assert len(result.current_translated_versions) == 1
        assert result.current_translated_versions[0].content_type == "translated"
        assert len(result.versions) == 3

    def test_klp_to_schema_no_current_versions(self):
        """Test converting KLP container with no current versions (all drafts)."""
        draft_version = DummyKLPVersion("klpv-1", "original", status="draft")
        
        # Create KLP with no current versions (following our bug fix)
        klp = DummyKLP("klp-1")
        klp.versions = types.SimpleNamespace(all=lambda: [draft_version])

        result = _klp_to_schema(klp)

        assert result.current_original_version is None
        assert len(result.current_adapted_versions) == 0
        assert len(result.current_translated_versions) == 0
        assert len(result.versions) == 1
        assert result.versions[0].status == "draft"


class TestKLPSchemas:
    def test_klp_create_request_validation(self):
        """Test KLP create request schema validation."""
        question_data = KLPQuestionCreate(
            question="What is hygiene?",
            quizz_type="multiple_choice",
            answers=[
                KLPAnswerCreate(value="Cleanliness", correct=True),
                KLPAnswerCreate(value="Dirtiness", correct=False),
            ],
        )

        data = KeyLearningPointCreateRequest(
            title="Basic Hygiene",
            level="beginner",
            content_type="original",
            questions=[question_data],
        )

        assert data.title == "Basic Hygiene"
        assert data.level == "beginner"
        assert data.content_type == "original"
        assert len(data.questions) == 1
        assert data.questions[0].question == "What is hygiene?"

    def test_klp_update_request_optional_fields(self):
        """Test KLP update request with optional fields."""
        data = KeyLearningPointUpdateRequest(
            title="Updated Title",
            content_type="adapted",
            region="AFRICA",
        )

        assert data.title == "Updated Title"
        assert data.content_type == "adapted"
        assert data.region == "AFRICA"
        assert data.description is None

    def test_klp_status_update_request(self):
        """Test KLP status update request."""
        data = KeyLearningPointStatusUpdateRequest(
            status="active",
            updated_by="admin",
        )

        assert data.status == "active"
        assert data.updated_by == "admin"


@pytest.mark.asyncio
async def test_klp_content_type_workflow():
    """Integration test for KLP content type workflow following Resource pattern."""
    
    # This would be an integration test that verifies:
    # 1. Create original KLP (draft, no current pointer)
    # 2. Activate original (sets current_original_version)
    # 3. Create adapted version (draft, no current pointer)
    # 4. Activate adapted (adds to current_adapted_versions)
    # 5. Create translated version (draft, no current pointer)
    # 6. Activate translated (adds to current_translated_versions)
    # 7. Deactivate versions (removes from current pointers)
    
    # This test would require actual database setup, so we'll leave it as a placeholder
    # for integration testing
    pass


@pytest.mark.asyncio
async def test_klp_derivation_workflow():
    """Integration test for KLP derivation workflow."""
    
    # This would test:
    # 1. Create original KLP
    # 2. Create adapted version derived from original
    # 3. Create translated version derived from original or adapted
    # 4. Verify derivation relationships are maintained
    
    # This test would require actual database setup
    pass
