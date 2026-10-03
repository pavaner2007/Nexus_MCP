"""
tests/test_eval_dataset.py
===========================
Structural validation suite for app/testing/eval_dataset.py.

This does NOT run any routing — it purely checks that the dataset is
well-formed and ready for Phase 11 benchmark consumption.

Checks
------
1. FULL_EVAL_SET has exactly 53 entries.
2. Exactly 40 entries have expected_mode="single".
3. The 40 single-engine entries are evenly split: 8 per category across
   all 5 categories (shopping, scholar, local, patents, search).
4. Exactly 8 entries have expected_mode="dual".
5. Exactly 5 entries have expected_mode="fallback".
6. Zero overlap between FULL_EVAL_SET queries and SEED_PHRASES
   (normalized: lowercase, strip whitespace + trailing punctuation).
7. Every entry has:
   - a non-empty query string
   - a valid expected_mode in {"single", "dual", "fallback"}
   - appropriate category fields set per mode
8. Dual entries all have expected_dual_categories with exactly 2 items.
9. Fallback entries all have expected_category="search".
10. Single entries all have expected_category set (not None).
"""

from __future__ import annotations

import re
import string

import pytest

from app.testing.eval_dataset import (
    FULL_EVAL_SET,
    SHOPPING_CASES,
    SCHOLAR_CASES,
    LOCAL_CASES,
    PATENTS_CASES,
    SEARCH_CASES,
    DUAL_CASES,
    FALLBACK_CASES,
    TestCase,
)
from app.classifier.seed_data import SEED_PHRASES

# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

_STRIP_TRAILING = re.compile(r"[" + re.escape(string.punctuation) + r"\s]+$")


def _normalise(s: str) -> str:
    """Lowercase, strip whitespace, remove trailing punctuation."""
    return _STRIP_TRAILING.sub("", s.strip().lower())


# ---------------------------------------------------------------------------
# 1. Total count
# ---------------------------------------------------------------------------


def test_full_eval_set_has_53_entries():
    assert len(FULL_EVAL_SET) == 53, (
        f"Expected 53 entries, got {len(FULL_EVAL_SET)}"
    )


# ---------------------------------------------------------------------------
# 2–3. Single-engine counts
# ---------------------------------------------------------------------------


def test_exactly_40_single_entries():
    singles = [tc for tc in FULL_EVAL_SET if tc.expected_mode == "single"]
    assert len(singles) == 40, f"Expected 40 single entries, got {len(singles)}"


@pytest.mark.parametrize("category,cases", [
    ("shopping", SHOPPING_CASES),
    ("scholar",  SCHOLAR_CASES),
    ("local",    LOCAL_CASES),
    ("patents",  PATENTS_CASES),
    ("search",   SEARCH_CASES),
])
def test_eight_cases_per_category(category, cases):
    assert len(cases) == 8, (
        f"Expected 8 cases for category '{category}', got {len(cases)}"
    )


@pytest.mark.parametrize("category", ["shopping", "scholar", "local", "patents", "search"])
def test_single_entries_evenly_split_by_category(category):
    """Each category must have exactly 8 single-engine entries in FULL_EVAL_SET."""
    count = sum(
        1 for tc in FULL_EVAL_SET
        if tc.expected_mode == "single" and tc.expected_category == category
    )
    assert count == 8, (
        f"Expected 8 single entries for '{category}', found {count}"
    )


# ---------------------------------------------------------------------------
# 4. Dual count
# ---------------------------------------------------------------------------


def test_exactly_8_dual_entries():
    duals = [tc for tc in FULL_EVAL_SET if tc.expected_mode == "dual"]
    assert len(duals) == 8, f"Expected 8 dual entries, got {len(duals)}"


# ---------------------------------------------------------------------------
# 5. Fallback count
# ---------------------------------------------------------------------------


def test_exactly_5_fallback_entries():
    fallbacks = [tc for tc in FULL_EVAL_SET if tc.expected_mode == "fallback"]
    assert len(fallbacks) == 5, f"Expected 5 fallback entries, got {len(fallbacks)}"


# ---------------------------------------------------------------------------
# 6. Zero overlap with SEED_PHRASES
# ---------------------------------------------------------------------------


