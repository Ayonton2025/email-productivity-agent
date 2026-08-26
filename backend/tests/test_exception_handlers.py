import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import EmailDeliveryError, PaymentError, SubscriptionError


@pytest.fixture
def exception_client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/payment")
    async def payment():
        raise PaymentError("Provider timed out", details={"provider": "paystack"})

    @app.get("/subscription")
    async def subscription():
        raise SubscriptionError("Unknown plan")

    @app.get("/email")
    async def email():
        raise EmailDeliveryError("SMTP unavailable")

    return TestClient(app)


def test_payment_error_has_stable_schema(exception_client):
    response = exception_client.get("/payment")
    assert response.status_code == 502
    assert response.json()["error"] == {
        "code": "payment_error",
        "message": "Provider timed out",
        "details": {"provider": "paystack"},
    }


def test_subscription_error_is_client_error(exception_client):
    response = exception_client.get("/subscription")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "subscription_error"


def test_email_delivery_error_is_gateway_error(exception_client):
    response = exception_client.get("/email")
    assert response.status_code == 502
    assert response.json()["error"]["message"] == "SMTP unavailable"


def test_subscription_error_preserves_value_error_compatibility():
    assert isinstance(SubscriptionError("bad plan"), ValueError)
