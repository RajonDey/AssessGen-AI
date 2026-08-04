"""Build initial Writing graph state — exposed for integration tests."""

from __future__ import annotations

import uuid

from app.modules.ielts.writing.request import WritingGenerationSpec
from app.workflows.writing_state import WritingGraphState


def build_initial_writing_state(
    *,
    run_id: uuid.UUID,
    organization_id: uuid.UUID,
    spec: object,
) -> WritingGraphState:
    parsed = spec if isinstance(spec, WritingGenerationSpec) else WritingGenerationSpec()
    return {
        "run_id": str(run_id),
        "organization_id": str(organization_id),
        "status": "queued",
        "topic": parsed.topic,
        "question_type": parsed.question_type,
        "target_band": parsed.target_band,
        "dev_mode": parsed.dev_mode,
        "prompt_attempt": 0,
        "item_version_ids": [],
    }
