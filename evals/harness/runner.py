"""Benchmark task runner."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Literal

from harness.live_reading import run_live_reading_task
from harness.planted_defects import run_planted_defect_task
from harness.schema import BenchmarkReport, BenchmarkTask, TaskResult


def load_tasks(tasks_dir: Path) -> list[BenchmarkTask]:
    tasks: list[BenchmarkTask] = []
    for path in sorted(tasks_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        tasks.append(BenchmarkTask.model_validate(raw))
    return tasks


def run_mock_task(task: BenchmarkTask, *, model_profile: str, repo_root: Path) -> TaskResult:
    started = time.perf_counter()
    if task.kind == "planted_defect" and task.fixture_path:
        fixture = repo_root / task.fixture_path
        return run_planted_defect_task(
            fixture_path=fixture,
            model_profile=model_profile,
            mode="mock",
            task_id=task.id,
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return TaskResult(
        task_id=task.id,
        model_profile=model_profile,
        mode="mock",
        passed=True,
        wall_time_ms=elapsed_ms,
        notes=f"Mock stub — live LLM run not executed for {task.kind}",
    )


async def run_live_task_async(
    task: BenchmarkTask,
    *,
    model_profile: str,
    repo_root: Path,
) -> TaskResult:
    if task.kind == "planted_defect" and task.fixture_path:
        return run_planted_defect_task(
            fixture_path=repo_root / task.fixture_path,
            model_profile=model_profile,
            mode="live",
            task_id=task.id,
        )
    if task.kind == "generation" and task.module == "reading":
        return await run_live_reading_task(
            task=task,
            model_profile=model_profile,
            repo_root=repo_root,
        )

    started = time.perf_counter()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return TaskResult(
        task_id=task.id,
        model_profile=model_profile,
        mode="live",
        passed=False,
        wall_time_ms=elapsed_ms,
        notes=f"Live runner not implemented for {task.module}/{task.kind}",
    )


async def run_benchmark_async(
    *,
    repo_root: Path,
    mode: Literal["mock", "live"],
    model_profiles: list[str],
) -> BenchmarkReport:
    tasks_dir = repo_root / "evals/benchmarks/tasks"
    tasks = load_tasks(tasks_dir)
    report = BenchmarkReport(mode=mode, model_profiles=model_profiles)

    if mode == "mock":
        for profile in model_profiles:
            for task in tasks:
                report.task_results.append(
                    run_mock_task(task, model_profile=profile, repo_root=repo_root)
                )
        return report

    for profile in model_profiles:
        for task in tasks:
            report.task_results.append(
                await run_live_task_async(task, model_profile=profile, repo_root=repo_root)
            )
    return report


def run_benchmark(
    *,
    repo_root: Path,
    mode: Literal["mock", "live"],
    model_profiles: list[str],
) -> BenchmarkReport:
    return asyncio.run(
        run_benchmark_async(
            repo_root=repo_root,
            mode=mode,
            model_profiles=model_profiles,
        )
    )
