from typing import Optional, Union, List, Any
from pydantic import BaseModel
from datetime import datetime


class OnboardingFlowVersionCreate(BaseModel):
    """Schema for creating a new onboarding flow version."""
    data: Union[dict, list]  # Full onboarding flow data (list of questions)
    updated_by: Optional[str] = None


class OnboardingFlowUpdate(BaseModel):
    """Schema for updating onboarding flow version content."""
    data: Optional[Union[dict, list]] = None
    updated_by: Optional[str] = None


class OnboardingFlowVersionResponse(BaseModel):
    """Schema for onboarding flow version response."""
    onboarding_flow_version_id: str
    onboarding_flow_id: str
    key: str
    data: Union[dict, list]
    version: float
    status: str
    created_at: datetime
