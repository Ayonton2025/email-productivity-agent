from pathlib import Path

from app.core.config import Settings
from app.services.attachment_service import AttachmentService


def test_attachment_storage_uses_configured_writable_directory(tmp_path, monkeypatch):
    location = tmp_path / "mail" / "attachments"
    monkeypatch.setenv("ATTACHMENT_STORAGE_PATH", str(location))
    settings = Settings(_env_file=None)
    monkeypatch.setattr("app.services.attachment_service.settings", settings)
    service = AttachmentService()
    assert service.storage_root == Path(location)
    assert location.is_dir()
