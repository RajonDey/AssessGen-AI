"""Adapters and factories for L2 originality and dedup in Reading runs."""

from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.domain.quality.dedup import DedupReport as DomainDedupReport
from app.domain.quality.dedup import SimilarityHit as DomainSimilarityHit
from app.domain.quality.originality import OriginalityMatch as DomainOriginalityMatch
from app.domain.quality.originality import OriginalityReport as DomainOriginalityReport
from app.infrastructure.db.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.db.repositories.reference_documents import ReferenceDocumentRepository
from app.infrastructure.originality.checker import OriginalityChecker
from app.infrastructure.originality.types import OriginalityReport as InfraOriginalityReport
from app.infrastructure.vector.dedup import DedupService
from app.infrastructure.vector.types import DedupReport as InfraDedupReport
from app.workflows.context import ReadingGraphContext


def _to_domain_originality(report: InfraOriginalityReport) -> DomainOriginalityReport:
    match = None
    if report.match is not None:
        match = DomainOriginalityMatch(
            ngram=report.match.ngram,
            source_document_id=report.match.source_document_id,
        )
    return DomainOriginalityReport(
        passed=report.passed,
        checked_ngram_count=report.checked_ngram_count,
        match=match,
    )


def _to_domain_dedup(report: InfraDedupReport) -> DomainDedupReport:
    return DomainDedupReport(
        passed=report.passed,
        threshold=report.threshold,
        hits=tuple(
            DomainSimilarityHit(
                target_id=hit.target_id,
                target_type=hit.target_type,
                similarity=hit.similarity,
            )
            for hit in report.hits
        ),
    )


class OriginalityPortAdapter:
    def __init__(self, checker: OriginalityChecker) -> None:
        self._checker = checker

    async def check(
        self,
        text: str,
        *,
        allowed_source_text: str | None = None,
    ) -> DomainOriginalityReport:
        report = await self._checker.check(text, allowed_source_text=allowed_source_text)
        return _to_domain_originality(report)

    @staticmethod
    def source_hash(text: str) -> str:
        return OriginalityChecker.source_hash(text)


class DedupPortAdapter:
    def __init__(self, service: DedupService) -> None:
        self._service = service

    async def check_passage(
        self,
        *,
        run_id: uuid.UUID,
        text: str,
        exclude_target_id: uuid.UUID | None = None,
    ) -> DomainDedupReport:
        report = await self._service.check_passage(
            run_id=run_id,
            text=text,
            exclude_target_id=exclude_target_id,
        )
        return _to_domain_dedup(report)


async def build_reading_graph_context(
    *,
    settings: Settings,
    session: AsyncSession,
    redis: aioredis.Redis,
    organization_id: uuid.UUID,
) -> ReadingGraphContext:
    import importlib

    factory = importlib.import_module("app.infrastructure.llm.factory")
    gateway = factory.build_llm_gateway(
        settings=settings,
        session=session,
        redis=redis,
    )
    originality = OriginalityChecker(ReferenceDocumentRepository(session))
    await originality.load()
    dedup = DedupService(
        settings=settings,
        gateway=gateway,
        embeddings=EmbeddingRepository(session, organization_id),
    )
    return ReadingGraphContext(
        gateway=gateway,
        session=session,
        originality=OriginalityPortAdapter(originality),
        dedup=DedupPortAdapter(dedup),
    )
