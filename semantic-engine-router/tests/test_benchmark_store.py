"""
tests/test_benchmark_store.py
================================
Unit tests for app/demo/benchmark_store.py.

All expensive computations (run_token_benchmark, run_accuracy_benchmark,
run_latency_benchmark) are mocked — no network or SerpApi calls, no model
loading overhead beyond what's already in the module cache.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_STORE   = "app.demo.benchmark_store"
_TOKENS  = "app.testing.benchmark_tokens"
_ACC     = "app.testing.benchmark_accuracy"
_LATENCY = "app.testing.benchmark_latency"

FAKE_TOKEN_RESULT = {
    "tokens_20_tools": 7116,
    "tokens_1_tool": 187,
    "tokens_saved": 6929,
    "percent_reduction": 97.4,
    "tool_count_20": 20,
    "breakdown": [{"name": "google_shopping_search", "tokens": 340}],
}

FAKE_ACCURACY_RESULT = {
    "overall_accuracy": 58.5,
    "per_category": {
        "shopping": {"total": 8, "correct": 7, "wrong": 1, "accuracy": 87.5},
    },
    "misses": [],
    "total": 53,
    "total_correct": 31,
    "meta": {"elapsed_s": 1.5, "MIN_CONFIDENCE_THRESHOLD": 0.20, "DUAL_ROUTE_THRESHOLD": 0.15},
}

FAKE_LATENCY_RESULT = {
    "available": True,
    "classification_overhead_ms": {"min": 10.0, "mean": 13.0, "median": 12.5, "max": 18.0, "count": 20},
    "single":   {"min": 300.0, "mean": 450.0, "median": 440.0, "max": 620.0, "count": 3},
    "dual":     {"min": 400.0, "mean": 550.0, "median": 530.0, "max": 720.0, "count": 3},
    "fallback": {"min": 280.0, "mean": 420.0, "median": 410.0, "max": 590.0, "count": 3},
    "meta": {"iterations": 3},
}


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Redirect CACHE_DIR to a temporary directory for every test."""
    import app.demo.benchmark_store as store
    monkeypatch.setattr(store, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(store, "_TOKENS_FILE",   tmp_path / "tokens.json")
    monkeypatch.setattr(store, "_ACCURACY_FILE", tmp_path / "accuracy.json")
    monkeypatch.setattr(store, "_LATENCY_FILE",  tmp_path / "latency.json")
    yield tmp_path


# ---------------------------------------------------------------------------
# Token benchmark
# ---------------------------------------------------------------------------


def test_token_cache_written_on_first_call(isolated_cache, mocker):
    mocker.patch(f"{_TOKENS}.run_token_benchmark", return_value=FAKE_TOKEN_RESULT)
    from app.demo.benchmark_store import get_token_benchmark
    get_token_benchmark()
    assert (isolated_cache / "tokens.json").exists()


def test_token_cache_has_generated_at(isolated_cache, mocker):
    mocker.patch(f"{_TOKENS}.run_token_benchmark", return_value=FAKE_TOKEN_RESULT)
    from app.demo.benchmark_store import get_token_benchmark
    result = get_token_benchmark()
    assert "generated_at" in result


def test_token_second_call_reads_cache(isolated_cache, mocker):
    """Second call should NOT re-invoke run_token_benchmark."""
    mock_fn = mocker.patch(f"{_TOKENS}.run_token_benchmark", return_value=FAKE_TOKEN_RESULT)
    from app.demo.benchmark_store import get_token_benchmark
    get_token_benchmark()   # first call — computes
    get_token_benchmark()   # second call — should read cache
    assert mock_fn.call_count == 1


def test_token_refresh_recomputes(isolated_cache, mocker):
    """refresh=True must recompute even if cache exists."""
    mock_fn = mocker.patch(f"{_TOKENS}.run_token_benchmark", return_value=FAKE_TOKEN_RESULT)
    from app.demo.benchmark_store import get_token_benchmark
    get_token_benchmark()              # first call
    get_token_benchmark(refresh=True)  # forced refresh
    assert mock_fn.call_count == 2


# ---------------------------------------------------------------------------
# Accuracy benchmark
# ---------------------------------------------------------------------------


def test_accuracy_cache_written_on_first_call(isolated_cache, mocker):
    mocker.patch(f"{_ACC}.run_accuracy_benchmark", return_value=FAKE_ACCURACY_RESULT)
    from app.demo.benchmark_store import get_accuracy_benchmark
    get_accuracy_benchmark()
    assert (isolated_cache / "accuracy.json").exists()


def test_accuracy_cache_has_generated_at(isolated_cache, mocker):
    mocker.patch(f"{_ACC}.run_accuracy_benchmark", return_value=FAKE_ACCURACY_RESULT)
    from app.demo.benchmark_store import get_accuracy_benchmark
    result = get_accuracy_benchmark()
    assert "generated_at" in result


def test_accuracy_second_call_reads_cache(isolated_cache, mocker):
    mock_fn = mocker.patch(f"{_ACC}.run_accuracy_benchmark", return_value=FAKE_ACCURACY_RESULT)
    from app.demo.benchmark_store import get_accuracy_benchmark
    get_accuracy_benchmark()
    get_accuracy_benchmark()
    assert mock_fn.call_count == 1


def test_accuracy_refresh_recomputes(isolated_cache, mocker):
    mock_fn = mocker.patch(f"{_ACC}.run_accuracy_benchmark", return_value=FAKE_ACCURACY_RESULT)
    from app.demo.benchmark_store import get_accuracy_benchmark
    get_accuracy_benchmark()
    get_accuracy_benchmark(refresh=True)
    assert mock_fn.call_count == 2


# ---------------------------------------------------------------------------
# Latency benchmark
# ---------------------------------------------------------------------------


def test_latency_returns_unavailable_when_no_cache_and_no_refresh(isolated_cache):
    from app.demo.benchmark_store import get_latency_benchmark
    result = run(get_latency_benchmark(refresh=False))
    assert result["available"] is False
    assert "message" in result


def test_latency_no_cache_written_when_refresh_false(isolated_cache):
    from app.demo.benchmark_store import get_latency_benchmark
    run(get_latency_benchmark(refresh=False))
    assert not (isolated_cache / "latency.json").exists()


def test_latency_refresh_true_runs_and_caches(isolated_cache, mocker):
    async def _fake_latency(iterations=5):
        return FAKE_LATENCY_RESULT

    mocker.patch(f"{_LATENCY}.run_latency_benchmark", side_effect=_fake_latency)
    from app.demo.benchmark_store import get_latency_benchmark
    result = run(get_latency_benchmark(refresh=True))
    assert (isolated_cache / "latency.json").exists()
    assert result["available"] is True


def test_latency_cache_has_generated_at(isolated_cache, mocker):
    async def _fake_latency(iterations=5):
        return FAKE_LATENCY_RESULT

    mocker.patch(f"{_LATENCY}.run_latency_benchmark", side_effect=_fake_latency)
    from app.demo.benchmark_store import get_latency_benchmark
    result = run(get_latency_benchmark(refresh=True))
    assert "generated_at" in result


def test_latency_second_call_reads_cache(isolated_cache, mocker):
    async def _fake_latency(iterations=5):
        return FAKE_LATENCY_RESULT

    mock_fn = mocker.patch(f"{_LATENCY}.run_latency_benchmark", side_effect=_fake_latency)
    from app.demo.benchmark_store import get_latency_benchmark
    run(get_latency_benchmark(refresh=True))   # writes cache
    run(get_latency_benchmark(refresh=False))  # should read cache
    assert mock_fn.call_count == 1
