"""Pydantic schemas for benchmark tasks and results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BenchmarkTask(BaseModel):
    id: str
    name: str
    module: str
    description: str
    kind: Literal["generation", "planted_defect", "rule_calibration"]
    fixture_path: str | None = None
    generation_spec: dict[str, Any] | None = None


class TaskMetric(BaseModel):
    name: str
    value: float
    unit: str = "ratio"
    detail: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    task_id: str
    model_profile: str
    mode: Literal["mock", "live"]
    passed: bool
    wall_time_ms: int
    metrics: list[TaskMetric] = Field(default_factory=list)
    notes: str | None = None


class BenchmarkReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    mode: Literal["mock", "live"]
    model_profiles: list[str]
    task_results: list[TaskResult] = Field(default_factory=list)

    def summary_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for result in self.task_results:
            primary = result.metrics[0].value if result.metrics else 0.0
            rows.append(
                {
                    "task": result.task_id,
                    "model": result.model_profile,
                    "mode": result.mode,
                    "passed": result.passed,
                    "primary_metric": primary,
                    "wall_time_ms": result.wall_time_ms,
                }
            )
        return rows
