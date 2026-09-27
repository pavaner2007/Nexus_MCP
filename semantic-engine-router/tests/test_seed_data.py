"""
tests/test_seed_data.py
=======================
Structural validation for SEED_PHRASES and AMBIGUOUS_TEST_QUERIES.

These tests do NOT evaluate semantic quality — they enforce the
hard structural contracts the Phase 2 classifier training pipeline
will depend on.
"""

import pytest

from app.classifier.seed_data import AMBIGUOUS_TEST_QUERIES, SEED_PHRASES

# The exact set of engine keys that must be present.
REQUIRED_KEYS = {"shopping", "scholar", "local", "patents", "search"}

# Minimum number of seed phrases per category.
MIN_PHRASES_PER_CATEGORY = 40

# Minimum number of held-out ambiguous queries.
MIN_AMBIGUOUS_QUERIES = 8


class TestSeedPhrasesStructure:
    """Validate the SEED_PHRASES constant structure and contents."""

    def test_seed_phrases_is_dict(self) -> None:
        """SEED_PHRASES must be a dict."""
        assert isinstance(SEED_PHRASES, dict), (
            f"SEED_PHRASES should be a dict, got {type(SEED_PHRASES)}"
        )

    def test_seed_phrases_has_exactly_five_keys(self) -> None:
        """SEED_PHRASES must have exactly 5 top-level keys."""
        assert len(SEED_PHRASES) == 5, (
            f"Expected 5 keys, got {len(SEED_PHRASES)}: {set(SEED_PHRASES.keys())}"
        )

    def test_seed_phrases_has_required_keys(self) -> None:
        """SEED_PHRASES must contain exactly the required engine keys."""
        assert set(SEED_PHRASES.keys()) == REQUIRED_KEYS, (
            f"Key mismatch.\n"
            f"  Missing: {REQUIRED_KEYS - set(SEED_PHRASES.keys())}\n"
            f"  Extra:   {set(SEED_PHRASES.keys()) - REQUIRED_KEYS}"
        )

    @pytest.mark.parametrize("key", sorted(REQUIRED_KEYS))
    def test_each_category_value_is_list(self, key: str) -> None:
        """Every category value must be a list."""
        assert isinstance(SEED_PHRASES[key], list), (
            f"SEED_PHRASES['{key}'] should be a list, got {type(SEED_PHRASES[key])}"
        )

    @pytest.mark.parametrize("key", sorted(REQUIRED_KEYS))
    def test_each_category_has_minimum_phrases(self, key: str) -> None:
        """Every category must have at least MIN_PHRASES_PER_CATEGORY entries."""
        count = len(SEED_PHRASES[key])
        assert count >= MIN_PHRASES_PER_CATEGORY, (
            f"SEED_PHRASES['{key}'] has only {count} phrases "
            f"(minimum is {MIN_PHRASES_PER_CATEGORY})"
        )

    @pytest.mark.parametrize("key", sorted(REQUIRED_KEYS))
    def test_all_phrases_are_non_empty_strings(self, key: str) -> None:
        """All phrases in every category must be non-empty strings."""
        for idx, phrase in enumerate(SEED_PHRASES[key]):
            assert isinstance(phrase, str) and phrase.strip(), (
                f"SEED_PHRASES['{key}'][{idx}] is not a non-empty string: {phrase!r}"
            )

    @pytest.mark.parametrize("key", sorted(REQUIRED_KEYS))
    def test_no_duplicate_phrases_within_category(self, key: str) -> None:
        """Duplicate phrases within the same category indicate a copy-paste error."""
        phrases = SEED_PHRASES[key]
        seen: set[str] = set()
        duplicates = []
        for phrase in phrases:
            lower = phrase.strip().lower()
            if lower in seen:
                duplicates.append(phrase)
            seen.add(lower)
        assert not duplicates, (
            f"Duplicate phrases found in SEED_PHRASES['{key}']: {duplicates}"
        )


class TestAmbiguousTestQueries:
    """Validate the AMBIGUOUS_TEST_QUERIES held-out list."""

    def test_ambiguous_queries_is_list(self) -> None:
        """AMBIGUOUS_TEST_QUERIES must be a list."""
        assert isinstance(AMBIGUOUS_TEST_QUERIES, list), (
            f"AMBIGUOUS_TEST_QUERIES should be a list, "
            f"got {type(AMBIGUOUS_TEST_QUERIES)}"
        )

    def test_ambiguous_queries_minimum_count(self) -> None:
        """AMBIGUOUS_TEST_QUERIES must have at least MIN_AMBIGUOUS_QUERIES entries."""
        count = len(AMBIGUOUS_TEST_QUERIES)
        assert count >= MIN_AMBIGUOUS_QUERIES, (
            f"AMBIGUOUS_TEST_QUERIES has only {count} entries "
            f"(minimum is {MIN_AMBIGUOUS_QUERIES})"
        )

    def test_all_ambiguous_queries_are_non_empty_strings(self) -> None:
        """Every entry in AMBIGUOUS_TEST_QUERIES must be a non-empty string."""
        for idx, query in enumerate(AMBIGUOUS_TEST_QUERIES):
            assert isinstance(query, str) and query.strip(), (
                f"AMBIGUOUS_TEST_QUERIES[{idx}] is not a non-empty string: {query!r}"
            )

    def test_no_overlap_with_seed_phrases(self) -> None:
        """Held-out queries must NOT appear in SEED_PHRASES (they are test-only)."""
        all_seed = {
            phrase.strip().lower()
            for phrases in SEED_PHRASES.values()
            for phrase in phrases
        }
        leaks = [
            q for q in AMBIGUOUS_TEST_QUERIES
            if q.strip().lower() in all_seed
        ]
        assert not leaks, (
            f"These AMBIGUOUS_TEST_QUERIES also appear in SEED_PHRASES (data leak!): "
            f"{leaks}"
        )
