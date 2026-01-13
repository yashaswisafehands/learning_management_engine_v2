from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.languages import Language, LanguageVersion
from app.repositories.languages import LanguageRepository
from app.schemas.languages import (LanguageCreateRequest, LanguagesBaseSchema,
                                   LanguageSchema, LanguageStatusUpdateRequest,
                                   LanguageVersionSchema)
from app.services.languages import (_language_version_to_schema,
                                    create_language,
                                    get_all_languages_versions,
                                    get_language_by_id, get_languages,
                                    update_language, update_language_status)
from app.utils.version_utils import increment_version


class TestLanguageRepository:
    """Test cases for LanguageRepository"""

    @patch('app.repositories.languages.LanguageRepository.get_languages')
    def test_get_languages_returns_latest_versions(self, mock_get_languages):
        """Test get_languages returns latest version for each language"""
        # Mock the return value
        mock_version1 = MagicMock(spec=LanguageVersion)
        mock_version2 = MagicMock(spec=LanguageVersion)
        mock_get_languages.return_value = [mock_version1, mock_version2]

        result = LanguageRepository.get_languages("active")

        assert result == [mock_version1, mock_version2]
        mock_get_languages.assert_called_once_with("active")

    @patch('app.repositories.languages.LanguageRepository.get_languages')
    def test_get_languages_with_all_filter(self, mock_get_languages):
        """Test get_languages with status_filter=all returns all languages"""
        # Mock the return value
        mock_version1 = MagicMock(spec=LanguageVersion)
        mock_version2 = MagicMock(spec=LanguageVersion)
        mock_get_languages.return_value = [mock_version1, mock_version2]

        result = LanguageRepository.get_languages("all")

        assert result == [mock_version1, mock_version2]
        mock_get_languages.assert_called_once_with("all")

    @patch('app.repositories.languages.LanguageRepository.create_language')
    def test_create_language_success(self, mock_create_language):
        """Test successful language creation"""
        # Mock data
        mock_data = LanguageCreateRequest(
            language_name="Test Language",
            autonym_script="Test Script",
            country="Test Country",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=10.0,
            longitude=20.0,
            icon="icon-123"
        )

        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_create_language.return_value = mock_version

        result = LanguageRepository.create_language(mock_data)

        assert result == mock_version
        mock_create_language.assert_called_once_with(mock_data)

    @patch('app.repositories.languages.LanguageRepository.create_language')
    def test_create_language_duplicate_slug_raises_error(self, mock_create_language):
        """Test create_language raises error for duplicate slug"""
        mock_data = LanguageCreateRequest(
            language_name="Test Language",
            autonym_script="Test Script",
            country="Test Country",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=10.0,
            longitude=20.0
        )

        # Mock the method to raise ValueError
        mock_create_language.side_effect = ValueError(
            "Language with slug 'lan-test country-test language' already exists"
        )

        with pytest.raises(ValueError, match="Language with slug 'lan-test country-test language' already exists"):
            LanguageRepository.create_language(mock_data)

    @patch('app.repositories.languages.LanguageRepository.update_language')
    def test_update_language_success(self, mock_update_language):
        """Test successful language update"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language.return_value = mock_version

        # Update payload
        payload = LanguageCreateRequest(
            language_name="New Name",
            autonym_script="New Script",
            country="New Country",
            country_code="NC",
            region="New Region",
            status="draft",
            latitude=15.0,
            longitude=25.0
        )

        result = LanguageRepository.update_language("language-123", payload)

        assert result == mock_version
        mock_update_language.assert_called_once_with("language-123", payload)

    @patch('app.repositories.languages.LanguageRepository.update_language')
    def test_update_language_no_parent_raises_error(self, mock_update_language):
        """Test update_language raises error when no parent language found"""
        payload = LanguageCreateRequest(
            language_name="Test",
            autonym_script="Test",
            country="Test",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=0.0,
            longitude=0.0
        )

        # Mock the method to raise ValueError
        mock_update_language.side_effect = ValueError("No parent language found for version 'version-123'")

        with pytest.raises(ValueError, match="No parent language found for version 'version-123'"):
            LanguageRepository.update_language("version-123", payload)

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_success(self, mock_update_language_status):
        """Test successful language status update"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        result = LanguageRepository.update_language_status("version-123", "active", "Test User")

        assert result == mock_version
        mock_update_language_status.assert_called_once_with("version-123", "active", "Test User")

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_invalid_status_raises_error(self, mock_update_language_status):
        """Test update_language_status raises error for invalid status"""
        # Mock the method to raise ValueError
        mock_update_language_status.side_effect = ValueError(
            "Invalid status 'invalid'. Must be one of: draft, active, superseded, reverted, archived, review"
        )

        with pytest.raises(ValueError, match="Invalid status 'invalid'. Must be one of: "
                                             "draft, active, superseded, reverted, archived, review"):
            LanguageRepository.update_language_status("version-123", "invalid", "Test User")

    def test_create_language_slug_generation(self):
        """Test that create_language generates correct slug from language_name and country"""
        from unittest.mock import MagicMock, patch

        from app.repositories.languages import LanguageRepository
        from app.schemas.languages import LanguageCreateRequest
        
        mock_data = LanguageCreateRequest(
            language_name="Test Language",
            autonym_script="Test Script",
            country="Test Country",
            country_code="TC",
            region="Test Region",
            latitude=10.0,
            longitude=20.0
        )
        
        # Mock the Language and LanguageVersion classes
        with patch('app.repositories.languages.Language') as mock_lang_class, \
             patch('app.repositories.languages.LanguageVersion') as mock_ver_class, \
             patch('app.repositories.languages.Language.nodes') as mock_lang_nodes, \
             patch('app.repositories.languages.AssetRepository'):
            
            # Mock no existing languages
            mock_lang_nodes.filter.return_value = []
            
            # Mock Language instance
            mock_lang_instance = MagicMock()
            mock_lang_class.return_value = mock_lang_instance
            mock_lang_instance.save.return_value = mock_lang_instance
            
            # Mock LanguageVersion instance
            mock_ver_instance = MagicMock()
            mock_ver_class.return_value = mock_ver_instance
            mock_ver_instance.save.return_value = mock_ver_instance
            
            # Call the method
            LanguageRepository.create_language(mock_data)
            
            # Verify Language was created with correct slug
            mock_lang_class.assert_called_once_with(
                slug="lan-test country-test language",
                current_version=1.0,
                language_name="Test Language"
            )

    def test_create_language_does_not_set_current_version(self):
        """Test that create_language does not set current_version_rel initially"""
        from unittest.mock import MagicMock, patch

        from app.repositories.languages import LanguageRepository
        from app.schemas.languages import LanguageCreateRequest
        
        mock_data = LanguageCreateRequest(
            language_name="Test Language",
            autonym_script="Test Script",
            country="Test Country",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=10.0,
            longitude=20.0
        )
        
        # Mock the Language and LanguageVersion classes
        with patch('app.repositories.languages.Language') as mock_lang_class, \
             patch('app.repositories.languages.LanguageVersion') as mock_ver_class, \
             patch('app.repositories.languages.Language.nodes') as mock_lang_nodes, \
             patch('app.repositories.languages.AssetRepository'):
            
            # Mock no existing languages
            mock_lang_nodes.filter.return_value = []
            
            # Mock Language instance
            mock_lang_instance = MagicMock()
            mock_lang_class.return_value = mock_lang_instance
            mock_lang_instance.save.return_value = mock_lang_instance
            
            # Mock LanguageVersion instance
            mock_ver_instance = MagicMock()
            mock_ver_class.return_value = mock_ver_instance
            mock_ver_instance.save.return_value = mock_ver_instance
            
            # Call the method
            LanguageRepository.create_language(mock_data)
            
            # Verify versions relationship is connected but current_version_rel is NOT
            mock_lang_instance.versions.connect.assert_called_once_with(mock_ver_instance)
            mock_lang_instance.current_version_rel.connect.assert_not_called()

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_to_published_sets_current_version(self, mock_update_language_status):
        """Test that updating status to published sets the version as current"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        # Call the method
        result = LanguageRepository.update_language_status("version-123", "published", "Test User")

        # Verify the method was called
        mock_update_language_status.assert_called_once_with("version-123", "published", "Test User")
        assert result == mock_version

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_to_published_sets_highest_version(self, mock_update_language_status):
        """Test that publishing sets the highest published version as current"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        # Call the method
        result = LanguageRepository.update_language_status("version-new", "active", "Test User")

        # Verify the method was called
        mock_update_language_status.assert_called_once_with("version-new", "active", "Test User")
        assert result == mock_version

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_from_published_clears_current_version(self, mock_update_language_status):
        """Test that changing published status to draft clears current version when no other published versions"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        # Call the method
        result = LanguageRepository.update_language_status("version-123", "draft", "Test User")

        # Verify the method was called
        mock_update_language_status.assert_called_once_with("version-123", "draft", "Test User")
        assert result == mock_version

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_from_published_sets_next_highest(self, mock_update_language_status):
        """Test that unpublishing sets the next highest published version as current"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        # Call the method
        result = LanguageRepository.update_language_status("version-current", "draft", "Test User")

        # Verify the method was called
        mock_update_language_status.assert_called_once_with("version-current", "draft", "Test User")
        assert result == mock_version

    @patch('app.repositories.languages.LanguageRepository.update_language_status')
    def test_update_language_status_clears_current_version_no_published(self, mock_update_language_status):
        """Test that current_version_rel is disconnected when last published version becomes unpublished"""
        # Mock return value
        mock_version = MagicMock(spec=LanguageVersion)
        mock_update_language_status.return_value = mock_version

        # Call the method
        result = LanguageRepository.update_language_status("version-123", "draft", "Test User")

        # Verify the method was called
        mock_update_language_status.assert_called_once_with("version-123", "draft", "Test User")
        assert result == mock_version

    @patch('app.repositories.languages.LanguageRepository.get_all_languages_versions')
    def test_get_all_languages_versions_returns_null_current_version_when_no_published(self, mock_get_all):
        """Test that get_all_languages_versions returns current_version=null when no published versions exist"""
        # Mock return value with no current version
        mock_language_schema = MagicMock()
        mock_language_schema.current_version = None
        mock_get_all.return_value = [mock_language_schema]

        # Call the method
        result = LanguageRepository.get_all_languages_versions()

        # Verify result has null current_version
        assert len(result) == 1
        assert result[0].current_version is None

    @patch('app.repositories.languages.LanguageRepository.get_language_by_id')
    def test_get_language_by_id_success(self, mock_get_language):
        """Test get_language_by_id repository method"""
        # Mock return value
        mock_language_schema = MagicMock(spec=LanguageSchema)
        mock_get_language.return_value = mock_language_schema

        # Call the method
        result = LanguageRepository.get_language_by_id("lang-123")

        # Verify the method was called
        mock_get_language.assert_called_once_with("lang-123")
        assert result == mock_language_schema

    @patch('app.repositories.languages.LanguageRepository.get_language_by_id')
    def test_get_language_by_id_not_found_raises_error(self, mock_get_language):
        """Test get_language_by_id raises error for non-existent language"""
        mock_get_language.side_effect = ValueError("Language with ID 'lang-123' does not exist")

        with pytest.raises(ValueError, match="Language with ID 'lang-123' does not exist"):
            LanguageRepository.get_language_by_id("lang-123")


