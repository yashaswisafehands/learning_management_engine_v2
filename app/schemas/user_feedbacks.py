from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserFeedbackAnswerCreate(BaseModel):
    answer_id: Optional[str] = None
    label: str
    value: str
    order: Optional[int] = None
    is_default: bool = False
    is_correct: bool = False
    metadata: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackQuestionCreate(BaseModel):
    question_key: Optional[str] = None
    label: str
    question_type: str
    help_text: Optional[str] = None
    required: bool = False
    order: Optional[int] = None
    metadata: Optional[str] = None
    answers: List[UserFeedbackAnswerCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackCreateRequest(BaseModel):
    title: str
    tag: str
    description: Optional[str] = None
    content_type: str = Field(default="original")
    created_by: Optional[str] = "System"
    language_id: Optional[str] = None
    region: Optional[str] = None
    derived_from_id: Optional[str] = None
    questions: List[UserFeedbackQuestionCreate] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackUpdateRequest(BaseModel):
    title: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    created_by: Optional[str] = None
    language_id: Optional[str] = None
    region: Optional[str] = None
    derived_from_id: Optional[str] = None
    questions: Optional[List[UserFeedbackQuestionCreate]] = None

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackStatusUpdateRequest(BaseModel):
    status: str
    updated_by: Optional[str] = "System"


class UserFeedbackAnswerResponse(BaseModel):
    answer_id: str
    label: str
    value: str
    order: Optional[int] = None
    is_default: bool = False
    is_correct: bool = False
    metadata: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackQuestionResponse(BaseModel):
    question_key: str
    label: str
    question_type: str
    help_text: Optional[str] = None
    required: bool
    order: Optional[int] = None
    metadata: Optional[str] = None
    answers: List[UserFeedbackAnswerResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackBaseSchema(BaseModel):
    feedback_id: str
    slug: str
    title: str
    tag: str
    content_type: str
    version: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackVersionSchema(BaseModel):
    feedback_version_id: str
    title: str
    description: Optional[str]
    content_type: str
    version: float
    status: str
    created_at: datetime
    created_by: str
    region: Optional[str] = None
    language_id: Optional[str] = None
    language_name: Optional[str] = None
    derived_from_id: Optional[str] = None
    questions: List[UserFeedbackQuestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackSchema(BaseModel):
    feedback_id: str
    slug: str
    title: str
    tag: str
    is_deleted: bool = False
    current_original_version: Optional[UserFeedbackVersionSchema] = None
    current_adapted_versions: List[UserFeedbackVersionSchema] = Field(
        default_factory=list
    )
    current_translated_versions: List[UserFeedbackVersionSchema] = Field(
        default_factory=list
    )
    versions: List[UserFeedbackVersionSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackAnswerSubmission(BaseModel):
    question_id: str
    answer_id: Optional[str] = None
    answer_value: str
    free_text: Optional[str] = None


class UserFeedbackSubmitRequest(BaseModel):
    language_id: str
    user_id: Optional[str] = None
    answers: List[UserFeedbackAnswerSubmission]


class UserFeedbackSubmitResponse(BaseModel):
    saved_count: int
