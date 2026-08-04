"""Write benchmark reports to evals/benchmarks/results/."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from harness.schema import BenchmarkReport


def write_report(report: BenchmarkReport, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = results_dir / f"benchmark-{report.mode}-{stamp}.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    md_path = results_dir / f"benchmark-{report.mode}-{stamp}.md"
    lines = [
        "# Benchmark report",
        "",
        f"- Mode: `{report.mode}`",
        f"- Models: {', '.join(f'`{p}`' for p in report.model_profiles)}",
        f"- Generated: {report.generated_at.isoformat()}",
        "",
        "| Task | Model | Passed | Primary metric | Wall ms |",
        "|------|-------|--------|----------------|---------|",
    ]
    for row in report.summary_rows():
        lines.append(
            f"| {row['task']} | {row['model']} | {row['passed']} | "
            f"{row['primary_metric']:.2f} | {row['wall_time_ms']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path


def print_summary(report: BenchmarkReport) -> None:
    print(f"Benchmark complete ({report.mode} mode)")
    for row in report.summary_rows():
        status = "PASS" if row["passed"] else "FAIL"
        print(
            f"  [{status}] {row['task']} @ {row['model']} "
            f"metric={row['primary_metric']:.2f} time={row['wall_time_ms']}ms"
        )
