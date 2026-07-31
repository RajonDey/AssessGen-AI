"""Reference-corpus originality checker — the only permitted consumer of reference_documents."""

from __future__ import annotations

from app.infrastructure.db.repositories.reference_documents import ReferenceDocumentRepository
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.originality.ngrams import build_ngrams, content_hash, find_forbidden_overlap
from app.infrastructure.originality.types import OriginalityMatch, OriginalityReport


class OriginalityChecker:
    def __init__(self, repository: ReferenceDocumentRepository) -> None:
        self._repository = repository
        self._forbidden: frozenset[str] | None = None
        self._log = get_logger("app.originality")

    async def load(self) -> None:
        self._forbidden = await self._repository.forbidden_ngrams()

    async def check(
        self,
        text: str,
        *,
        allowed_source_text: str | None = None,
    ) -> OriginalityReport:
        if self._forbidden is None:
            await self.load()

        forbidden = self._forbidden or frozenset()
        allowed = build_ngrams(allowed_source_text) if allowed_source_text else None
        overlap = find_forbidden_overlap(text, forbidden, allowed=allowed)
        checked = len(build_ngrams(text))

        if overlap is None:
            return OriginalityReport(passed=True, checked_ngram_count=checked)

        self._log.warning(
            "quality.originality.blocked",
            ngram=overlap,
            checked_ngram_count=checked,
        )
        return OriginalityReport(
            passed=False,
            checked_ngram_count=checked,
            match=OriginalityMatch(ngram=overlap),
        )

    @staticmethod
    def source_hash(text: str) -> str:
        return content_hash(text)
