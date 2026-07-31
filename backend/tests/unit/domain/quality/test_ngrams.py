"""Unit tests for 8-gram originality utilities."""

from app.domain.quality.common.ngrams import (
    build_ngrams,
    find_forbidden_overlap,
    normalize_for_ngrams,
)


def test_normalize_collapses_whitespace_and_case() -> None:
    assert normalize_for_ngrams("  Hello, WORLD!  ") == "hello world"


def test_build_ngrams_requires_eight_words() -> None:
    short = build_ngrams("one two three four five six seven")
    assert not short
    long = build_ngrams(" ".join(f"word{i}" for i in range(10)))
    assert len(long) == 3


def test_find_forbidden_overlap_detects_match() -> None:
    text = " ".join(f"token{i}" for i in range(12))
    forbidden = build_ngrams(text)
    overlap = find_forbidden_overlap(text, forbidden)
    assert overlap is not None


def test_allowed_source_ngrams_are_permitted() -> None:
    source = " ".join(f"licensed{i}" for i in range(12))
    generated = f"{source} extra words appended for uniqueness beyond source"
    forbidden = build_ngrams(source)
    allowed = build_ngrams(source)
    overlap = find_forbidden_overlap(generated, forbidden, allowed=allowed)
    assert overlap is None
