"""Trivial end-to-end graph for Phase 1A verification."""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy import func, select

from app.agents.metadata_agent import MetadataAgent, MetadataInput
from app.infrastructure.db.models import AgentInvocation
from app.workflows.context import SmokeGraphContext
from app.workflows.state import SmokeGraphState


async def call_metadata_agent(
    state: SmokeGraphState,
    runtime: Runtime[SmokeGraphContext],
) -> dict[str, Any]:
    agent = MetadataAgent()
    result = await agent.run(
        runtime.context.gateway,
        MetadataInput(
            run_id=uuid.UUID(state["run_id"]),
            prompt="Return a short friendly greeting as JSON with a 'greeting' field.",
        ),
    )
    return {"greeting": result.greeting, "status": "metadata_complete"}


async def persist_invocation(
    state: SmokeGraphState,
    runtime: Runtime[SmokeGraphContext],
) -> dict[str, Any]:
    run_id = uuid.UUID(state["run_id"])
    count = await runtime.context.session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    if not count:
        return {
            "status": "failed",
            "error": "Expected agent_invocations row after metadata call.",
            "invocation_recorded": False,
        }
    return {"status": "completed", "invocation_recorded": True}


def build_smoke_graph(checkpointer: BaseCheckpointSaver) -> Any:
    builder = StateGraph(SmokeGraphState)
    builder.add_node("call_metadata_agent", call_metadata_agent)
    builder.add_node("persist_invocation", persist_invocation)
    builder.add_edge(START, "call_metadata_agent")
    builder.add_edge("call_metadata_agent", "persist_invocation")
    builder.add_edge("persist_invocation", END)
    return builder.compile(checkpointer=checkpointer)
