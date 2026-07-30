"""Schema-constrained completion with a repair loop."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.infrastructure.llm.types import ChatMessage, ProviderResponse

MAX_REPAIR_ATTEMPTS = 2
MAX_TOTAL_ATTEMPTS = MAX_REPAIR_ATTEMPTS + 1


@dataclass(frozen=True, slots=True)
class StructuredAttempt:
    attempt: int
    response: ProviderResponse
    parsed: BaseModel | None
    validation_error: str | None


@dataclass(frozen=True, slots=True)
class StructuredResult:
    value: BaseModel
    attempts: tuple[StructuredAttempt, ...]


class SchemaValidationError(Exception):
    def __init__(self, attempts: tuple[StructuredAttempt, ...]) -> None:
        self.attempts = attempts
        super().__init__("Structured output failed schema validation after retries")


def _repair_message(error: str) -> ChatMessage:
    return ChatMessage(
        role="user",
        content=(
            "Your previous response failed validation. "
            f"Error: {error}. "
            "Return corrected JSON only, matching the required schema exactly."
        ),
    )


def _parse_schema[T: BaseModel](content: str, schema: type[T]) -> T:
    payload = json.loads(content)
    return schema.model_validate(payload)


async def complete_with_repair[T: BaseModel](
    *,
    schema: type[T],
    base_messages: tuple[ChatMessage, ...],
    invoke: Callable[[tuple[ChatMessage, ...]], Awaitable[ProviderResponse]],
) -> StructuredResult:
    messages = list(base_messages)
    attempts: list[StructuredAttempt] = []

    for attempt_no in range(1, MAX_TOTAL_ATTEMPTS + 1):
        response = await invoke(tuple(messages))
        try:
            parsed = _parse_schema(response.content, schema)
        except (json.JSONDecodeError, ValidationError) as exc:
            error_text = str(exc)
            attempts.append(
                StructuredAttempt(
                    attempt=attempt_no,
                    response=response,
                    parsed=None,
                    validation_error=error_text,
                )
            )
            if attempt_no >= MAX_TOTAL_ATTEMPTS:
                break
            messages.append(_repair_message(error_text))
            continue

        attempts.append(
            StructuredAttempt(
                attempt=attempt_no,
                response=response,
                parsed=parsed,
                validation_error=None,
            )
        )
        return StructuredResult(value=parsed, attempts=tuple(attempts))

    raise SchemaValidationError(tuple(attempts))
