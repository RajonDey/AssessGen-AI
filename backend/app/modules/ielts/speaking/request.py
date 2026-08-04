"""Parse generation run requests for IELTS Speaking."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError


class SpeakingGenerationSpec(BaseModel):
    topic_domain: str = Field(default="Learning and skills", min_length=1)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    dev_mode: bool = False


def parse_speaking_spec(request: dict[str, Any]) -> SpeakingGenerationSpec:
    raw = request.get("spec")
    if raw is None:
        return SpeakingGenerationSpec()
    if not isinstance(raw, dict):
        msg = "Speaking run request.spec must be an object"
        raise ValueError(msg)
    try:
        return SpeakingGenerationSpec.model_validate(raw)
    except ValidationError as exc:
        msg = f"Invalid speaking generation spec: {exc}"
        raise ValueError(msg) from exc
