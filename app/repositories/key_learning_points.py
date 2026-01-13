from typing import Dict, List, Optional, Tuple

from neomodel.exceptions import DoesNotExist

from app.models.key_learning_points import (KeyLearningPoint,
                                            KeyLearningPointVersion, KLPAnswer,
                                            KLPQuestion)
from app.models.modules import Module
from app.models.resources import Resource
from app.repositories.assets import AssetRepository
from app.schemas.key_learning_points import (KeyLearningPointCreateRequest,
                                             KeyLearningPointUpdateRequest)
from app.utils.lifecycle import validate_status
from app.utils.neo4j_rel import safe_relationship_all
from app.utils.slug import build_slug
from app.utils.uuid import get_uid
from app.utils.version_utils import increment_version


class KeyLearningPointRepository:
    @staticmethod
    def _ensure_unique_slug(slug: str, *, exclude_klp_id: Optional[str] = None) -> None:
        """Ensure slug is unique across non-deleted KLP containers."""

        existing = list(KeyLearningPoint.nodes.filter(slug=slug))
        if exclude_klp_id:
            existing = [klp for klp in existing if klp.klp_id != exclude_klp_id]
        if existing:
            raise ValueError(f"Key Learning Point with slug '{slug}' already exists")

    @staticmethod
    def _resolve_content_dimensions(
        content_type: Optional[str],
        *,
        language_id: Optional[str],
        region: Optional[str],
    ) -> Tuple[str, Optional[str]]:
        """Determine content type/region following Resource rules."""

        explicit = content_type

        if explicit:
            if explicit not in {"original", "adapted", "translated"}:
                raise ValueError(
                    f"Invalid content_type '{explicit}'. Must be one of original|adapted|translated"
                )
            if explicit == "translated" and not language_id:
                raise ValueError("language_id is required for translated KLP versions")
            if explicit == "original" and language_id:
                raise ValueError(
                    "language_id should not be set when creating or updating an original KLP version"
                )
            if explicit == "adapted" and not region:
                region = "GLOBAL"
            if explicit in {"original", "adapted"} and not region:
                region = "GLOBAL"
            return explicit, region

        # Infer content type when not explicitly provided
        if not language_id and not region:
            return "original", "GLOBAL"
        if region and not language_id:
            return "adapted", region or "GLOBAL"
        if language_id:
            # translated variants can carry optional region metadata
            return "translated", region

        return "original", "GLOBAL"

    @staticmethod
    def _get_language(language_id: str):
        from app.models.languages import \
            Language  # Lazy import to avoid cycles

        try:
            return Language.nodes.get(language_id=language_id)
        except DoesNotExist:
            raise ValueError(f"Language with id '{language_id}' not found")

    @staticmethod
    def _get_resource(resource_id: str) -> Resource:
        try:
            return Resource.nodes.get(resource_id=resource_id)
        except DoesNotExist:
            raise ValueError(f"Resource with id '{resource_id}' not found")

    @staticmethod
    def create_klp(data: KeyLearningPointCreateRequest) -> KeyLearningPoint:
        """Create KLP container and initial version following Resource pattern."""
        # Create the KeyLearningPoint container (like Resource)
        slug = build_slug("klp", data.level, data.title)
        KeyLearningPointRepository._ensure_unique_slug(slug)

        content_type, resolved_region = (
            KeyLearningPointRepository._resolve_content_dimensions(
                getattr(data, "content_type", None),
                language_id=data.language_id,
                region=data.region,
            )
        )

        klp = KeyLearningPoint(
            title=data.title,
            slug=slug,
            level=data.level,
            is_deleted=False,
        ).save()

        # Create the first KeyLearningPointVersion (like ResourceVersion)
        klp_version = KeyLearningPointVersion(
            title=data.title,
            description=data.description,
            content_type=content_type,
            region=resolved_region,
            status="draft",
            version=1.0,
            created_by=data.created_by or "System",
            language_id=data.language_id if content_type == "translated" else None,
        ).save()

        # Link version to container
        klp.versions.connect(klp_version)
        klp_version.key_learning_point.connect(klp)

        # DON'T set as current version - only active versions should be current
        # Draft versions are not linked to current pointers until they become active

        # Handle derivation relationship
        if data.derived_from_id:
            try:
                source_version = KeyLearningPointVersion.nodes.get(
                    klp_version_id=data.derived_from_id
                )
                klp_version.derived_from.connect(source_version)
            except DoesNotExist:
                pass  # Source version not found, continue without derivation

        # Handle language relationship for translations
        if content_type == "translated" and data.language_id:
            language = KeyLearningPointRepository._get_language(data.language_id)
            klp_version.language.connect(language)

        # Add questions to this version
        for idx, q_data in enumerate(data.questions):
            question_payload = q_data.model_dump()
            question_payload.setdefault("order", idx)
            KeyLearningPointRepository.add_question(klp_version, question_payload)

        return klp

    @staticmethod
    def get_klp_by_id(klp_id: str) -> KeyLearningPoint:
        """Get KLP container by klp_id."""
        try:
            return KeyLearningPoint.nodes.get(klp_id=klp_id)
        except DoesNotExist:
            raise ValueError(f"KeyLearningPoint with id '{klp_id}' not found")

    @staticmethod
    def get_klps(
        status_filter: str = "active",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include_containers: bool = False,
    ) -> list:
        """Get KLPs following Resource pattern."""
        from neomodel import db

        # Backward compatibility: map 'published' to 'active'
        if status_filter == "published":
            status_filter = "active"

        if include_containers:
            if status_filter == "all":
                base_query = """
                    MATCH (klp:KeyLearningPoint)
                    WHERE NOT klp.is_deleted
                    RETURN DISTINCT klp
                """
                params: dict[str, int] = {}
            else:
                base_query = """
                    MATCH (klp:KeyLearningPoint)
                    WHERE NOT klp.is_deleted
                    OPTIONAL MATCH (klp)-[:HAS_VERSION]->(klpv:KeyLearningPointVersion {status: $status})
                    WITH klp, collect(klpv) AS versions
                    WHERE any(v IN versions WHERE v IS NOT NULL)
                    RETURN DISTINCT klp
                """
                params = {"status": status_filter}

            if offset is not None and limit is not None:
                query = base_query + " SKIP $skip LIMIT $limit"
                params = {**params, "skip": offset, "limit": limit}
            elif offset is not None:
                query = base_query + " SKIP $skip"
                params = {**params, "skip": offset}
            elif limit is not None:
                query = base_query + " LIMIT $limit"
                params = {**params, "limit": limit}
            else:
                query = base_query

            results, _ = db.cypher_query(query, params)
            return [KeyLearningPoint.inflate(row[0]) for row in results]

        # Return version list (following Resource pattern)
        if status_filter == "all":
            base_query = """
                MATCH (klpv:KeyLearningPointVersion)
                WHERE NOT klpv.is_deleted
                RETURN klpv
            """
        else:
            base_query = f"""
                MATCH (klpv:KeyLearningPointVersion {{status: '{status_filter}'}})
                WHERE NOT klpv.is_deleted
                RETURN klpv
            """

        params = {}
        if offset is not None and limit is not None:
            query = base_query + " SKIP $skip LIMIT $limit"
            params = {"skip": offset, "limit": limit}
        elif offset is not None:
            query = base_query + " SKIP $skip"
            params = {"skip": offset}
        elif limit is not None:
            query = base_query + " LIMIT $limit"
            params = {"limit": limit}
        else:
            query = base_query

        results, _ = db.cypher_query(query, params)
        return [KeyLearningPointVersion.inflate(row[0]) for row in results]

    @staticmethod
    def update_klp(
        klp_id: str, payload: KeyLearningPointUpdateRequest
    ) -> KeyLearningPointVersion:
        """Update KLP following Resource pattern - create new version."""
        klp = KeyLearningPointRepository.get_klp_by_id(klp_id)

        # Update container metadata and slug when title/level change
        updated_title = payload.title if payload.title is not None else klp.title
        updated_level = payload.level if payload.level is not None else klp.level

        if not updated_title:
            raise ValueError("Title is required for Key Learning Points")

        slug_changed = updated_title != klp.title or updated_level != klp.level
        if slug_changed:
            new_slug = build_slug("klp", updated_level, updated_title)
            KeyLearningPointRepository._ensure_unique_slug(
                new_slug, exclude_klp_id=klp.klp_id
            )
            klp.title = updated_title
            klp.level = updated_level
            klp.slug = new_slug
        else:
            # Persist any other container adjustments even when slug stays constant
            if payload.title is not None or payload.level is not None:
                klp.title = updated_title
                klp.level = updated_level

        # Determine desired content type for new version
        requested_content_type = payload.content_type or None
        if requested_content_type:
            content_type_for_lookup = requested_content_type
        elif payload.language_id:
            content_type_for_lookup = "translated"
        elif payload.region:
            content_type_for_lookup = "adapted"
        else:
            content_type_for_lookup = "original"

        # Get current version based on content type
        if content_type_for_lookup == "original":
            current_version = klp.current_original_version.single()
        elif content_type_for_lookup == "adapted":
            # Get the latest adapted version
            adapted_versions = klp.current_adapted_versions.all()
            current_version = (
                max(adapted_versions, key=lambda v: v.version)
                if adapted_versions
                else None
            )
        elif content_type_for_lookup == "translated":
            # Get the latest translated version
            translated_versions = safe_relationship_all(
                klp,
                "current_translated_versions",
                rel_type="CURRENT_TRANSLATION",
            )
            current_version = (
                max(translated_versions, key=lambda v: v.version)
                if translated_versions
                else None
            )
        else:
            current_version = klp.current_original_version.single()

        if not current_version:
            # If no current version, get any version as template
            versions = klp.versions.all()
            current_version = versions[0] if versions else None
            if not current_version:
                raise ValueError(f"No versions found for KLP '{klp_id}'")

        # Determine base language/region when not explicitly supplied
        existing_language_id = None
        language_rel = getattr(current_version, "language", None)
        if language_rel and hasattr(language_rel, "single"):
            language_obj = language_rel.single()
            if language_obj:
                existing_language_id = getattr(language_obj, "language_id", None)

        base_region = current_version.region

        resolved_content_type, resolved_region = (
            KeyLearningPointRepository._resolve_content_dimensions(
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

        # Calculate new version
        existing_versions = list(
            klp.versions.filter(content_type=resolved_content_type)
        )
        current_max = max((v.version for v in existing_versions), default=1.0)
        new_version = increment_version(current_max)

        # Create new version
        new_klp_version = KeyLearningPointVersion(
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
            version=new_version,
            created_by=(
                payload.created_by
                if payload.created_by is not None
                else current_version.created_by
            ),
            language_id=language_to_link,
        ).save()

        # Link to container
        klp.versions.connect(new_klp_version)
        new_klp_version.key_learning_point.connect(klp)

        # Handle derivation relationship
        if payload.derived_from_id:
            try:
                source_version = KeyLearningPointVersion.nodes.get(
                    klp_version_id=payload.derived_from_id
                )
                new_klp_version.derived_from.connect(source_version)
            except DoesNotExist:
                pass

        # Handle language relationship for translations
        if resolved_content_type == "translated" and language_to_link:
            language = KeyLearningPointRepository._get_language(language_to_link)
            new_klp_version.language.connect(language)

        # Ensure container updates are persisted when metadata changed
        if slug_changed or payload.title is not None or payload.level is not None:
            klp.save()

        # Snapshot existing questions for granular updates
        existing_question_map: Dict[str, KLPQuestion] = {
            question.question_id: question
            for question in current_version.questions.all()
        }

        # Handle questions
        if payload.questions is not None:
            for idx, q_data in enumerate(payload.questions):
                question_payload = (
                    q_data.model_dump()
                    if hasattr(q_data, "model_dump")
                    else dict(q_data)
                )
                question_payload.setdefault("order", idx)
                source_question = existing_question_map.get(
                    question_payload.get("question_id")
                )
                KeyLearningPointRepository._create_question_for_version(
                    new_klp_version,
                    question_payload,
                    source_question=source_question,
                )
        else:
            # Copy existing questions
            for question in current_version.questions.all():
                KeyLearningPointRepository._copy_question(question, new_klp_version)

        return new_klp_version

    @staticmethod
    def update_klp_status(
        klp_version_id: str, status: str, updated_by: str = "System"
    ) -> KeyLearningPointVersion:
        """Update KLP version status using lifecycle helpers."""
        try:
            version = KeyLearningPointVersion.nodes.get(klp_version_id=klp_version_id)
        except Exception:
            raise ValueError(f"KLP version with ID '{klp_version_id}' does not exist")

        # Backward compatibility
        if status == "published":
            status = "active"
        validate_status(status)

        klp = version.key_learning_point.single()
        if not klp:
            raise ValueError(f"No parent KLP found for version '{klp_version_id}'")

        # Update current pointers based on content type and status following Resource pattern
        if status == "active":
            content_type = version.content_type
            if content_type == "original":
                # Replace current original version
                current = klp.current_original_version.single()
                if current:
                    klp.current_original_version.disconnect(current)
                klp.current_original_version.connect(version)
            elif content_type == "adapted":
                # Add to current adapted versions
                klp.current_adapted_versions.connect(version)
            elif content_type == "translated":
                # Add to current translated versions
                klp.current_translated_versions.connect(version)

        elif version.status == "active" and status != "active":
            # Remove from current pointers when deactivating
            content_type = version.content_type
            if content_type == "original":
                klp.current_original_version.disconnect(version)
            elif content_type == "adapted":
                klp.current_adapted_versions.disconnect(version)
            elif content_type == "translated":
                klp.current_translated_versions.disconnect(version)

        version.status = status
        if updated_by:
            version.created_by = updated_by
        version.save()
        klp.save()
        return version

    @staticmethod
    def add_question(
        klp_version: KeyLearningPointVersion, question_data: dict
    ) -> KLPQuestion:
        """Add question to KLP version."""
        return KeyLearningPointRepository._create_question_for_version(
            klp_version, question_data
        )

    @staticmethod
    def _copy_question(
        original_question: KLPQuestion, new_version: KeyLearningPointVersion
    ) -> KLPQuestion:
        """Copy question to new version."""
        return KeyLearningPointRepository._create_question_for_version(
            new_version,
            {},
            source_question=original_question,
        )

    @staticmethod
    def _create_question_for_version(
        klp_version: KeyLearningPointVersion,
        question_data: dict,
        *,
        source_question: Optional[KLPQuestion] = None,
    ) -> KLPQuestion:
        """Create question (with answers) for a version, optionally using a source question."""

        # Fall back to source values when not provided to support granular updates
        question_text = question_data.get("question")
        if question_text is None and source_question is not None:
            question_text = source_question.question
        if question_text is None:
            raise ValueError(
                "Question text is required for Key Learning Point versions"
            )

        quizz_type = question_data.get("quizz_type")
        if quizz_type is None and source_question is not None:
            quizz_type = source_question.quizz_type
        if quizz_type is None:
            raise ValueError("quizz_type is required for Key Learning Point questions")

        show_toggle = (
            question_data.get("show_toggle")
            if "show_toggle" in question_data
            else (source_question.show_toggle if source_question else False)
        )
        essential = (
            question_data.get("essential")
            if "essential" in question_data
            else (source_question.essential if source_question else False)
        )
        description = (
            question_data.get("description")
            if "description" in question_data
            else (source_question.description if source_question else None)
        )

        order_value = question_data.get("order")
        if order_value is None and source_question is not None:
            order_value = getattr(source_question, "order", 0)
        if order_value is None:
            order_value = 0

        new_question = KLPQuestion(
            question_id=str(get_uid()),
            question=question_text,
            quizz_type=quizz_type,
            show_toggle=show_toggle,
            essential=essential,
            description=description,
            order=order_value,
        ).save()
        klp_version.questions.connect(new_question)

        # Icon handling
        if "icon" in question_data:
            icon_ref = question_data.get("icon")
            if icon_ref:
                icon_asset = AssetRepository.get_asset_by_id(icon_ref)
                new_question.icon.connect(icon_asset)
        elif source_question is not None:
            icon = source_question.icon.single()
            if icon:
                new_question.icon.connect(icon)

        # Resource link handling
        if "link" in question_data:
            link_ref = question_data.get("link")
            if link_ref:
                resource = KeyLearningPointRepository._get_resource(link_ref)
                new_question.link.connect(resource)
        elif source_question is not None:
            resource = source_question.link.single()
            if resource:
                new_question.link.connect(resource)

        source_answers: List[KLPAnswer] = []
        if source_question is not None:
            source_answers = list(source_question.answers.all())

        answers_payload = question_data.get("answers")
        if answers_payload is not None:
            base_answers: Dict[str, KLPAnswer] = {
                answer.answer_id: answer for answer in source_answers
            }

            for idx, ans_data in enumerate(answers_payload):
                # Support dict or BaseModel instances
                if hasattr(ans_data, "model_dump"):
                    ans_dict = ans_data.model_dump()
                else:
                    ans_dict = dict(ans_data)

                base_answer = (
                    base_answers.get(ans_dict.get("answer_id"))
                    if base_answers
                    else None
                )

                value = ans_dict.get("value")
                if value is None and base_answer is not None:
                    value = base_answer.value
                if value is None:
                    raise ValueError(
                        "Answer value is required for Key Learning Point questions"
                    )

                correct = ans_dict.get("correct")
                if correct is None:
                    correct = base_answer.correct if base_answer is not None else False

                answer_order = ans_dict.get("order")
                if answer_order is None and base_answer is not None:
                    answer_order = getattr(base_answer, "order", idx)
                if answer_order is None:
                    answer_order = idx

                new_answer = KLPAnswer(
                    value=value,
                    correct=correct,
                    order=answer_order,
                ).save()
                new_question.answers.connect(new_answer)
        elif source_question is not None:
            for answer in source_answers:
                new_answer = KLPAnswer(
                    value=answer.value,
                    correct=answer.correct,
                    order=answer.order,
                ).save()
                new_question.answers.connect(new_answer)

        return new_question

    @staticmethod

    def connect_to_module(klp: KeyLearningPoint, module_id: str):
        module = Module.nodes.get(module_id=module_id)
        klp.module.connect(module)

        # --- FIX: Also connect to active ModuleVersion ---
        mv = module.current_version.single()
        if mv:
            mv.key_learning_points.connect(klp)

        return klp
