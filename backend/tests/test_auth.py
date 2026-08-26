from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decrypt_credential,
    encrypt_credential,
    get_password_hash,
    safe_json_parse,
    sanitize_email_content,
    validate_email_address,
    verify_password,
    verify_token,
)


def test_password_hash_round_trip():
    password_hash = get_password_hash("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong", password_hash)


def test_password_hash_rejects_bcrypt_overflow():
    with pytest.raises(ValueError, match="72"):
        get_password_hash("x" * 73)


def test_access_token_round_trip():
    assert verify_token(create_access_token({"user_id": "user-123"}))["user_id"] == "user-123"


def test_expired_access_token_is_rejected():
    token = create_access_token({"user_id": "user-123"}, expires_delta=timedelta(seconds=-1))
    assert verify_token(token) is None


def test_credential_encryption_round_trip():
    encrypted = encrypt_credential("smtp-password")
    assert encrypted != "smtp-password"
    assert decrypt_credential(encrypted) == "smtp-password"


@pytest.mark.parametrize("value", ["person@example.com", "a.b+tag@sub.example.org"])
def test_valid_email_addresses(value):
    assert validate_email_address(value)


@pytest.mark.parametrize("value", ["", "missing-at.example.com", "a@localhost", "a@@example.com"])
def test_invalid_email_addresses(value):
    assert not validate_email_address(value)


def test_sanitize_email_content_removes_script_vectors():
    cleaned = sanitize_email_content("<script>alert(1)</script><img onerror=boom>")
    assert "<script>" not in cleaned and "onerror=" not in cleaned


def test_safe_json_parse_handles_valid_and_invalid_input():
    assert safe_json_parse('{"ok": true}') == {"ok": True}
    assert safe_json_parse("not json") is None


def test_register_rejects_missing_fields(client):
    response = client.post("/api/v1/register", json={"email": "person@example.test"})
    assert response.status_code == 422
    assert any(error["type"] == "missing" for error in response.json()["detail"])


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/api/v1/register",
        json={"email": "invalid", "full_name": "Test User", "password": "StrongPassword1!"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "email"
