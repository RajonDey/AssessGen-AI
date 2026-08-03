"""Build initial Listening graph state — exposed for integration tests."""

from __future__ import annotations

import uuid

from app.modules.ielts.listening.request import ListeningGenerationSpec
from app.workflows.listening_state import ListeningGraphState


def build_initial_listening_state(
    *,
    run_id: uuid.UUID,
    organization_id: uuid.UUID,
    spec: object,
) -> ListeningGraphState:
    parsed = spec if isinstance(spec, ListeningGenerationSpec) else ListeningGenerationSpec()
    return {
        "run_id": str(run_id),
        "organization_id": str(organization_id),
        "status": "queued",
        "topic": parsed.topic,
        "section": parsed.section,
        "target_band": parsed.target_band,
        "question_count": parsed.question_count,
        "accent": parsed.accent,
        "script_attempt": 0,
    }
