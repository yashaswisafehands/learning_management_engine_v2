from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.modules import ModuleBaseSchema


class CategoryCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    modules: Optional[list[str]] = []
    created_by: Optional[str] = "System"


class CategoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    modules: Optional[list[str]] = []
    created_by: Optional[str] = None


class CategoryStatusUpdateRequest(BaseModel):
    # Allowed: draft, active, archived, review, superseded, reverted
    # Legacy 'published' accepted by API but translated to 'active'.
    status: str
    updated_by: Optional[str] = "System"


class CategoryVersionSchema(BaseModel):
    category_version_id: str
    title: str
    description: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    version: float
    icon: Optional[str] = None
    modules: Optional[List[ModuleBaseSchema]] = []
    status: str

    class Config:
        from_attributes = True


class CategoryBaseSchema(BaseModel):
    category_id: str
    title: str
    slug: str
    description: str
    icon: Optional[str] = None
    version: float
    modules: Optional[List[ModuleBaseSchema]] = []

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    category_id: str
    slug: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    # Optional shorthand latest version number for convenience
    version: Optional[float] = None

    versions: Optional[List[CategoryVersionSchema]] = None
    current_version: Optional[CategoryVersionSchema] = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
