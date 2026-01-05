"""Pytest configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator

# Set test environment before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.auth.models import APIKey
from app.auth.service import APIKeyService
from app.db.base import Base
from app.db.session import get_db, get_db_no_commit
from app.main import app

# Use SQLite for tests (faster and no external DB needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Create a fresh database session for each test."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession) -> tuple[str, APIKey]:
    """Create a test API key and return both the raw key and model."""
    raw_key = APIKeyService.generate_key()
    api_key = APIKey(
        name="Test Key",
        client_id="test-client",
        key_hash=APIKeyService.hash_key(raw_key),
        key_prefix=APIKeyService.get_key_prefix(raw_key),
        is_active=True,
    )
    db_session.add(api_key)
    await db_session.flush()
    await db_session.refresh(api_key)
    return raw_key, api_key


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Create test client with overridden dependencies."""

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_no_commit] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient,
    test_api_key: tuple[str, APIKey],
) -> AsyncClient:
    """Client with API key header set."""
    raw_key, _ = test_api_key
    client.headers["X-API-Key"] = raw_key
    return client
