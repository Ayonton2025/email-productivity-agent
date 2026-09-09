from datetime import datetime, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api import auth_endpoints
from app.core import security
from app.core.config import settings
from app.main import app
from app.models.database import User as LegacyUser
from app.models.database import get_db
from app.models.user_models import User


def test_user_password_behavior_and_sensitive_serialization():
    user = User(
        id="user", email="person@example.com", plan="business", subscription_status="active", preferred_language="sw"
    )
    user.created_at = datetime.now(timezone.utc)
    user.set_password("ValidPassword1!")
    assert user.check_password("ValidPassword1!")
    assert not user.check_password("wrong-password")
    with pytest.raises(ValueError, match="72"):
        user.set_password("x" * 73)
    user.verification_token = "private-verification-token"
    user.reset_token = "private-reset-token"
    data = user.to_dict()
    assert data["plan"] == "business" and data["subscription_status"] == "active"
    assert data["preferred_language"] == "sw"
    assert {"password_hash", "verification_token", "reset_token"}.isdisjoint(data)
    user.password_hash = "invalid-hash"
    assert not user.check_password("ValidPassword1!")


@pytest.mark.parametrize(
    ("method", "field", "seconds"),
    [
        ("generate_verification_token", "verification_token", 86400),
        ("generate_reset_token", "reset_token", 3600),
    ],
)
@pytest.mark.parametrize("user_id", [None, "token-user"])
def test_user_tokens_preserve_claims_and_expiry(method, field, seconds, user_id):
    user = User(id=user_id, email="token@example.com")
    before = datetime.now(timezone.utc).timestamp()
    token = getattr(user, method)()
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert user.id is not None
    if user_id is not None:
        assert user.id == user_id
    assert getattr(user, field) == token
    assert claims["user_id"] == user.id and claims["email"] == user.email
    assert before + seconds - 1 <= claims["exp"] <= datetime.now(timezone.utc).timestamp() + seconds


@pytest.mark.asyncio
async def test_registration_login_verification_and_reset_use_the_same_user(db_session, monkeypatch):
    async def override_db():
        yield db_session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[security._lazy_get_db] = override_db
    monkeypatch.setattr(auth_endpoints, "send_password_reset_email", AsyncMock())
    email, password = "model-contract@example.com", "ValidPassword1!"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/register", json={"email": email, "password": password, "full_name": "Model Contract"}
            )
            assert response.status_code == 200, response.text
            user = (await db_session.execute(select(LegacyUser).where(LegacyUser.email == email))).scalar_one()
            assert isinstance(user, User)
            assert user.plan == "personal" and user.subscription_status == "free"
            assert jwt.decode(user.verification_token, settings.SECRET_KEY, algorithms=["HS256"])["user_id"] == user.id
            verified = await client.post("/api/v1/verify-email", params={"token": user.verification_token})
            assert verified.status_code == 200, verified.text
            login = await client.post("/api/v1/login", json={"email": email, "password": password})
            assert login.status_code == 200, login.text
            user.plan, user.subscription_status = "business", "active"
            await db_session.commit()
            identity = await security.get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=login.json()["access_token"]),
                db_session,
            )
            assert identity is user and identity.plan == "business"
            me = await client.get("/api/v1/me", headers={"Authorization": "Bearer " + login.json()["access_token"]})
            assert me.status_code == 200 and me.json()["id"] == user.id
            forgotten = await client.post("/api/v1/forgot-password", json={"email": email})
            assert forgotten.status_code == 200
            await db_session.refresh(user)
            token = user.reset_token
            reset = await client.post(
                "/api/v1/reset-password", json={"token": token, "new_password": "ChangedPassword2!"}
            )
            assert reset.status_code == 200, reset.text
            replay = await client.post(
                "/api/v1/reset-password", json={"token": token, "new_password": "OtherPassword3!"}
            )
            assert replay.status_code == 400
            assert (await client.post("/api/v1/login", json={"email": email, "password": password})).status_code == 401
            assert (
                await client.post("/api/v1/login", json={"email": email, "password": "ChangedPassword2!"})
            ).status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
