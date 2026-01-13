from typing import Optional, Union, List, Any
from pydantic import BaseModel
from datetime import datetime


class ScreenDataVersionCreate(BaseModel):
    """Schema for creating a new screen data version."""
    data: Union[dict, list]  # Full screen data (dict or list of items)
    updated_by: Optional[str] = None


class ScreenDataUpdate(BaseModel):
    """Schema for updating screen data version content."""
    data: Optional[Union[dict, list]] = None
    updated_by: Optional[str] = None


class ScreenDataVersionResponse(BaseModel):
    """Schema for screen data version response."""
    screen_data_version_id: str
    data_id: str
    key: str
    data: Union[dict, list]
    version: float
    status: str
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None


class ScreenDataResponse(BaseModel):
    """Schema for screen data container response."""
    data_id: str
    key: str
    current_version: Optional[ScreenDataVersionResponse] = None
    all_versions: list[ScreenDataVersionResponse] = []
