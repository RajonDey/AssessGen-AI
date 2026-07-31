"""Reading graph integration tests."""

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
from app.domain.enums import PassageSourceMode
from app.modules.ielts.reading.request import ReadingGenerationSpec
from app.services.reading_quality import DedupPortAdapter, OriginalityPortAdapter
from app.workflows.context import ReadingGraphContext
from app.workflows.graphs.reading_graph import build_reading_graph
from app.workflows.reading_runner import build_initial_reading_state
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_service import ExportService
from tests.integration.helpers import create_org, create_user
from tests.integration.reading_mock_provider import ReadingMockProvider, long_passage_body


@pytest.mark.asyncio
async def test_reading_graph_completes_with_quality_gates(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run_id = uuid.uuid4()
    run = GenerationRun(
        id=run_id,
        organization_id=org.id,
        module="reading",
        request={
            "module": "reading",
            "spec": ReadingGenerationSpec(topic="Urban farms", question_count=1).model_dump(
                mode="json"
            ),
        },
        status="queued",
        requested_by=user.id,
    )
    db_session.add(run)
    await db_session.commit()

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=ReadingMockProvider(),
        session=db_session,
    )
    originality = OriginalityChecker(ReferenceDocumentRepository(db_session))
    await originality.load()
    dedup = DedupService(
        settings=Settings(llm_profile="fast"),
        gateway=gateway,
        embeddings=EmbeddingRepository(db_session, org.id),
    )
    graph = build_reading_graph(InMemorySaver())
    context = ReadingGraphContext(
        gateway=gateway,
        session=db_session,
        originality=OriginalityPortAdapter(originality),
        dedup=DedupPortAdapter(dedup),
    )
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = build_initial_reading_state(
        run_id=run_id,
        organization_id=org.id,
        spec=ReadingGenerationSpec(topic="Urban farms", question_count=1),
    )

    paused_state = await graph.ainvoke(
        initial_state,
        config=config,
        context=context,
        durability="sync",
    )
    assert paused_state.get("__interrupt__")
    assert paused_state.get("passage_version_id")
    assert paused_state["critic_output"]["findings"] == []

    final_state = await graph.ainvoke(
        Command(resume={"decision": "approve", "reviewer_id": str(user.id)}),
        config=config,
        context=context,
        durability="sync",
    )

    assert final_state["status"] == "completed"
    assert final_state["passage"]
    assert len(final_state["items"]) == 1
    assert final_state["passage_quality"]["passed"] is True
    assert final_state["originality_report"]["passed"] is True
    assert final_state["dedup_report"]["passed"] is True
    assert final_state["item_quality"]["passed"] is True

    passage = await db_session.get(Passage, uuid.UUID(final_state["passage_id"]))
    assert passage is not None
    assert passage.status == "approved"

    export = await ExportService(db_session).export_reading_run(
        run_id=run_id,
        organization_id=org.id,
        publish=True,
    )
    assert export["passage_count"] == 1
    assert export["question_count"] == 1
    await db_session.refresh(passage)
    assert passage.status == "published"

    count = await db_session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    assert count == 5

    history = [state async for state in graph.aget_state_history(config)]
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_reading_graph_ingested_source_completes(db_session: AsyncSession) -> None:
    org = await create_org(db_session)
    user = await create_user(db_session, org)
    run_id = uuid.uuid4()
    source_text = f"{long_passage_body()}\n\nSecond paragraph with supporting detail."
    spec = ReadingGenerationSpec(
        topic="Urban farms",
        question_count=1,
        source_mode=PassageSourceMode.INGESTED,
        source_text=source_text,
    )
    run = GenerationRun(
        id=run_id,
        organization_id=org.id,
        module="reading",
        request={"module": "reading", "spec": spec.model_dump(mode="json")},
        status="queued",
        requested_by=user.id,
    )
    db_session.add(run)
    await db_session.commit()

    gateway = LLMGateway(
        settings=Settings(llm_profile="fast"),
        lease=InMemoryModelLease(),
        provider=ReadingMockProvider(),
        session=db_session,
    )
    originality = OriginalityChecker(ReferenceDocumentRepository(db_session))
    await originality.load()
    dedup = DedupService(
        settings=Settings(llm_profile="fast"),
        gateway=gateway,
        embeddings=EmbeddingRepository(db_session, org.id),
    )
    graph = build_reading_graph(InMemorySaver())
    context = ReadingGraphContext(
        gateway=gateway,
        session=db_session,
        originality=OriginalityPortAdapter(originality),
        dedup=DedupPortAdapter(dedup),
    )
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = build_initial_reading_state(
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
    assert paused_state.get("status") != "failed"

    final_state = await graph.ainvoke(
        Command(resume={"decision": "approve", "reviewer_id": str(user.id)}),
        config=config,
        context=context,
        durability="sync",
    )
    assert final_state["status"] == "completed"
    assert final_state["passage"]["title"]
