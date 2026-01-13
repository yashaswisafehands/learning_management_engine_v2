from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.modules import Module, ModuleVersion
from app.repositories.modules import ModuleRepository
from app.schemas.modules import (ModuleBaseSchema, ModuleCreateRequest,
                                 ModuleSchema, ModuleStatusUpdateRequest,
                                 ModuleUpdateRequest, ModuleVersionSchema)
from app.services.modules import (_version_to_base, _version_to_schema,
                                  create_module, get_module_by_id,
                                  list_modules, update_module,
                                  update_module_status)


class TestModuleRepository:
    @patch('app.repositories.modules.ModuleRepository.get_modules')
    def test_get_modules_active(self, mock_get):
        v = MagicMock(spec=ModuleVersion)
        mock_get.return_value = [v]
        result = ModuleRepository.get_modules('active')
        assert result == [v]
        mock_get.assert_called_once_with('active')

    @patch('app.repositories.modules.ModuleRepository.get_modules')
    def test_get_modules_all(self, mock_get):
        v = MagicMock(spec=ModuleVersion)
        mock_get.return_value = [v]
        result = ModuleRepository.get_modules('all')
        assert result == [v]
        mock_get.assert_called_once_with('all')


class TestModuleService:
    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.get_modules')
    @patch('app.services.modules.run_sync')
    async def test_list_modules_base(self, mock_run_sync, mock_repo_get):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'draft'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        parent = MagicMock(spec=Module)
        parent.slug = 'mod-t'
        parent.module_id = 'm-1'
        v.module.single.return_value = parent
        v.icon.single.return_value = None
        v.videos.all.return_value = []
        v.action_cards.all.return_value = []
        v.practical_procedures.all.return_value = []
        v.drugs.all.return_value = []

        mock_repo_get.return_value = [v]
        mock_run_sync.return_value = [v]

        result = await list_modules()
        assert isinstance(result[0], ModuleBaseSchema)
        assert result[0].module_id == 'm-1'

    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.get_modules')
    @patch('app.services.modules.run_sync')
    async def test_list_modules_include_versions(self, mock_run_sync, mock_repo_get):
        m = MagicMock(spec=Module)
        m.module_id = 'm-1'
        m.slug = 'mod-t'
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'active'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.icon.single.return_value = None
        v.videos.all.return_value = []
        v.action_cards.all.return_value = []
        v.practical_procedures.all.return_value = []
        v.drugs.all.return_value = []
        m.versions.all.return_value = [v]
        m.current_version_rel.single.return_value = v

        mock_repo_get.return_value = [m]
        mock_run_sync.return_value = [m]

        result = await list_modules(include_versions=True)
        assert isinstance(result[0], ModuleSchema)
        assert isinstance(result[0].versions, list)
        assert len(result[0].versions) == 1
        assert result[0].current_version is not None

    def test_version_to_schema(self):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'draft'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.icon.single.return_value = None
        v.videos.all.return_value = []
        v.action_cards.all.return_value = []
        v.practical_procedures.all.return_value = []
        v.drugs.all.return_value = []
        s = _version_to_schema(v, 'mod-t')
        assert isinstance(s, ModuleVersionSchema)
        assert s.module_version_id == 'mv-1'
        # language_id/region removed from model and response

    def test_version_to_base(self):
        v = MagicMock(spec=ModuleVersion)
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.icon.single.return_value = None
        p = MagicMock(spec=Module)
        p.slug = 'mod-t'
        p.module_id = 'm-1'
        v.module.single.return_value = p
        s = _version_to_base(v)
        assert isinstance(s, ModuleBaseSchema)
        assert s.module_id == 'm-1'

    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.get_latest_version_by_module_id')
    @patch('app.services.modules.run_sync')
    async def test_get_module_by_id(self, mock_run_sync, mock_repo_get):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'active'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.icon.single.return_value = None
        p = MagicMock(spec=Module)
        p.slug = 'mod-t'
        p.module_id = 'm-1'
        p.versions.all.return_value = [v]
        p.current_version_rel.single.return_value = v
        v.module.single.return_value = p
        mock_repo_get.return_value = v
        mock_run_sync.return_value = v

        res = await get_module_by_id('m-1')
        assert isinstance(res, ModuleSchema)
        assert isinstance(res.versions, list)

    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.create_module')
    @patch('app.services.modules.run_sync')
    async def test_create_module(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'draft'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.language_id = None
        v.region = None
        v.icon.single.return_value = None
        p = MagicMock(spec=Module)
        p.slug = 'mod-t'
        p.module_id = 'm-1'
        p.versions.all.return_value = [v]
        p.current_version_rel.single.return_value = None
        v.module.single.return_value = p
        mock_repo.return_value = v
        mock_run_sync.return_value = v

        data = ModuleCreateRequest(title='T', description='D')
        res = await create_module(data, MagicMock())
        assert isinstance(res, ModuleSchema)

    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.update_module')
    @patch('app.services.modules.run_sync')
    async def test_update_module(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T2'
        v.description = 'D2'
        v.version = 1.1
        v.status = 'draft'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.language_id = 'lang-2'
        v.region = 'EU'
        v.icon.single.return_value = None
        p = MagicMock(spec=Module)
        p.slug = 'mod-t'
        p.module_id = 'm-1'
        p.versions.all.return_value = [v]
        p.current_version_rel.single.return_value = None
        v.module.single.return_value = p
        mock_repo.return_value = v
        mock_run_sync.return_value = v

        payload = ModuleUpdateRequest(title='T2')
        res = await update_module('m-1', payload, MagicMock())
        assert isinstance(res, ModuleSchema)

    @pytest.mark.asyncio
    @patch('app.services.modules.ModuleRepository.update_module_status')
    @patch('app.services.modules.run_sync')
    async def test_update_module_status(self, mock_run_sync, mock_repo):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = 'mv-1'
        v.title = 'T'
        v.description = 'D'
        v.version = 1.0
        v.status = 'active'
        v.created_at = datetime.now()
        v.created_by = 'System'
        v.is_deleted = False
        v.language_id = None
        v.region = None
        v.icon.single.return_value = None
        p = MagicMock(spec=Module)
        p.slug = 'mod-t'
        p.module_id = 'm-1'
        p.versions.all.return_value = [v]
        p.current_version_rel.single.return_value = v
        v.module.single.return_value = p
        mock_repo.return_value = v
        mock_run_sync.return_value = v

        req = ModuleStatusUpdateRequest(status='active', updated_by='Tester')
        res = await update_module_status('mv-1', req)
        assert isinstance(res, ModuleVersionSchema)


class TestModuleLifecycleLogic:
    def _mk_version(self, module_id: str, mv_id: str, version_num: float, status: str, title: str, module_ref=None):
        v = MagicMock(spec=ModuleVersion)
        v.module_version_id = mv_id
        v.version = version_num
        v.status = status
        v.title = title
        v.created_by = 'System'
        v.created_at = datetime.now()
        v.is_deleted = False
        v.language_id = None
        v.region = None
        v.icon.single.return_value = None
        v.videos.all.return_value = []
        v.action_cards.all.return_value = []
        v.practical_procedures.all.return_value = []
        v.drugs.all.return_value = []
        if module_ref is not None:
            v.module.single.return_value = module_ref
        return v

    def _mk_module(self, module_id: str, slug: str):
        m = MagicMock(spec=Module)
        m.module_id = module_id
        m.slug = slug
        return m

    def test_activate_newer_supersedes_old(self, monkeypatch):
        m = self._mk_module('m-1', 'slug')
        older = self._mk_version('m-1', 'mv-old', 1.0, 'active', 'Old Title', m)
        newer = self._mk_version('m-1', 'mv-new', 1.1, 'draft', 'New Title', m)
        m.versions.all.return_value = [older, newer]
        # current pointer simulation
        m.current_version_rel.single.return_value = older

        def disconnect(v):
            assert v is older

        def connect(v):
            assert v is newer
        m.current_version_rel.disconnect.side_effect = disconnect
        m.current_version_rel.connect.side_effect = connect
        from app.repositories import modules as mod_repo_mod
        mod_repo_mod.ModuleRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'mv-old': older,
            'mv-new': newer,
        }
        # save is no-op
        newer.save.return_value = None
        older.save.return_value = None
        m.save.return_value = None
        res = ModuleRepository.update_module_status('mv-new', 'active', 'Tester')
        assert res is newer
        assert newer.status == 'active'
        assert older.status == 'superseded'
        assert m.title == 'New Title'

    def test_activate_older_reverts_current(self, monkeypatch):
        m = self._mk_module('m-1', 'slug')
        older = self._mk_version('m-1', 'mv-old', 1.0, 'draft', 'Old Title', m)
        newer = self._mk_version('m-1', 'mv-new', 1.1, 'active', 'New Title', m)
        m.versions.all.return_value = [older, newer]
        m.current_version_rel.single.return_value = newer

        def disconnect(v):
            assert v is newer

        def connect(v):
            assert v is older
        m.current_version_rel.disconnect.side_effect = disconnect
        m.current_version_rel.connect.side_effect = connect
        from app.repositories import modules as mod_repo_mod
        mod_repo_mod.ModuleRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'mv-old': older,
            'mv-new': newer,
        }
        older.save.return_value = None
        newer.save.return_value = None
        m.save.return_value = None
        res = ModuleRepository.update_module_status('mv-old', 'active', 'Tester')
        assert res is older
        assert older.status == 'active'
        assert newer.status == 'reverted'
        assert m.title == 'Old Title'

    def test_deactivate_active_promotes_highest(self, monkeypatch):
        m = self._mk_module('m-1', 'slug')
        v1 = self._mk_version('m-1', 'mv-1', 1.0, 'active', 'Title1', m)
        v2 = self._mk_version('m-1', 'mv-2', 1.1, 'active', 'Title2', m)
        # current pointer returns v1 (simulate out-of-order scenario)
        m.current_version_rel.single.return_value = v1
        m.versions.all.return_value = [v1, v2]

        def disconnect(v):
            assert v is v1

        def connect(v):
            assert v is v2
        m.current_version_rel.disconnect.side_effect = disconnect
        m.current_version_rel.connect.side_effect = connect
        from app.repositories import modules as mod_repo_mod
        mod_repo_mod.ModuleRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'mv-1': v1,
            'mv-2': v2,
        }
        v1.save.return_value = None
        v2.save.return_value = None
        m.save.return_value = None
        res = ModuleRepository.update_module_status('mv-1', 'draft', 'Tester')
        assert res is v1
        assert v1.status == 'draft'
        # v2 should remain active and be connected
        assert v2.status == 'active'

    def test_activate_sets_active_status(self, monkeypatch):
        m = self._mk_module('m-1', 'slug')
        v = self._mk_version('m-1', 'mv-1', 1.0, 'draft', 'Title', m)
        m.versions.all.return_value = [v]
        m.current_version_rel.single.return_value = None
        m.current_version_rel.connect.side_effect = lambda ver: None
        from app.repositories import modules as mod_repo_mod
        mod_repo_mod.ModuleRepository._test_in_memory_versions = {  # type: ignore[attr-defined]
            'mv-1': v,
        }
        v.save.return_value = None
        m.save.return_value = None
        res = ModuleRepository.update_module_status('mv-1', 'active', 'Tester')
        assert res.status == 'active'
