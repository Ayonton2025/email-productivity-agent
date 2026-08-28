import pytest
from pydantic import ValidationError

from app.api.billing.schemas import CreditTopupRequest, UpgradeRequest
from app.api.schemas import (
    AgentChatRequest,
    AgentProcessRequest,
    DraftCreateRequest,
    PromptCreateRequest,
    RegisterRequest,
    ResetPasswordRequest,
)


@pytest.mark.parametrize("email", ["missing-at.example.com", "person@localhost", ""])
def test_registration_rejects_invalid_email(email):
    with pytest.raises(ValidationError):
        RegisterRequest(email=email, full_name="Secure User", password="StrongPass1!")


@pytest.mark.parametrize(
    "password", ["short", "alllowercase1!", "ALLUPPERCASE1!", "NoNumberHere!", "NoSpecial123"]
)
def test_registration_rejects_weak_passwords(password):
    with pytest.raises(ValidationError):
        RegisterRequest(email="secure@example.com", full_name="Secure User", password=password)


def test_registration_accepts_strong_password():
    request = RegisterRequest(
        email="secure@example.com", full_name="Secure User", password="StrongPassword1!"
    )
    assert request.password == "StrongPassword1!"


@pytest.mark.parametrize("credits", [0, -1, 1_000_001])
def test_credit_topup_rejects_invalid_amounts(credits):
    with pytest.raises(ValidationError):
        CreditTopupRequest(credits=credits, email="buyer@example.com")


def test_credit_topup_validates_email_and_normalizes_country():
    request = CreditTopupRequest(credits=100, email="buyer@example.com", country_code="ke")
    assert request.country_code == "KE"
    with pytest.raises(ValidationError):
        CreditTopupRequest(credits=100, email="invalid")


def test_upgrade_rejects_unknown_payment_method():
    with pytest.raises(ValidationError):
        UpgradeRequest(plan_id="plus", payment_method="cash")


def test_reset_password_uses_same_complexity_policy():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="x" * 16, new_password="weak-password")


def test_prompt_request_requires_nonempty_template():
    with pytest.raises(ValidationError):
        PromptCreateRequest(name="Summary", template="", category="summary")


def test_draft_request_validates_recipient_and_allows_blank_recipient():
    assert DraftCreateRequest(subject="Draft", recipient="").recipient is None
    with pytest.raises(ValidationError):
        DraftCreateRequest(subject="Draft", recipient="not-an-email")


def test_agent_requests_reject_empty_or_missing_content():
    with pytest.raises(ValidationError):
        AgentChatRequest(message="")
    with pytest.raises(ValidationError):
        AgentProcessRequest(email_id="email-1", prompt_type="")
