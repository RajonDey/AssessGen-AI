"""Lightweight eval harness for skills + structural rules (Phase 3).

Usage (from repo root):
  cd backend && uv run python -m evals_runner

Or:
  make eval
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Allow running as ``python -m`` from backend/ with repo root on path
_BACKEND = Path(__file__).resolve().parent
_ROOT = _BACKEND.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.rules.structure import evaluate_structure  # noqa: E402

SAMPLES = {
    "reading": _ROOT / "docs" / "question" / "reading-01.json",
    "writing": _ROOT / "docs" / "question" / "writing-01.json",
    "listening": _ROOT / "docs" / "question" / "listening-01.json",
}

PLANTED = _ROOT / "evals" / "fixtures" / "planted"


@dataclass
class CaseResult:
    case_id: str
    module: str
    passed: bool
    must_findings: list[str]
    notes: str = ""


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_sample_cases() -> list[CaseResult]:
    results: list[CaseResult] = []
    for module, path in SAMPLES.items():
        content = _load_json(path)
        report = evaluate_structure(module, content)
        must = [f"[{f.code}] {f.message}" for f in report.findings if f.severity == "must"]
        # Samples are pattern references — they may lack answer_key/script; only musts fail
        results.append(
            CaseResult(
                case_id=f"sample-{module}",
                module=module,
                passed=report.passed,
                must_findings=must,
                notes=f"findings={len(report.findings)} path={path.name}",
            )
        )
    return results


def run_planted_cases() -> list[CaseResult]:
    results: list[CaseResult] = []
    if not PLANTED.is_dir():
        return results
    for path in sorted(PLANTED.glob("*.json")):
        raw = _load_json(path)
        module = str(raw.get("module") or "reading")
        expect_fail = bool(raw.get("expect_must_fail", True))
        content = raw.get("content") or {}
        report = evaluate_structure(module, content)
        must = [f"[{f.code}] {f.message}" for f in report.findings if f.severity == "must"]
        ok = (not report.passed) if expect_fail else report.passed
        results.append(
            CaseResult(
                case_id=path.stem,
                module=module,
                passed=ok,
                must_findings=must,
                notes=f"expect_must_fail={expect_fail}",
            )
        )
    return results


def main() -> int:
    cases = [*run_sample_cases(), *run_planted_cases()]
    failed = [c for c in cases if not c.passed]
    print(json.dumps({"cases": [asdict(c) for c in cases], "failed": len(failed)}, indent=2))
    for c in cases:
        status = "PASS" if c.passed else "FAIL"
        print(f"{status}  {c.case_id}  ({c.module})  {c.notes}")
        for m in c.must_findings:
            print(f"       must: {m}")
    if failed:
        print(f"\n{len(failed)}/{len(cases)} failed")
        return 1
    print(f"\nAll {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
