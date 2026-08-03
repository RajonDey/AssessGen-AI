"""Writing graph mock LLM responses for integration tests."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.modules.ielts.writing.prompt_examples import task2_json_example
from pydantic import BaseModel


class WritingMockProvider:
    name = "mock"

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        del model, messages, params
        schema_name = schema.__name__ if schema is not None else ""
        if schema_name == "WritingTask2Prompt":
            content = task2_json_example(question_type="opinion")
        else:
            content = '{"greeting":"fallback"}'
        # Validate shape round-trips
        json.loads(content)
        return ProviderResponse(
            content=content,
            input_tokens=40,
            output_tokens=100,
            latency_ms=80,
        )

    async def embed(self, *, model: str, text: str) -> list[float]:
        del model, text
        return [0.0] * 768
