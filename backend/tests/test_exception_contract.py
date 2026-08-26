from app.core.exceptions import PaymentError, SubscriptionError


def test_application_errors_expose_stable_codes_and_statuses():
    payment = PaymentError("provider unavailable")
    subscription = SubscriptionError("plan unavailable")
    assert payment.code == "payment_error"
    assert payment.status_code == 502
    assert subscription.code == "subscription_error"
    assert subscription.status_code == 400
