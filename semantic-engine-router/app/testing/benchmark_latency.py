"""
app/testing/benchmark_latency.py
=================================
Phase 12B — End-to-end latency benchmark.

!!! WARNING: This script makes REAL SerpApi calls and consumes API quota. !!!
!!! Ensure SERPAPI_KEY is set in .env before running.                    !!!
!!! Default: 5 iterations x 3 modes = 15 live SerpApi requests.         !!!

Measures two distinct latency dimensions:

1. Classification overhead (no network I/O)
   -- classify_top() + decide_route() across 20 diverse queries
   -- Represents the pure routing cost added by this project

2. End-to-end latency (live SerpApi calls)
   -- classify_top -> decide_route -> execute_route for all 3 routing modes
   -- Single, Dual, Fallback — each run `iterations` times
   -- Reports min / mean / median / max in milliseconds

Usage
-----
    python -m app.testing.benchmark_latency
    python -m app.testing.benchmark_latency --iterations 3   # fewer SerpApi calls
"""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import Any

from app.classifier.centroids import load_centroids
from app.classifier.classify import classify_top
from app.routing.router import decide_route, execute_route

# ---------------------------------------------------------------------------
# 20 diverse queries for classification-only overhead measurement
# ---------------------------------------------------------------------------

_CLASSIFY_QUERIES: list[str] = [
    "buy Sony WH-1000XM5 headphones",
    "peer-reviewed papers on transformer self-attention",
    "best ramen restaurants near downtown Chicago",
    "patent for flexible OLED display hinge",
    "what is the capital of Portugal",
    "Samsung Galaxy S24 Ultra price comparison",
    "systematic review on intermittent fasting",
    "plumber available Saturday in Brooklyn",
    "prior art for solid-state battery cathode",
    "how does inflation work",
    "iPhone 15 Pro Max 256GB best deal",
    "citations for AlphaFold protein folding paper",
    "rooftop bar open late near Nashville",
    "Tesla patents on battery thermal management",
    "current weather in Mumbai",
    "ergonomic office chair under $500",
    "academic papers on federated learning privacy",
    "pediatric dentist near zip code 90210",
    "who invented the mRNA vaccine technology",
    "convert 1000 Indian rupees to USD",
]

# Representative queries for the three routing modes
_SINGLE_QUERY = "iPhone 15 price"
_DUAL_QUERY = "compare iPhone 15 prices with recent reviews"
_FALLBACK_QUERY = "what is the general weather during monsoon season in India"


# ---------------------------------------------------------------------------
# Helper: measure a list of wall-clock durations → stats dict
# ---------------------------------------------------------------------------


def _stats(durations_ms: list[float]) -> dict[str, float]:
    if not durations_ms:
        return {"min": 0, "mean": 0, "median": 0, "max": 0, "count": 0}
    return {
        "min": round(min(durations_ms), 1),
        "mean": round(statistics.mean(durations_ms), 1),
        "median": round(statistics.median(durations_ms), 1),
        "max": round(max(durations_ms), 1),
        "count": len(durations_ms),
    }


# ---------------------------------------------------------------------------
# Core async benchmark
# ---------------------------------------------------------------------------


