"""Profile resolution tests."""

import pytest
from app.infrastructure.llm.profiles import resolve_model
from app.infrastructure.llm.types import LLMRole


def test_fast_profile_resolves_metadata_role() -> None:
    model = resolve_model("fast", LLMRole.METADATA)
    assert model.model_name == "qwen3.5:4b"
    assert model.provider == "ollama"


def test_local_profile_uses_larger_generator() -> None:
    model = resolve_model("local", "generator")
    assert model.model_name == "qwen3.5:9b"
    assert model.memory_gb == 6.6


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="Unknown LLM profile"):
        resolve_model("missing", LLMRole.METADATA)  # type: ignore[arg-type]
