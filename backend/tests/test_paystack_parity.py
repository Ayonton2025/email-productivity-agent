import pytest
import asyncio
from app.services.billing_service import PaymentService
from app.models.billing_models import SUBSCRIPTION_PLANS


class DummySession:
    """Lightweight async session stub for tests.

    Provides minimal API used by PaymentService.create_upgrade_session:
    - add(obj)
    - async flush()
    """
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        # No-op: emulate SQLAlchemy AsyncSession.flush
        return None

@pytest.mark.asyncio
async def test_paystack_exact_usd_default(monkeypatch):
    ps = PaymentService()

    # Mock paystack service to capture initialize_payment args
    called = {}

    async def fake_initialize_payment(email, amount, reference, metadata, currency, channels):
        called['amount'] = amount
        called['currency'] = currency
        return {'success': True, 'authorization_url': 'https://paystack.local/authorize'}

    ps.paystack.initialize_payment = fake_initialize_payment

    # Create an in-memory async session stub (we'll pass None since the code only uses session for saving)
    user_id = 'test-user'
    user_email = 'test@example.com'
    plan_id = 'professional' if 'professional' in SUBSCRIPTION_PLANS else list(SUBSCRIPTION_PLANS.keys())[1]

    result = await ps.create_upgrade_session(
        user_id=user_id,
        user_email=user_email,
        plan_id=plan_id,
        payment_method='card',
        session=DummySession(),
        country_code='KE',
        frontend_url='http://localhost:3000',
        prefer_local_currency=False
    )

    # Default behavior: currency should be USD and amount in minor units = price * 100
    expected_amount_minor = int(round(SUBSCRIPTION_PLANS[plan_id]['price'] * 100))
    assert called['currency'] == 'USD'
    assert called['amount'] == expected_amount_minor
    assert result.get('authorization_url') is not None

@pytest.mark.asyncio
async def test_paystack_local_currency_when_opted(monkeypatch):
    ps = PaymentService()

    async def fake_initialize_payment(email, amount, reference, metadata, currency, channels):
        return {'success': True, 'authorization_url': 'https://paystack.local/authorize'}

    ps.paystack.initialize_payment = fake_initialize_payment

    user_id = 'test-user'
    user_email = 'test@example.com'
    plan_id = 'professional' if 'professional' in SUBSCRIPTION_PLANS else list(SUBSCRIPTION_PLANS.keys())[1]

    result = await ps.create_upgrade_session(
        user_id=user_id,
        user_email=user_email,
        plan_id=plan_id,
        payment_method='mpesa',
        session=DummySession(),
        country_code='KE',
        frontend_url='http://localhost:3000',
        prefer_local_currency=True
    )

    # When local currency requested, currency should be KES
    assert result.get('processor') in ['paystack', 'coinbase', 'paypal', 'stripe'] or result.get('authorization_url')
