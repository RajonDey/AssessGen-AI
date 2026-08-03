"""Shared helpers for Writing generation agents."""

from __future__ import annotations

from app.infrastructure.llm.types import ChatMessage, hash_messages
from app.modules.ielts.writing.prompts import render_prompt


def build_user_message(template: str, **values: object) -> ChatMessage:
    return ChatMessage(role="user", content=render_prompt(template, **values))


def prompt_hash_for(template: str, **values: object) -> str:
    return hash_messages((build_user_message(template, **values),))
