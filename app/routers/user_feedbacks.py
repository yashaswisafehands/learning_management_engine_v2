from typing import Literal, Optional, Union
from fastapi import APIRouter, BackgroundTasks, Query, Depends
from app.core.auth import validate_token

from app.schemas.user_feedbacks import (UserFeedbackBaseSchema,
                                        UserFeedbackCreateRequest,
                                        UserFeedbackQuestionResponse,
                                        UserFeedbackSchema,
                                        UserFeedbackStatusUpdateRequest,
                                        UserFeedbackSubmitRequest,
                                        UserFeedbackSubmitResponse,
                                        UserFeedbackUpdateRequest,
                                        UserFeedbackVersionSchema)
from app.services import user_feedbacks as user_feedback_service

router = APIRouter(prefix="/user-feedbacks", tags=["User Feedbacks"], dependencies=[Depends(validate_token)])


@router.post("/", response_model=UserFeedbackSchema)
async def create_user_feedback(
    payload: UserFeedbackCreateRequest,
    background_tasks: BackgroundTasks,
):
    return await user_feedback_service.create_feedback(payload, background_tasks)


@router.get(
    "/",
    response_model=Union[list[UserFeedbackSchema], list[UserFeedbackBaseSchema]],
)
async def list_user_feedbacks(
    status_filter: Literal["active", "draft", "all"] = Query("active"),
    include_containers: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=200),
    offset: Optional[int] = Query(None, ge=0),
):
    return await user_feedback_service.list_feedbacks(
        status_filter=status_filter,
        include_containers=include_containers,
        limit=limit,
        offset=offset,
    )


@router.get("/{feedback_id}", response_model=UserFeedbackSchema)
async def get_user_feedback(feedback_id: str):
    return await user_feedback_service.get_feedback_by_id(feedback_id)


@router.patch("/{feedback_id}", response_model=UserFeedbackSchema)
async def update_user_feedback(
    feedback_id: str,
    payload: UserFeedbackUpdateRequest,
    background_tasks: BackgroundTasks,
):
    return await user_feedback_service.update_feedback(
        feedback_id=feedback_id,
        data=payload,
        background_tasks=background_tasks,
    )


@router.patch(
    "/versions/{feedback_version_id}/status",
    response_model=UserFeedbackVersionSchema,
)
async def update_user_feedback_status(
    feedback_version_id: str,
    status_update: UserFeedbackStatusUpdateRequest,
):
    return await user_feedback_service.update_feedback_status(
        feedback_version_id,
        status_update,
    )


@router.get(
    "/questions",
    response_model=list[UserFeedbackQuestionResponse],
)
async def get_questions(
    language_id: str = Query(..., description="Language identifier")
):
    return await user_feedback_service.get_questions_for_language(language_id)


@router.post(
    "/responses",
    response_model=UserFeedbackSubmitResponse,
)
async def submit_user_feedback(payload: UserFeedbackSubmitRequest):
    return await user_feedback_service.submit_feedback(payload)
