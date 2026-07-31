"""Quarantined reference corpus repository — originality checker ONLY.

This module must never be imported from agents, workflows, or module packs.
Enforced by the reference-corpus-quarantine import-linter contract.
"""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.originality.ngrams import build_ngrams
from app.infrastructure.db.models.reference import ReferenceDocument


class ReferenceDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_documents(self) -> tuple[ReferenceDocument, ...]:
        stmt = select(ReferenceDocument).order_by(ReferenceDocument.created_at)
        rows = (await self.session.scalars(stmt)).all()
        return tuple(rows)

    async def get_by_id(self, document_id: uuid.UUID) -> ReferenceDocument | None:
        return cast(
            ReferenceDocument | None,
            await self.session.get(ReferenceDocument, document_id),
        )

    async def create(
        self,
        *,
        source: str,
        licence_note: str,
        body: str,
        document_id: uuid.UUID | None = None,
    ) -> ReferenceDocument:
        ngrams = sorted(build_ngrams(body))
        document = ReferenceDocument(
            id=document_id or uuid.uuid4(),
            source=source,
            licence_note=licence_note,
            body=body,
            ngram_index={"8grams": ngrams},
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def forbidden_ngrams(self) -> frozenset[str]:
        forbidden: set[str] = set()
        for document in await self.list_documents():
            index = document.ngram_index or {}
            stored = index.get("8grams")
            if isinstance(stored, list):
                forbidden.update(str(value) for value in stored)
            else:
                forbidden.update(build_ngrams(document.body))
        return frozenset(forbidden)
