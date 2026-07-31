"""Structured output repair loop tests."""

import pytest
from app.infrastructure.llm.structured import SchemaValidationError, complete_with_repair
from app.infrastructure.llm.types import ChatMessage, ProviderResponse
from pydantic import BaseModel, Field


class GreetingSchema(BaseModel):
    greeting: str = Field(min_length=1)


@pytest.mark.asyncio
async def test_repair_loop_retries_until_schema_valid() -> None:
    calls = 0

    async def invoke(messages: tuple[ChatMessage, ...]) -> ProviderResponse:
        nonlocal calls
        calls += 1
        content = '{"greeting": ""}' if calls == 1 else '{"greeting": "hello"}'
        return ProviderResponse(
            content=content,
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
        )

    result = await complete_with_repair(
        schema=GreetingSchema,
        base_messages=(ChatMessage(role="user", content="Say hello"),),
        invoke=invoke,
    )

    assert isinstance(result.value, GreetingSchema)
    assert result.value.greeting == "hello"
    assert len(result.attempts) == 2
    assert calls == 2


@pytest.mark.asyncio
async def test_schema_validation_error_after_max_attempts() -> None:
    async def invoke(_messages: tuple[ChatMessage, ...]) -> ProviderResponse:
        return ProviderResponse(
            content='{"greeting": ""}',
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
        )

    with pytest.raises(SchemaValidationError) as exc_info:
        await complete_with_repair(
            schema=GreetingSchema,
            base_messages=(ChatMessage(role="user", content="Say hello"),),
            invoke=invoke,
        )

    assert len(exc_info.value.attempts) == 3
