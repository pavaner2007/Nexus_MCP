"""
tests/test_router.py
=====================
Unit tests for app/routing/router.py.

All engine calls are mocked — no real SerpApi or model calls.

Test groups
-----------
a. decide_route() — threshold logic
b. execute_route() — single mode
c. execute_route() — dual mode: happy path, source_engine injection,
   partial failure (one engine raises), partial failure (one stub)
d. Diagnostic: run AMBIGUOUS_TEST_QUERIES through classify_top + decide_route
   and print how many trigger dual mode.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.routing.router import (
    DUAL_ROUTE_THRESHOLD,
    decide_route,
    execute_route,
    ENGINE_MAP,
)
from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROUTER_PREFIX = "app.routing.router"


def _make_engine_response(engine: str, n: int = 2) -> EngineResponse:
    """Build a fake successful EngineResponse with ``n`` dummy results."""
    return EngineResponse(
        success=True,
        engine=engine,
        result_count=n,
        results=[
            EngineResult(
                title=f"{engine} result {i}",
                snippet=f"Snippet {i}",
                link=f"https://example.com/{engine}/{i}",
                metadata={},
            )
            for i in range(n)
        ],
    )


def run(coro):
    """Tiny helper: run an async coroutine synchronously in tests."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# (a) decide_route — threshold logic
# ---------------------------------------------------------------------------


class TestDecideRoute:
    def test_single_when_gap_is_wide(self):
        """Large gap → single-engine routing."""
        scores = [("shopping", 0.85), ("scholar", 0.20)]
        decision = decide_route(scores)
        assert decision["mode"] == "single"
        assert decision["categories"] == ["shopping"]

    def test_dual_when_gap_is_close(self):
        """Gap ≤ threshold → dual-engine routing."""
        scores = [("shopping", 0.60), ("scholar", 0.55)]
        decision = decide_route(scores)
        gap = 0.60 - 0.55  # 0.05 ≤ 0.15
        assert gap <= DUAL_ROUTE_THRESHOLD
        assert decision["mode"] == "dual"
        assert decision["categories"] == ["shopping", "scholar"]

    def test_dual_when_gap_exactly_at_threshold(self):
        """Gap == threshold → dual (boundary condition, inclusive)."""
        scores = [("local", 0.70), ("patents", 0.70 - DUAL_ROUTE_THRESHOLD)]
        decision = decide_route(scores)
        assert decision["mode"] == "dual"

    def test_single_when_gap_just_above_threshold(self):
        """Gap = threshold + ε → single."""
        scores = [("local", 0.70), ("patents", 0.70 - DUAL_ROUTE_THRESHOLD - 0.001)]
        decision = decide_route(scores)
        assert decision["mode"] == "single"

    def test_single_when_only_one_score(self):
        """Only one score available → always single."""
        scores = [("scholar", 0.91)]
        decision = decide_route(scores)
        assert decision["mode"] == "single"
        assert decision["categories"] == ["scholar"]

    def test_scores_carried_forward(self):
        """Original scores list is returned in the decision dict."""
        scores = [("shopping", 0.80), ("search", 0.50)]
        decision = decide_route(scores)
        assert decision["scores"] is scores

    def test_raises_on_empty_scores(self):
        with pytest.raises(ValueError, match="non-empty"):
            decide_route([])

    def test_correct_categories_for_dual(self):
        """Dual mode picks top-1 and top-2, not lower-ranked."""
        scores = [("patents", 0.62), ("local", 0.58), ("search", 0.10)]
        decision = decide_route(scores)
        assert decision["mode"] == "dual"
        assert decision["categories"] == ["patents", "local"]


# ---------------------------------------------------------------------------
# (b) execute_route — single mode
# ---------------------------------------------------------------------------


