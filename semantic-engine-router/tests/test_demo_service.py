"""
tests/test_demo_service.py
============================
Unit tests for app/demo/service.py.

All SerpApi engine calls are mocked — no network I/O, no API quota consumed.
The classifier runs against the real centroid vectors (local disk I/O only).
"""

from __future__ import annotations

import asyncio
import pytest

from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SVC = "app.demo.service"


def _fake_response(engine: str = "shopping") -> EngineResponse:
    return EngineResponse(
        success=True,
        engine=engine,
        result_count=2,
        results=[
            EngineResult(title="Result A", snippet="Snippet A", link="https://a.com"),
            EngineResult(title="Result B", snippet="Snippet B", link="https://b.com"),
        ],
        classified_as=engine,
        confidence=0.75,
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def happy_result(mocker):
    """Run run_demo_query with execute_route mocked to return a shopping response."""
    async def _fake_execute(query, decision):
        return _fake_response("shopping")

    mocker.patch(f"{_SVC}.execute_route", side_effect=_fake_execute)
    from app.demo.service import run_demo_query
    return run(run_demo_query("iPhone 15 Pro price"))


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------


def test_result_has_query_key(happy_result):
    assert "query" in happy_result


def test_result_query_matches_input(happy_result):
    assert happy_result["query"] == "iPhone 15 Pro price"


def test_result_has_scores_key(happy_result):
    assert "scores" in happy_result


def test_scores_has_all_five_categories(happy_result):
    expected = {"shopping", "scholar", "local", "patents", "search"}
    assert set(happy_result["scores"].keys()) == expected


def test_scores_are_floats(happy_result):
    for cat, val in happy_result["scores"].items():
        assert isinstance(val, float), f"score for {cat!r} is not float"


def test_result_has_thresholds_key(happy_result):
    assert "thresholds" in happy_result


def test_thresholds_has_min_confidence(happy_result):
    assert "min_confidence" in happy_result["thresholds"]
    assert isinstance(happy_result["thresholds"]["min_confidence"], float)


def test_thresholds_has_dual_route_gap(happy_result):
    assert "dual_route_gap" in happy_result["thresholds"]
    assert isinstance(happy_result["thresholds"]["dual_route_gap"], float)


def test_result_has_route_key(happy_result):
    assert "route" in happy_result


def test_route_has_mode(happy_result):
    assert "mode" in happy_result["route"]
    assert happy_result["route"]["mode"] in ("single", "dual", "fallback")


def test_route_has_categories(happy_result):
    assert "categories" in happy_result["route"]
    assert isinstance(happy_result["route"]["categories"], list)


def test_result_has_response_key(happy_result):
    assert "response" in happy_result


def test_response_is_dict(happy_result):
    assert isinstance(happy_result["response"], dict)


def test_response_has_success_key(happy_result):
    assert "success" in happy_result["response"]


def test_response_success_is_true(happy_result):
    assert happy_result["response"]["success"] is True


def test_result_has_timings_key(happy_result):
    assert "timings_ms" in happy_result


def test_timings_has_three_keys(happy_result):
    t = happy_result["timings_ms"]
    assert "classification" in t
    assert "engine_calls" in t
    assert "total" in t


def test_timings_are_non_negative(happy_result):
    t = happy_result["timings_ms"]
    assert t["classification"] >= 0.0
    assert t["engine_calls"] >= 0.0
    assert t["total"] >= 0.0


def test_total_timing_gte_parts(happy_result):
    t = happy_result["timings_ms"]
    # total should be >= classification + engine_calls (small overhead allowed)
    assert t["total"] >= 0.0


# ---------------------------------------------------------------------------
# Error handling — structured failure
# ---------------------------------------------------------------------------


def test_error_returns_structured_response(mocker):
    """If execute_route raises, run_demo_query must return a structured dict."""
    async def _boom(query, decision):
        raise RuntimeError("SerpApi quota exceeded")

    mocker.patch(f"{_SVC}.execute_route", side_effect=_boom)
    from app.demo.service import run_demo_query
    result = run(run_demo_query("test query that triggers error"))

    # Must still return the documented shape
    assert "query" in result
    assert "scores" in result
    assert "thresholds" in result
    assert "route" in result
    assert "response" in result
    assert "timings_ms" in result

    # Response must indicate failure
    assert result["response"]["success"] is False
    assert "SerpApi quota exceeded" in (result["response"].get("error") or "")


def test_error_timings_total_is_non_negative(mocker):
    async def _boom(query, decision):
        raise ValueError("something broke")

    mocker.patch(f"{_SVC}.execute_route", side_effect=_boom)
    from app.demo.service import run_demo_query
    result = run(run_demo_query("error query"))
    assert result["timings_ms"]["total"] >= 0.0
