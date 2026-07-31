"""Generation API integration tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch

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


async def _login(client: AsyncClient, db_session: AsyncSession) -> str:
    org = await create_org(db_session)
    password = "gen-password"
    user = await create_user(
        db_session,
        org,
        email=f"gen-user-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=ph.hash(password),
    )
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    body = response.json()
    assert response.status_code == 200
    token = str(body["access_token"])
    return token


@pytest.mark.asyncio
async def test_create_generation_run_returns_202(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _login(api_client, db_session)

    with patch("app.services.generation_service.celery_app.send_task") as mock_send:
        response = await api_client.post(
            "/api/v1/generation/runs",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "smoke-key-1",
            },
            json={"module": "smoke", "spec": {"kind": "smoke"}},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["module"] == "smoke"
    assert response.headers["location"].endswith(body["run_id"])
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_create_generation_run_requires_idempotency_key(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token = await _login(api_client, db_session)
    response = await api_client.post(
        "/api/v1/generation/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"module": "smoke"},
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
