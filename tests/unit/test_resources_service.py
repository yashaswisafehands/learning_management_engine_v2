import types

import pytest

from app.services import resources as resources_service


class DummyVersion:
    def __init__(self, resource_version_id, content_type, version=1.0, status='active', icon=None, content=None):
        self.resource_version_id = resource_version_id
        self.content_type = content_type
        self.version = version
        self.status = status
        self.icon = icon
        self.content = content
        self.title = f"Title {resource_version_id}"
        self.description = "Desc"
        self.region = 'GLOBAL'
        self.created_by = 'tester'
        self.language = types.SimpleNamespace(single=lambda: None)
        self.is_deleted = False
        self.created_at = None


class DummyResource:
    def __init__(self, resource_id, slug, tag='tag'):  # minimal attrs used
        self.resource_id = resource_id
        self.slug = slug
        self.tag = tag
        # Relationship managers for current versions
        self.current_original_version = types.SimpleNamespace(single=lambda: None)
        self.current_adapted_versions = types.SimpleNamespace(all=lambda: [])
        self.current_translated_versions = types.SimpleNamespace(all=lambda: [])
        self.icon = types.SimpleNamespace(single=lambda: None)


@pytest.mark.asyncio
async def test_get_all_resources_language_filter_excludes_when_no_translation(monkeypatch):
    # Arrange: 2 resources, neither has translated version; language_id specified -> expect empty list
    r1 = DummyResource('r1', 'r1-slug')
    r2 = DummyResource('r2', 'r2-slug')

    async def fake_run_sync(func, *args):
        # emulate resources retrieval first call
        if func.__name__ == 'get_resources':
            return [r1, r2]
        if func.__name__ == 'get_best_fit_version':
            # Simulate no best-fit translated version
            return None
        if func.__name__ == 'get_all_versions_by_resource_id':
            return []
        if func.__name__ == 'get_current_versions':
            return (None, [], [])
        raise AssertionError(f"Unexpected call {func.__name__}")

    monkeypatch.setattr(resources_service, 'run_sync', fake_run_sync)

    # Act
    data = await resources_service.get_all_resources(language_id='lang-1')

    # Assert
    assert data == []


@pytest.mark.asyncio
async def test_get_all_resources_fallback_when_no_language_specified(monkeypatch):
    # Arrange: 1 resource without translated; should fallback to latest version when language_id not provided
    r1 = DummyResource('r1', 'r1-slug')
    v_latest = DummyVersion('v1', 'original', version=2.0)

    async def fake_run_sync(func, *args):
        if func.__name__ == 'get_resources':
            return [r1]
        if func.__name__ == 'get_best_fit_version':
            return None  # triggers fallback
        if func.__name__ == 'get_all_versions_by_resource_id':
            return [v_latest]
        if func.__name__ == 'get_current_versions':
            return (None, [], [])
        raise AssertionError(f"Unexpected call {func.__name__}")

    monkeypatch.setattr(resources_service, 'run_sync', fake_run_sync)

    # Act
    data = await resources_service.get_all_resources()

    # Assert base schema
    assert len(data) == 1
    base = data[0]
    assert base.resource_id == 'r1'
    assert base.version == 2.0  # fell back to latest


@pytest.mark.asyncio
async def test_get_all_resources_include_versions(monkeypatch):
    r1 = DummyResource('r1', 'r1-slug')
    v1 = DummyVersion('v1', 'original', version=1.0, status='active')
    v2 = DummyVersion('v2', 'adapted', version=1.5, status='draft')

    async def fake_run_sync(func, *args):
        if func.__name__ == 'get_resources':
            return [r1]
        if func.__name__ == 'get_all_versions_by_resource_id':
            return [v1, v2]
        if func.__name__ == 'get_current_versions':
            return (None, [], [])
        raise AssertionError(f"Unexpected call {func.__name__}")

    monkeypatch.setattr(resources_service, 'run_sync', fake_run_sync)

    # Act
    data = await resources_service.get_all_resources(include_versions=True)

    # Assert rich schema
    assert len(data) == 1
    rich = data[0]
    assert rich.resource_id == 'r1'
    assert len(rich.versions) == 2
    ct_set = {v.content_type for v in rich.versions}
    assert ct_set == {'original', 'adapted'}


@pytest.mark.asyncio
async def test_get_all_resources_content_type_filter_with_versions(monkeypatch):
    r1 = DummyResource('r1', 'r1-slug')
    v1 = DummyVersion('v1', 'original', version=1.0)
    v2 = DummyVersion('v2', 'translated', version=2.0)

    async def fake_run_sync(func, *args):
        if func.__name__ == 'get_resources':
            return [r1]
        if func.__name__ == 'get_all_versions_by_resource_id':
            return [v1, v2]
        if func.__name__ == 'get_current_versions':
            return (None, [], [])
        raise AssertionError(f"Unexpected call {func.__name__}")

    monkeypatch.setattr(resources_service, 'run_sync', fake_run_sync)

    data = await resources_service.get_all_resources(include_versions=True, content_type='translated')

    assert len(data) == 1
    rich = data[0]
    assert len(rich.versions) == 1
    assert rich.versions[0].content_type == 'translated'


@pytest.mark.asyncio
async def test_get_all_resources_content_type_filter_base(monkeypatch):
    r1 = DummyResource('r1', 'r1-slug')
    translated = DummyVersion('v2', 'translated', version=3.0)

    async def fake_run_sync(func, *args):
        if func.__name__ == 'get_resources':
            return [r1]
        if func.__name__ == 'get_best_fit_version':
            # Pretend best-fit is translated when content_type specified
            return translated
        if func.__name__ == 'get_current_versions':
            return (None, [], [])
        raise AssertionError(f"Unexpected call {func.__name__}")

    monkeypatch.setattr(resources_service, 'run_sync', fake_run_sync)

    data = await resources_service.get_all_resources(content_type='translated')

    assert len(data) == 1
    base = data[0]
    assert base.version == 3.0
    # Ensure we didn't accidentally return a ResourceSchema (no versions attribute array in base schema)
    assert not hasattr(base, 'versions') or base.__class__.__name__ == 'ResourceBaseSchema'
