from typing import Optional

from pydantic import BaseModel, Field


class TranslationAddRequest(BaseModel):

    entity_id: str = Field(
        ..., description="The unique ID of the entity (e.g., category_id, course_id)."
    )
    entity_label: str = Field(
        ..., description="The label of the entity (e.g., 'Category', 'Course')."
    )
    language_id: str = Field(
        ..., description="The ID of the language for this translation."
    )
    text: str = Field(..., description="The translated caption text.")


class TranslationAddResponse(BaseModel):

    status: str
    message: str
    translation_id: Optional[str] = None


class TranslationSchema(BaseModel):
    translation_id: str
    entity_id: str
    entity_label: str
    language_id: str
    text: str

    class Config:
        from_attributes = True
