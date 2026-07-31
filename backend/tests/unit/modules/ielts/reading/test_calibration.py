"""Reading calibration harness tests."""

from __future__ import annotations

from pathlib import Path

from app.modules.ielts.reading.calibration import (
    built_in_fixtures,
    discover_fixtures,
    run_calibration,
)


def test_built_in_fixtures_pass_calibration() -> None:
    fixtures = built_in_fixtures()
    report = run_calibration(fixtures, sources=["builtin"])
    assert report.fixture_count == len(fixtures)
    assert report.rule_checks > 0
    assert report.must_failures == 0
    assert report.passed is True


def test_discover_fixtures_includes_builtin() -> None:
    repo_root = Path(__file__).resolve().parents[6]
    fixtures, sources = discover_fixtures(repo_root)
    assert len(fixtures) >= 2
    assert "builtin" in sources
