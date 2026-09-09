import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.schemas.ai_schemas import ClassifyEmailRequest, WorkspaceAssistRequest
from app.main import app


def test_classify_valid_boundary():
    request = ClassifyEmailRequest(sender="s" * 320, subject="s" * 1000, body="b" * 100000)
    assert len(request.body) == 100000


@pytest.mark.parametrize(
    "field, value",
    [
        ("sender", ""),
        ("subject", ""),
        ("body", ""),
        ("body", "b" * 100001),
        ("sender", "s" * 321),
        ("subject", "s" * 1001),
        ("body", None),
    ],
    ids=lambda value: str(value)[:24],
)
def test_classify_rejects_invalid_fields(field, value):
    payload = dict(sender="sender@example.com", subject="Review", body="Please review")
    payload[field] = value
    with pytest.raises(ValidationError):
        ClassifyEmailRequest(**payload)


def test_workspace_defaults_and_nested_draft():
    request = WorkspaceAssistRequest(page="workflows", objective="Organize mail", draft={"steps": [{"name": "Review"}]})
    assert request.mode == "draft" and request.confirmed is False
    assert request.confirmation_token is None
    assert request.model_dump()["draft"]["steps"][0]["name"] == "Review"


@pytest.mark.parametrize(
    "field, value",
    [
        ("page", ""),
        ("page", "p" * 121),
        ("objective", ""),
        ("objective", "o" * 10001),
        ("mode", ""),
        ("mode", "m" * 41),
        ("context", []),
        ("draft", "invalid"),
    ],
    ids=lambda value: str(value)[:24],
)
def test_workspace_rejects_invalid_fields(field, value):
    payload = dict(page="agents", objective="Help with mail")
    payload[field] = value
    with pytest.raises(ValidationError):
        WorkspaceAssistRequest(**payload)


def test_openapi_paths_and_schemas_match_phase3_contract():
    expected = json.loads((Path(__file__).parent / "fixtures" / "phase4_openapi.json").read_text())
    document = app.openapi()
    actual = {
        section: {
            key: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest() for key, value in values.items()
        }
        for section, values in [("paths", document["paths"]), ("schemas", document["components"]["schemas"])]
    }
    assert actual == expected
