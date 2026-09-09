import pytest
from sqlalchemy.exc import IntegrityError

from app.models.prompt_models import PromptTemplate
from app.models.provider_models import EmailProviderConfig, SyncHistory
from app.models.user_models import User


@pytest.mark.asyncio
async def test_prompt_defaults_serialization_and_per_user_uniqueness(db_session):
    user = User(email="prompt-owner@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    prompt = PromptTemplate(
        user_id=user.id, name="Draft", template="Reply to {email}", category="reply", prompt_metadata={"tone": "formal"}
    )
    db_session.add(prompt)
    await db_session.commit()
    data = prompt.to_dict()
    assert data["template"] == "Reply to {email}" and data["metadata"] == {"tone": "formal"}
    assert data["version"] == 1 and data["is_active"] is True and data["is_system"] is False
    db_session.add(PromptTemplate(user_id=user.id, name="Draft", template="Duplicate", category="reply"))
    with pytest.raises(IntegrityError, match="UNIQUE"):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_provider_history_preserves_json_email_list(db_session):
    user = User(email="provider-owner@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    config = EmailProviderConfig(user_id=user.id, provider="gmail", config_data={"access_token": "secret"})
    db_session.add(config)
    await db_session.flush()
    history = SyncHistory(
        user_id=user.id, provider_config_id=config.id, sync_type="incremental", emails_processed=["message-1"]
    )
    db_session.add(history)
    await db_session.commit()
    assert history.to_dict()["emails_processed"] == ["message-1"]
    assert history.to_dict()["provider_config_id"] == config.id
    assert "config_data" not in config.to_dict()
