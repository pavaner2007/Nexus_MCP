"""
tests/test_benchmark_accuracy.py
==================================
Structural tests for app/testing/benchmark_accuracy.py.

These tests verify the benchmark RUNS correctly and returns a well-formed
result dict.  They do NOT assert a specific accuracy score — the real
numbers are output by the CLI report.

No SerpApi calls are made.  The only I/O is loading / building the
cached centroid file via load_centroids() (a local filesystem operation).
"""

from __future__ import annotations

import pytest

from app.testing.benchmark_accuracy import run_accuracy_benchmark
from app.testing.eval_dataset import FULL_EVAL_SET


@pytest.fixture(scope="module")
def result():
    """Run benchmark once and share result across all tests in this module."""
    return run_accuracy_benchmark()


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------


def test_result_has_required_keys(result):
    assert "overall_accuracy" in result
    assert "per_category" in result
    assert "misses" in result
    assert "meta" in result
    assert "total" in result
    assert "total_correct" in result


def test_overall_accuracy_is_float(result):
    assert isinstance(result["overall_accuracy"], float)


def test_overall_accuracy_in_valid_range(result):
    assert 0.0 <= result["overall_accuracy"] <= 100.0


def test_per_category_is_dict(result):
    assert isinstance(result["per_category"], dict)


def test_misses_is_list(result):
    assert isinstance(result["misses"], list)


# ---------------------------------------------------------------------------
# Accounting integrity
# ---------------------------------------------------------------------------


def test_correct_plus_wrong_equals_total(result):
    """All correct counts across categories must sum to total_correct."""
    summed_correct = sum(c["correct"] for c in result["per_category"].values())
    assert summed_correct == result["total_correct"]


def test_misses_plus_correct_equals_dataset_size(result):
    """len(misses) + total_correct == 53 (size of FULL_EVAL_SET)."""
    assert len(result["misses"]) + result["total_correct"] == len(FULL_EVAL_SET)


def test_total_matches_eval_set_size(result):
    assert result["total"] == len(FULL_EVAL_SET) == 53


def test_per_category_totals_sum_to_53(result):
    total_from_cats = sum(s["total"] for s in result["per_category"].values())
    assert total_from_cats == 53


# ---------------------------------------------------------------------------
# Per-category structure
# ---------------------------------------------------------------------------


def test_per_category_has_expected_keys(result):
    for label, stats in result["per_category"].items():
        assert "total" in stats, f"Missing 'total' for label {label!r}"
        assert "correct" in stats, f"Missing 'correct' for label {label!r}"
        assert "wrong" in stats, f"Missing 'wrong' for label {label!r}"
        assert "accuracy" in stats, f"Missing 'accuracy' for label {label!r}"


def test_per_category_accuracy_values_in_range(result):
    for label, stats in result["per_category"].items():
        assert 0.0 <= stats["accuracy"] <= 100.0, (
            f"Accuracy out of range for {label!r}: {stats['accuracy']}"
        )


def test_per_category_correct_plus_wrong_equals_total(result):
    for label, stats in result["per_category"].items():
        assert stats["correct"] + stats["wrong"] == stats["total"], (
            f"Correct + wrong != total for {label!r}"
        )


# ---------------------------------------------------------------------------
# Miss structure
# ---------------------------------------------------------------------------


def test_miss_entries_have_required_fields(result):
    required = {"query", "expected_mode", "expected", "actual_mode", "actual", "top_scores"}
    for m in result["misses"]:
        missing = required - m.keys()
        assert not missing, f"Miss entry missing fields {missing}: {m['query']!r}"


def test_miss_actual_is_list(result):
    for m in result["misses"]:
        assert isinstance(m["actual"], list), (
            f"'actual' must be a list in miss: {m['query']!r}"
        )


def test_miss_top_scores_is_list(result):
    for m in result["misses"]:
        assert isinstance(m["top_scores"], list), (
            f"'top_scores' must be a list in miss: {m['query']!r}"
        )


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def test_meta_has_timing(result):
    assert result["meta"]["elapsed_s"] >= 0.0


def test_meta_has_thresholds(result):
    assert "MIN_CONFIDENCE_THRESHOLD" in result["meta"]
    assert "DUAL_ROUTE_THRESHOLD" in result["meta"]
