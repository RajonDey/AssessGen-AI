"""Application settings — local Ollama or paid OpenAI-compatible API."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AssessGen AI"
    environment: str = "development"

    # ollama | openai (OpenAI-compatible: OpenAI, Groq, etc.)
    llm_provider: Literal["ollama", "openai"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_generator_model: str = "gemma4:e2b"
    ollama_reviewer_model: str = "gemma4:e2b"

    # OpenAI-compatible
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_generator_model: str = "gpt-4.1-mini"
    openai_reviewer_model: str = "gpt-4.1-mini"

    max_revision_loops: int = 2
    # 0 = no read timeout (wait as long as Ollama needs). Positive = seconds.
    llm_timeout_seconds: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
