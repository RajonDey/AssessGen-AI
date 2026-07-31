"""Ollama provider via langchain-ollama."""

from __future__ import annotations

import time
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse


def _to_langchain_messages(messages: tuple[ChatMessage, ...]) -> list[Any]:
    mapped: list[Any] = []
    for message in messages:
        if message.role == "system":
            mapped.append(SystemMessage(content=message.content))
        elif message.role == "assistant":
            mapped.append(AIMessage(content=message.content))
        else:
            mapped.append(HumanMessage(content=message.content))
    return mapped


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        llm = ChatOllama(
            model=model,
            base_url=self.base_url,
            temperature=params.temperature,
            top_p=params.top_p,
            num_ctx=params.num_ctx,
            seed=params.seed,
            reasoning=False,
            format="json" if schema is not None else None,
        )

        started = time.perf_counter()
        response = await llm.ainvoke(_to_langchain_messages(messages))
        latency_ms = int((time.perf_counter() - started) * 1000)

        usage = cast(dict[str, Any], response.usage_metadata or {})
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        metadata = response.response_metadata or {}
        model_digest = metadata.get("model")

        content = response.content
        if isinstance(content, list):
            content = "".join(str(part) for part in content)

        return ProviderResponse(
            content=str(content),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_digest=str(model_digest) if model_digest else None,
        )

    async def embed(self, *, model: str, text: str) -> list[float]:
        from langchain_ollama import OllamaEmbeddings

        started = time.perf_counter()
        embeddings = OllamaEmbeddings(model=model, base_url=self.base_url)
        vector = await embeddings.aembed_query(text)
        _ = int((time.perf_counter() - started) * 1000)
        return [float(value) for value in vector]
