import datetime
import types

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class DummyQuestion:
    def __init__(self, key):
        self.question_key = key


@pytest.fixture
def mock_run_sync(monkeypatch):
    # State containers
    created_flows = []
    created_versions = []
    questions = {}
    answers = {}
    sessions = {}

    def fake_create_flow(data):
        flow = types.SimpleNamespace(
            onboarding_flow_id="flow1",
            title=data.title,
            slug=data.title.lower().replace(" ", "-"),
            description=data.description,
            target_audience=None,
            estimated_duration_minutes=5,
            is_deleted=False,
            versions=[],
            current_original_version=types.SimpleNamespace(single=lambda: None),
            current_adapted_versions=[],
            current_translated_versions=[],
            created_at=datetime.datetime.utcnow(),
            created_by="tester",
        )
        created_flows.append(flow)
        return flow

    def fake_create_version(flow_id, data):
        version = types.SimpleNamespace(
            onboarding_flow_version_id="v1",
            title=data.title,
            description=data.description,
            version=1.0,
            content_type=data.content_type,
            status="draft",
            language=types.SimpleNamespace(single=lambda: None),
            region=data.region,
            derived_from=types.SimpleNamespace(single=lambda: None),
            completion_message=data.completion_message or "Thanks",
            questions=[],
            start_question=types.SimpleNamespace(single=lambda: None),
            onboarding_flow=types.SimpleNamespace(single=lambda: created_flows[0]),
            created_at=datetime.datetime.utcnow(),
            created_by="tester",
            is_deleted=False,
        )
        created_flows[0].versions.append(version)
        created_versions.append(version)
        return version

    def fake_update_status(version_id, status, updated_by):
        v = created_versions[0]
        v.status = status
        # emulate pointer update for active original
        if v.content_type == "original" and status == "active":
            created_flows[0].current_original_version = types.SimpleNamespace(single=lambda: v)
        return v

    def fake_create_question(data):
        q = types.SimpleNamespace(
            onboarding_question_id=f"q-{data.question_key}",
            question_text=data.question_text,
            question_key=data.question_key,
            question_type=data.question_type,
            is_required=True,
            help_text=None,
            placeholder_text=None,
            min_value=None,
            max_value=None,
            max_length=None,
            category=None,
            tags=None,
            answers=[],
            created_at=datetime.datetime.utcnow(),
            created_by="tester",
            is_deleted=False,
        )
        questions[data.question_key] = q
        return q

    def fake_add_question(version_id, question_id, is_start):
        q = list(questions.values())[0] if question_id.startswith("q-") else None
        v = created_versions[0]
        v.questions.append(q)
        if is_start:
            v.start_question = types.SimpleNamespace(single=lambda: q)
        return v

    def fake_create_answer(question_id, data):
        parent = list(questions.values())[0]
        ans = types.SimpleNamespace(
            onboarding_answer_id=f"ans-{data.answer_key}",
            answer_text=data.answer_text,
            answer_key=data.answer_key,
            answer_value=data.answer_value,
            order=data.order,
            is_default=data.is_default,
            next_question_key=data.next_question_key,
            end_flow=data.end_flow,
            category=data.category,
            score=data.score,
            tags=data.tags,
            created_at=datetime.datetime.utcnow(),
            created_by="tester",
            is_deleted=False,
        )
        parent.answers.append(ans)
        answers[data.answer_key] = ans
        return ans

    def fake_create_session(data):
        version = created_versions[0]
        start_q = version.start_question.single()
        sess = types.SimpleNamespace(
            session_id="sess1",
            user_id=data.user_id,
            session_token="tok1",
            status="started",
            current_question=types.SimpleNamespace(single=lambda: start_q),
            responses={},
            progress_percentage=0,
            started_at=datetime.datetime.utcnow(),
            last_activity_at=datetime.datetime.utcnow(),
            completed_at=None,
            is_deleted=False,
            flow_version=types.SimpleNamespace(single=lambda: version),
            save=lambda: None,
        )
        sessions[sess.session_id] = sess
        return sess

    def fake_update_response(session_id, question_key, response_value):
        sess = sessions[session_id]
        sess.responses[question_key] = response_value
        return sess

    def fake_get_next_question_key(session, current_key, value):
        # single question flow ends
        return None

    async def fake_run_sync(func, *args, **kwargs):
        name = func.__name__
        if name == "create_onboarding_flow":
            return fake_create_flow(*args, **kwargs)
        if name == "create_onboarding_flow_version":
            return fake_create_version(*args, **kwargs)
        if name == "get_onboarding_flow_by_id":
            return created_flows[0]
        if name == "update_onboarding_flow_version_status":
            return fake_update_status(*args, **kwargs)
        if name == "create_question":
            return fake_create_question(*args, **kwargs)
        if name == "add_question_to_flow_version":
            return fake_add_question(*args, **kwargs)
        if name == "create_answer":
            return fake_create_answer(*args, **kwargs)
        if name == "create_session":
            return fake_create_session(*args, **kwargs)
        if name == "update_session_response":
            return fake_update_response(*args, **kwargs)
        if name == "get_next_question_key":
            return fake_get_next_question_key(*args, **kwargs)
        raise AssertionError(f"Unexpected call {name}")

    monkeypatch.setattr("app.services.onboarding_flows.run_sync", fake_run_sync)

    yield {
        "flows": created_flows,
        "versions": created_versions,
        "questions": questions,
        "answers": answers,
        "sessions": sessions,
    }


