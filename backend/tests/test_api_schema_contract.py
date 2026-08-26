import pytest
from pydantic import ValidationError

from app.api.schemas import BulkEmailActionRequest, RegisterRequest


def test_registration_schema_enforces_password_policy():
    request = RegisterRequest(email="user@example.com", password="StrongPass1!", full_name="Test User")
    assert str(request.email) == "user@example.com"


def test_bulk_email_request_rejects_empty_and_duplicate_ids():
    with pytest.raises(ValidationError):
        BulkEmailActionRequest(email_ids=[])
    with pytest.raises(ValidationError):
        BulkEmailActionRequest(email_ids=[1, 1])
