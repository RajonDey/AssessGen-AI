"""Registry tests for item and set rules."""

from app.modules.ielts.reading.rules import (
    build_item_rule_registry,
    build_reading_rule_registry,
    build_set_rule_registry,
)


def test_item_registry_contains_expected_codes() -> None:
    codes = build_item_rule_registry().codes()
    assert "R-ITEM-001" in codes
    assert "R-COMP-001" in codes
    assert "R-HEAD-001" in codes


def test_set_registry_contains_expected_codes() -> None:
    codes = build_set_rule_registry().codes()
    assert "R-SET-001" in codes
    assert "R-SET-006" in codes


def test_reading_registry_has_all_families() -> None:
    codes = build_reading_rule_registry().codes()
    assert len(codes) == 34
