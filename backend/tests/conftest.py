import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ["ENABLE_MOCK_MODE"] = "true"
os.environ["SKIP_DB_INIT"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CELERY_ENABLED"] = "false"
os.environ["ENABLE_LIVE_FX_RATES"] = "false"
os.environ["ENABLE_GEOIP_DETECTION"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-at-least-32-characters"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import get_current_user  # noqa: E402
from app.main import app  # noqa: E402
from app.models.database import Base, get_db  # noqa: E402


@pytest.fixture
def authenticated_user():
    return SimpleNamespace(
        id="test-user-id",
        email="developer@example.test",
        full_name="Test Developer",
        is_active=True,
        is_verified=True,
        is_admin=False,
        is_superuser=False,
        plan="professional",
    )


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture
def client(authenticated_user):
    async def override_user():
        return authenticated_user

    async def override_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    app.dependency_overrides.clear()
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