class TestExecuteRouteSingle:
    def test_single_calls_correct_engine(self, mocker):
        fake = _make_engine_response("shopping")
        mocker.patch(f"{_ROUTER_PREFIX}.asyncio.to_thread", return_value=fake)

        decision = {"mode": "single", "categories": ["shopping"],
                    "scores": [("shopping", 0.82)]}
        result = run(execute_route("iPhone 15", decision))

        assert result.success is True
        assert result.engine == "shopping"

    def test_single_injects_classified_as(self, mocker):
        fake = _make_engine_response("scholar")
        mocker.patch(f"{_ROUTER_PREFIX}.asyncio.to_thread", return_value=fake)

        decision = {"mode": "single", "categories": ["scholar"],
                    "scores": [("scholar", 0.77)]}
        result = run(execute_route("attention mechanism papers", decision))

        assert result.classified_as == "scholar"

    def test_single_injects_confidence(self, mocker):
        fake = _make_engine_response("shopping")
        mocker.patch(f"{_ROUTER_PREFIX}.asyncio.to_thread", return_value=fake)

        decision = {"mode": "single", "categories": ["shopping"],
                    "scores": [("shopping", 0.82)]}
        result = run(execute_route("buy laptop", decision))

        assert abs(result.confidence - 0.82) < 1e-6

    def test_single_returns_stub_for_unmapped_engine(self):
        """'search' maps to None → stub response, no engine call."""
        decision = {"mode": "single", "categories": ["search"],
                    "scores": [("search", 0.55)]}
        result = run(execute_route("latest news", decision))

        assert result.success is False
        assert result.engine == "search"
        assert "not yet implemented" in result.error


# ---------------------------------------------------------------------------
# (c) execute_route — dual mode: happy path
# ---------------------------------------------------------------------------


class TestExecuteRouteDualHappy:
    def _dual_decision(self):
        return {
            "mode": "dual",
            "categories": ["shopping", "scholar"],
            "scores": [("shopping", 0.62), ("scholar", 0.55)],
        }

    def _patch_gather(self, mocker, r1, r2):
        """Mock asyncio.gather AND _run_engine to avoid unawaited-coroutine warnings.

        Patching _run_engine prevents real coroutines from being created when
        execute_route calls _run_engine(cat1, query) as gather arguments.  Those
        coroutines would otherwise be created but never awaited (gather is replaced).
        """
        async def fake_gather(*args, return_exceptions=True):
            return (r1, r2)

        mocker.patch(f"{_ROUTER_PREFIX}.asyncio.gather", side_effect=fake_gather)
        mocker.patch(f"{_ROUTER_PREFIX}._run_engine")  # prevents real coroutine creation

    def test_dual_result_count_is_sum(self, mocker):
        r1 = _make_engine_response("shopping", n=3)
        r2 = _make_engine_response("scholar", n=2)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.result_count == 5
        assert len(result.results) == 5

    def test_dual_engine_name_formatted(self, mocker):
        r1 = _make_engine_response("shopping", n=1)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.engine == "dual:shopping+scholar"

    def test_dual_classified_as_dual(self, mocker):
        r1 = _make_engine_response("shopping", n=1)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.classified_as == "dual"

    def test_dual_confidence_is_average(self, mocker):
        r1 = _make_engine_response("shopping", n=1)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        expected = round((0.62 + 0.55) / 2, 4)
        assert abs(result.confidence - expected) < 1e-6

    def test_dual_route_detail_has_scores(self, mocker):
        r1 = _make_engine_response("shopping", n=1)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.route_detail is not None
        assert abs(result.route_detail["shopping"] - 0.62) < 1e-6
        assert abs(result.route_detail["scholar"] - 0.55) < 1e-6

    def test_dual_source_engine_injected_in_metadata(self, mocker):
        r1 = _make_engine_response("shopping", n=2)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        shopping_results = [r for r in result.results if r.metadata.get("source_engine") == "shopping"]
        scholar_results  = [r for r in result.results if r.metadata.get("source_engine") == "scholar"]
        assert len(shopping_results) == 2
        assert len(scholar_results) == 1

    def test_dual_results_ordered_cat1_then_cat2(self, mocker):
        """Cat1 results must come before cat2 results in the merged list."""
        r1 = _make_engine_response("shopping", n=2)
        r2 = _make_engine_response("scholar", n=1)
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        sources = [r.metadata["source_engine"] for r in result.results]
        assert sources == ["shopping", "shopping", "scholar"]


