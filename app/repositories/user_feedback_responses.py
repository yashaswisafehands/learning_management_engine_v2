from neomodel.exceptions import DoesNotExist

from app.models.user_feedbacks import (UserFeedbackAnswer,
                                       UserFeedbackQuestion,
                                       UserFeedbackResponse)


class UserFeedbackResponseRepository:
    @staticmethod
    def save_responses(language_id: str, user_id: str, answers: list[dict]):
        saved_nodes = []
        for ans in answers:
            qid = ans["question_id"]
            value = ans["answer_value"]
            free_text = ans.get("free_text")
            answer_id = ans.get("answer_id")

            feedback = UserFeedbackResponse(
                language_id=language_id,
                question_key=qid,
                answer_value=value,
                user_id=user_id,
                free_text=free_text,
            ).save()

            question_node = UserFeedbackQuestion.nodes.get_or_none(question_key=qid)
            if question_node:
                feedback.question.connect(question_node)

            if answer_id:
                answer_node = None
                if question_node:
                    answer_node = next(
                        (
                            ans
                            for ans in question_node.answers.all()
                            if ans.answer_id == answer_id
                        ),
                        None,
                    )
                if not answer_node:
                    answer_node = UserFeedbackResponseRepository._get_answer_by_id(
                        answer_id
                    )
                if answer_node:
                    feedback.answer.connect(answer_node)

            saved_nodes.append(feedback)

        return saved_nodes

    @staticmethod
    def get_responses_by_user(user_id: str, language_id: str = None):
        """
        Fetch all responses given by a user. Optionally filter by language_id.
        """
        filters = {"user_id": user_id}
        if language_id:
            filters["language_id"] = language_id

        responses = UserFeedbackResponse.nodes.filter(**filters)

        return [
            {
                "question_id": r.question_key,
                "answer_value": r.answer_value,
                "language_id": r.language_id,
                "user_id": r.user_id,
                "free_text": getattr(r, "free_text", None),
            }
            for r in responses
        ]

    @staticmethod
    def _get_answer_by_id(answer_id: str):
        try:
            return UserFeedbackAnswer.nodes.get(answer_id=answer_id)
        except DoesNotExist:
            return None
