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

    assert MockEmailLoader().load() == [{"id": "one"}]


def test_loader_wraps_invalid_json(monkeypatch, tmp_path):
    data_file = tmp_path / "mock.json"
    data_file.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(MockEmailLoader, "paths", (str(data_file),))

    with pytest.raises(EmailDataLoadError):
        MockEmailLoader().load()
