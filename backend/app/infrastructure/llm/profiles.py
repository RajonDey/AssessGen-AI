"""Role → model resolution from the active LLM profile."""

from __future__ import annotations

from typing import Literal

from app.infrastructure.llm.types import LLMRole, ModelConfig

ProfileName = Literal["fast", "local", "local-hq", "cloud"]

_PROFILES: dict[ProfileName, dict[LLMRole, ModelConfig]] = {
    "fast": {
        LLMRole.GENERATOR: ModelConfig("qwen3.5:4b", 3.5),
        LLMRole.CRITIC: ModelConfig("qwen3.5:4b", 3.5),
        LLMRole.METADATA: ModelConfig("qwen3.5:4b", 3.5),
        LLMRole.EMBEDDING: ModelConfig("nomic-embed-text", 0.3),
    },
    "local": {
        LLMRole.GENERATOR: ModelConfig("qwen3.5:9b", 6.6),
        LLMRole.CRITIC: ModelConfig("qwen3.5:9b", 6.6),
        LLMRole.METADATA: ModelConfig("qwen3.5:4b", 3.5),
        LLMRole.EMBEDDING: ModelConfig("nomic-embed-text", 0.3),
    },
    "local-hq": {
        LLMRole.GENERATOR: ModelConfig("gemma4:12b", 8.0),
        LLMRole.CRITIC: ModelConfig("qwen3.5:9b", 6.6),
        LLMRole.METADATA: ModelConfig("qwen3.5:4b", 3.5),
        LLMRole.EMBEDDING: ModelConfig("nomic-embed-text", 0.3),
    },
    "cloud": {
        LLMRole.GENERATOR: ModelConfig("cloud-tbd", 0.0, provider="cloud"),
        LLMRole.CRITIC: ModelConfig("cloud-tbd", 0.0, provider="cloud"),
        LLMRole.METADATA: ModelConfig("cloud-tbd", 0.0, provider="cloud"),
        LLMRole.EMBEDDING: ModelConfig("cloud-tbd", 0.0, provider="cloud"),
    },
}


def resolve_model(profile: ProfileName, role: LLMRole | str) -> ModelConfig:
    role_enum = LLMRole(role)
    try:
        profile_map = _PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown LLM profile: {profile}") from exc
    try:
        return profile_map[role_enum]
    except KeyError as exc:
        raise ValueError(f"Role {role_enum} is not configured for profile {profile}") from exc
