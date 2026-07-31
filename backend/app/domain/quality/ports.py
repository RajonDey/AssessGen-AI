"""Quality gate ports — structural protocols for workflow dependency injection."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.quality.dedup import DedupReport
from app.domain.quality.originality import OriginalityReport


class OriginalityPort(Protocol):
    async def check(
        self,
        text: str,
        *,
        allowed_source_text: str | None = None,
    ) -> OriginalityReport: ...

    @staticmethod
    def source_hash(text: str) -> str: ...


class DedupPort(Protocol):
    async def check_passage(
        self,
        *,
        run_id: UUID,
        text: str,
        exclude_target_id: UUID | None = None,
    ) -> DedupReport: ...
