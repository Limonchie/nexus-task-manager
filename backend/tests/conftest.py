"""
Фикстуры pytest: тестовая БД, клиент, авторизованный клиент, Bearer-заголовки.
Fixtures: db_engine, db_session, client, auth_client (cookies), auth_headers (Bearer).
"""

import os
import asyncio
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("AUTH_RATE_LIMIT_PER_MINUTE", "300")  # High limit for tests

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_password_hash
from app.db.base_class import Base
from app.main import app
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Test user credentials for login/register
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"
TEST_USER_FULL_NAME = "Test User"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        # Trigger app lifespan so DB tables are created
        await ac.get("/health")
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession):
    """Client with authenticated user: create user in DB then login. Cookies set automatically."""
    email = f"authed_{uuid.uuid4().hex[:12]}@example.com"
    user = User(
        email=email,
        hashed_password=get_password_hash(TEST_USER_PASSWORD),
        full_name=TEST_USER_FULL_NAME,
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": TEST_USER_PASSWORD},
    )
    assert r.status_code == 200
    yield client


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession):
    """Create user in DB, return dict with Bearer token for Authorization header."""
    from app.core.security import create_access_token

    user = User(
        email=f"bearer-{uuid.uuid4().hex[:12]}@example.com",
        hashed_password=get_password_hash("pass123"),
        full_name="Bearer User",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(user)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}", "_user_id": user.id, "_email": user.email}
