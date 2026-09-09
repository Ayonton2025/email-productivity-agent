from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import database
from app.models.base import Base
from app.models.prompt_models import PromptTemplate
from app.models.user_models import User


@pytest.mark.asyncio
async def test_initialization_registers_all_tables_and_preserves_existing_rows(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", sessions)
    try:
        await database.init_db()
        async with sessions() as session:
            user = User(id="retained", email="retained@example.com", password_hash="unchanged-hash", plan="business")
            session.add(user)
            await session.flush()
            session.add(PromptTemplate(user_id=user.id, name="Custom", template="Keep this", category="reply"))
            await session.commit()
        await database.init_db()
        async with engine.connect() as connection:
            tables = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            assert set(tables) == set(Base.metadata.tables)
        async with sessions() as session:
            retained = await session.get(User, "retained")
            assert retained.plan == "business" and retained.password_hash == "unchanged-hash"
            prompts = (await session.execute(select(PromptTemplate))).scalars().all()
            assert sum(prompt.is_system for prompt in prompts) == 4
            assert next(prompt for prompt in prompts if prompt.name == "Custom").template == "Keep this"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_session_dependency_commits_or_rolls_back_and_always_closes(monkeypatch, failure):
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())

    @asynccontextmanager
    async def sessions():
        yield session

    monkeypatch.setattr(database, "AsyncSessionLocal", sessions)
    if failure:
        with pytest.raises(RuntimeError, match="operation failed"):
            async with asynccontextmanager(database.get_db)() as actual:
                assert actual is session
                raise RuntimeError("operation failed")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
    else:
        async with asynccontextmanager(database.get_db)() as actual:
            assert actual is session
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()
