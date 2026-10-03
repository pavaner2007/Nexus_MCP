"""
app/testing/benchmark_accuracy.py
===================================
Phase 11 — Routing-accuracy benchmark.

Runs every TestCase in FULL_EVAL_SET through the real classifier + router
pipeline (``classify_top`` → ``decide_route``) and compares the actual
routing decision against the hand-labeled expected outcome.

No SerpApi calls are made.  The only external I/O is loading the cached
centroid vectors from ``app/classifier/centroids.npz`` (or building them
from seed phrases on a cold start using the local embedding model).

Scoring rules
-------------
single   Correct iff actual_mode == "single"
           AND actual_categories[0] == expected_category
dual     Correct iff actual_mode == "dual"
           AND (expected_dual_categories is None
                OR set(actual_categories) == set(expected_dual_categories))
fallback Correct iff actual_mode == "fallback"

Usage
-----
    python -m app.testing.benchmark_accuracy

    # or from the project root:
    .venv/Scripts/python -m app.testing.benchmark_accuracy
"""

from __future__ import annotations

import time
from typing import Any

from app.classifier.centroids import load_centroids
from app.classifier.classify import classify_top
from app.routing.router import MIN_CONFIDENCE_THRESHOLD, DUAL_ROUTE_THRESHOLD, decide_route
from app.testing.eval_dataset import FULL_EVAL_SET, TestCase


# ---------------------------------------------------------------------------
# Core benchmark function
# ---------------------------------------------------------------------------


def _is_correct(tc: TestCase, actual_mode: str, actual_categories: list[str]) -> bool:
    """Return True if the routing decision matches the hand-labeled expectation."""
    if tc.expected_mode == "single":
        return (
            actual_mode == "single"
            and bool(actual_categories)
            and actual_categories[0] == tc.expected_category
        )
    if tc.expected_mode == "dual":
        if actual_mode != "dual":
            return False
        if tc.expected_dual_categories is None:
            return True  # any dual outcome is acceptable
        return set(actual_categories) == set(tc.expected_dual_categories)
    if tc.expected_mode == "fallback":
        return actual_mode == "fallback"
    return False


def _expected_label(tc: TestCase) -> str | list:
    """Human-readable expected label for the miss report."""
    if tc.expected_mode == "dual":
        return tc.expected_dual_categories or ["(any dual)"]
    return tc.expected_category or tc.expected_mode


def run_accuracy_benchmark() -> dict[str, Any]:
    """
    Execute the accuracy benchmark against FULL_EVAL_SET.

    Returns
    -------
    dict with keys:
        overall_accuracy  float  percentage 0.0 – 100.0
        per_category      dict   per-label accuracy breakdown
        misses            list   failed test cases with diagnostic info
        meta              dict   threshold values + timing
    """
    t0 = time.perf_counter()

    # ── 1. Load classifier centroids (fast if cached) ─────────────────────
    centroids = load_centroids()

    # ── 2. Iterate FULL_EVAL_SET ──────────────────────────────────────────
    # Accumulate per-label stats.  Labels are expected_mode for dual/fallback
    # and expected_category for single cases.
    label_stats: dict[str, dict[str, int]] = {}

    misses: list[dict[str, Any]] = []

    for tc in FULL_EVAL_SET:
        # Classify
        scores = classify_top(tc.query, centroids, top_n=2)
        decision = decide_route(scores)

        actual_mode: str = decision["mode"]
        actual_categories: list[str] = decision["categories"]

        correct = _is_correct(tc, actual_mode, actual_categories)

        # Determine the label bucket for per-category stats
        if tc.expected_mode == "single":
            label = tc.expected_category or "unknown"
        else:
            label = tc.expected_mode  # "dual" or "fallback"

        if label not in label_stats:
            label_stats[label] = {"total": 0, "correct": 0}
        label_stats[label]["total"] += 1
        if correct:
            label_stats[label]["correct"] += 1
        else:
            misses.append(
                {
                    "query": tc.query,
                    "expected_mode": tc.expected_mode,
                    "expected": _expected_label(tc),
                    "actual_mode": actual_mode,
                    "actual": actual_categories,
                    "top_scores": scores,
                    "notes": tc.notes,
                }
            )

    # ── 3. Compute summary stats ──────────────────────────────────────────
    total = len(FULL_EVAL_SET)
    total_correct = sum(s["correct"] for s in label_stats.values())
    overall_accuracy = round(total_correct / total * 100, 1) if total else 0.0

    per_category: dict[str, dict[str, Any]] = {}
    for label, stats in label_stats.items():
        acc = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] else 0.0
        per_category[label] = {
            "total": stats["total"],
            "correct": stats["correct"],
            "wrong": stats["total"] - stats["correct"],
            "accuracy": acc,
        }

    elapsed = round(time.perf_counter() - t0, 3)

    return {
        "overall_accuracy": overall_accuracy,
        "total": total,
        "total_correct": total_correct,
        "per_category": per_category,
        "misses": misses,
        "meta": {
            "MIN_CONFIDENCE_THRESHOLD": MIN_CONFIDENCE_THRESHOLD,
            "DUAL_ROUTE_THRESHOLD": DUAL_ROUTE_THRESHOLD,
            "elapsed_s": elapsed,
        },
    }


