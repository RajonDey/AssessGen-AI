"""Speaking graph mock LLM responses for integration tests."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.modules.ielts.speaking.prompt_examples import speaking_content_json_example
from pydantic import BaseModel


class SpeakingMockProvider:
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
        if schema_name == "SpeakingPart1And2":
            content = speaking_content_json_example()
        else:
            content = '{"greeting":"fallback"}'
        json.loads(content)
        return ProviderResponse(
            content=content,
            input_tokens=40,
            output_tokens=120,
            latency_ms=85,
        )

    async def embed(self, *, model: str, text: str) -> list[float]:
        del model, text
        return [0.0] * 768
