"""Export API schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReadingExportRequest(BaseModel):
    run_id: UUID
    publish: bool = True


class ReadingExportResponse(BaseModel):
    format: str
    run_id: UUID
    module: str
    passage_count: int
    question_count: int
    passages: list[dict[str, Any]] = Field(default_factory=list)
