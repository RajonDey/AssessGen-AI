"""Run the Reading rule engine against calibration fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.modules.ielts.reading.calibration import run_calibration_from_repo


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate IELTS Reading MUST rules.")
    parser.add_argument(
        "--max-fp-rate",
        type=float,
        default=0.05,
        help="Maximum allowed false-positive rate (default: 0.05).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full calibration report as JSON.",
    )
    args = parser.parse_args()

    report = run_calibration_from_repo(_repo_root(), max_false_positive_rate=args.max_fp_rate)
    if args.json:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        pct = report.false_positive_rate * 100
        max_pct = report.max_allowed_rate * 100
        status = "PASS" if report.passed else "FAIL"
        print(
            f"Calibration {status}: {report.must_failures}/{report.rule_checks} MUST failures "
            f"({pct:.1f}% false-positive rate; limit {max_pct:.1f}%) "
            f"across {report.fixture_count} fixtures."
        )
        for failure in report.failures:
            print(f"  - {failure.fixture_id}: {failure.rule_code} — {failure.message}")

    results_dir = _repo_root() / "evals" / "calibration" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "reading-latest.json"
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
