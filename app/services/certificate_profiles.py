from app.repositories.certificate_profiles import CertificateProfileRepository
from app.repositories.languages import LanguageRepository
from app.schemas.certificate_profiles import (
    CertificateProfileBaseSchema, CertificateProfileCreateRequest,
    CertificateProfileSchema, CertificateProfileUpdateRequest,
    CertificateProfileVersionSchema,
    CertificateProfileVersionStatusUpdateRequest)
from app.utils.executors import run_sync


def _language_status_filter(status: str) -> str | None:
    return None if status == "all" else "active"


def _version_to_schema(
    v,
    language_map: dict[str, list[str]] | None = None,
) -> CertificateProfileVersionSchema:
    """Map a version node to its API schema representation."""

    # languages are derived from country code via LanguageRepository
    country_code = getattr(v, "country_code", None)
    lang_ids = []
    if language_map is not None and country_code:
        lang_ids = language_map.get(country_code, [])

    # modules -> list of config schemas
    modules = []
    try:
        mods = getattr(v, "modules", None)
        if mods and hasattr(mods, "all"):
            module_payloads = []
            for module in mods.all():
                rel = mods.relationship(module)
                order_value = getattr(rel, "order", None)
                module_payloads.append(
                    (
                        order_value if order_value is not None else float("inf"),
                        {
                            "module_id": module.module_id,
                            "weightage": getattr(rel, "weightage", 0.0),
                            "passing_percentage": getattr(
                                rel, "passing_percentage", 0.0
                            ),
                            "mandatory": getattr(rel, "mandatory", False),
                            "order": order_value,
                        },
                    )
                )
            module_payloads.sort(key=lambda item: item[0])
            modules = [payload for _, payload in module_payloads]
    except Exception:
        modules = []

    return CertificateProfileVersionSchema(
        certificate_profile_version_id=getattr(v, "certificate_profile_version_id", ""),
        version=getattr(v, "version", None),
        status=getattr(v, "status", None),
        country_code=getattr(v, "country_code", None),
        region=getattr(v, "region", None),
        nursing_council_name=getattr(v, "nursing_council_name", None),
        champion_certificate_score=getattr(v, "champion_certificate_score", 0.0),
        language_ids=lang_ids,
        modules=modules,
        created_at=getattr(v, "created_at", None),
        created_by=getattr(v, "created_by", None),
        is_deleted=getattr(v, "is_deleted", False),
        version_code=getattr(v, "version_code", None),
        certificate_template=getattr(v, "certificate_template", None),
    )


def _profile_to_schema(
    profile,
    status_filter: str | None = None,
    language_map: dict[str, list[str]] | None = None,
) -> CertificateProfileSchema:
    versions = []
    try:
        vers = getattr(profile, "versions", None)
        if vers and hasattr(vers, "all"):
            all_versions = vers.all()
            if status_filter == "active":
                all_versions = [
                    v for v in all_versions if getattr(v, "status", None) == "active"
                ]
            versions = [_version_to_schema(v, language_map) for v in all_versions]
    except Exception:
        versions = []

    return CertificateProfileSchema(
        certificate_profile_id=getattr(profile, "certificate_profile_id", ""),
        slug=getattr(profile, "slug", ""),
        country_code=getattr(profile, "country_code", ""),
        country_name=getattr(profile, "country_name", None),
        certificate_template=getattr(profile, "certificate_template", None),
        current_version=getattr(profile, "current_version", None),
        versions=versions,
        created_at=getattr(profile, "created_at", None),
        created_by=getattr(profile, "created_by", None),
        is_deleted=getattr(profile, "is_deleted", False),
    )


def _version_to_base_schema(v) -> CertificateProfileBaseSchema:
    relationship = getattr(v, "certificate_profile", None)
    parent = None
    try:
        parent = (
            relationship.single()
            if relationship and hasattr(relationship, "single")
            else None
        )
    except Exception:
        parent = None

    return CertificateProfileBaseSchema(
        certificate_profile_id=getattr(parent, "certificate_profile_id", ""),
        slug=getattr(parent, "slug", "") if parent else "",
        country_code=getattr(parent, "country_code", "") if parent else "",
        country_name=getattr(parent, "country_name", None) if parent else None,
        version=getattr(v, "version", 1.0),
        status=getattr(v, "status", "draft"),
        current_version=getattr(parent, "current_version", None) if parent else None,
        certificate_template=(
            getattr(parent, "certificate_template", None) if parent else None
        ),
    )