async def run_latency_benchmark(iterations: int = 5) -> dict[str, Any]:
    """
    Run the full latency benchmark.

    Parameters
    ----------
    iterations:
        Number of end-to-end timed runs per routing mode (default 5).
        Each run makes one live SerpApi call.

    Returns
    -------
    dict with keys:
        classification_overhead_ms   dict (min/mean/median/max over 20 queries)
        single                       dict (min/mean/median/max over iterations)
        dual                         dict (min/mean/median/max over iterations)
        fallback                     dict (min/mean/median/max over iterations)
        meta                         dict (iterations, queries used, notes)
    """
    # ── Warmup: load centroids + one classification to eliminate cold-start skew ──
    centroids = load_centroids()
    classify_top("warmup query", centroids)

    # ── 1. Classification-only overhead (20 queries, no SerpApi) ──────────────
    classify_times: list[float] = []
    for q in _CLASSIFY_QUERIES:
        t0 = time.perf_counter()
        scores = classify_top(q, centroids, top_n=2)
        decide_route(scores)
        classify_times.append((time.perf_counter() - t0) * 1000)

    classify_stats = _stats(classify_times)

    # ── 2. End-to-end: single mode ────────────────────────────────────────────
    single_times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        scores = classify_top(_SINGLE_QUERY, centroids, top_n=2)
        decision = decide_route(scores)
        await execute_route(_SINGLE_QUERY, decision)
        single_times.append((time.perf_counter() - t0) * 1000)

    # ── 3. End-to-end: dual mode ──────────────────────────────────────────────
    dual_times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        scores = classify_top(_DUAL_QUERY, centroids, top_n=2)
        decision = decide_route(scores)
        await execute_route(_DUAL_QUERY, decision)
        dual_times.append((time.perf_counter() - t0) * 1000)

    # ── 4. End-to-end: fallback mode ─────────────────────────────────────────
    fallback_times: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        scores = classify_top(_FALLBACK_QUERY, centroids, top_n=2)
        decision = decide_route(scores)
        await execute_route(_FALLBACK_QUERY, decision)
        fallback_times.append((time.perf_counter() - t0) * 1000)

    return {
        "classification_overhead_ms": classify_stats,
        "single": _stats(single_times),
        "dual": _stats(dual_times),
        "fallback": _stats(fallback_times),
        "meta": {
            "iterations": iterations,
            "single_query": _SINGLE_QUERY,
            "dual_query": _DUAL_QUERY,
            "fallback_query": _FALLBACK_QUERY,
            "note": "End-to-end times include live SerpApi network latency.",
        },
    }


# ---------------------------------------------------------------------------
# CLI report
# ---------------------------------------------------------------------------


def _print_report(r: dict[str, Any]) -> None:
    meta = r["meta"]
    co = r["classification_overhead_ms"]

    print()
    print("=" * 72)
    print("  SEMANTIC ENGINE ROUTER -- LATENCY BENCHMARK  (Phase 12B)")
    print("=" * 72)
    print(f"  WARNING: This benchmark made real SerpApi calls.")
    print(f"  Iterations per mode : {meta['iterations']}")
    print("=" * 72)
    print()
    print("  [1] CLASSIFICATION-ONLY OVERHEAD  (20 queries, no SerpApi)")
    print(f"      Min    : {co['min']:>8.1f} ms")
    print(f"      Mean   : {co['mean']:>8.1f} ms")
    print(f"      Median : {co['median']:>8.1f} ms")
    print(f"      Max    : {co['max']:>8.1f} ms")
    print()

    for mode_key, label, query in [
        ("single", "[2] SINGLE-ENGINE", meta["single_query"]),
        ("dual",   "[3] DUAL-ENGINE",   meta["dual_query"]),
        ("fallback","[4] FALLBACK",      meta["fallback_query"]),
    ]:
        s = r[mode_key]
        print(f"  {label} end-to-end latency")
        print(f"      Query  : {query[:60]}")
        print(f"      Min    : {s['min']:>8.1f} ms")
        print(f"      Mean   : {s['mean']:>8.1f} ms")
        print(f"      Median : {s['median']:>8.1f} ms")
        print(f"      Max    : {s['max']:>8.1f} ms")
        print()

    print("=" * 72)
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _main(iterations: int = 5) -> None:
    import sys
    iters = iterations
    for arg in sys.argv[1:]:
        if arg.startswith("--iterations="):
            iters = int(arg.split("=")[1])
        elif arg == "--iterations" and len(sys.argv) > sys.argv.index(arg) + 1:
            iters = int(sys.argv[sys.argv.index(arg) + 1])

    print(f"\n  Running latency benchmark ({iters} iterations x 3 modes)...")
    print("  WARNING: This will make real SerpApi calls and consume quota!\n")
    result = await run_latency_benchmark(iterations=iters)
    _print_report(result)


if __name__ == "__main__":
    asyncio.run(_main())
