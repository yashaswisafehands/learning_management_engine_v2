from uuid import uuid4

import pytest

from app.repositories.resources import ResourceRepository
from app.schemas.resources import (ResourcePostRequestData,
                                   ResourceUpdateRequestData)


class DummyLanguage:  # minimal stand-in if language relationship not exercised
    pass


def test_create_resource_original_infers_defaults(monkeypatch):
    unique_title = f"Test Res {uuid4().hex[:8]}"
    data = ResourcePostRequestData(title=unique_title, description="Desc")
    res = ResourceRepository.create_resource(data, tag="video")
    assert res.slug.startswith("res-test-res")
    versions = res.versions.all()
    assert len(versions) == 1
    v = versions[0]
    assert v.content_type == "original"
    assert v.region == "GLOBAL"
    assert v.version == 1.0
    assert v.created_by == "System"


def test_create_resource_adapted_with_region():
    unique_title = f"Adapt Res {uuid4().hex[:8]}"
    data = ResourcePostRequestData(title=unique_title, description="D", region="AFRICA")
    res = ResourceRepository.create_resource(data, tag="article")
    v = res.versions.all()[0]
    assert v.content_type == "adapted"
    assert v.region == "AFRICA"


def test_create_resource_translated_requires_language(monkeypatch):
    unique_title = f"Trans Res {uuid4().hex[:8]}"
    data = ResourcePostRequestData(title=unique_title, description="D", language_id="lang-123")
    with pytest.raises(ValueError, match="Language with ID 'lang-123' does not exist"):
        ResourceRepository.create_resource(data, tag="article")


def test_update_resource_creates_new_version(monkeypatch):
    base_title = f"Updatable {uuid4().hex[:8]}"
    base = ResourcePostRequestData(title=base_title, description="D")
    res = ResourceRepository.create_resource(base, tag="article")
    before_count = len(res.versions.all())
    upd_title = f"{base_title} v2"
    upd = ResourceUpdateRequestData(title=upd_title, region="EU")
    res_again = ResourceRepository.update_resource(res.resource_id, upd)
    after_count = len(res_again.versions.all())
    assert after_count == before_count + 1
    # Find the updated version deterministically by title
    updated_versions = [v for v in res_again.versions.all() if getattr(v, "title", None) == upd_title]
    assert updated_versions, "Updated version not found by title"
    latest = updated_versions[0]
    assert latest.content_type == "adapted"
    assert latest.region == "EU"


def test_update_resource_without_title_preserves_previous(monkeypatch):
    base_title = f"Preserve {uuid4().hex[:8]}"
    base = ResourcePostRequestData(title=base_title, description="Baseline")
    res = ResourceRepository.create_resource(base, tag="article")
    prior_version = res.versions.all()[0]

    updated = ResourceRepository.update_resource(res.resource_id, ResourceUpdateRequestData(region="AFRICA"))
    new_versions = [
        v
        for v in updated.versions.all()
        if v.resource_version_id != prior_version.resource_version_id
    ]
    assert new_versions, "Expected a new version to be created"
    new_version = new_versions[0]
    assert new_version.title == prior_version.title
    assert new_version.description == prior_version.description

