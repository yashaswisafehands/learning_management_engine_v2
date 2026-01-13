from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AssetSchema(BaseModel):
    asset_id: str
    filename: str
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    extension: Optional[str] = None
    tag: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    file_url: Optional[str] = None
    version: Optional[float] = 1.0
    status: Optional[str] = "draft"
    linked_assets: List[AssetSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AssetBaseSchema(BaseModel):
    asset_id: str
    filename: str

    class Config:
        from_attributes = True


class AssetSASResponse(BaseModel):
    sas_url: str


class AssetUploadResponse(BaseModel):
    asset_id: str
    filename: str
    original_filename: str
    mime_type: str
    extension: str
    size_bytes: int
    file_url: str
    sha256: str
    created_at: datetime
    tag: str
    version: float
    linked_assets: List[AssetSchema] = Field(default_factory=list)


class AssetDownloadResponse(BaseModel):
    asset_id: str
    asset_url: str
    sha256: str
    expires_in_minutes: int
    size_bytes: int


AssetSchema.update_forward_refs()
