"""Construct gateway dependencies."""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.lease import build_model_lease
from app.infrastructure.llm.providers.ollama import OllamaProvider


def build_llm_gateway(
    *,
    settings: Settings,
    session: AsyncSession,
    redis: Redis | None = None,
) -> LLMGateway:
    lease = build_model_lease(
        redis=redis,
        budget_gb=settings.llm_memory_budget_gb,
        ttl_seconds=settings.llm_lease_ttl_seconds,
    )
    provider = OllamaProvider(base_url=settings.ollama_base_url)
    return LLMGateway(
        settings=settings,
        lease=lease,
        provider=provider,
        session=session,
    )
