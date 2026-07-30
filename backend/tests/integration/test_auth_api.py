"""Integration tests for auth endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from app.main import create_app
from app.services.database import get_session
from argon2 import PasswordHasher
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import create_org, create_user

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

ph = PasswordHasher()


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_returns_jwt(api_client: AsyncClient, db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    password = "test-password"
    user = await create_user(
        db_session,
        org,
        email="auth-user@example.com",
        password_hash=ph.hash(password),
        role="admin",
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_with_bad_password_returns_401(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    org = await create_org(db_session)
    await create_user(
        db_session,
        org,
        email="bad-pass@example.com",
        password_hash=ph.hash("correct"),
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "bad-pass@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/invalid-credentials")


@pytest.mark.asyncio
async def test_me_requires_authentication(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.asyncio
async def test_me_returns_current_user(api_client: AsyncClient, db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    password = "me-password"
    user = await create_user(
        db_session,
        org,
        email="me-user@example.com",
        password_hash=ph.hash(password),
        role="reviewer",
    )
    await db_session.commit()

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    token = login.json()["access_token"]

    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["role"] == "reviewer"
    assert body["organization_id"] == str(org.id)
