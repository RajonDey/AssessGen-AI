"""L2 originality and dedup gate helpers for Reading graph nodes."""

from __future__ import annotations

import uuid

from app.domain.quality.dedup import DedupReport
from app.domain.quality.originality import OriginalityReport
from app.domain.quality.ports import DedupPort, OriginalityPort
from app.modules.ielts.reading.schemas import ReadingPassage


def originality_to_state(report: OriginalityReport) -> dict[str, object]:
    return {
        "passed": report.passed,
        "is_blocking": report.is_blocking,
        "checked_ngram_count": report.checked_ngram_count,
        "match": report.match.model_dump(mode="json") if report.match else None,
    }


def dedup_to_state(report: DedupReport) -> dict[str, object]:
    return {
        "passed": report.passed,
        "is_blocking": report.is_blocking,
        "threshold": report.threshold,
        "hits": [hit.model_dump(mode="json") for hit in report.hits],
    }


async def check_passage_originality(
    checker: OriginalityPort,
    passage: ReadingPassage,
    *,
    allowed_source_text: str | None,
) -> OriginalityReport:
    return await checker.check(passage.body, allowed_source_text=allowed_source_text)


async def check_passage_dedup(
    dedup: DedupPort,
    passage: ReadingPassage,
    *,
    run_id: uuid.UUID,
) -> DedupReport:
    return await dedup.check_passage(run_id=run_id, text=passage.body)
