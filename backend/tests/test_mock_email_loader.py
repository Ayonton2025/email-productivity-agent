import json

import pytest

from app.core.exceptions import EmailDataLoadError
from app.services.mock_email_loader import MockEmailLoader


def test_loader_returns_twenty_unique_fallback_emails(monkeypatch):
    monkeypatch.setattr("app.services.mock_email_loader.os.path.exists", lambda _path: False)

    emails = MockEmailLoader().load()

    assert len(emails) == 20
    assert len({(email["sender"], email["subject"]) for email in emails}) == 20


def test_loader_reads_json_file(monkeypatch, tmp_path):
    data_file = tmp_path / "mock.json"
    data_file.write_text(json.dumps([{"id": "one"}]), encoding="utf-8")
    monkeypatch.setattr(MockEmailLoader, "paths", (str(data_file),))

    assert MockEmailLoader().load() == [
        {
            "id": "one",
            "category": "Uncategorized",
            "priority": "medium",
            "is_read": False,
            "is_archived": False,
            "is_starred": False,
            "action_items": [],
            "summary": "",
        }
    ]


def test_loader_wraps_invalid_json(monkeypatch, tmp_path):
    data_file = tmp_path / "mock.json"
    data_file.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(MockEmailLoader, "paths", (str(data_file),))

    with pytest.raises(EmailDataLoadError):
        MockEmailLoader().load()


@pytest.mark.parametrize("payload", [{}, None, "inbox", [None], [1], ["email"]])
def test_loader_rejects_invalid_record_shapes(monkeypatch, tmp_path, payload):
    data_file = tmp_path / "mock.json"
    data_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(MockEmailLoader, "paths", (str(data_file),))
    with pytest.raises(EmailDataLoadError, match="array of record objects"):
        MockEmailLoader().load()


def test_original_demonstration_content_is_preserved(monkeypatch):
    monkeypatch.setattr(MockEmailLoader, "paths", ())
    records = MockEmailLoader().load()
    assert records[0]["subject"] == "Q4 Project Review Meeting"
    assert records[0]["sender"] == "project.manager@company.com"
    assert len({record["category"] for record in records}) > 1
    assert len({record["priority"] for record in records}) > 1
    records[0]["subject"] = "Changed"
    assert MockEmailLoader().load()[0]["subject"] == "Q4 Project Review Meeting"
