"""In-process LLM call ledger for cost visibility (dev / single-worker)."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Bucket:
    llm_calls: int = 0
    planner_calls: int = 0
    generator_calls: int = 0
    critic_calls: int = 0
    runs: int = 0


_lock = threading.Lock()
_by_module: dict[str, _Bucket] = defaultdict(_Bucket)


@dataclass
class CallCounter:
    """Mutable per-run counters passed through the pipeline."""

    llm_calls: int = 0
    planner_calls: int = 0
    generator_calls: int = 0
    critic_calls: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def add_planner(self, n: int = 1) -> None:
        self.planner_calls += n
        self.llm_calls += n

    def add_generator(self, n: int = 1) -> None:
        self.generator_calls += n
        self.llm_calls += n

    def add_critic(self, n: int = 1) -> None:
        self.critic_calls += n
        self.llm_calls += n

    def merge(self, other: CallCounter) -> None:
        self.llm_calls += other.llm_calls
        self.planner_calls += other.planner_calls
        self.generator_calls += other.generator_calls
        self.critic_calls += other.critic_calls


def record_run(module: str, counter: CallCounter) -> None:
    with _lock:
        b = _by_module[module]
        b.llm_calls += counter.llm_calls
        b.planner_calls += counter.planner_calls
        b.generator_calls += counter.generator_calls
        b.critic_calls += counter.critic_calls
        b.runs += 1


def snapshot() -> dict[str, Any]:
    with _lock:
        modules = {
            mod: {
                "runs": b.runs,
                "llm_calls": b.llm_calls,
                "planner_calls": b.planner_calls,
                "generator_calls": b.generator_calls,
                "critic_calls": b.critic_calls,
                "avg_llm_calls_per_run": round(b.llm_calls / b.runs, 2) if b.runs else 0,
            }
            for mod, b in sorted(_by_module.items())
        }
        total_calls = sum(b.llm_calls for b in _by_module.values())
        total_runs = sum(b.runs for b in _by_module.values())
        return {
            "modules": modules,
            "totals": {
                "runs": total_runs,
                "llm_calls": total_calls,
                "avg_llm_calls_per_run": round(total_calls / total_runs, 2) if total_runs else 0,
            },
        }


def reset() -> None:
    with _lock:
        _by_module.clear()