def test_no_overlap_with_seed_phrases():
    """
    Normalised FULL_EVAL_SET queries must not appear in normalised SEED_PHRASES.

    Normalisation: lowercase + strip trailing punctuation + strip whitespace.
    The 8 dual queries come from AMBIGUOUS_TEST_QUERIES which are already
    held-out from SEED_PHRASES by design — this test confirms that guarantee
    holds after any future edits.
    """
    seed_normalised: set[str] = set()
    for phrases in SEED_PHRASES.values():
        for p in phrases:
            seed_normalised.add(_normalise(p))

    overlaps: list[str] = []
    for tc in FULL_EVAL_SET:
        if _normalise(tc.query) in seed_normalised:
            overlaps.append(tc.query)

    assert overlaps == [], (
        f"Found {len(overlaps)} query/queries in FULL_EVAL_SET that overlap "
        f"with SEED_PHRASES:\n" + "\n".join(f"  - {q!r}" for q in overlaps)
    )


# ---------------------------------------------------------------------------
# 7. Per-entry field validity
# ---------------------------------------------------------------------------


VALID_MODES = {"single", "dual", "fallback"}


@pytest.mark.parametrize("tc", FULL_EVAL_SET, ids=[tc.query[:60] for tc in FULL_EVAL_SET])
def test_entry_has_non_empty_query(tc: TestCase):
    assert isinstance(tc.query, str) and tc.query.strip(), (
        f"Empty query in TestCase: {tc!r}"
    )


@pytest.mark.parametrize("tc", FULL_EVAL_SET, ids=[tc.query[:60] for tc in FULL_EVAL_SET])
def test_entry_has_valid_mode(tc: TestCase):
    assert tc.expected_mode in VALID_MODES, (
        f"Invalid mode {tc.expected_mode!r} for query {tc.query!r}"
    )


@pytest.mark.parametrize("tc", FULL_EVAL_SET, ids=[tc.query[:60] for tc in FULL_EVAL_SET])
def test_entry_has_appropriate_category_fields(tc: TestCase):
    if tc.expected_mode == "single":
        assert tc.expected_category is not None, (
            f"Single-mode entry missing expected_category: {tc.query!r}"
        )
        assert tc.expected_dual_categories is None, (
            f"Single-mode entry should not have expected_dual_categories: {tc.query!r}"
        )
    elif tc.expected_mode == "dual":
        assert tc.expected_dual_categories is not None, (
            f"Dual-mode entry missing expected_dual_categories: {tc.query!r}"
        )
    elif tc.expected_mode == "fallback":
        assert tc.expected_category == "search", (
            f"Fallback entry must have expected_category='search': {tc.query!r}"
        )


# ---------------------------------------------------------------------------
# 8. Dual entries have exactly 2 categories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tc", DUAL_CASES, ids=[tc.query[:60] for tc in DUAL_CASES])
def test_dual_entry_has_two_categories(tc: TestCase):
    assert isinstance(tc.expected_dual_categories, list), (
        f"expected_dual_categories must be a list: {tc.query!r}"
    )
    assert len(tc.expected_dual_categories) == 2, (
        f"Dual entry must list exactly 2 categories, got "
        f"{len(tc.expected_dual_categories)}: {tc.query!r}"
    )


# ---------------------------------------------------------------------------
# 9. Fallback entries have expected_category="search"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tc", FALLBACK_CASES, ids=[tc.query[:60] for tc in FALLBACK_CASES])
def test_fallback_entry_category_is_search(tc: TestCase):
    assert tc.expected_category == "search", (
        f"Fallback entry must have expected_category='search', "
        f"got {tc.expected_category!r}: {tc.query!r}"
    )


# ---------------------------------------------------------------------------
# 10. Single entries have expected_category set
# ---------------------------------------------------------------------------


SINGLE_CASES = [tc for tc in FULL_EVAL_SET if tc.expected_mode == "single"]


@pytest.mark.parametrize("tc", SINGLE_CASES, ids=[tc.query[:60] for tc in SINGLE_CASES])
def test_single_entry_has_expected_category(tc: TestCase):
    assert tc.expected_category is not None and tc.expected_category.strip(), (
        f"Single-mode entry must have a non-empty expected_category: {tc.query!r}"
    )


# ---------------------------------------------------------------------------
# 11. All queries are unique within FULL_EVAL_SET
# ---------------------------------------------------------------------------


def test_all_queries_unique():
    queries = [tc.query for tc in FULL_EVAL_SET]
    duplicates = [q for q in queries if queries.count(q) > 1]
    assert not duplicates, (
        f"Duplicate queries found in FULL_EVAL_SET: {list(set(duplicates))}"
    )
