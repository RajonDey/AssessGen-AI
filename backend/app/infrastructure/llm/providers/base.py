"""Provider protocol for LLM backends."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse


class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse: ...

    async def embed(self, *, model: str, text: str) -> list[float]: ...
