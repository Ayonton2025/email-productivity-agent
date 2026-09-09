import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.email_models import Email, EmailDraft, UserEmailAccount
from app.models.user_models import User


def test_account_serialization_preserves_oauth_hosted_fields_and_hides_secrets():
    account = UserEmailAccount(
        id="account",
        user_id="owner",
        email="owner@example.com",
        provider="gmail",
        email_account_type="hosted_internal",
        hosted_provider="mailu",
        send_limit_daily=200,
        send_count_daily=4,
        encrypted_password="secret-password",
        access_token="secret-access",
        refresh_token="secret-refresh",
        history_id="42",
    )
    account.created_at = account.last_sync = account.watch_expiration = datetime(
        2026, 1, 2, 12, tzinfo=timezone(timedelta(hours=3))
    )
    data = account.to_dict()
    assert data["has_oauth"] is True and data["hosted_provider"] == "mailu"
    assert data["send_limit_daily"] == 200 and data["send_count_daily"] == 4
    assert data["last_sync"] == data["watch_expiration"] == "2026-01-02T09:00:00Z"
    assert "secret-" not in json.dumps(data)


@pytest.mark.asyncio
async def test_email_account_message_and_draft_round_trip(db_session):
    user = User(email="mail-owner@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    account = UserEmailAccount(
        user_id=user.id,
        provider="gmail",
        email=user.email,
        imap_host="imap.example.com",
        smtp_host="smtp.example.com",
        encrypted_password="encrypted",
        access_token="oauth-access",
        refresh_token="oauth-refresh",
        history_id="123",
        email_account_type="hosted_internal",
        hosted_provider="mailu",
    )
    db_session.add(account)
    await db_session.flush()
    message = Email(
        account_id=account.id,
        user_id=user.id,
        message_id="message",
        uid=9223372036854775807,
        sender="sender@example.com",
        recipients=[user.email],
        body_html="<p>Hello</p>",
        received_at=datetime(2026, 1, 2, 9),
        ai_category="Work",
        ai_summary="Summary",
        is_flagged=True,
        follow_up_enabled=True,
        follow_up_stage=2,
        attachments=[{"filename": "report.pdf"}],
    )
    draft = EmailDraft(user_id=user.id, subject="Reply", body="Draft", draft_metadata={"tone": "formal"})
    db_session.add_all([message, draft])
    await db_session.commit()
    db_session.expire_all()
    stored = (await db_session.execute(select(Email).where(Email.message_id == "message"))).scalar_one()
    data = stored.to_dict()
    assert stored.uid == 9223372036854775807
    assert data["timestamp"] == data["received_at"] == "2026-01-02T09:00:00Z"
    assert data["body"] == "<p>Hello</p>" and data["is_starred"] is True
    assert data["category"] == "Work" and data["summary"] == "Summary"
    assert data["follow_up_stage"] == 2 and data["follow_up_enabled"] is True
    stored_account = (await db_session.execute(select(UserEmailAccount))).scalar_one()
    assert stored_account.access_token == "oauth-access" and stored_account.history_id == "123"
    assert stored_account.hosted_provider == "mailu"
    stored_draft = (await db_session.execute(select(EmailDraft))).scalar_one()
    assert stored_draft.to_dict()["metadata"] == {"tone": "formal"}


@pytest.mark.asyncio
async def test_email_account_foreign_key_rejects_missing_owner(db_session):
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    db_session.add(
        UserEmailAccount(
            user_id="missing",
            provider="imap",
            email="orphan@example.com",
            imap_host="imap",
            smtp_host="smtp",
            encrypted_password="encrypted",
        )
    )
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        await db_session.commit()
    await db_session.rollback()
