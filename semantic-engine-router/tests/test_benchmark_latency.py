"""
tests/test_benchmark_latency.py
=================================
Mocked smoke tests for app/testing/benchmark_latency.py.

All SerpApi calls are patched — no network I/O, no quota consumed.
Tests verify that run_latency_benchmark() executes, aggregates stats
correctly, and returns a well-formed result dictionary.
"""

from __future__ import annotations

import asyncio
import pytest

from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN = asyncio.get_event_loop().run_until_complete


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _fake_engine_response(engine: str = "shopping") -> EngineResponse:
    return EngineResponse(
        success=True,
        engine=engine,
        result_count=2,
        results=[
            EngineResult(title="Result 1", snippet="Snippet 1", link="https://a.com"),
            EngineResult(title="Result 2", snippet="Snippet 2", link="https://b.com"),
        ],
        classified_as=engine,
        confidence=0.75,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ROUTER_MOD = "app.testing.benchmark_latency"


@pytest.fixture(scope="module")
def bench_result(module_mocker):
    """
    Run benchmark with 2 iterations, all SerpApi calls mocked.
    Shared across all tests in this module for speed.
    """
    # Mock execute_route to return immediately without network calls
    async def _fake_execute(query, decision):
        mode = decision.get("mode", "single")
        if mode == "dual":
            return EngineResponse(
                success=True,
                engine="dual:shopping+local",
                result_count=4,
                results=[
                    EngineResult(title="Shop 1", snippet="s", link="https://s.com"),
                    EngineResult(title="Local 1", snippet="l", link="https://l.com"),
                ],
                classified_as="dual",
                confidence=0.55,
            )
        elif mode == "fallback":
            return EngineResponse(
                success=True,
                engine="search",
                result_count=3,
                results=[
                    EngineResult(title="FB 1", snippet="f", link="https://f.com"),
                ],
                classified_as="search (fallback)",
                confidence=0.15,
            )
        return _fake_engine_response()

    module_mocker.patch(f"{_ROUTER_MOD}.execute_route", side_effect=_fake_execute)

    from app.testing.benchmark_latency import run_latency_benchmark
    return run(run_latency_benchmark(iterations=2))


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------


def test_result_has_required_top_level_keys(bench_result):
    assert "classification_overhead_ms" in bench_result
    assert "single" in bench_result
    assert "dual" in bench_result
    assert "fallback" in bench_result
    assert "meta" in bench_result


def test_classification_overhead_has_stat_keys(bench_result):
    co = bench_result["classification_overhead_ms"]
    for key in ("min", "mean", "median", "max", "count"):
        assert key in co, f"Missing key '{key}' in classification_overhead_ms"


def test_each_mode_has_stat_keys(bench_result):
    for mode in ("single", "dual", "fallback"):
        s = bench_result[mode]
        for key in ("min", "mean", "median", "max", "count"):
            assert key in s, f"Missing key '{key}' in mode '{mode}'"


# ---------------------------------------------------------------------------
# Accounting integrity
# ---------------------------------------------------------------------------


def test_classification_count_is_20(bench_result):
    """Classification overhead is measured over 20 diverse queries."""
    assert bench_result["classification_overhead_ms"]["count"] == 20


def test_each_mode_count_matches_iterations(bench_result):
    for mode in ("single", "dual", "fallback"):
        assert bench_result[mode]["count"] == 2, (
            f"Expected 2 iterations for mode '{mode}', "
            f"got {bench_result[mode]['count']}"
        )


def test_latency_values_are_positive(bench_result):
    for mode in ("single", "dual", "fallback"):
        s = bench_result[mode]
        assert s["min"] >= 0
        assert s["mean"] >= 0
        assert s["median"] >= 0
        assert s["max"] >= 0


def test_min_lte_median_lte_max(bench_result):
    for mode in ("single", "dual", "fallback", "classification_overhead_ms"):
        s = bench_result[mode]
        assert s["min"] <= s["median"] <= s["max"], (
            f"Ordering violated for '{mode}': "
            f"min={s['min']} median={s['median']} max={s['max']}"
        )


def test_mean_between_min_and_max(bench_result):
    for mode in ("single", "dual", "fallback"):
        s = bench_result[mode]
        assert s["min"] <= s["mean"] <= s["max"], (
            f"Mean out of range for '{mode}': "
            f"min={s['min']} mean={s['mean']} max={s['max']}"
        )


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def test_meta_has_iteration_count(bench_result):
    assert bench_result["meta"]["iterations"] == 2


def test_meta_has_query_strings(bench_result):
    meta = bench_result["meta"]
    assert "single_query" in meta and meta["single_query"]
    assert "dual_query" in meta and meta["dual_query"]
    assert "fallback_query" in meta and meta["fallback_query"]


def test_meta_has_note(bench_result):
    assert "note" in bench_result["meta"]
