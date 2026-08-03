"""Persist generated speaking content before human review."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.runtime import Runtime

from app.infrastructure.db.repositories.content_repository import ContentRepository
from app.modules.ielts.reading.schemas import ReadingPassage
from app.modules.ielts.speaking.helpers import content_to_passage, format_content_body
from app.modules.ielts.speaking.schemas import SpeakingPart1And2
from app.workflows.context import ReadingGraphContext
from app.workflows.speaking_state import SpeakingGraphState


def _paragraphs_payload(passage: ReadingPassage) -> list[dict[str, object]]:
    offset = 0
    payload: list[dict[str, object]] = []
    for index, paragraph in enumerate(passage.paragraphs):
        prefix = f"{paragraph.label}\n"
        text = paragraph.text
        start = offset + len(prefix)
        end = start + len(text)
        payload.append(
            {
                "label": paragraph.label,
                "text": text,
                "start": start,
                "end": end,
            }
        )
        offset = end + (2 if index < len(passage.paragraphs) - 1 else 0)
    return payload


async def persist_speaking_content(
    state: SpeakingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    if state.get("passage_version_id"):
        return {"status": "persisted"}

    content = SpeakingPart1And2.model_validate(state["speaking_content"])
    passage = content_to_passage(content)
    body = format_content_body(content)
    repo = ContentRepository(runtime.context.session)
    passage_id, passage_version_id = await repo.persist_speaking_content(
        organization_id=uuid.UUID(state["organization_id"]),
        run_id=uuid.UUID(state["run_id"]),
        title=content.part2.topic,
        body=body,
        paragraphs=_paragraphs_payload(passage),
        word_count=len(passage.body.split()),
        target_band=state["target_band"],
        metadata=content.model_dump(mode="json"),
    )
    await runtime.context.session.flush()
    return {
        "passage_id": str(passage_id),
        "passage_version_id": str(passage_version_id),
        "item_version_ids": [],
        "status": "persisted",
    }
