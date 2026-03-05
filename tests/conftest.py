"""Test fixtures — in-memory test database, test client, test user."""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401, F403
from app.middleware.auth import create_access_token
from app.settings import settings

# Use a test database
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_org(db: AsyncSession):
    from app.models.organization import Organization
    org = Organization(rut="12.345.678-9", name="Test Org")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db: AsyncSession, test_org):
    from app.models.user import User
    from app.services.auth_service import hash_password
    user = User(
        organization_id=test_org.id,
        email="test@org.cl",
        password_hash=hash_password("test1234"),
        name="Test User",
        role="admin_org",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(test_user, test_org):
    """Authenticated HTTP client with JWT cookie."""
    token = create_access_token(test_user.id, test_org.id, test_user.role)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(settings.cookie_name, token)
        yield client


@pytest_asyncio.fixture
async def client():
    """Unauthenticated HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
