from typing import Union

from fastapi import APIRouter, Query, Depends
from typing_extensions import Literal

from app.core.auth import validate_token
from app.schemas.certificate_profiles import (
    CertificateProfileBaseSchema, CertificateProfileCreateRequest,
    CertificateProfileSchema, CertificateProfileUpdateRequest,
    CertificateProfileVersionSchema,
    CertificateProfileVersionStatusUpdateRequest)
from app.services import certificate_profiles as service

router = APIRouter(prefix="/certificate-profiles", tags=["Certificate Profiles"], dependencies=[Depends(validate_token)])


@router.post("", response_model=CertificateProfileSchema)
async def create_profile(payload: CertificateProfileCreateRequest):
    return await service.create_certificate_profile(payload)


@router.get(
    "",
    response_model=Union[
        CertificateProfileSchema,
        CertificateProfileBaseSchema,
        list[CertificateProfileSchema],
        list[CertificateProfileBaseSchema],
    ],
)
async def list_profiles(
    status: Literal["active", "all"] = Query(
        "all", description="Filter profiles by active or include all"
    ),
    include_versions: bool = Query(
        False,
        description="When true, return profiles with versions; otherwise return a base snapshot",
    ),
    profile_id: str | None = Query(
        None,
        alias="id",
        description="Optional certificate_profile_id to fetch a single profile",
    ),
):
    if profile_id:
        return await service.get_certificate_profile_by_id(
            profile_id,
            status=status,
            include_versions=include_versions,
        )

    return await service.list_certificate_profiles(
        status=status, include_versions=include_versions
    )


@router.get(
    "/{country_code}",
    response_model=Union[CertificateProfileSchema, CertificateProfileBaseSchema],
)
async def get_by_country_code(
    country_code: str,
    status: Literal["active", "all"] = Query(
        "active", description="Filter versions by status for this profile"
    ),
    include_versions: bool = Query(
        False, description="When true, include versions (filtered by status if active)"
    ),
):
    return await service.get_certificate_profile_by_country_code(
        country_code, status=status, include_versions=include_versions
    )


@router.patch(
    "/versions/{version_id}/status",
    response_model=CertificateProfileVersionSchema,
)
async def update_version_status(
    version_id: str, payload: CertificateProfileVersionStatusUpdateRequest
):
    return await service.update_certificate_profile_version_status(version_id, payload)


@router.patch("/{profile_id}", response_model=CertificateProfileSchema)
async def update_profile(profile_id: str, payload: CertificateProfileUpdateRequest):
    return await service.update_certificate_profile(profile_id, payload)
