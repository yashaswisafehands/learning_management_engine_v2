from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KLPAnswerCreate(BaseModel):
    answer_id: Optional[str] = None
    value: str
    correct: bool = False
    order: Optional[int] = None

    class Config:
        from_attributes = True


class KLPQuestionCreate(BaseModel):
    question_id: Optional[str] = None
    question: str
    quizz_type: str
    icon: Optional[str] = None
    link: Optional[str] = None
    show_toggle: bool = False
    essential: bool = False
    description: Optional[str] = None
    order: Optional[int] = None
    answers: List[KLPAnswerCreate] = Field(default_factory=list)

    class Config:
        from_attributes = True


class KeyLearningPointCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    level: str  # Required level field from container
    content_type: str = Field(
        default="original", description="Content type: original, adapted, translated"
    )
    created_by: Optional[str] = "System"
    language_id: Optional[str] = None  # For translated content
    region: Optional[str] = None  # For adapted content
    derived_from_id: Optional[str] = None  # ID of the version this is derived from
    questions: List[KLPQuestionCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KeyLearningPointUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    content_type: Optional[str] = None
    created_by: Optional[str] = None
    language_id: Optional[str] = None
    region: Optional[str] = None
    derived_from_id: Optional[str] = None
    questions: Optional[List[KLPQuestionCreate]] = None

    model_config = ConfigDict(from_attributes=True)


class KeyLearningPointStatusUpdateRequest(BaseModel):
    status: str  # one of: draft, active, superseded, reverted, archived, review
    updated_by: Optional[str] = "System"


class KLPAnswerResponse(BaseModel):
    answer_id: str
    value: str
    correct: bool
    order: Optional[int] = None

    class Config:
        from_attributes = True


class KLPQuestionResponse(BaseModel):
    question_id: str
    question: str
    quizz_type: str
    icon: Optional[str] = None
    link: Optional[str] = None  # resource id instead of URL string
    show_toggle: bool
    essential: bool
    description: Optional[str] = None
    order: Optional[int] = None
    answers: List[KLPAnswerResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class KeyLearningPointBaseSchema(BaseModel):
    klp_id: str
    slug: str
    title: str
    description: Optional[str]
    level: str  # From container
    content_type: str
    version: Optional[float] = 1.0

    model_config = ConfigDict(from_attributes=True)


class KeyLearningPointVersionSchema(BaseModel):
    klp_version_id: str
    title: str
    description: Optional[str]
    content_type: str  # original, adapted, translated
    version: float
    status: str
    created_at: datetime
    created_by: str
    is_deleted: bool
    language_id: Optional[str] = None
    language_name: Optional[str] = None
    region: Optional[str] = None
    derived_from_id: Optional[str] = None
    questions: List[KLPQuestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KeyLearningPointSchema(BaseModel):
    klp_id: str
    title: str
    slug: str
    level: str  # From container
    is_deleted: bool = False
    # Following Resource pattern with current pointers
    current_original_version: Optional[KeyLearningPointVersionSchema] = None
    current_adapted_versions: List[KeyLearningPointVersionSchema] = Field(
        default_factory=list
    )
    current_translated_versions: List[KeyLearningPointVersionSchema] = Field(
        default_factory=list
    )
    versions: List[KeyLearningPointVersionSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Legacy schemas for backward compatibility
class KeyLearningPointResponse(BaseModel):
    klp_id: str
    title: Optional[str] = None
    version: Optional[float] = None
    level: Optional[str] = None
    description: Optional[str] = None
    questions: list[KLPQuestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
