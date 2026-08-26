import pytest
from pydantic import ValidationError

from app.api.billing.schemas import CouponRequest, CreditTopupRequest, UpgradeRequest


def test_billing_schemas_normalize_country_and_validate_coupon():
    topup = CreditTopupRequest(credits=100, email="user@example.com", country_code="ng")
    assert topup.country_code == "NG"
    assert CouponRequest(code="WELCOME_10").code == "WELCOME_10"


def test_billing_schemas_reject_invalid_values():
    with pytest.raises(ValidationError):
        CreditTopupRequest(credits=0, email="user@example.test")
    with pytest.raises(ValidationError):
        UpgradeRequest(plan_id="", payment_method="paystack")
    with pytest.raises(ValidationError):
        CouponRequest(code="not valid")
