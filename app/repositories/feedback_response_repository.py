from app.models.user_feedbacks import (UserFeedbackQuestion,
                                       UserFeedbackResponse)


class FeedbackResponseRepository:
    @staticmethod
    def save_responses(language_id: str, user_id: str, answers: list[dict]):
        saved_nodes = []
        for ans in answers:
            qid = ans["question_id"]
            value = ans["answer_value"]

            feedback = UserFeedbackResponse(
                language_id=language_id,
                question_key=qid,
                answer_value=value,
                user_id=user_id,
            ).save()

            question_node = UserFeedbackQuestion.nodes.get_or_none(question_key=qid)
            if question_node:
                feedback.question.connect(question_node)

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
            }
            for r in responses
        ]