def _build_base_profile_schema(profile, status: str) -> CertificateProfileBaseSchema:
    if status == "active":
        try:
            current = profile.current_version_rel.single()
        except Exception:
            current = None
        if current and getattr(current, "status", None) == "active":
            return _version_to_base_schema(current)

    try:
        versions = profile.versions.all()
    except Exception:
        versions = []

    if status == "active":
        active_versions = [
            v for v in versions if getattr(v, "status", None) == "active"
        ]
        if active_versions:
            latest_active = max(
                active_versions, key=lambda item: getattr(item, "version", 0)
            )
            return _version_to_base_schema(latest_active)

    if versions:
        latest = max(versions, key=lambda item: getattr(item, "version", 0))
        return _version_to_base_schema(latest)

    return CertificateProfileBaseSchema(
        certificate_profile_id=getattr(profile, "certificate_profile_id", ""),
        slug=getattr(profile, "slug", ""),
        country_code=getattr(profile, "country_code", ""),
        country_name=getattr(profile, "country_name", None),
        version=1.0,
        status="draft",
        current_version=getattr(profile, "current_version", None),
        certificate_template=getattr(profile, "certificate_template", None),
    )


async def _compose_profile_response(
    profile,
    *,
    status: str,
    include_versions: bool,
):
    if include_versions:
        language_map = await run_sync(
            LanguageRepository.get_language_ids_by_country_codes,
            [getattr(profile, "country_code", None)],
            status=_language_status_filter(status),
        )
        return _profile_to_schema(
            profile,
            status_filter=(status if status == "active" else None),
            language_map=language_map,
        )

    return _build_base_profile_schema(profile, status)


async def create_certificate_profile(
    payload: CertificateProfileCreateRequest,
) -> CertificateProfileSchema:
    profile = await run_sync(CertificateProfileRepository.create_profile, payload)
    return _profile_to_schema(profile)


async def get_certificate_profile_by_country_code(
    country_code: str,
    status: str = "active",
    include_versions: bool = False,
):
    profile = await run_sync(
        CertificateProfileRepository.get_profile_and_versions_by_country_code,
        country_code,
        status,
    )
    return await _compose_profile_response(
        profile,
        status=status,
        include_versions=include_versions,
    )


async def list_certificate_profiles(
    status: str = "active", include_versions: bool = False
):
    items = await run_sync(
        CertificateProfileRepository.get_profiles, status, include_versions
    )

    if include_versions:
        country_codes = [getattr(item, "country_code", None) for item in items]
        language_map = await run_sync(
            LanguageRepository.get_language_ids_by_country_codes,
            country_codes,
            status=_language_status_filter(status),
        )
        return [
            _profile_to_schema(
                item,
                status_filter=(status if status == "active" else None),
                language_map=language_map,
            )
            for item in items
        ]

    return [_version_to_base_schema(version) for version in items]


async def create_certificate_profile_version(
    profile_id: str, payload: CertificateProfileUpdateRequest
) -> CertificateProfileVersionSchema:
    version = await run_sync(
        CertificateProfileRepository.create_version, profile_id, payload
    )
    language_map = await run_sync(
        LanguageRepository.get_language_ids_by_country_codes,
        [getattr(version, "country_code", None)],
    )
    return _version_to_schema(version, language_map)


async def get_certificate_profile_by_id(
    profile_id: str,
    *,
    status: str = "all",
    include_versions: bool = True,
):
    profile = await run_sync(CertificateProfileRepository.get_by_id, profile_id)
    return await _compose_profile_response(
        profile,
        status=status,
        include_versions=include_versions,
    )


async def update_certificate_profile(
    profile_id: str, payload: CertificateProfileUpdateRequest
) -> CertificateProfileSchema:
    await run_sync(CertificateProfileRepository.create_version, profile_id, payload)
    profile = await run_sync(CertificateProfileRepository.get_by_id, profile_id)
    language_map = await run_sync(
        LanguageRepository.get_language_ids_by_country_codes,
        [getattr(profile, "country_code", None)],
    )
    return _profile_to_schema(profile, language_map=language_map)


async def update_certificate_profile_version_status(
    version_id: str, payload: CertificateProfileVersionStatusUpdateRequest
) -> CertificateProfileVersionSchema:
    version = await run_sync(
        CertificateProfileRepository.update_version_status,
        version_id,
        payload.status,
        payload.updated_by,
    )
    language_map = await run_sync(
        LanguageRepository.get_language_ids_by_country_codes,
        [getattr(version, "country_code", None)],
    )
    return _version_to_schema(version, language_map)
