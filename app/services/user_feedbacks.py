from typing import Optional

from fastapi import BackgroundTasks
from neomodel.exceptions import DoesNotExist

from app.repositories.user_feedback_responses import \
    UserFeedbackResponseRepository
from app.repositories.user_feedbacks import UserFeedbackRepository
from app.schemas.user_feedbacks import (UserFeedbackAnswerResponse,
                                        UserFeedbackBaseSchema,
                                        UserFeedbackCreateRequest,
                                        UserFeedbackQuestionResponse,
                                        UserFeedbackSchema,
                                        UserFeedbackStatusUpdateRequest,
                                        UserFeedbackSubmitRequest,
                                        UserFeedbackSubmitResponse,
                                        UserFeedbackUpdateRequest,
                                        UserFeedbackVersionSchema)
from app.utils.executors import run_sync
from app.utils.neo4j_rel import safe_relationship_all


def _safe_single(relationship):
    if relationship and hasattr(relationship, "single"):
        try:
            return relationship.single()
        except DoesNotExist:
            return None
    return None


def _version_to_schema(version) -> Optional[UserFeedbackVersionSchema]:
    if not version:
        return None

    language_rel = getattr(version, "language", None)
    language_node = _safe_single(language_rel)
    language_id = getattr(language_node, "language_id", None) if language_node else None
    language_name = getattr(language_node, "name", None) if language_node else None

    derived_rel = getattr(version, "derived_from", None)
    derived_node = _safe_single(derived_rel)
    derived_from_id = (
        getattr(derived_node, "feedback_version_id", None) if derived_node else None
    )

    questions: list[UserFeedbackQuestionResponse] = []
    try:
        question_nodes = list(version.questions.all())
        question_nodes.sort(
            key=lambda q: (getattr(q, "order", 0), getattr(q, "question_key", ""))
        )
        for question in question_nodes:
            answer_nodes = (
                list(question.answers.all()) if hasattr(question, "answers") else []
            )
            answer_nodes.sort(
                key=lambda a: (getattr(a, "order", 0), getattr(a, "answer_id", ""))
            )
            answers = [
                UserFeedbackAnswerResponse(
                    answer_id=getattr(answer, "answer_id", ""),
                    label=answer.label,
                    value=answer.value,
                    order=getattr(answer, "order", None),
                    is_default=getattr(answer, "is_default", False),
                    is_correct=getattr(answer, "is_correct", False),
                    metadata=getattr(answer, "metadata", None),
                )
                for answer in answer_nodes
            ]

            questions.append(
                UserFeedbackQuestionResponse(
                    question_key=question.question_key,
                    label=question.label,
                    question_type=question.question_type,
                    help_text=question.help_text,
                    required=question.required,
                    order=getattr(question, "order", None),
                    metadata=getattr(question, "metadata", None),
                    answers=answers,
                )
            )
    except AttributeError:
        questions = []

    return UserFeedbackVersionSchema(
        feedback_version_id=version.feedback_version_id,
        title=version.title,
        description=version.description,
        content_type=version.content_type,
        version=version.version,
        status=getattr(version, "status", "draft"),
        created_at=version.created_at,
        created_by=version.created_by or "System",
        region=getattr(version, "region", None),
        language_id=language_id,
        language_name=language_name,
        derived_from_id=derived_from_id,
        questions=questions,
    )


def _feedback_to_base(version) -> UserFeedbackBaseSchema:
    feedback_rel = getattr(version, "feedback", None)
    feedback = _safe_single(feedback_rel)
    slug = feedback.slug if feedback else ""
    tag = feedback.tag if feedback else ""
    title = feedback.title if feedback else version.title
    feedback_id = (
        feedback.feedback_id
        if feedback
        else getattr(version, "feedback_version_id", "")
    )

    return UserFeedbackBaseSchema(
        feedback_id=feedback_id,
        slug=slug,
        title=title,
        tag=tag,
        content_type=version.content_type,
        version=version.version,
        status=getattr(version, "status", "draft"),
    )


