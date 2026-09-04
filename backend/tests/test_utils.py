from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.utils.helpers import (
    async_retry,
    calculate_priority_score,
    clean_email_body,
    extract_email_parts,
    format_duration,
    format_priority,
    format_timestamp,
    generate_id,
    parse_json_safely,
    truncate_text,
    validate_email_structure,
)
from app.utils.validators import EmailValidator, JSONValidator, PromptValidator, URLValidator


def test_identifier_and_timestamp_helpers_return_stable_formats():
    assert len(generate_id()) == 36
    assert format_timestamp(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05"
    assert datetime.fromisoformat(format_timestamp())


@pytest.mark.parametrize(
    ("raw", "default", "expected"),
    [('{"ok": true}', None, {"ok": True}), ("not-json", [], []), (None, "fallback", "fallback")],
)
def test_parse_json_safely(raw, default, expected):
    assert parse_json_safely(raw, default) == expected


def test_text_and_address_helpers_cover_boundaries():
    assert truncate_text("short", 10) == "short"
    assert truncate_text("abcdefghij", 7) == "abcd..."
    assert extract_email_parts("person@example.com") == {
        "local": "person",
        "domain": "example.com",
        "full": "person@example.com",
    }
    assert extract_email_parts("invalid") == {"local": "", "domain": "", "full": "invalid"}
    assert clean_email_body("Hello   team\nPlease review\nBest,\nSender") == "Hello team\nPlease review"
    assert clean_email_body("\n--- Forwarded message ---\nFrom: old@example.com\nUseful") == "Useful"
    assert clean_email_body("") == ""


@pytest.mark.parametrize(
    ("email_data", "expected"),
    [
        ({"sender": "ceo@company.com", "subject": "Urgent action required", "body": "x" * 501}, 100),
        ({"sender": "person@example.com", "subject": "Hello", "body": "short"}, 40),
        ({"sender": "person@example.com", "subject": "Update", "body": "x" * 100}, 50),
    ],
)
def test_priority_score(email_data, expected):
    assert calculate_priority_score(email_data) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [(80, "urgent"), (60, "high"), (40, "medium"), (39, "low")],
)
def test_format_priority(score, expected):
    assert format_priority(score) == expected


@pytest.mark.parametrize(("seconds", "expected"), [(30, "30s"), (120, "2m"), (3720, "1h 2m")])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


@pytest.mark.asyncio
async def test_async_retry_returns_after_transient_failure(monkeypatch):
    operation = AsyncMock(side_effect=[RuntimeError("temporary"), "done"])
    sleep = AsyncMock()
    monkeypatch.setattr("app.utils.helpers.asyncio.sleep", sleep)

    assert await async_retry(operation, max_retries=2, delay=0.25) == "done"
    sleep.assert_awaited_once_with(0.25)


@pytest.mark.asyncio
async def test_async_retry_reraises_last_error_and_rejects_empty_attempts(monkeypatch):
    operation = AsyncMock(side_effect=RuntimeError("still unavailable"))
    monkeypatch.setattr("app.utils.helpers.asyncio.sleep", AsyncMock())

    with pytest.raises(RuntimeError, match="still unavailable"):
        await async_retry(operation, max_retries=2, delay=0)
    with pytest.raises(ValueError, match="at least 1"):
        await async_retry(operation, max_retries=0)


def test_validate_email_structure_reports_missing_and_invalid_fields():
    assert validate_email_structure({}) == [
        "Missing required field: sender",
        "Missing required field: subject",
        "Missing required field: body",
    ]
    assert validate_email_structure({"sender": "invalid", "subject": "Hi", "body": "Body"}) == [
        "Invalid sender email format"
    ]
    assert validate_email_structure({"sender": "valid@example.com", "subject": "Hi", "body": "Body"}) == []


@pytest.mark.parametrize(
    ("address", "expected"),
    [("person@example.com", True), ("bad-address", False), ("", False), (f"x@{'a' * 250}.com", False)],
)
def test_email_format_validation(address, expected):
    assert EmailValidator.validate_email_format(address) is expected


