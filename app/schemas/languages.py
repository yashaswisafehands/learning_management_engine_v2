from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.schemas.categories import CategorySchema
from app.schemas.assets import AssetSchema

class LanguageVersionSchema(BaseModel):
    language_version_id: str
    slug: Optional[str] = None
    language_name: str
    
    # --- CHANGED: Made these Optional to handle null database values ---
    autonym_script: Optional[str] = None
    learning_platform: Optional[bool] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # -----------------------------------------------------------------

    version: float
    status: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    icon: Optional[str] = None
    categories: Optional[list[str]] = Field(default_factory=list)
    screen_data: Optional[list[str]] = Field(default_factory=list)
    transcriptions: Optional[list[str]] = Field(default_factory=list)
    onboarding_questions: Optional[list[str]] = Field(default_factory=list) 

    model_config = ConfigDict(from_attributes=True)


class LanguageVersionBaseSchema(BaseModel):
    language_version_id: str
    slug: Optional[str] = None
    language_name: str
    
    # --- CHANGED: Made these Optional here as well ---
    autonym_script: Optional[str] = None
    learning_platform: Optional[bool] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # -------------------------------------------------

    version: float
    status: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    icon: Optional[str] = None
    categories: Optional[list[str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LanguageSchema(BaseModel):
    language_id: str
    slug: Optional[str] = None
    language_name: str
    versions: Optional[list[LanguageVersionSchema]] = Field(default_factory=list)
    current_version: Optional[LanguageVersionSchema] = None
    categories: Optional[list[CategorySchema]] = Field(default_factory=list)
    screen_data: Optional[list[str]] = Field(default_factory=list)
    transcriptions: Optional[list[str]] = Field(default_factory=list)
    onboarding_questions: Optional[list[str]] = Field(default_factory=list) 

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class LanguagesBaseSchema(BaseModel):
    language_id: str
    slug: str
    language_name: str
    
    # --- CHANGED: Made these Optional ---
    autonym_script: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # ------------------------------------

    icon: Optional[str] = None
    categories: Optional[list[str]] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class LanguageCreateRequest(BaseModel):
    language_name: str
    autonym_script: str
    learning_platform: Optional[bool] = True
    country: str
    country_code: str
    region: str
    latitude: float
    longitude: float
    created_by: Optional[str] = "System"
    icon: Optional[str] = None
    categories: Optional[list[str]] = Field(default_factory=list)


class LanguageUpdateRequest(BaseModel):
    language_name: Optional[str] = None
    autonym_script: Optional[str] = None
    learning_platform: Optional[bool] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_by: Optional[str] = None
    icon: Optional[str] = None
    categories: Optional[list[str]] = Field(default_factory=list)


class LanguageStatusUpdateRequest(BaseModel):
    status: str  # Should be one of: "draft", "published", "archived", "review"
    updated_by: Optional[str] = "System"


class ModuleEnableDisableRequest(BaseModel):
    """Request to enable or disable a module for a language."""
    enabled: bool  # True = enable (remove from blacklist), False = disable (add to blacklist)
    updated_by: Optional[str] = "System"


class DisabledModuleResponse(BaseModel):
    """Response showing a disabled module."""
    module_id: str
    title: str
    disabled_at: Optional[datetime] = None
    disabled_by: Optional[str] = None


class ResourceEnableDisableRequest(BaseModel):
    """Request to enable or disable a resource for a language."""
    enabled: bool  # True = enable (remove from blacklist), False = disable (add to blacklist)
    updated_by: Optional[str] = "System"


class DisabledResourceResponse(BaseModel):
    """Response showing a disabled resource."""
    resource_id: str
    title: str
    disabled_at: Optional[datetime] = None
    disabled_by: Optional[str] = None