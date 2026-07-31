"""Runtime context passed into LangGraph nodes."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.quality.ports import DedupPort, OriginalityPort
from app.infrastructure.llm.gateway import LLMGateway


@dataclass(slots=True)
class SmokeGraphContext:
    gateway: LLMGateway
    session: AsyncSession


@dataclass(slots=True)
class ReadingGraphContext:
    gateway: LLMGateway
    session: AsyncSession
    originality: OriginalityPort
    dedup: DedupPort
