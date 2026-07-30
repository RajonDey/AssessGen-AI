"""Helpers for integration tests."""

from __future__ import annotations

import uuid

from app.infrastructure.db.models import (
    GenerationRun,
    Item,
    ItemVersion,
    Organization,
    Passage,
    PassageVersion,
    User,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def create_org(session: AsyncSession, slug: str | None = None) -> Organization:
    org_slug = slug or f"org-{uuid.uuid4().hex[:12]}"
    org = Organization(id=uuid.uuid4(), slug=org_slug, name="Test Org")
    session.add(org)
    await session.flush()
    return org


async def create_user(
    session: AsyncSession,
    org: Organization,
    *,
    email: str | None = None,
    password_hash: str = "hash",
    role: str = "admin",
) -> User:
    user = User(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=email or f"{uuid.uuid4()}@example.com",
        password_hash=password_hash,
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def create_run(session: AsyncSession, org: Organization, user: User) -> GenerationRun:
    run = GenerationRun(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        request={"module": "reading"},
        status="queued",
        requested_by=user.id,
    )
    session.add(run)
    await session.flush()
    return run


async def create_passage_with_version(
    session: AsyncSession,
    org: Organization,
    *,
    version_no: int = 0,
) -> tuple[Passage, PassageVersion]:
    passage = Passage(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        status="draft",
    )
    session.add(passage)
    await session.flush()

    version = PassageVersion(
        id=uuid.uuid4(),
        passage_id=passage.id,
        version_no=version_no,
        content_hash=f"hash-{uuid.uuid4()}",
        title="Title",
        body="Body text for testing.",
        paragraphs=[{"label": "A", "text": "Body", "start": 0, "end": 4}],
        word_count=4,
        readability={"flesch_kincaid": 8.0},
        organization_id=org.id,
    )
    session.add(version)
    await session.flush()
    await session.refresh(version)
    passage.current_version_id = version.id
    await session.flush()
    return passage, version


async def create_item_with_version(
    session: AsyncSession,
    org: Organization,
    passage: Passage | None = None,
    *,
    version_no: int = 0,
) -> tuple[Item, ItemVersion]:
    item = Item(
        id=uuid.uuid4(),
        organization_id=org.id,
        module="reading",
        item_type="mcq_single",
        passage_id=passage.id if passage else None,
        status="draft",
    )
    session.add(item)
    await session.flush()

    version = ItemVersion(
        id=uuid.uuid4(),
        item_id=item.id,
        version_no=version_no,
        content_hash=f"hash-{uuid.uuid4()}",
        stem="What is the answer?",
        answer_key={"type": "exact", "values": ["answer"]},
    )
    session.add(version)
    await session.flush()
    await session.refresh(version)
    item.current_version_id = version.id
    await session.flush()
    return item, version
