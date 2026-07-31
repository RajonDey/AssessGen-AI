"""Generation API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateGenerationRunRequest(BaseModel):
    module: str = Field(default="smoke", min_length=1)
    exam: str = Field(default="ielts")
    variant: str = Field(default="academic")
    spec: dict[str, Any] = Field(default_factory=lambda: {"kind": "smoke"})


class GenerationRunResponse(BaseModel):
    run_id: UUID
    status: str
    module: str
    created_at: datetime
    failure_reason: str | None = None
