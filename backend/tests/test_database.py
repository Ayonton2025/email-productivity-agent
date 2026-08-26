from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect, select

from app.models.billing_models import Subscription
from app.models.database import Base, Email, User, UserEmailAccount


def test_core_tables_registered():
    assert {"users", "user_email_accounts", "emails", "subscriptions"} <= set(Base.metadata.tables)


def test_user_serialization():
    user = User(email="person@example.test", password_hash="hash", full_name="Person")
    user.id, user.created_at = "user-1", datetime.utcnow()
    data = user.to_dict()
    assert data["email"] == "person@example.test"
    assert data["full_name"] == "Person"


def test_email_account_serialization_hides_credentials():
    account = UserEmailAccount(
        user_id="user-1",
        provider="imap",
        email="person@example.test",
        imap_host="imap.example.test",
        smtp_host="smtp.example.test",
        encrypted_password="ciphertext",
    )
    account.id, account.created_at = "account-1", datetime.utcnow()
    data = account.to_dict()
    assert data["email"] == "person@example.test"
    assert "encrypted_password" not in data


@pytest.mark.asyncio
async def test_user_round_trip(db_session):
    db_session.add(User(id="db-user", email="db@example.test", password_hash="hash"))
    await db_session.commit()
    found = (await db_session.execute(select(User).where(User.id == "db-user"))).scalar_one()
    assert found.email == "db@example.test"


@pytest.mark.asyncio
async def test_email_foreign_keys_persist(db_session):
    user = User(id="mail-user", email="mail@example.test", password_hash="hash")
    account = UserEmailAccount(
        id="mail-account",
        user_id=user.id,
        provider="imap",
        email=user.email,
        imap_host="imap.example.test",
        smtp_host="smtp.example.test",
        encrypted_password="encrypted",
    )
    message = Email(
        id="message-1",
        account_id=account.id,
        user_id=user.id,
        message_id="provider-message-1",
        uid=1,
        sender="sender@example.test",
        recipients=[user.email],
        subject="Hello",
        body_text="Body",
        folder="INBOX",
        received_at=datetime.utcnow(),
    )
    db_session.add_all([user, account, message])
    await db_session.commit()
    stored = (await db_session.execute(select(Email).where(Email.id == "message-1"))).scalar_one()
    assert stored.account_id == "mail-account"
    assert stored.recipients == ["mail@example.test"]


@pytest.mark.asyncio
async def test_subscription_model_round_trip(db_session):
    user = User(id="subscriber", email="subscriber@example.test", password_hash="hash")
    subscription = Subscription(
        user_id=user.id,
        tenant_id="tenant",
        plan_id="plus",
        plan_name="Plus",
        price_usd=12,
        current_period_end=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add_all([user, subscription])
    await db_session.commit()
    stored = (await db_session.execute(select(Subscription))).scalar_one()
    assert stored.plan_id == "plus"
    assert float(stored.price_usd) == 12.0


@pytest.mark.asyncio
async def test_sqlite_schema_contains_email_foreign_keys(db_session):
    connection = await db_session.connection()
    foreign_keys = await connection.run_sync(lambda sync: inspect(sync).get_foreign_keys("emails"))
    assert {"users", "user_email_accounts"} <= {fk["referred_table"] for fk in foreign_keys}