# ---------------------------------------------------------------------------
# (c) execute_route — dual mode: partial failure (one engine raises)
# ---------------------------------------------------------------------------


class TestExecuteRouteDualPartialFailure:
    def _dual_decision(self):
        return {
            "mode": "dual",
            "categories": ["shopping", "scholar"],
            "scores": [("shopping", 0.62), ("scholar", 0.55)],
        }

    def _patch_gather(self, mocker, r1, r2):
        async def fake_gather(*args, return_exceptions=True):
            return (r1, r2)
        mocker.patch(f"{_ROUTER_PREFIX}.asyncio.gather", side_effect=fake_gather)
        mocker.patch(f"{_ROUTER_PREFIX}._run_engine")  # prevents unawaited coroutines

    def test_partial_failure_still_returns_success(self, mocker):
        """If one engine raises, the other's results are still returned."""
        r1 = _make_engine_response("shopping", n=3)
        exc = RuntimeError("Connection refused")
        self._patch_gather(mocker, r1, exc)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.success is True
        assert result.result_count == 3

    def test_partial_failure_error_recorded_in_route_detail(self, mocker):
        r1 = _make_engine_response("shopping", n=2)
        exc = RuntimeError("Timeout")
        self._patch_gather(mocker, r1, exc)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert "scholar_error" in result.route_detail
        assert "Timeout" in result.route_detail["scholar_error"]

    def test_partial_failure_engine_returned_failure_response(self, mocker):
        """If one engine returns success=False, other results still returned."""
        r1 = _make_engine_response("shopping", n=2)
        r2 = EngineResponse(success=False, engine="scholar", error="Invalid API key")
        self._patch_gather(mocker, r1, r2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.success is True
        assert result.result_count == 2
        assert "scholar_error" in result.route_detail

    def test_both_fail_returns_empty_success(self, mocker):
        """If both engines fail, return empty success (don't raise)."""
        exc1 = RuntimeError("Timeout on shopping")
        exc2 = RuntimeError("Timeout on scholar")
        self._patch_gather(mocker, exc1, exc2)
        result = run(execute_route("compare iPhone research", self._dual_decision()))
        assert result.success is True
        assert result.result_count == 0
        assert "shopping_error" in result.route_detail
        assert "scholar_error" in result.route_detail


# ---------------------------------------------------------------------------
# (d) Diagnostic: ambiguous queries
# ---------------------------------------------------------------------------


class TestAmbiguousQueriesDiagnostic:
    def test_ambiguous_queries_dual_route_count(self, capsys):
        """
        Diagnostic — NOT a correctness assertion.

        Runs all AMBIGUOUS_TEST_QUERIES through the real classifier + decide_route.
        Prints how many trigger dual mode.  Always passes.
        """
        from app.classifier.seed_data import AMBIGUOUS_TEST_QUERIES
        from app.classifier.centroids import load_centroids
        from app.classifier.classify import classify_top

        centroids = load_centroids()
        dual_count = 0
        details = []

        for query in AMBIGUOUS_TEST_QUERIES:
            scores = classify_top(query, centroids, top_n=2)
            decision = decide_route(scores)
            is_dual = decision["mode"] == "dual"
            if is_dual:
                dual_count += 1
            details.append(
                f"  [{'DUAL  ' if is_dual else 'single'}] {query!r:55s} "
                f"top: {scores[0][0]}={scores[0][1]:.3f}, "
                f"{scores[1][0]}={scores[1][1]:.3f}  "
                f"gap={scores[0][1]-scores[1][1]:.3f}"
            )

        with capsys.disabled():
            print(f"\n{'='*70}")
            print(f"Ambiguous query routing diagnostic ({dual_count}/{len(AMBIGUOUS_TEST_QUERIES)} dual):")
            print(f"{'='*70}")
            for line in details:
                print(line)
            print(f"DUAL_ROUTE_THRESHOLD = {DUAL_ROUTE_THRESHOLD}")
            print(f"{'='*70}\n")

        # Always passes — this is a diagnostic, not a correctness assertion.
        assert isinstance(dual_count, int)
