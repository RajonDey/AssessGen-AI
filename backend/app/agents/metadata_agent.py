"""Metadata tagging agent — smoke / enrichment calls."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import ChatMessage, LLMRole, hash_messages


class MetadataInput(BaseModel):
    run_id: UUID
    prompt: str


class MetadataOutput(BaseModel):
    greeting: str = Field(min_length=1)


class MetadataAgent:
    async def run(self, gateway: LLMGateway, input: MetadataInput) -> MetadataOutput:
        messages = (ChatMessage(role="user", content=input.prompt),)
        return await gateway.complete(
            role=LLMRole.METADATA,
            agent="metadata_agent",
            run_id=input.run_id,
            messages=messages,
            schema=MetadataOutput,
            prompt_hash=hash_messages(messages),
        )