def test_full_onboarding_flow_lifecycle(mock_run_sync):
    # 1. Create flow
    resp = client.post("/onboarding-flows/", json={"title": "Pregnancy Flow"})
    assert resp.status_code == 200, resp.text
    flow_id = resp.json()["onboarding_flow_id"]

    # 2. Create version
    v_resp = client.post(
        f"/onboarding-flows/{flow_id}/versions",
        json={"title": "Original V1", "content_type": "original"},
    )
    assert v_resp.status_code == 200
    assert len(v_resp.json()["versions"]) == 1

    version_id = v_resp.json()["versions"][0]["onboarding_flow_version_id"]

    # 3. Activate version
    act = client.patch(
        f"/onboarding-flows/versions/{version_id}/status",
        json={"status": "active", "updated_by": "tester"},
    )
    assert act.status_code == 200
    assert act.json()["status"] == "active"

    # 4. Create question
    q_resp = client.post("/onboarding-flows/questions", json={
        "question_text": "Are you pregnant?",
        "question_key": "pregnant",
        "question_type": "single_choice"
    })
    assert q_resp.status_code == 200
    q_id = q_resp.json()["onboarding_question_id"]

    # 5. Add question to flow version as start
    add_q = client.post(f"/onboarding-flows/{version_id}/questions/{q_id}?is_start_question=true")
    assert add_q.status_code == 200
    assert add_q.json()["start_question_key"] == "pregnant"

    # 6. Add answer to question
    ans_resp = client.post(f"/onboarding-flows/questions/{q_id}/answers", json={
        "answer_text": "Yes",
        "answer_key": "yes_key",
        "answer_value": "yes",
        "end_flow": True
    })
    assert ans_resp.status_code == 200

    # 7. Create session
    sess_resp = client.post("/onboarding-flows/sessions", json={"flow_version_id": version_id})
    assert sess_resp.status_code == 200
    assert sess_resp.json()["first_question"]["question_key"] == "pregnant"

    # 8. Submit response (ends flow)
    prog_resp = client.post("/onboarding-flows/sessions/sess1/responses", json={
        "question_key": "pregnant",
        "response_value": "yes"
    })
    assert prog_resp.status_code == 200
    assert prog_resp.json()["flow_completed"] is True
    assert prog_resp.json()["next_question_key"] is None
