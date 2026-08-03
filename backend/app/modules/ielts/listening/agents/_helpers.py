"""Shared helpers for Listening generation agents."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, hash_messages
from app.modules.ielts.listening.prompts import render_prompt


def build_user_message(template: str, **values: object) -> ChatMessage:
    return ChatMessage(role="user", content=render_prompt(template, **values))


def prompt_hash_for(template: str, **values: object) -> str:
    return hash_messages((build_user_message(template, **values),))


def plan_to_json(plan: object) -> str:
    return json.dumps(plan.model_dump(mode="json"), indent=2)  # type: ignore[attr-defined]