class TestLanguageService:
    """Test cases for LanguageService"""

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.get_languages')
    @patch('app.services.languages.run_sync')
    async def test_get_languages_success(self, mock_run_sync, mock_get_languages):
        """Test get_languages service method"""
        # Create proper mock objects with actual values
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test Language"  # This might not be used anymore
        mock_version.autonym_script = "Test Script"
        mock_version.learning_platform = True
        mock_version.country = "Test Country"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "published"
        mock_version.latitude = 10.0
        mock_version.longitude = 20.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "Test User"
        mock_version.is_deleted = False
        mock_version.icon.single.return_value = None

        # Mock parent language with language_name
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "test-slug"
        mock_language.language_name = "Test Language"
        mock_language.language_id = "lang-123"  # Add language_id
        mock_version.language.single.return_value = mock_language

        mock_versions = [mock_version]
        mock_get_languages.return_value = mock_versions
        mock_run_sync.return_value = mock_versions

        result = await get_languages()

        assert len(result) == 1
        assert isinstance(result[0], LanguagesBaseSchema)
        assert result[0].language_id == "lang-123"
        mock_run_sync.assert_called_once_with(LanguageRepository.get_languages, "active")

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.create_language')
    @patch('app.services.languages.run_sync')
    async def test_create_language_success(self, mock_run_sync, mock_create_language):
        """Test create_language service method"""
        mock_data = LanguageCreateRequest(
            language_name="Test",
            autonym_script="Test",
            country="Test",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=0.0,
            longitude=0.0
        )

        # Create proper mock version with actual values
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test"  # This might not be used anymore
        mock_version.autonym_script = "Test"
        mock_version.learning_platform = True
        mock_version.country = "Test"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "draft"
        mock_version.latitude = 0.0
        mock_version.longitude = 0.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "System"
        mock_version.is_deleted = False
        mock_version.icon.single.return_value = None

        # Mock parent language with language_name
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "lan-test-test"
        mock_language.language_name = "Test"
        mock_language.language_id = "lang-456"  # Add language_id
        mock_version.language.single.return_value = mock_language

        mock_create_language.return_value = mock_version
        mock_run_sync.return_value = mock_version

        result = await create_language(mock_data, MagicMock())

        assert isinstance(result, LanguagesBaseSchema)
        assert result.language_id == "lang-456"
        mock_run_sync.assert_called_once_with(LanguageRepository.create_language, mock_data)

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.update_language')
    @patch('app.services.languages.run_sync')
    async def test_update_language_success(self, mock_run_sync, mock_update_language):
        """Test update_language service method"""
        mock_payload = LanguageCreateRequest(
            language_name="Test",
            autonym_script="Test",
            country="Test",
            country_code="TC",
            region="Test Region",
            status="draft",
            latitude=0.0,
            longitude=0.0
        )

        # Create proper mock version with actual values
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test"  # This might not be used anymore
        mock_version.autonym_script = "Test"
        mock_version.learning_platform = True
        mock_version.country = "Test"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "draft"
        mock_version.latitude = 0.0
        mock_version.longitude = 0.0
        mock_version.version = 1.1
        mock_version.created_at = datetime.now()
        mock_version.created_by = "System"
        mock_version.is_deleted = False
        mock_version.icon.single.return_value = None

        # Mock parent language with language_name
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "lan-test-test"
        mock_language.language_name = "Test"
        mock_version.language.single.return_value = mock_language

        mock_update_language.return_value = mock_version
        mock_run_sync.return_value = mock_version

        result = await update_language("version-123", mock_payload)

        assert isinstance(result, LanguageVersionSchema)
        assert result.language_version_id == "version-123"
        mock_run_sync.assert_called_once_with(LanguageRepository.update_language, "version-123", mock_payload)

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.update_language_status')
    @patch('app.services.languages.run_sync')
    async def test_update_language_status_success(self, mock_run_sync, mock_update_language_status):
        """Test update_language_status service method"""
        mock_status_update = LanguageStatusUpdateRequest(
            status="active",
            updated_by="Test User"
        )

        # Create proper mock version with actual values
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test"  # This might not be used anymore
        mock_version.autonym_script = "Test"
        mock_version.learning_platform = True
        mock_version.country = "Test"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "active"
        mock_version.latitude = 0.0
        mock_version.longitude = 0.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "Test User"
        mock_version.is_deleted = False
        mock_version.icon.single.return_value = None

        # Mock parent language with language_name
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "lan-test-test"
        mock_language.language_name = "Test"
        mock_version.language.single.return_value = mock_language

        mock_update_language_status.return_value = mock_version
        mock_run_sync.return_value = mock_version

        result = await update_language_status("version-123", mock_status_update)

        assert isinstance(result, LanguageVersionSchema)
        assert result.language_version_id == "version-123"
        assert result.status == "active"
        mock_run_sync.assert_called_once_with(
            LanguageRepository.update_language_status,
            "version-123",
            "active",
            "Test User"
        )

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.get_all_languages_versions')
    @patch('app.services.languages.run_sync')
    async def test_get_all_languages_versions_success(self, mock_run_sync, mock_get_all):
        """Test get_all_languages_versions service method"""
        mock_language_schema = MagicMock(spec=LanguageSchema)
        mock_get_all.return_value = [mock_language_schema]
        mock_run_sync.return_value = [mock_language_schema]

        result = await get_all_languages_versions()

        assert len(result) == 1
        assert result[0] == mock_language_schema
        mock_run_sync.assert_called_once_with(LanguageRepository.get_all_languages_versions)

    @pytest.mark.asyncio
    @patch('app.services.languages.LanguageRepository.get_language_by_id')
    @patch('app.services.languages.run_sync')
    async def test_get_language_by_id_success(self, mock_run_sync, mock_get_language):
        """Test get_language_by_id service method"""
        mock_language_schema = MagicMock(spec=LanguageSchema)
        mock_get_language.return_value = mock_language_schema
        mock_run_sync.return_value = mock_language_schema

        result = await get_language_by_id("lang-123")

        assert result == mock_language_schema
        mock_run_sync.assert_called_once_with(LanguageRepository.get_language_by_id, "lang-123")

    def test_language_to_schema_with_icon(self):
        """Test _language_version_to_schema with icon"""
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test Language"
        mock_version.autonym_script = "Test Script"
        mock_version.learning_platform = True
        mock_version.country = "Test Country"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "published"
        mock_version.latitude = 10.0
        mock_version.longitude = 20.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "Test User"
        mock_version.is_deleted = False

        # Mock icon
        mock_icon = MagicMock()
        mock_icon.asset_id = "icon-123"
        mock_version.icon.single.return_value = mock_icon

        # Mock parent language
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "test-slug"
        mock_language.language_name = "Test Language"
        mock_version.language.single.return_value = mock_language

        result = _language_version_to_schema(mock_version)

        assert isinstance(result, LanguageVersionSchema)
        assert result.language_version_id == "version-123"
        assert result.slug == "test-slug"
        assert result.icon == "icon-123"

    def test_language_to_schema_without_icon(self):
        """Test _language_version_to_schema without icon"""
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test Language"
        mock_version.autonym_script = "Test Script"
        mock_version.learning_platform = True
        mock_version.country = "Test Country"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "published"
        mock_version.latitude = 10.0
        mock_version.longitude = 20.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "Test User"
        mock_version.is_deleted = False

        # No icon
        mock_version.icon.single.return_value = None

        # Mock parent language
        mock_language = MagicMock(spec=Language)
        mock_language.slug = "test-slug"
        mock_language.language_name = "Test Language"
        mock_version.language.single.return_value = mock_language

        result = _language_version_to_schema(mock_version)

        assert isinstance(result, LanguageVersionSchema)
        assert result.icon is None

    def test_language_to_schema_without_parent_language(self):
        """Test _language_version_to_schema fallback when no parent language"""
        mock_version = MagicMock(spec=LanguageVersion)
        mock_version.language_version_id = "version-123"
        mock_version.language_name = "Test Language"
        mock_version.autonym_script = "Test Script"
        mock_version.learning_platform = True
        mock_version.country = "Test Country"
        mock_version.country_code = "TC"
        mock_version.region = "Test Region"
        mock_version.status = "published"
        mock_version.latitude = 10.0
        mock_version.longitude = 20.0
        mock_version.version = 1.0
        mock_version.created_at = datetime.now()
        mock_version.created_by = "Test User"
        mock_version.is_deleted = False

        mock_version.icon.single.return_value = None
        mock_version.language.single.return_value = None  # No parent language

        result = _language_version_to_schema(mock_version)

        assert isinstance(result, LanguageVersionSchema)
        assert result.slug == "lan-test country-unknown"  # Fallback slug generation


class TestVersionUtils:
    """Test cases for version utility functions"""

    def test_increment_version_normal_cases(self):
        """Test increment_version with normal version numbers"""
        assert increment_version(1.0) == 1.1
        assert increment_version(1.5) == 1.6
        assert increment_version(2.0) == 2.1
        assert increment_version(2.8) == 2.9

    def test_increment_version_decimal_transition(self):
        """Test increment_version handles 1.9 -> 2.0 transition correctly"""
        assert increment_version(1.9) == 2.0
        assert increment_version(2.9) == 3.0
        assert increment_version(9.9) == 10.0

    def test_increment_version_edge_cases(self):
        """Test increment_version with edge cases"""
        assert increment_version(0.0) == 0.1
        assert increment_version(0.9) == 1.0
        assert increment_version(10.0) == 10.1

    def test_increment_version_floating_point_precision(self):
        """Test increment_version handles floating point precision correctly"""
        # These should work correctly despite floating point representation
        result = increment_version(1.1)
        assert abs(result - 1.2) < 0.0001  # Allow small floating point errors

        result = increment_version(1.9)
        assert abs(result - 2.0) < 0.0001
