"""Live Reading generation tasks for the benchmark harness."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx
from app.config import Settings
from app.domain.enums import PassageSourceMode
from app.infrastructure.db.models import GenerationRun, Organization, User
from app.infrastructure.db.repositories.embedding_repository import EmbeddingRepository
from app.infrastructure.db.repositories.reference_documents import ReferenceDocumentRepository
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.llm.factory import build_llm_gateway
from app.infrastructure.llm.profiles import ProfileName
from app.infrastructure.originality.checker import OriginalityChecker
from app.infrastructure.vector.dedup import DedupService
from app.modules.ielts.reading.request import ReadingGenerationSpec
from app.services.reading_quality import DedupPortAdapter, OriginalityPortAdapter
from app.workflows.context import ReadingGraphContext
from app.workflows.graphs.reading_graph import build_reading_graph
from app.workflows.reading_runner import build_initial_reading_state
from harness.schema import BenchmarkTask, TaskMetric, TaskResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _build_reading_spec(task: BenchmarkTask, repo_root: Path) -> ReadingGenerationSpec:
    raw = dict(task.generation_spec or {})
    if task.fixture_path and raw.get("source_mode") == PassageSourceMode.INGESTED.value:
        fixture = repo_root / task.fixture_path
        raw["source_text"] = fixture.read_text(encoding="utf-8").strip()
    return ReadingGenerationSpec.model_validate(raw)


async def _ollama_reachable(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def _database_reachable(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _create_benchmark_actor(session: AsyncSession) -> tuple[Organization, User]:
    org = Organization(
        id=uuid.uuid4(),
        slug=f"benchmark-{uuid.uuid4().hex[:10]}",
        name="Benchmark Org",
    )
    user = User(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=f"benchmark-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="benchmark",
        role="admin",
        is_active=True,
    )
    session.add(org)
    session.add(user)
    await session.flush()
    return org, user


async def run_live_reading_task(
    *,
    task: BenchmarkTask,
    model_profile: str,
    repo_root: Path,
) -> TaskResult:
    """Run one Reading graph end-to-end with dev_mode and auto-approve."""
    started = time.perf_counter()
    settings = Settings(llm_profile=model_profile)  # type: ignore[arg-type]

    if not await _ollama_reachable(settings.ollama_base_url):
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return TaskResult(
            task_id=task.id,
            model_profile=model_profile,
            mode="live",
            passed=False,
            wall_time_ms=elapsed_ms,
            notes=f"Ollama unreachable at {settings.ollama_base_url}",
        )

    try:
        spec = _build_reading_spec(task, repo_root)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return TaskResult(
            task_id=task.id,
            model_profile=model_profile,
            mode="live",
            passed=False,
            wall_time_ms=elapsed_ms,
            notes=f"Invalid generation spec: {exc}",
        )

    async with async_session_factory() as session:
        if not await _database_reachable(session):
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return TaskResult(
                task_id=task.id,
                model_profile=model_profile,
                mode="live",
                passed=False,
                wall_time_ms=elapsed_ms,
                notes="Database unreachable — start the dev stack (`make dev`) and run migrations",
            )

        org, user = await _create_benchmark_actor(session)
        run_id = uuid.uuid4()
        run = GenerationRun(
            id=run_id,
            organization_id=org.id,
            module="reading",
            request={"module": "reading", "spec": spec.model_dump(mode="json")},
            status="queued",
            requested_by=user.id,
        )
        session.add(run)
        await session.commit()

        gateway = build_llm_gateway(settings=settings, session=session, redis=None)
        originality = OriginalityChecker(ReferenceDocumentRepository(session))
        await originality.load()
        dedup = DedupService(
            settings=settings,
            gateway=gateway,
            embeddings=EmbeddingRepository(session, org.id),
        )
        graph = build_reading_graph(InMemorySaver())
        context = ReadingGraphContext(
            gateway=gateway,
            session=session,
            originality=OriginalityPortAdapter(originality),
            dedup=DedupPortAdapter(dedup),
        )
        config: dict[str, Any] = {"configurable": {"thread_id": str(run_id)}}
        initial_state = build_initial_reading_state(
            run_id=run_id,
            organization_id=org.id,
            spec=spec,
        )

        try:
            paused_state = await graph.ainvoke(
                initial_state,
                config=config,
                context=context,
                durability="sync",
            )
            if paused_state.get("status") == "failed" or paused_state.get("error"):
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return TaskResult(
                    task_id=task.id,
                    model_profile=model_profile,
                    mode="live",
                    passed=False,
                    wall_time_ms=elapsed_ms,
                    metrics=[
                        TaskMetric(
                            name="quality_gate_pass",
                            value=0.0,
                            detail={"status": paused_state.get("status"), "error": paused_state.get("error")},
                        )
                    ],
                    notes=str(paused_state.get("error") or paused_state.get("status")),
                )

            if paused_state.get("__interrupt__"):
                final_state = await graph.ainvoke(
                    Command(resume={"decision": "approve", "reviewer_id": str(user.id)}),
                    config=config,
                    context=context,
                    durability="sync",
                )
            else:
                final_state = paused_state
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return TaskResult(
                task_id=task.id,
                model_profile=model_profile,
                mode="live",
                passed=False,
                wall_time_ms=elapsed_ms,
                notes=f"Graph execution failed: {exc}",
            )

        completed = final_state.get("status") == "completed"
        items = final_state.get("items") or []
        passage = final_state.get("passage") or {}
        word_count = len(str(passage.get("body", "")).split())
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return TaskResult(
            task_id=task.id,
            model_profile=model_profile,
            mode="live",
            passed=completed,
            wall_time_ms=elapsed_ms,
            metrics=[
                TaskMetric(
                    name="quality_gate_pass",
                    value=1.0 if completed else 0.0,
                    detail={
                        "status": final_state.get("status"),
                        "item_count": len(items),
                        "passage_word_count": word_count,
                        "profile": model_profile,
                    },
                )
            ],
            notes=None if completed else str(final_state.get("error") or final_state.get("status")),
        )


def run_live_reading_task_sync(
    *,
    task: BenchmarkTask,
    model_profile: ProfileName | str,
    repo_root: Path,
) -> TaskResult:
    import asyncio

    return asyncio.run(
        run_live_reading_task(task=task, model_profile=str(model_profile), repo_root=repo_root)
    )
