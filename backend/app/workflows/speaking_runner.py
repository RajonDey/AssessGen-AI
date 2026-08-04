"""Build initial Speaking graph state — exposed for integration tests."""

from __future__ import annotations

import uuid

from app.modules.ielts.speaking.request import SpeakingGenerationSpec
from app.workflows.speaking_state import SpeakingGraphState


def build_initial_speaking_state(
    *,
    run_id: uuid.UUID,
    organization_id: uuid.UUID,
    spec: object,
) -> SpeakingGraphState:
    parsed = spec if isinstance(spec, SpeakingGenerationSpec) else SpeakingGenerationSpec()
    return {
        "run_id": str(run_id),
        "organization_id": str(organization_id),
        "status": "queued",
        "topic_domain": parsed.topic_domain,
        "target_band": parsed.target_band,
        "dev_mode": parsed.dev_mode,
        "content_attempt": 0,
        "item_version_ids": [],
    }
