"""Persist generated writing content before human review."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.runtime import Runtime

from app.infrastructure.db.repositories.content_repository import ContentRepository
from app.modules.ielts.reading.schemas import ReadingPassage
from app.modules.ielts.writing.helpers import prompt_to_passage
from app.modules.ielts.writing.schemas import WritingTask2Prompt
from app.workflows.context import ReadingGraphContext
from app.workflows.writing_state import WritingGraphState


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


async def persist_writing_content(
    state: WritingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    if state.get("passage_version_id"):
        return {"status": "persisted"}

    task2 = WritingTask2Prompt.model_validate(state["task2_prompt"])
    passage = prompt_to_passage(task2)
    body = passage.body
    repo = ContentRepository(runtime.context.session)
    passage_id, passage_version_id = await repo.persist_writing_prompt(
        organization_id=uuid.UUID(state["organization_id"]),
        run_id=uuid.UUID(state["run_id"]),
        title=task2.topic,
        body=body,
        paragraphs=_paragraphs_payload(passage),
        word_count=len(body.split()),
        target_band=state["target_band"],
        metadata=task2.model_dump(mode="json"),
    )
    await runtime.context.session.flush()
    return {
        "passage_id": str(passage_id),
        "passage_version_id": str(passage_version_id),
        "item_version_ids": [],
        "status": "persisted",
    }
