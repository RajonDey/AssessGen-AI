"""Review API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ResumeGenerationRunRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject|request_changes)$")
    notes: str | None = None
    reason_code: str | None = None
    time_spent_seconds: int | None = Field(default=None, ge=0)


class ReviewQueueItem(BaseModel):
    run_id: UUID
    module: str
    topic: str | None = None
    created_at: datetime
    interrupt_payload: dict[str, Any] | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
