from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from neomodel import db
from neomodel.exceptions import DoesNotExist

from app.models.user_feedbacks import (UserFeedback, UserFeedbackAnswer,
                                       UserFeedbackQuestion,
                                       UserFeedbackVersion)
from app.utils.neo4j_rel import safe_relationship_all
from app.utils.slug import build_slug
from app.utils.uuid import get_uid
from app.utils.version_utils import increment_version


class UserFeedbackRepository:
    @staticmethod
    def _resolve_content_dimensions(
        content_type: Optional[str],
        *,
        language_id: Optional[str],
        region: Optional[str],
    ) -> Tuple[str, Optional[str]]:
        explicit = content_type

        if explicit:
            if explicit not in {"original", "adapted", "translated"}:
                raise ValueError(
                    f"Invalid content_type '{explicit}'. Must be one of original|adapted|translated"
                )
            if explicit == "translated" and not language_id:
                raise ValueError(
                    "language_id is required for translated user feedback versions"
                )
            if explicit == "original" and language_id:
                raise ValueError(
                    "language_id should not be provided for original user feedback versions"
                )
            if explicit == "adapted" and not region:
                region = "GLOBAL"
            if explicit in {"original", "adapted"} and not region:
                region = "GLOBAL"
            return explicit, region

        if not language_id and not region:
            return "original", "GLOBAL"
        if region and not language_id:
            return "adapted", region or "GLOBAL"
        if language_id:
            return "translated", region

        return "original", "GLOBAL"

    @staticmethod
    def _ensure_unique_slug(
        slug: str, *, exclude_feedback_id: Optional[str] = None
    ) -> None:
        existing = list(UserFeedback.nodes.filter(slug=slug))
        if exclude_feedback_id:
            existing = [
                node for node in existing if node.feedback_id != exclude_feedback_id
            ]
        if existing:
            raise ValueError(f"User feedback with slug '{slug}' already exists")

    @staticmethod
    def _get_language(language_id: str):
        from app.models.languages import Language

        try:
            return Language.nodes.get(language_id=language_id)
        except (
            DoesNotExist
        ) as exc:  # pragma: no cover - neomodel wraps exceptions dynamically
            raise ValueError(f"Language with id '{language_id}' not found") from exc

    @staticmethod
    def create_feedback(data) -> UserFeedback:
        slug = build_slug("ufb", data.tag, data.title)
        UserFeedbackRepository._ensure_unique_slug(slug)

        content_type, resolved_region = (
            UserFeedbackRepository._resolve_content_dimensions(
                getattr(data, "content_type", None),
                language_id=data.language_id,
                region=data.region,
            )
        )

        feedback = UserFeedback(
            title=data.title,
            slug=slug,
            tag=data.tag,
            is_deleted=False,
        ).save()

        version = UserFeedbackVersion(
            title=data.title,
            description=data.description,
            content_type=content_type,
            region=resolved_region,
            status="draft",
            version=1.0,
            created_by=data.created_by or "System",
        ).save()

        feedback.versions.connect(version)
        version.feedback.connect(feedback)

        if content_type == "translated" and data.language_id:
            language = UserFeedbackRepository._get_language(data.language_id)
            version.language.connect(language)

        for idx, question in enumerate(data.questions):
            payload = question.model_dump()
            payload.setdefault("order", idx)
            UserFeedbackRepository._create_question(version, payload)

        return feedback

    @staticmethod
    def get_feedback_by_id(feedback_id: str) -> UserFeedback:
        try:
            return UserFeedback.nodes.get(feedback_id=feedback_id)
        except DoesNotExist as exc:
            raise ValueError(f"UserFeedback with id '{feedback_id}' not found") from exc

    @staticmethod
    def list_feedbacks(
        *,
        status_filter: str = "active",
        include_containers: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List:
        if status_filter == "published":
            status_filter = "active"

        if include_containers:
            base_query = """
                MATCH (uf:UserFeedback)
                WHERE uf.is_deleted = false
            """
            params: dict[str, object] = {}
            if status_filter != "all":
                base_query += "\n                MATCH (uf)-[:HAS_VERSION]->(ufv:UserFeedbackVersion {status: $status})"
                params["status"] = status_filter
            base_query += "\n                RETURN DISTINCT uf"

            if offset is not None and limit is not None:
                base_query += " SKIP $skip LIMIT $limit"
                params.update({"skip": offset, "limit": limit})
            elif offset is not None:
                base_query += " SKIP $skip"
                params.update({"skip": offset})
            elif limit is not None:
                base_query += " LIMIT $limit"
                params.update({"limit": limit})

            results, _ = db.cypher_query(base_query, params)
            return [UserFeedback.inflate(row[0]) for row in results]

        if status_filter == "all":
            base_query = """
                MATCH (ufv:UserFeedbackVersion)
                WHERE ufv.is_deleted = false OR NOT EXISTS(ufv.is_deleted)
                RETURN ufv
            """
            params: dict[str, object] = {}
        else:
            base_query = """
                MATCH (ufv:UserFeedbackVersion {status: $status})
                WHERE ufv.is_deleted = false OR NOT EXISTS(ufv.is_deleted)
                RETURN ufv
            """
            params = {"status": status_filter}

        if offset is not None and limit is not None:
            base_query += " SKIP $skip LIMIT $limit"
            params.update({"skip": offset, "limit": limit})
        elif offset is not None:
            base_query += " SKIP $skip"
            params.update({"skip": offset})
        elif limit is not None:
            base_query += " LIMIT $limit"
            params.update({"limit": limit})

        results, _ = db.cypher_query(base_query, params)
        return [UserFeedbackVersion.inflate(row[0]) for row in results]

    @staticmethod
    def update_feedback(feedback_id: str, payload) -> UserFeedbackVersion:
        feedback = UserFeedbackRepository.get_feedback_by_id(feedback_id)

        updated_title = payload.title if payload.title is not None else feedback.title
        updated_tag = payload.tag if payload.tag is not None else feedback.tag

        if not updated_title:
            raise ValueError("Title is required for user feedback")
        if not updated_tag:
            raise ValueError("Tag is required for user feedback")

        slug_changed = updated_title != feedback.title or updated_tag != feedback.tag
        if slug_changed:
            new_slug = build_slug("ufb", updated_tag, updated_title)
            UserFeedbackRepository._ensure_unique_slug(
                new_slug, exclude_feedback_id=feedback.feedback_id
            )
            feedback.slug = new_slug

        if payload.title is not None:
            feedback.title = updated_title
        if payload.tag is not None:
            feedback.tag = updated_tag

        requested_content_type = payload.content_type or None
        if requested_content_type:
            content_type_for_lookup = requested_content_type
        elif payload.language_id:
            content_type_for_lookup = "translated"
        elif payload.region:
            content_type_for_lookup = "adapted"
        else:
            content_type_for_lookup = "original"

        if content_type_for_lookup == "original":
            current_version = feedback.current_original_version.single()
        elif content_type_for_lookup == "adapted":
            adapted_versions = feedback.current_adapted_versions.all()
            current_version = (
                max(adapted_versions, key=lambda v: v.version)
                if adapted_versions
                else None
            )
        elif content_type_for_lookup == "translated":
            translated_versions = safe_relationship_all(
                feedback.current_translated_versions, "CURRENT_TRANSLATION"
            )
            current_version = (
                max(translated_versions, key=lambda v: v.version)
                if translated_versions
                else None
            )
        else:
            current_version = feedback.current_original_version.single()

        if not current_version:
            versions = feedback.versions.all()
            current_version = versions[0] if versions else None
            if not current_version:
                raise ValueError(f"No versions found for UserFeedback '{feedback_id}'")

        existing_language_id = None
        language_rel = getattr(current_version, "language", None)
        if language_rel and hasattr(language_rel, "single"):
            language_obj = language_rel.single()
            if language_obj:
                existing_language_id = getattr(language_obj, "language_id", None)

        base_region = current_version.region

        resolved_content_type, resolved_region = (
            UserFeedbackRepository._resolve_content_dimensions(
                requested_content_type,
                language_id=(
                    payload.language_id
                    if payload.language_id is not None
                    else existing_language_id
                ),
                region=payload.region if payload.region is not None else base_region,
            )
        )

        language_to_link = (
            payload.language_id
            if payload.language_id is not None
            else existing_language_id if resolved_content_type == "translated" else None
        )

        existing_versions = list(
            feedback.versions.filter(content_type=resolved_content_type)
        )
        current_max = max((v.version for v in existing_versions), default=1.0)
        new_version_value = increment_version(current_max)

        new_version = UserFeedbackVersion(
            title=(
                updated_title
                if resolved_content_type == "original"
                else (
                    payload.title
                    if payload.title is not None
                    else current_version.title
                )
            ),
            description=(
                payload.description
                if payload.description is not None
                else current_version.description
            ),
            content_type=resolved_content_type,
            region=resolved_region,
            status="draft",
            version=new_version_value,
            created_by=(
                payload.created_by
                if payload.created_by is not None
                else current_version.created_by
            ),
        ).save()

        feedback.versions.connect(new_version)
        new_version.feedback.connect(feedback)

        if payload.derived_from_id:
            try:
                source_version = UserFeedbackVersion.nodes.get(
                    feedback_version_id=payload.derived_from_id
                )
                new_version.derived_from.connect(source_version)
            except DoesNotExist:
                pass

        if resolved_content_type == "translated" and language_to_link:
            language = UserFeedbackRepository._get_language(language_to_link)
            new_version.language.connect(language)

        existing_questions: Dict[str, UserFeedbackQuestion] = {
            question.question_key: question
            for question in current_version.questions.all()
        }

        if payload.questions is not None:
            for idx, question in enumerate(payload.questions):
                question_payload = (
                    question.model_dump()
                    if hasattr(question, "model_dump")
                    else dict(question)
                )
                question_payload.setdefault("order", idx)
                source_question = existing_questions.get(
                    question_payload.get("question_key")
                )
                UserFeedbackRepository._create_question(
                    new_version,
                    question_payload,
                    source_question=source_question,
                )
        else:
            for question in current_version.questions.all():
                UserFeedbackRepository._create_question(
                    new_version, {}, source_question=question
                )

        if slug_changed or payload.title is not None or payload.tag is not None:
            feedback.save()

        return new_version

    @staticmethod
    def update_feedback_status(
        feedback_version_id: str, status: str, updated_by: str = "System"
    ) -> UserFeedbackVersion:
        try:
            version = UserFeedbackVersion.nodes.get(
                feedback_version_id=feedback_version_id
            )
        except DoesNotExist as exc:
            raise ValueError(
                f"UserFeedback version with ID '{feedback_version_id}' does not exist"
            ) from exc

        if status == "published":
            status = "active"

        feedback = version.feedback.single()
        if not feedback:
            raise ValueError(
                f"No parent feedback found for version '{feedback_version_id}'"
            )

        if status == "active":
            content_type = version.content_type
            if content_type == "original":
                current = feedback.current_original_version.single()
                if current:
                    feedback.current_original_version.disconnect(current)
                feedback.current_original_version.connect(version)
            elif content_type == "adapted":
                feedback.current_adapted_versions.connect(version)
            elif content_type == "translated":
                feedback.current_translated_versions.connect(version)
        elif version.status == "active" and status != "active":
            content_type = version.content_type
            if content_type == "original":
                feedback.current_original_version.disconnect(version)
            elif content_type == "adapted":
                feedback.current_adapted_versions.disconnect(version)
            elif content_type == "translated":
                feedback.current_translated_versions.disconnect(version)

        version.status = status
        version.created_by = updated_by or version.created_by
        version.save()
        feedback.save()
        return version

    @staticmethod
    def get_active_questions(language_id: str) -> List[dict]:
        query = """
            MATCH (ufv:UserFeedbackVersion {status: 'active'})
            WHERE (
                ufv.content_type = 'translated' AND
                (ufv)-[:IN_LANGUAGE]->(:Language {language_id: $language_id})
            ) OR ufv.content_type IN ['original', 'adapted']

            WITH ufv,
                 CASE ufv.content_type
                     WHEN 'translated' THEN 2
                     WHEN 'adapted' THEN 1
                     ELSE 0
                 END AS priority
            ORDER BY priority DESC
            LIMIT 1

            MATCH (ufv)-[:HAS_QUESTION]->(q:UserFeedbackQuestion)
            OPTIONAL MATCH (q)-[:HAS_ANSWER]->(a:UserFeedbackAnswer)
            WITH q, a
            ORDER BY q.order, q.question_key, a.order

            RETURN q, collect(a) AS answers
        """
        results, _ = db.cypher_query(query, {"language_id": language_id})

        questions: List[dict] = []
        if not results:
            return questions

        # The query is structured to return one row per question, with its answers collected.
        for q_node, answers in results:
            questions.append(
                {
                    "question_id": q_node["question_key"],
                    "label": q_node["label"],
                    "type": q_node["question_type"],
                    "help_text": q_node.get("help_text"),
                    "required": q_node.get("required", False),
                    "metadata": q_node.get("metadata"),
                    "order": q_node.get("order"),
                    "answers": [
                        {
                            "answer_id": answer.get("answer_id"),
                            "value": answer["value"],
                            "label": answer["label"],
                            "question_id": q_node["question_key"],
                            "order": answer.get("order"),
                            "is_default": answer.get("is_default", False),
                        }
                        for answer in answers
                        if answer is not None
                    ],
                }
            )
        return questions

    @staticmethod
    def _create_question(
        version: UserFeedbackVersion,
        question_data: dict,
        *,
        source_question: Optional[UserFeedbackQuestion] = None,
    ) -> UserFeedbackQuestion:
        question_key = question_data.get("question_key")
        if question_key is None and source_question is not None:
            question_key = source_question.question_key
        if question_key is None:
            question_key = str(get_uid())

        label = question_data.get("label")
        if label is None and source_question is not None:
            label = source_question.label
        if label is None:
            raise ValueError("Question label is required for user feedback")

        question_type = question_data.get("question_type")
        if question_type is None and source_question is not None:
            question_type = source_question.question_type
        if question_type is None:
            raise ValueError("Question type is required for user feedback")

        help_text = question_data.get("help_text")
        if help_text is None and source_question is not None:
            help_text = source_question.help_text

        required = question_data.get("required")
        if required is None and source_question is not None:
            required = source_question.required
        if required is None:
            required = False

        order_value = question_data.get("order")
        if order_value is None and source_question is not None:
            order_value = getattr(source_question, "order", 0)
        if order_value is None:
            order_value = 0

        metadata = question_data.get("metadata")
        if metadata is None and source_question is not None:
            metadata = source_question.metadata

        question_node = UserFeedbackQuestion(
            question_id=str(get_uid()),
            question_key=question_key,
            label=label,
            question_type=question_type,
            help_text=help_text,
            required=required,
            order=order_value,
            metadata=metadata,
        ).save()

        version.questions.connect(question_node)

        source_answers: List[UserFeedbackAnswer] = []
        if source_question is not None:
            source_answers = list(source_question.answers.all())

        answers_payload = question_data.get("answers")
        if answers_payload is not None:
            base_answers: Dict[str, UserFeedbackAnswer] = {
                answer.answer_id: answer for answer in source_answers
            }
            for idx, answer in enumerate(answers_payload):
                answer_dict = (
                    answer.model_dump()
                    if hasattr(answer, "model_dump")
                    else dict(answer)
                )

                answer_lookup_id = answer_dict.get("answer_id")
                base_answer = (
                    base_answers.get(answer_lookup_id) if base_answers else None
                )

                label_value = answer_dict.get("label")
                if label_value is None and base_answer is not None:
                    label_value = base_answer.label
                if label_value is None:
                    raise ValueError("Answer label is required for user feedback")

                value = answer_dict.get("value")
                if value is None and base_answer is not None:
                    value = base_answer.value
                if value is None:
                    raise ValueError("Answer value is required for user feedback")

                order_value = answer_dict.get("order")
                if order_value is None and base_answer is not None:
                    order_value = getattr(base_answer, "order", idx)
                if order_value is None:
                    order_value = idx

                is_default = answer_dict.get("is_default")
                if is_default is None and base_answer is not None:
                    is_default = getattr(base_answer, "is_default", False)
                if is_default is None:
                    is_default = False

                is_correct = answer_dict.get("is_correct")
                if is_correct is None and base_answer is not None:
                    is_correct = getattr(base_answer, "is_correct", False)
                if is_correct is None:
                    is_correct = False

                metadata = answer_dict.get("metadata")
                if metadata is None and base_answer is not None:
                    metadata = base_answer.metadata

                new_answer_id = answer_lookup_id or str(get_uid())
                answer_node = UserFeedbackAnswer(
                    answer_id=new_answer_id,
                    label=label_value,
                    value=value,
                    order=order_value,
                    is_default=is_default,
                    is_correct=is_correct,
                    metadata=metadata,
                ).save()
                question_node.answers.connect(answer_node)
        elif source_question is not None:
            for answer in source_answers:
                new_answer = UserFeedbackAnswer(
                    answer_id=str(get_uid()),
                    label=answer.label,
                    value=answer.value,
                    order=answer.order,
                    is_default=answer.is_default,
                    is_correct=answer.is_correct,
                    metadata=answer.metadata,
                ).save()
                question_node.answers.connect(new_answer)

        return question_node
