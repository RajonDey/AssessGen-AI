"""Database trigger and constraint integration tests."""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest
from app.infrastructure.db.errors import TenantScopeError
from app.infrastructure.db.models import GenerationRun, Passage, PassageVersion, QualityCheck
from app.infrastructure.db.repositories.base import TenantScopedRepository
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.db_url import to_async_psycopg_url
from tests.integration.helpers import (
    create_item_with_version,
    create_org,
    create_passage_with_version,
    create_user,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_updating_an_item_version_raises(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    _, version = await create_item_with_version(db_session, org)
    await db_session.commit()

    with pytest.raises(DBAPIError, match="immutable table"):
        await db_session.execute(
            text("UPDATE item_versions SET stem = 'changed' WHERE id = :id"),
            {"id": version.id},
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_updating_a_passage_version_raises(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    _, version = await create_passage_with_version(db_session, org)
    await db_session.commit()

    with pytest.raises(DBAPIError, match="immutable table"):
        await db_session.execute(
            text("UPDATE passage_versions SET body = 'changed' WHERE id = :id"),
            {"id": version.id},
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_version_numbers_are_assigned_monotonically(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    passage, first = await create_passage_with_version(db_session, org, version_no=0)
    assert first.version_no == 1

    second = PassageVersion(
        id=uuid.uuid4(),
        passage_id=passage.id,
        version_no=0,
        content_hash=f"hash-{uuid.uuid4()}",
        title="Title 2",
        body="Second body.",
        paragraphs=[{"label": "A", "text": "Second", "start": 0, "end": 6}],
        word_count=2,
        readability={"flesch_kincaid": 8.0},
        organization_id=org.id,
    )
    db_session.add(second)
    await db_session.flush()
    await db_session.refresh(second)
    assert second.version_no == 2


@pytest.mark.asyncio
async def test_passage_version_org_denorm_from_passage(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    passage = Passage(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        status="draft",
    )
    db_session.add(passage)
    await db_session.flush()

    version = PassageVersion(
        id=uuid.uuid4(),
        passage_id=passage.id,
        version_no=0,
        content_hash=f"hash-{uuid.uuid4()}",
        title="Title",
        body="Body",
        paragraphs=[{"label": "A", "text": "Body", "start": 0, "end": 4}],
        word_count=4,
        readability={"flesch_kincaid": 8.0},
        organization_id=uuid.uuid4(),
    )
    db_session.add(version)
    await db_session.flush()
    await db_session.refresh(version)
    assert version.organization_id == org.id


@pytest.mark.asyncio
async def test_approving_with_failing_must_rule_is_rejected(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    item, version = await create_item_with_version(db_session, org)

    db_session.add(
        QualityCheck(
            id=uuid.uuid4(),
            target_type="item_version",
            target_id=version.id,
            engine="rule",
            rule_code="R-READ-001",
            severity="must",
            passed=False,
            engine_version="1.0.0",
        )
    )
    await db_session.flush()

    with pytest.raises(DBAPIError, match="blocked by quality gate"):
        await db_session.execute(
            text("UPDATE items SET status = 'approved' WHERE id = :id"),
            {"id": item.id},
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_repository_query_without_org_id_raises() -> None:
    with pytest.raises(TenantScopeError):
        TenantScopedRepository(session=None, organization_id=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_idempotency_key_conflict_returns_original_run(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    key = str(uuid.uuid4())

    first = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        request={"module": "reading"},
        status="queued",
        idempotency_key=key,
        requested_by=user.id,
    )
    db_session.add(first)
    await db_session.commit()
    first_id = first.id

    duplicate = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        request={"module": "reading"},
        status="queued",
        idempotency_key=key,
        requested_by=user.id,
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()
    result = await db_session.scalar(select(GenerationRun).where(GenerationRun.id == first_id))
    assert result is not None
    assert result.idempotency_key == key


def test_migrations_apply_from_empty() -> None:
    """Alembic upgrade head succeeds on a fresh database."""
    pytest.importorskip("testcontainers")
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg18") as postgres:
        async_url = to_async_psycopg_url(postgres.get_connection_url())
        env = os.environ.copy()
        env["DATABASE_URL"] = async_url
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            check=True,
        )
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            check=True,
        )
