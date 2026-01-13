import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.assets import AssetBaseSchema, AssetSchema


class ResourcePostRequestData(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    content: Optional[str] = None
    language_id: Optional[str] = None
    region: Optional[str] = None
    content_type: Optional[str] = None
    created_by: Optional[str] = "System"


class ResourceUpdateRequestData(BaseModel):
    language_id: Optional[str] = None
    title: Optional[str] = None
    icon: Optional[str] = None
    content: Optional[str] = None
    derived_from_id: Optional[str] = (
        None  # ID of the ResourceVersion it is derived from if None its an original
    )
    description: Optional[str] = None
    content_type: Optional[str] = None
    region: Optional[str] = None


class ResourceVersionSchema(BaseModel):
    resource_version_id: str
    title: str
    language_id: Optional[str] = None
    language_name: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    content_type: str
    version: float
    status: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    icon: Optional[str] = None
    content: Optional[AssetBaseSchema] = None

    class Config:
        from_attributes = True
        validate_by_name = True
        use_enum_values = True
        arbitrary_types_allowed = True


class ResourceBaseSchema(BaseModel):
    resource_id: str
    slug: str
    tag: str
    version: float
    icon: Optional[str] = None
    content: Optional[AssetBaseSchema] = None

    class Config:
        from_attributes = True
        validate_by_name = True
        use_enum_values = True
        arbitrary_types_allowed = True


class ResourceSchema(BaseModel):
    resource_id: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    slug: str
    tag: str
    versions: list[ResourceVersionSchema] = Field(default_factory=list)
    current_original_version: Optional[ResourceVersionSchema] = None
    current_adapted_versions: list[ResourceVersionSchema] = Field(default_factory=list)
    current_translated_versions: list[ResourceVersionSchema] = Field(
        default_factory=list
    )

    class Config:
        from_attributes = True
        validate_by_name = True
        use_enum_values = True
        arbitrary_types_allowed = True


class ResourceWithOrderSchema(BaseModel):
    resource_id: str
    title: Optional[str] = None
    tag: Optional[str] = None
    order: int

    content: Optional[AssetSchema] = None
    icon: Optional[AssetSchema] = None

    summary: Optional[str] = None
    description: Optional[str] = None
    version: Optional[float] = None

    class Config:
        from_attributes = True
        validate_by_name = True
        use_enum_values = True
        arbitrary_types_allowed = True


class ResourceStatusUpdateRequest(BaseModel):
    status: str  # one of: draft, active, superseded, reverted, archived, review
    updated_by: Optional[str] = "System"
