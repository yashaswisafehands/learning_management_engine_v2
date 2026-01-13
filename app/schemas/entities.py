from typing import Optional

from pydantic import BaseModel


class EntityCreateSchema(BaseModel):
    entity: str
    description: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        extra = "forbid"


class EntityPatchSchema(BaseModel):
    entity: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        extra = "forbid"


class EntitiyResponseSchema(BaseModel):
    entity_id: str
    entity: str
    description: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        from_attributes = True
