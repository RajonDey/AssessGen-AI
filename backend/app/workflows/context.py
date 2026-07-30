"""Runtime context passed into LangGraph nodes."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.llm.gateway import LLMGateway


@dataclass(slots=True)
class SmokeGraphContext:
    gateway: LLMGateway
    session: AsyncSession
