"""Shared helpers for Reading generation agents."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, hash_messages
from app.modules.ielts.reading.prompts import render_prompt


def build_user_message(template: str, **values: object) -> ChatMessage:
    return ChatMessage(role="user", content=render_prompt(template, **values))


def prompt_hash_for(template: str, **values: object) -> str:
    return hash_messages((build_user_message(template, **values),))


def format_item_types(types: tuple[object, ...]) -> str:
    return ", ".join(str(item_type) for item_type in types)


def drafts_to_json(drafts: tuple[object, ...]) -> str:
    payload = [draft.model_dump(mode="json") for draft in drafts]
    return json.dumps(payload, indent=2)


def models_to_json(models: tuple[object, ...]) -> str:
    return drafts_to_json(models)