# ---------------------------------------------------------------------------
# Console report formatter
# ---------------------------------------------------------------------------

_COL = 58   # query truncation width
_SEP = "-" * 72


def _print_report(result: dict[str, Any]) -> None:
    meta = result["meta"]
    per_category = result["per_category"]
    misses = result["misses"]

    # ── Header ─────────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  SEMANTIC ENGINE ROUTER -- ROUTING ACCURACY BENCHMARK  (Phase 11)")
    print("=" * 72)
    print(f"  Overall accuracy : {result['overall_accuracy']:.1f}%  "
          f"({result['total_correct']}/{result['total']} correct)")
    print(f"  MIN_CONFIDENCE   : {meta['MIN_CONFIDENCE_THRESHOLD']}")
    print(f"  DUAL_THRESHOLD   : {meta['DUAL_ROUTE_THRESHOLD']}")
    print(f"  Elapsed          : {meta['elapsed_s']:.3f} s")
    print("=" * 72)

    # ── Per-category table ─────────────────────────────────────────────────
    print()
    print(f"  {'Label':<12} {'Total':>6} {'Correct':>8} {'Wrong':>6} {'Accuracy':>9}")
    print(f"  {_SEP[:64]}")

    # Fixed display order
    order = ["shopping", "scholar", "local", "patents", "search", "dual", "fallback"]
    for label in order:
        if label not in per_category:
            continue
        s = per_category[label]
        bar = "[OK]" if s["accuracy"] == 100.0 else ("[~~]" if s["accuracy"] >= 75.0 else "[!!]")
        print(
            f"  {label:<12} {s['total']:>6} {s['correct']:>8} {s['wrong']:>6} "
            f"{s['accuracy']:>8.1f}%  {bar}"
        )

    print()

    # ── Misses ─────────────────────────────────────────────────────────────
    if not misses:
        print("  No misclassifications -- perfect score!")
    else:
        print(f"  MISSES ({len(misses)} total)")
        print(f"  {_SEP}")
        for i, m in enumerate(misses, 1):
            q = m["query"][:_COL] + ("…" if len(m["query"]) > _COL else "")
            expected = (
                "+".join(m["expected"]) if isinstance(m["expected"], list) else m["expected"]
            )
            actual = "+".join(m["actual"])
            print(f"\n  [{i:02d}] {q}")
            print(f"       Expected : {m['expected_mode']}/{expected}")
            print(f"       Actual   : {m['actual_mode']}/{actual}")

            # Print top-2 scores
            scores_sorted = sorted(m["top_scores"], key=lambda x: x[1], reverse=True)
            score_str = "  ".join(f"{cat}={sc:.3f}" for cat, sc in scores_sorted)
            print(f"       Scores   : {score_str}")

            if m["notes"]:
                note_safe = m["notes"].encode("ascii", errors="replace").decode("ascii")
                note_short = note_safe[:120] + ("..." if len(note_safe) > 120 else "")
                print(f"       Notes    : {note_short}")

    print()
    print("=" * 72)
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    result = run_accuracy_benchmark()
    _print_report(result)
