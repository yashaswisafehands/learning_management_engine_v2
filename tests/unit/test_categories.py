from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.categories import Category, CategoryVersion
from app.repositories.categories import CategoryRepository
from app.schemas.categories import (CategoryBaseSchema, CategoryCreateRequest,
                                    CategorySchema, CategoryUpdateRequest)
from app.services.categories import (_category_version_to_base_schema,
                                     _category_version_to_version_schema,
                                     create_category, get_category_by_id,
                                     list_categories, update_category)


class TestCategoryRepository:
    @patch('app.repositories.categories.CategoryRepository.get_categories')
    def test_get_categories_published(self, mock_get_categories):
        mock_ver = MagicMock(spec=CategoryVersion)
        mock_get_categories.return_value = [mock_ver]
        result = CategoryRepository.get_categories('published')
        assert result == [mock_ver]
        mock_get_categories.assert_called_once_with('published')

    @patch('app.repositories.categories.CategoryRepository.get_categories')
    def test_get_categories_all(self, mock_get_categories):
        mock_ver = MagicMock(spec=CategoryVersion)
        mock_get_categories.return_value = [mock_ver]
        result = CategoryRepository.get_categories('all')
        assert result == [mock_ver]
        mock_get_categories.assert_called_once_with('all')


class TestCategoryService:
    @pytest.mark.asyncio
    @patch('app.services.categories.CategoryRepository.get_categories')
    @patch('app.services.categories.run_sync')
    async def test_list_categories_base(self, mock_run_sync, mock_repo_get):
        # Base path (include_versions=False) returns flattened base schemas
        mock_ver = MagicMock(spec=CategoryVersion)
        mock_ver.category_version_id = 'cv-123'
        mock_parent = MagicMock(spec=Category)
        mock_parent.slug = 'cat-test'
        mock_parent.category_id = 'cat-123'
        mock_ver.category.single.return_value = mock_parent
        mock_ver.title = 'T'
        mock_ver.description = 'D'
        mock_ver.created_at = datetime.now()
        mock_ver.created_by = 'System'
        mock_ver.is_deleted = False
        mock_ver.version = 1.0
        mock_ver.icon.single.return_value = None
        mock_ver.modules.all.return_value = []
        mock_ver.status = 'draft'

        mock_repo_get.return_value = [mock_ver]
        mock_run_sync.return_value = [mock_ver]

        result = await list_categories()
        assert isinstance(result[0], CategoryBaseSchema)
        assert result[0].category_id == 'cat-123'
        mock_run_sync.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.categories.CategoryRepository.get_categories')
    @patch('app.services.categories.run_sync')
    async def test_list_categories_include_versions(self, mock_run_sync, mock_repo_get):
        # include_versions=True path returns CategorySchema with current/latest
        mock_cat = MagicMock(spec=Category)
        mock_cat.category_id = 'cat-123'
        mock_cat.slug = 'cat-slug'

        # versions
        v1 = MagicMock(spec=CategoryVersion)
        v1.category_version_id = 'cv-1'
        v1.version = 1.0
        v1.category.single.return_value = mock_cat
        v1.icon.single.return_value = None
        v1.modules.all.return_value = []
        v1.title = 'T1'
        v1.description = 'D1'
        v1.created_at = datetime.now()
        v1.created_by = 'System'
        v1.is_deleted = False
        v1.status = 'published'

        mock_cat.versions.all.return_value = [v1]
        mock_cat.current_version_rel.single.return_value = v1

        mock_repo_get.return_value = [mock_cat]
        mock_run_sync.return_value = [mock_cat]

        result = await list_categories(include_versions=True)
        assert isinstance(result[0], CategorySchema)
        assert result[0].current_version is not None
        assert result[0].version is not None

    def test_category_version_to_version_schema(self):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = 'cv-1'
        v.title = 'T'
        v.description = 'D'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.version = 1.0
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        v.status = 'draft'
        s = _category_version_to_version_schema(v)
        assert s.category_version_id == 'cv-1'

    def test_category_version_to_base_schema(self):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = 'cv-1'
        c = MagicMock(spec=Category)
        c.slug = 'cat-s'
        c.category_id = 'cat-1'
        v.category.single.return_value = c
        v.title = 'T'
        v.description = 'D'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.version = 1.0
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        v.status = 'draft'
        s = _category_version_to_base_schema(v)
        assert s.category_id == 'cat-1'

    @pytest.mark.asyncio
    @patch('app.services.categories.CategoryRepository.get_latest_version_by_category_id')
    @patch('app.services.categories.run_sync')
    async def test_get_category_by_id(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = 'cv-1'
        v.title = 'T'
        v.description = 'D'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.version = 1.0
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        v.status = 'published'
        c = MagicMock(spec=Category)
        c.slug = 'cat-s'
        c.category_id = 'cat-1'
        c.versions.all.return_value = [v]
        c.current_version_rel.single.return_value = v
        v.category.single.return_value = c
        mock_repo.return_value = v
        mock_run_sync.return_value = v

        result = await get_category_by_id('cat-1')
        assert isinstance(result, CategorySchema)

    @pytest.mark.asyncio
    @patch('app.services.categories.CategoryRepository.create_category')
    @patch('app.services.categories.run_sync')
    async def test_create_category(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = 'cv-1'
        v.title = 'T'
        v.description = 'D'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.version = 1.0
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        v.status = 'draft'
        c = MagicMock(spec=Category)
        c.category_id = 'cat-1'
        c.slug = 'cat-s'
        c.versions.all.return_value = [v]
        c.current_version_rel.single.return_value = v
        v.category.single.return_value = c
        mock_repo.return_value = v
        mock_run_sync.return_value = v
        data = CategoryCreateRequest(title='T', description='D')
        res = await create_category(data, MagicMock())
        assert isinstance(res, CategorySchema)

    @pytest.mark.asyncio
    @patch('app.services.categories.CategoryRepository.update_category')
    @patch('app.services.categories.run_sync')
    async def test_update_category(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = 'cv-1'
        v.title = 'T2'
        v.description = 'D2'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.version = 1.0
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        v.status = 'draft'
        c = MagicMock(spec=Category)
        c.category_id = 'cat-1'
        c.slug = 'cat-s'
        c.versions.all.return_value = [v]
        c.current_version_rel.single.return_value = v
        v.category.single.return_value = c
        mock_repo.return_value = v
        mock_run_sync.return_value = v
        payload = CategoryUpdateRequest(title='T2')
        res = await update_category('cat-1', payload, MagicMock())
        assert isinstance(res, CategorySchema)


class TestCategoryLifecycleLogic:
    def _mk_version(self, cat_id: str, cv_id: str, version_num: float, status: str, title: str, cat_ref=None):
        v = MagicMock(spec=CategoryVersion)
        v.category_version_id = cv_id
        v.version = version_num
        v.status = status
        v.title = title
        v.created_by = 'System'
        v.created_at = datetime.now()
        v.is_deleted = False
        v.icon.single.return_value = None
        v.modules.all.return_value = []
        if cat_ref is not None:
            v.category.single.return_value = cat_ref
        return v

    def _mk_category(self, category_id: str, slug: str):
        c = MagicMock(spec=Category)
        c.category_id = category_id
        c.slug = slug
        return c

    def test_activate_newer_supersedes_old(self, monkeypatch):
        c = self._mk_category('cat-1', 'slug')
        older = self._mk_version('cat-1', 'cv-old', 1.0, 'active', 'Old Title', c)
        newer = self._mk_version('cat-1', 'cv-new', 1.1, 'draft', 'New Title', c)
        c.versions.all.return_value = [older, newer]
        c.current_version_rel.single.return_value = older

        def disconnect(v):
            assert v is older

        def connect(v):
            assert v is newer
        c.current_version_rel.disconnect.side_effect = disconnect
        c.current_version_rel.connect.side_effect = connect
        # Register in-memory versions for repository to avoid DB
        from app.repositories import categories as cat_repo_mod
        cat_repo_mod.CategoryRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'cv-old': older,
            'cv-new': newer,
        }
        newer.save.return_value = None
        older.save.return_value = None
        c.save.return_value = None
        res = CategoryRepository.update_category_status('cv-new', 'active', 'Tester')
        assert res is newer
        assert newer.status == 'active'
        assert older.status == 'superseded'
        assert c.title == 'New Title'

    def test_activate_older_reverts_current(self, monkeypatch):
        c = self._mk_category('cat-1', 'slug')
        older = self._mk_version('cat-1', 'cv-old', 1.0, 'draft', 'Old Title', c)
        newer = self._mk_version('cat-1', 'cv-new', 1.1, 'active', 'New Title', c)
        c.versions.all.return_value = [older, newer]
        c.current_version_rel.single.return_value = newer

        def disconnect(v):
            assert v is newer

        def connect(v):
            assert v is older
        c.current_version_rel.disconnect.side_effect = disconnect
        c.current_version_rel.connect.side_effect = connect
        from app.repositories import categories as cat_repo_mod
        cat_repo_mod.CategoryRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'cv-old': older,
            'cv-new': newer,
        }
        older.save.return_value = None
        newer.save.return_value = None
        c.save.return_value = None
        res = CategoryRepository.update_category_status('cv-old', 'active', 'Tester')
        assert res is older
        assert older.status == 'active'
        assert newer.status == 'reverted'
        assert c.title == 'Old Title'

    def test_deactivate_active_promotes_highest(self, monkeypatch):
        c = self._mk_category('cat-1', 'slug')
        v1 = self._mk_version('cat-1', 'cv-1', 1.0, 'active', 'Title1', c)
        v2 = self._mk_version('cat-1', 'cv-2', 1.1, 'active', 'Title2', c)
        c.current_version_rel.single.return_value = v1
        c.versions.all.return_value = [v1, v2]

        def disconnect(v):
            assert v is v1

        def connect(v):
            assert v is v2
        c.current_version_rel.disconnect.side_effect = disconnect
        c.current_version_rel.connect.side_effect = connect
        from app.repositories import categories as cat_repo_mod
        cat_repo_mod.CategoryRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'cv-1': v1,
            'cv-2': v2,
        }
        v1.save.return_value = None
        v2.save.return_value = None
        c.save.return_value = None
        res = CategoryRepository.update_category_status('cv-1', 'draft', 'Tester')
        assert res is v1
        assert v1.status == 'draft'
        assert v2.status == 'active'

    def test_legacy_published_maps_to_active(self, monkeypatch):
        c = self._mk_category('cat-1', 'slug')
        v = self._mk_version('cat-1', 'cv-1', 1.0, 'draft', 'Title', c)
        c.versions.all.return_value = [v]
        c.current_version_rel.single.return_value = None
        c.current_version_rel.connect.side_effect = lambda ver: None
        from app.repositories import categories as cat_repo_mod
        cat_repo_mod.CategoryRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'cv-1': v,
        }
        v.save.return_value = None
        c.save.return_value = None
        res = CategoryRepository.update_category_status('cv-1', 'published', 'Tester')
        assert res.status == 'active'
