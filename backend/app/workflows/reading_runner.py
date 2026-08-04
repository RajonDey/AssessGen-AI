"""Build initial Reading graph state — exposed for integration tests."""

from __future__ import annotations

import uuid

from app.modules.ielts.reading.request import ReadingGenerationSpec
from app.workflows.reading_state import ReadingGraphState


def build_initial_reading_state(
    *,
    run_id: uuid.UUID,
    organization_id: uuid.UUID,
    spec: object,
) -> ReadingGraphState:
    parsed = spec if isinstance(spec, ReadingGenerationSpec) else ReadingGenerationSpec()
    return {
        "run_id": str(run_id),
        "organization_id": str(organization_id),
        "status": "queued",
        "topic": parsed.topic,
        "target_band": parsed.target_band,
        "passage_count": parsed.passage_count,
        "question_count": parsed.question_count,
        "source_mode": parsed.source_mode.value,
        "source_text": parsed.source_text,
        "license_label": parsed.license_label,
        "adaptation_level": parsed.adaptation_level,
        "dev_mode": parsed.dev_mode,
        "planner_attempt": 0,
        "passage_attempt": 0,
        "revision_attempt": 0,
    }
