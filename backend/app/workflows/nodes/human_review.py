"""Human review gate — LangGraph interrupt before final approval."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from app.infrastructure.db.models import Review
from app.infrastructure.db.repositories.content_repository import ContentRepository
from app.workflows.context import ReadingGraphContext
from app.workflows.reading_state import ReadingGraphState


async def human_review(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    payload = {
        "run_id": state["run_id"],
        "passage_id": state.get("passage_id"),
        "passage_version_id": state.get("passage_version_id"),
        "item_version_ids": state.get("item_version_ids", []),
        "topic": state.get("topic"),
    }
    decision = interrupt(payload)
    if not isinstance(decision, dict):
        return {"status": "failed", "error": f"Invalid review decision: {decision!r}"}

    decision_value = decision.get("decision")
    reviewer_id = decision.get("reviewer_id")
    if reviewer_id and state.get("passage_version_id"):
        review = Review(
            id=uuid.uuid4(),
            target_type="passage_version",
            target_id=uuid.UUID(str(state["passage_version_id"])),
            reviewer_id=uuid.UUID(str(reviewer_id)),
            decision=str(decision_value),
            reason_code=decision.get("reason_code"),
            comment=decision.get("notes"),
            time_spent_seconds=decision.get("time_spent_seconds"),
        )
        runtime.context.session.add(review)
        await runtime.context.session.flush()

    if decision_value == "approve":
        passage_id = state.get("passage_id")
        if passage_id:
            repo = ContentRepository(runtime.context.session)
            await repo.approve_passage_set(
                uuid.UUID(str(passage_id)),
                organization_id=uuid.UUID(str(state["organization_id"])),
            )
        return {"status": "review_approved", "human_review": decision}
    notes = decision.get("notes") or decision_value or "rejected"
    return {"status": "failed", "error": f"Human review rejected: {notes}"}
