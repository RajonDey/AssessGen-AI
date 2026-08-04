"""Run the Phase 1D model benchmark harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AssessGen model benchmark harness")
    parser.add_argument(
        "--mode",
        choices=("mock", "live"),
        default="mock",
        help="mock runs deterministic tasks only; live requires Ollama (partial)",
    )
    parser.add_argument(
        "--models",
        default="fast,local",
        help="Comma-separated LLM profiles to compare (e.g. fast,local,local-hq)",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    evals_path = str(root / "evals")
    if evals_path not in sys.path:
        sys.path.insert(0, evals_path)

    from harness.report import print_summary, write_report
    from harness.runner import run_benchmark

    profiles = [part.strip() for part in args.models.split(",") if part.strip()]
    report = run_benchmark(repo_root=root, mode=args.mode, model_profiles=profiles)
    results_dir = root / "evals/benchmarks/results"
    output = write_report(report, results_dir)
    print_summary(report)
    print(f"Report written to {output}")
    failed = sum(1 for result in report.task_results if not result.passed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
