from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api import ai_endpoints
from app.core.config import settings
from app.main import app
from app.models.agent_models import Agent
from app.models.campaign_models import Campaign, CampaignSequence, Lead
from app.models.database import get_db
from app.models.prompt_models import PromptTemplate
from app.models.user_models import User
from app.models.workflow_models import Workflow, WorkflowStep
from app.services import workspace_confirmation as tokens
from app.services.workspace_execution import _execute_assistant_draft


@pytest.fixture
def workspace_session(client):
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: 0)), add=lambda row: rows.append(row)
    )
    rows = []
    session.rows = rows

    async def override():
        yield session

    app.dependency_overrides[get_db] = override
    return session


def test_workspace_preview_and_confirmed_execution(client, monkeypatch, workspace_session):
    draft = {"prompt": {"name": "Review", "template": "Review the message"}}
    generate = AsyncMock(return_value={"success": True, "draft": draft})
    execute = AsyncMock(return_value={"created": {"prompt_id": "created"}})
    monkeypatch.setattr(ai_endpoints.llm_service, "create_workspace_assist", generate)
    monkeypatch.setattr(ai_endpoints.workspace_assistant_service, "_execute_assistant_draft", execute)
    payload = dict(page="prompts", objective="Review messages", mode="execute")
    preview = client.post("/api/v1/ai/assistant/assist", json=payload)
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["requires_confirmation"] is True
    assert result["usage"]["month_used"] == 1
    assert len(workspace_session.rows) == 1
    assert workspace_session.rows[0].user_id == "test-user-id"
    execute.assert_not_awaited()
    confirmed = client.post(
        "/api/v1/ai/assistant/assist",
        json={**payload, "confirmed": True, "draft": draft, "confirmation_token": result["confirmation_token"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["execution"]["created"]["prompt_id"] == "created"
    execute.assert_awaited_once()
    generate.assert_awaited_once()
    assert len(workspace_session.rows) == 1


@pytest.mark.parametrize(
    "case, expected", [("missing", 400), ("signature", 400), ("user", 403), ("draft", 400), ("expired", 400)]
)
def test_confirmation_rejects_invalid_execution(client, monkeypatch, case, expected):
    draft = {"prompt": {"template": "Review"}}
    token = tokens._create_confirmation_token("other" if case == "user" else "test-user-id", "prompts", "Review", draft)
    if case == "signature":
        token += "tampered"
    if case == "draft":
        draft = {"prompt": {"template": "Changed"}}
    if case == "expired":
        monkeypatch.setattr(tokens.time, "time", lambda: 9999999999)
    execute = AsyncMock()
    monkeypatch.setattr(ai_endpoints.workspace_assistant_service, "_execute_assistant_draft", execute)
    response = client.post(
        "/api/v1/ai/assistant/assist",
        json=dict(
            page="prompts",
            objective="Review",
            mode="execute",
            confirmed=True,
            draft=draft,
            confirmation_token=None if case == "missing" else token,
        ),
    )
    assert response.status_code == expected, response.text
    execute.assert_not_awaited()


def test_workspace_quota_and_admin_bypass(client, authenticated_user, monkeypatch, workspace_session):
    monkeypatch.setattr(settings, "WORKPLACE_ASSIST_MONTHLY_LIMIT", 2)
    workspace_session.execute.return_value = SimpleNamespace(scalar_one=lambda: 2)
    generate = AsyncMock(return_value={"success": True, "draft": {}})
    monkeypatch.setattr(ai_endpoints.llm_service, "create_workspace_assist", generate)
    payload = dict(page="agents", objective="Review")
    assert client.post("/api/v1/ai/assistant/assist", json=payload).status_code == 429
    generate.assert_not_awaited()
    assert workspace_session.rows == []
    authenticated_user.is_admin = True
    assert client.post("/api/v1/ai/assistant/assist", json=payload).status_code == 200


@pytest.mark.parametrize(
    "result, status", [({"success": False, "error": "Unavailable"}, 502), (RuntimeError("provider failed"), 500)]
)
def test_workspace_provider_errors_do_not_record_usage(client, monkeypatch, workspace_session, result, status):
    generate = AsyncMock(side_effect=result) if isinstance(result, Exception) else AsyncMock(return_value=result)
    monkeypatch.setattr(ai_endpoints.llm_service, "create_workspace_assist", generate)
    response = client.post("/api/v1/ai/assistant/assist", json=dict(page="agents", objective="Review"))
    assert response.status_code == status
    assert workspace_session.rows == []


def test_provider_live_health_requires_admin(client, authenticated_user, monkeypatch):
    health = AsyncMock(return_value={"ready": True})
    monkeypatch.setattr(ai_endpoints.llm_service, "provider_health", health)
    assert client.get("/api/v1/ai/health?check_live=true").status_code == 403
    health.assert_not_awaited()
    authenticated_user.is_admin = True
    assert client.get("/api/v1/ai/health?check_live=true").status_code == 200
    assert health.call_args.kwargs["include_live_checks"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page, draft, model",
    [
        (
            "campaigns",
            {
                "campaign": {"name": "Campaign"},
                "sequences": [{"subject_template": "Hello", "body_template": "Body"}],
                "leads": [{"email": "lead@example.com"}],
            },
            Campaign,
        ),
        ("workflows", {"workflow": {"name": "Workflow"}, "steps": [{"name": "Review"}]}, Workflow),
        ("agents", {"agent": {"name": "Agent"}}, Agent),
        ("prompt_brain", {"prompt": {"name": "Prompt", "template": "Review"}}, PromptTemplate),
    ],
)
async def test_confirmed_drafts_persist_for_authenticated_user(db_session, page, draft, model):
    user = User(id="workspace-owner", email="owner@example.com", password_hash="test-only")
    db_session.add(user)
    await db_session.commit()
    result = await _execute_assistant_draft(page, draft, "Review", user, db_session)
    record = (await db_session.execute(select(model))).scalar_one()
    assert record.user_id == user.id
    assert record.id in result["created"].values()
    if page == "campaigns":
        assert (await db_session.execute(select(CampaignSequence))).scalar_one().campaign_id == record.id
        assert (await db_session.execute(select(Lead))).scalar_one().user_id == user.id
    if page == "workflows":
        assert (await db_session.execute(select(WorkflowStep))).scalar_one().workflow_id == record.id


@pytest.mark.asyncio
async def test_execution_failure_rolls_back(db_session, monkeypatch):
    user = User(id="workspace-owner", email="owner@example.com", password_hash="test-only")
    db_session.add(user)
    await db_session.commit()
    monkeypatch.setattr(db_session, "commit", AsyncMock(side_effect=RuntimeError("storage failed")))
    with pytest.raises(HTTPException) as error:
        await _execute_assistant_draft("agents", {"agent": {"name": "Must roll back"}}, "Review", user, db_session)
    assert error.value.status_code == 500
    assert (await db_session.execute(select(Agent))).scalars().all() == []
