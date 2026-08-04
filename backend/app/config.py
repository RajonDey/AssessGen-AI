"""Application configuration — the only module that reads environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AssessGen AI"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://assessgen:assessgen@localhost:5434/assessgen"
    )
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "assessgen"
    s3_secret_key: str = "assessgen-dev"
    s3_bucket: str = "assessgen"
    s3_region: str = "us-east-1"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    ollama_base_url: str = "http://localhost:11434"
    llm_profile: Literal["fast", "local", "local-hq", "cloud"] = "fast"
    llm_memory_budget_gb: float = 11.0
    llm_lease_ttl_seconds: int = 900

    generation_soft_timeout_seconds: int = 1800
    generation_hard_timeout_seconds: int = 2100

    dedup_reject_similarity: float = 0.95
    dedup_review_similarity: float = 0.88

    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
