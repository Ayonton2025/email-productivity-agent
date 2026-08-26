import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.billing_models import SUBSCRIPTION_PLANS, AICredits
from app.models.database import User
from app.services.billing_service import PaymentService, PaystackService, SubscriptionService


@pytest.mark.asyncio
async def test_mock_payment_initialization_success():
    result = await PaystackService().initialize_payment("buyer@example.test", 1200, "ref-success", currency="USD")
    assert result["success"] is True
    assert result["payment_status"] == "completed"


@pytest.mark.asyncio
async def test_mock_payment_verification_success():
    result = await PaystackService().verify_payment("ref-verify")
    assert result["success"] is True and result["mock"] is True


@pytest.mark.asyncio
async def test_payment_initialization_maps_provider_200(monkeypatch):
    service = PaystackService()
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"status": True, "data": {"authorization_url": "https://pay.test", "access_code": "access"}}

    async def post(*args, **kwargs):
        return Response()

    monkeypatch.setattr(service.client, "post", post)
    result = await service.initialize_payment("buyer@example.test", 100, "ref-200")
    assert result["success"] is True
    assert result["authorization_url"] == "https://pay.test"


@pytest.mark.asyncio
async def test_payment_initialization_handles_invalid_credentials(monkeypatch):
    service = PaystackService()
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)

    class Response:
        status_code = 401
        text = "unauthorized"

        def raise_for_status(self):
            raise httpx.HTTPStatusError("401", request=None, response=None)

        def json(self):
            return {"message": "Invalid key"}

    async def post(*args, **kwargs):
        return Response()

    monkeypatch.setattr(service.client, "post", post)
    result = await service.initialize_payment("buyer@example.test", 100, "ref-401")
    assert result == {"success": False, "message": "Invalid key"}


@pytest.mark.asyncio
async def test_payment_initialization_handles_timeout(monkeypatch):
    service = PaystackService()
    monkeypatch.setattr(settings, "ENABLE_MOCK_MODE", False)

    async def post(*args, **kwargs):
        raise httpx.TimeoutException("provider timeout")

    monkeypatch.setattr(service.client, "post", post)
    result = await service.initialize_payment("buyer@example.test", 100, "ref-timeout")
    assert result["success"] is False
    assert "timeout" in result["message"]


def test_mock_mode_exposes_payment_method_without_credentials():
    methods = PaymentService().get_available_payment_methods("US")
    assert any(method["id"] == "card" for method in methods)


@pytest.mark.asyncio
async def test_create_subscription_persists_plan_and_credits(db_session):
    user = User(id="create-sub", email="create@example.test", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    subscription = await SubscriptionService().create_subscription(user.id, "tenant", "plus", db_session)
    await db_session.commit()
    credits = (await db_session.execute(select(AICredits).where(AICredits.user_id == user.id))).scalar_one()
    assert subscription.plan_id == "plus"
    assert credits.balance == SUBSCRIPTION_PLANS["plus"]["ai_credits_monthly"]


@pytest.mark.asyncio
async def test_create_subscription_rejects_unknown_plan(db_session):
    with pytest.raises(ValueError, match="Unknown plan"):
        await SubscriptionService().create_subscription("user", "tenant", "not-a-plan", db_session)


@pytest.mark.asyncio
async def test_cancel_subscription_updates_user(db_session):
    user = User(id="cancel-sub", email="cancel@example.test", password_hash="hash", plan="plus")
    db_session.add(user)
    await db_session.flush()
    await SubscriptionService().create_subscription(user.id, "tenant", "plus", db_session)
    cancelled = await SubscriptionService().cancel_subscription(user.id, db_session)
    assert cancelled.status == "cancelled"
    assert cancelled.auto_renew is False
    assert user.subscription_status == "cancelled"


@pytest.mark.asyncio
async def test_renew_subscription_advances_period(db_session):
    user = User(id="renew-sub", email="renew@example.test", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    subscription = await SubscriptionService().create_subscription(user.id, "tenant", "plus", db_session)
    old_end = subscription.current_period_end
    subscription.status = "cancelled"
    renewed = await SubscriptionService().renew_subscription(user.id, db_session)
    assert renewed.status == "active" and renewed.auto_renew is True
    assert renewed.current_period_end >= old_end


@pytest.mark.asyncio
async def test_get_subscription_returns_none_for_unknown_user(db_session):
    assert await SubscriptionService().get_subscription("missing", db_session) is None