def test_email_header_validation_checks_required_sender_and_date():
    assert EmailValidator.validate_email_headers({}) == [
        "Missing required header: From",
        "Missing required header: Subject",
    ]
    issues = EmailValidator.validate_email_headers({"From": "not-an-address", "Subject": "Hello", "Date": "not-a-date"})
    assert "Invalid From header format" in issues
    assert "Invalid Date header format" in issues
    assert (
        EmailValidator.validate_email_headers(
            {"From": "Person <person@example.com>", "Subject": "Hello", "Date": "Mon, 1 Jan 2024 12:00:00 +0000"}
        )
        == []
    )


def test_email_content_sanitization_removes_active_content():
    content = '<script>alert(1)</script><a onclick="attack()" href="javascript:bad()">Safe</a>'
    sanitized = EmailValidator.sanitize_email_content(content)
    assert "script" not in sanitized.lower()
    assert "onclick" not in sanitized.lower()
    assert "javascript:" not in sanitized.lower()
    assert EmailValidator.sanitize_email_content("") == ""


def test_prompt_template_validation_covers_required_category_and_length_rules():
    valid = {"name": "Summary", "template": "Summarize this email", "category": "summary"}
    assert PromptValidator.validate_prompt_template(valid) == (True, [])

    is_valid, errors = PromptValidator.validate_prompt_template({"name": "", "template": "tiny", "category": "unknown"})
    assert is_valid is False
    assert "Missing required field: name" in errors
    assert any("Invalid category" in error for error in errors)
    assert "Prompt template too short (minimum 10 characters)" in errors

    _, errors = PromptValidator.validate_prompt_template(
        {"name": "Large", "template": "x" * 10001, "category": "analysis"}
    )
    assert "Prompt template too long (maximum 10,000 characters)" in errors


@pytest.mark.parametrize(
    ("parameters", "expected"),
    [
        ({"topic": {"type": "string", "required": True, "description": "Topic"}}, True),
        ([], False),
        ({"topic": "string"}, False),
        ({"topic": {"type": "string", "required": True}}, False),
        ({"topic": {"type": "unsupported", "required": True, "description": "Topic"}}, False),
    ],
)
def test_prompt_parameter_validation(parameters, expected):
    assert PromptValidator.validate_prompt_parameters(parameters) is expected


def test_json_structure_validation_handles_nested_objects_arrays_and_constraints():
    schema = {
        "type": dict,
        "required": ["name", "items"],
        "properties": {
            "name": {"type": str, "minLength": 3, "maxLength": 10},
            "items": {"type": list, "items": {"type": int}},
        },
    }
    assert JSONValidator.validate_json_structure({"name": "Inbox", "items": [1, 2]}, schema) == (True, [])

    valid, errors = JSONValidator.validate_json_structure({"name": "x", "items": [1, "bad"]}, schema)
    assert valid is False
    assert any("name.Value too short" in error for error in errors)
    assert any("items.[1].Expected type" in error for error in errors)
    assert JSONValidator.validate_json_structure([], schema)[0] is False
    assert JSONValidator.validate_json_structure({"name": "way-too-long", "items": []}, schema)[0] is False
    assert JSONValidator.validate_json_structure({"name": "Inbox"}, schema)[0] is False


def test_safe_json_and_url_validation_enforce_web_only_allowlist():
    assert JSONValidator.safe_json_loads('{"ok": true}') == {"ok": True}
    assert JSONValidator.safe_json_loads("broken", {}) == {}
    assert URLValidator.validate_url("https://example.com/path") is True
    assert URLValidator.validate_url("ftp://example.com/file") is False
    assert URLValidator.validate_url(None) is False
    assert URLValidator.is_safe_url("https://example.com", ["example.com"]) is True
    assert URLValidator.is_safe_url("https://evil.example", ["example.com"]) is False
    assert URLValidator.is_safe_url("javascript:alert(1)") is False
