"""Originality checker integration tests."""

from __future__ import annotations

import pytest
from app.infrastructure.db.repositories.reference_documents import ReferenceDocumentRepository
from app.infrastructure.originality.checker import OriginalityChecker
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_originality_blocks_reference_overlap(db_session: AsyncSession) -> None:
    shared = " ".join(f"cambridge{i}" for i in range(12))
    repo = ReferenceDocumentRepository(db_session)
    await repo.create(
        source="Cambridge sample",
        licence_note="test fixture",
        body=f"{shared} continues with authentic material.",
    )
    await db_session.commit()

    checker = OriginalityChecker(repo)
    report = await checker.check(f"Intro text. {shared} and more.")

    assert not report.passed
    assert report.match is not None


@pytest.mark.asyncio
async def test_originality_allows_licensed_source_overlap(db_session: AsyncSession) -> None:
    shared = " ".join(f"licensed{i}" for i in range(12))
    repo = ReferenceDocumentRepository(db_session)
    await repo.create(
        source="Other corpus",
        licence_note="test fixture",
        body=f"{shared} from another document.",
    )
    await db_session.commit()

    checker = OriginalityChecker(repo)
    source_text = f"{shared} adapted with additional commentary."
    report = await checker.check(source_text, allowed_source_text=source_text)

    assert report.passed
