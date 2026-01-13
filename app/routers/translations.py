from fastapi import APIRouter, HTTPException, status, Depends
from app.core.auth import validate_token

from app.schemas.translations import (TranslationAddRequest,
                                      TranslationAddResponse)
from app.services.translations import add_caption_to_entity

router = APIRouter(prefix="/translations", tags=["Translations"], dependencies=[Depends(validate_token)])


@router.post(
    "/category_translation",
    response_model=TranslationAddResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_caption(
    translation_data: TranslationAddRequest,
):
    result = add_caption_to_entity(
        entity_id=translation_data.entity_id,
        entity_label=translation_data.entity_label,
        language_id=translation_data.language_id,
        caption_text=translation_data.text,
    )

    # Handle potential errors from the service layer
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"],
        )

    return result
