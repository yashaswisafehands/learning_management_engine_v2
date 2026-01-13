from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CertificateModuleConfigRequest(BaseModel):
    module_id: str
    weightage: float = 0.0
    passing_percentage: float = 0.0
    mandatory: bool = False
    order: Optional[int] = None


class CertificateProfileCreateRequest(BaseModel):
    country_code: str
    country_name: str
    certificate_template: str
    nursing_council_name: Optional[str] = None
    champion_certificate_score: float = 0.0
    modules: List[CertificateModuleConfigRequest] = Field(default_factory=list)


# Not needed anymore
class CertificateProfileUpdateRequest(BaseModel):
    country_name: Optional[str] = None
    region: Optional[str] = None
    nursing_council_name: Optional[str] = None
    champion_certificate_score: Optional[float] = None
    modules: Optional[List[CertificateModuleConfigRequest]] = None
    created_by: Optional[str] = None
    certificate_template: Optional[str] = None


class CertificateProfileVersionStatusUpdateRequest(BaseModel):
    status: str
    updated_by: Optional[str] = "System"


class CertificateModuleConfigSchema(BaseModel):
    module_id: str
    weightage: float
    passing_percentage: float
    mandatory: bool
    order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateProfileVersionSchema(BaseModel):
    certificate_profile_version_id: str
    version: float
    status: str
    country_code: Optional[str] = None
    region: Optional[str] = None
    nursing_council_name: Optional[str] = None
    champion_certificate_score: float
    language_ids: List[str] = Field(default_factory=list)
    modules: List[CertificateModuleConfigSchema] = Field(default_factory=list)
    created_at: datetime
    created_by: Optional[str] = None
    is_deleted: bool
    version_code: Optional[str] = None
    certificate_template: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateProfileSchema(BaseModel):
    certificate_profile_id: str
    slug: str
    country_code: str
    country_name: str
    certificate_template: Optional[str] = None
    current_version: Optional[str] = None
    versions: List[CertificateProfileVersionSchema] = Field(default_factory=list)
    created_at: datetime
    created_by: Optional[str] = None
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class CertificateProfileBaseSchema(BaseModel):
    """Base schema summarizing a profile via a single version snapshot (typically active)."""

    certificate_profile_id: str
    slug: str
    country_code: str
    country_name: Optional[str] = None
    version: float
    status: str
    current_version: Optional[str] = None
    certificate_template: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
