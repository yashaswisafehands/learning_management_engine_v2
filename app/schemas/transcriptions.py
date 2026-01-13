from typing import Optional, Union, List, Any
from pydantic import BaseModel
from datetime import datetime


class TranscriptionVersionCreate(BaseModel):
    """Schema for creating a new transcription version."""
    data: Union[dict, list]  # Full transcription data (dict or list of items)
    updated_by: Optional[str] = None


class TranscriptionUpdate(BaseModel):
    """Schema for updating transcription version content."""
    data: Optional[Union[dict, list]] = None
    updated_by: Optional[str] = None


class TranscriptionVersionResponse(BaseModel):
    """Schema for transcription version response."""
    transcription_version_id: str
    transcription_id: str
    key: str
    data: Union[dict, list]
    version: float
    status: str
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Schema for transcription container response."""
    transcription_id: str
    key: str
    current_version: Optional[TranscriptionVersionResponse] = None
    all_versions: list[TranscriptionVersionResponse] = []