def _feedback_to_schema(feedback) -> UserFeedbackSchema:
    current_original = _safe_single(getattr(feedback, "current_original_version", None))
    current_adapted = sorted(
        feedback.current_adapted_versions.all(), key=lambda v: v.version, reverse=True
    )
    current_translated = sorted(
        safe_relationship_all(
            feedback.current_translated_versions,
            "CURRENT_TRANSLATION",
        ),
        key=lambda v: v.version,
        reverse=True,
    )
    all_versions = sorted(
        feedback.versions.all(), key=lambda v: v.version, reverse=True
    )

    return UserFeedbackSchema(
        feedback_id=feedback.feedback_id,
        slug=feedback.slug,
        title=feedback.title,
        tag=feedback.tag,
        is_deleted=feedback.is_deleted,
        current_original_version=(
            _version_to_schema(current_original) if current_original else None
        ),
        current_adapted_versions=[_version_to_schema(v) for v in current_adapted],
        current_translated_versions=[_version_to_schema(v) for v in current_translated],
        versions=[_version_to_schema(v) for v in all_versions],
    )


# Using centralized run_sync from app.utils.executors


async def create_feedback(
    data: UserFeedbackCreateRequest, background_tasks: Optional[BackgroundTasks]
) -> UserFeedbackSchema:
    feedback = await run_sync(UserFeedbackRepository.create_feedback, data)
    return _feedback_to_schema(feedback)


async def list_feedbacks(
    status_filter: str = "active",
    *,
    include_containers: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list:
    items = await run_sync(
        UserFeedbackRepository.list_feedbacks,
        status_filter=status_filter,
        include_containers=include_containers,
        limit=limit,
        offset=offset,
    )
    if include_containers:
        return [_feedback_to_schema(item) for item in items]
    return [_feedback_to_base(item) for item in items]


async def get_feedback_by_id(feedback_id: str) -> UserFeedbackSchema:
    feedback = await run_sync(UserFeedbackRepository.get_feedback_by_id, feedback_id)
    return _feedback_to_schema(feedback)


async def update_feedback(
    feedback_id: str,
    data: UserFeedbackUpdateRequest,
    background_tasks: Optional[BackgroundTasks],
) -> UserFeedbackSchema:
    version = await run_sync(UserFeedbackRepository.update_feedback, feedback_id, data)
    parent = version.feedback.single()
    return _feedback_to_schema(parent)


async def update_feedback_status(
    feedback_version_id: str, status_update: UserFeedbackStatusUpdateRequest
) -> UserFeedbackVersionSchema:
    version = await run_sync(
        UserFeedbackRepository.update_feedback_status,
        feedback_version_id,
        status_update.status,
        status_update.updated_by,
    )
    return _version_to_schema(version)


async def get_questions_for_language(
    language_id: str,
) -> list[UserFeedbackQuestionResponse]:
    records = await run_sync(UserFeedbackRepository.get_active_questions, language_id)
    return [
        UserFeedbackQuestionResponse(
            question_key=item["question_id"],
            label=item["label"],
            question_type=item["type"],
            help_text=item.get("help_text"),
            required=item.get("required", False),
            order=item.get("order"),
            metadata=item.get("metadata"),
            answers=[
                UserFeedbackAnswerResponse(
                    answer_id=answer.get("answer_id") or answer["value"],
                    label=answer["label"],
                    value=answer["value"],
                    order=answer.get("order"),
                    is_default=answer.get("is_default", False),
                )
                for answer in item["answers"]
            ],
        )
        for item in records
    ]


async def submit_feedback(
    payload: UserFeedbackSubmitRequest,
) -> UserFeedbackSubmitResponse:
    answers = [
        {
            "question_id": ans.question_id,
            "answer_id": ans.answer_id,
            "answer_value": ans.answer_value,
            "free_text": ans.free_text,
        }
        for ans in payload.answers
    ]
    saved = await run_sync(
        UserFeedbackResponseRepository.save_responses,
        payload.language_id,
        payload.user_id or "",
        answers,
    )
    return UserFeedbackSubmitResponse(saved_count=len(saved))
