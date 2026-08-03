"""Parse generation run requests for IELTS Listening."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator


class ListeningGenerationSpec(BaseModel):
    topic: str = Field(default="Everyday enquiry", min_length=1)
    section: int = Field(default=1, ge=1, le=2)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    question_count: int = Field(default=10, ge=1, le=10)
    accent: str = Field(default="british", min_length=1)

    @model_validator(mode="after")
    def validate_phase_1c_section(self) -> ListeningGenerationSpec:
        if self.section not in (1, 2):
            msg = "Phase 1C supports Listening sections 1 and 2 only"
            raise ValueError(msg)
        return self


def parse_listening_spec(request: dict[str, Any]) -> ListeningGenerationSpec:
    raw = request.get("spec")
    if raw is None:
        return ListeningGenerationSpec()
    if not isinstance(raw, dict):
        msg = "Listening run request.spec must be an object"
        raise ValueError(msg)
    try:
        return ListeningGenerationSpec.model_validate(raw)
    except ValidationError as exc:
        msg = f"Invalid listening generation spec: {exc}"
        raise ValueError(msg) from exc
