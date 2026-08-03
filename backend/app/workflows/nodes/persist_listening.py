"""Persist generated listening content before human review."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.runtime import Runtime

from app.infrastructure.db.repositories.content_repository import ContentRepository
from app.modules.ielts.listening.helpers import script_to_passage
from app.modules.ielts.listening.schemas import ListeningScript
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage
from app.workflows.context import ReadingGraphContext
from app.workflows.listening_state import ListeningGraphState


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


def _items_payload(items: tuple[ReadingItem, ...]) -> list[dict[str, object]]:
    return [
        {
            "item_type": item.item_type.value,
            "stem": item.stem,
            "instructions": item.instructions,
            "options": item.options,
            "answer_key": item.answer_key.model_dump(mode="json"),
            "evidence": item.evidence.model_dump(mode="json") if item.evidence else None,
        }
        for item in items
    ]


async def persist_listening_content(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    if state.get("passage_version_id"):
        return {"status": "persisted"}

    script = ListeningScript.model_validate(state["script"])
    passage = script_to_passage(script)
    items = tuple(ReadingItem.model_validate(raw) for raw in state.get("items", []))
    body = passage.body
    repo = ContentRepository(runtime.context.session)
    passage_id, passage_version_id, item_version_ids = await repo.persist_listening_set(
        organization_id=uuid.UUID(state["organization_id"]),
        run_id=uuid.UUID(state["run_id"]),
        title=script.context,
        body=body,
        paragraphs=_paragraphs_payload(passage),
        word_count=len(body.split()),
        items=_items_payload(items),
        target_band=state["target_band"],
        script=script.model_dump(mode="json"),
        section=script.section,
    )
    await runtime.context.session.flush()
    return {
        "passage_id": str(passage_id),
        "passage_version_id": str(passage_version_id),
        "item_version_ids": [str(item_id) for item_id in item_version_ids],
        "status": "persisted",
    }
