"""Gateway types — roles, requests, and provider responses."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class LLMRole(StrEnum):
    GENERATOR = "generator"
    CRITIC = "critic"
    METADATA = "metadata"
    EMBEDDING = "embedding"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    model_name: str
    memory_gb: float
    provider: str = "ollama"


@dataclass(frozen=True, slots=True)
class CompletionParams:
    temperature: float = 0.7
    top_p: float = 0.9
    seed: int | None = None
    num_ctx: int = 8192

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.num_ctx,
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        return payload


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    content: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_digest: str | None = None


@dataclass(frozen=True, slots=True)
class GatewayRequest:
    role: LLMRole
    agent: str
    run_id: UUID
    messages: tuple[ChatMessage, ...]
    prompt_hash: str
    prompt_version_id: UUID | None = None
    params: CompletionParams = field(default_factory=CompletionParams)


def hash_messages(messages: tuple[ChatMessage, ...]) -> str:
    digest = hashlib.sha256()
    for message in messages:
        digest.update(message.role.encode())
        digest.update(b"\0")
        digest.update(message.content.encode())
        digest.update(b"\0")
    return digest.hexdigest()
