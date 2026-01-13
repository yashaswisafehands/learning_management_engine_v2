from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.key_learning_points import KeyLearningPointResponse
from app.schemas.resources import ResourceWithOrderSchema


class ModuleCreateRequest(BaseModel):
    """Request payload for creating a Module.

    language_id/region removed in model update; they are no longer persisted.
    """

    title: str
    description: Optional[str]
    icon: Optional[str] = None
    created_by: Optional[str] = "System"

    videos: List[str] = Field(default_factory=list)
    action_cards: List[str] = Field(default_factory=list)
    practical_procedures: List[str] = Field(default_factory=list)
    key_learning_points: List[str] = Field(default_factory=list)
    drugs: List[str] = Field(default_factory=list)


class ModuleUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    created_by: Optional[str] = None
    videos: Optional[List[str]] = None
    action_cards: Optional[List[str]] = None
    practical_procedures: Optional[List[str]] = None
    key_learning_points: Optional[List[str]] = None
    drugs: Optional[List[str]] = None


class ModuleStatusUpdateRequest(BaseModel):
    # Allowed statuses: draft | active | superseded | reverted | archived | review
    status: str  # draft | active | superseded | reverted | archived | review
    updated_by: Optional[str] = "System"


class ModuleBaseSchema(BaseModel):
    module_id: str
    title: str
    slug: str
    tag: Optional[str] = None
    description: Optional[str]
    version: Optional[float] = 1.0
    icon: Optional[str] = None

    class Config:
        from_attributes = True


class ModuleVersionSchema(BaseModel):
    module_version_id: str
    title: str
    slug: str
    description: Optional[str]
    version: float
    status: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    icon: Optional[str] = None
    videos: List[ResourceWithOrderSchema] = Field(default_factory=list)
    action_cards: List[ResourceWithOrderSchema] = Field(default_factory=list)
    practical_procedures: List[ResourceWithOrderSchema] = Field(default_factory=list)
    drugs: List[ResourceWithOrderSchema] = Field(default_factory=list)
    key_learning_points: List[KeyLearningPointResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ModuleSchema(BaseModel):
    module_id: str
    title: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    versions: List[ModuleVersionSchema] = Field(default_factory=list)
    current_version: Optional[ModuleVersionSchema] = None

    class Config:
        from_attributes = True
