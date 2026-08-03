"""Writing graph integration tests."""

from __future__ import annotations

import uuid

import pytest
from app.config import Settings
from app.infrastructure.db.models import AgentInvocation, GenerationRun, Passage
from app.infrastructure.db.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.db.repositories.reference_documents import ReferenceDocumentRepository
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.lease import InMemoryModelLease
from app.infrastructure.originality.checker import OriginalityChecker
from app.infrastructure.vector.dedup import DedupService
from app.modules.ielts.writing.request import WritingGenerationSpec
from app.services.reading_quality import DedupPortAdapter, OriginalityPortAdapter
from app.workflows.context import ReadingGraphContext
from app.workflows.graphs.writing_graph import build_writing_graph
from app.workflows.writing_runner import build_initial_writing_state
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.helpers import create_org, create_user
from tests.integration.writing_mock_provider import WritingMockProvider


@pytest.mark.asyncio
async def test_writing_graph_completes_with_quality_gates(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run_id = uuid.uuid4()
    spec = WritingGenerationSpec(topic="Urban green spaces", question_type="opinion")
    run = GenerationRun(
        id=run_id,
        organization_id=org.id,
        module="writing",
        request={"module": "writing", "spec": spec.model_dump(mode="json")},
        status="queued",
        requested_by=user.id,
    )
    db_session.add(run)
    await db_session.commit()

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=WritingMockProvider(),
        session=db_session,
    )
    originality = OriginalityChecker(ReferenceDocumentRepository(db_session))
    await originality.load()
    dedup = DedupService(
        settings=Settings(llm_profile="fast"),
        gateway=gateway,
        embeddings=EmbeddingRepository(db_session, org.id),
    )
    graph = build_writing_graph(InMemorySaver())
    context = ReadingGraphContext(
        gateway=gateway,
        session=db_session,
        originality=OriginalityPortAdapter(originality),
        dedup=DedupPortAdapter(dedup),
    )
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = build_initial_writing_state(
        run_id=run_id,
        organization_id=org.id,
        spec=spec,
    )

    paused_state = await graph.ainvoke(
        initial_state,
        config=config,
        context=context,
        durability="sync",
    )
    assert paused_state.get("__interrupt__")
    assert paused_state.get("passage_version_id")
    assert paused_state["prompt_quality"]["passed"] is True
    assert paused_state["originality_report"]["passed"] is True
    assert paused_state["dedup_report"]["passed"] is True

    final_state = await graph.ainvoke(
        Command(resume={"decision": "approve", "reviewer_id": str(user.id)}),
        config=config,
        context=context,
        durability="sync",
    )

    assert final_state["status"] == "completed"
    assert final_state["task2_prompt"]["question_type"] == "opinion"

    passage = await db_session.get(Passage, uuid.UUID(final_state["passage_id"]))
    assert passage is not None
    assert passage.module == "writing"
    assert passage.status == "approved"

    count = await db_session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    assert count == 1
