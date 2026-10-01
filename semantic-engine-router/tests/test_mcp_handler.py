"""
tests/test_mcp_handler.py
==========================
Unit tests for the Universal_Search MCP tool handler.

Phase 8 notes
-------------
- ``universal_search`` is now ``async`` — calls are wrapped in
  ``asyncio.run()`` so no extra dependencies (e.g. pytest-asyncio) are needed.
- Routing now goes through ``app.routing.router.execute_route``, so engine
  mocks target ``app.routing.router.<engine>`` and routing functions.
- local + patents are real engines; "search" is the only remaining stub.

All external calls are mocked — no real API calls, no model loading.

Run with:
    pytest tests/test_mcp_handler.py -v
"""

from __future__ import annotations

import asyncio
import json

import pytest

# Import the tool function directly — FastMCP's @mcp.tool() decorator
# returns the original function unchanged, so it's callable as a normal function.
from app.mcp.server import universal_search
from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Mock targets
# ---------------------------------------------------------------------------

_GET_CENTROIDS    = "app.mcp.server._get_centroids"
_CLASSIFY_TOP     = "app.mcp.server.classify_top"
_DECIDE_ROUTE     = "app.mcp.server.decide_route"
_EXECUTE_ROUTE    = "app.mcp.server.execute_route"

# Router-level engine patches (used only when testing routing directly)
_ROUTER_SHOPPING  = "app.routing.router.search_shopping"
_ROUTER_SCHOLAR   = "app.routing.router.search_scholar"
_ROUTER_LOCAL     = "app.routing.router.search_local"
_ROUTER_PATENTS   = "app.routing.router.search_patents"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(query: str) -> str:
    """Run ``universal_search`` synchronously in tests."""
    return asyncio.run(universal_search(query))


# ---------------------------------------------------------------------------
# Shared fake data
# ---------------------------------------------------------------------------

FAKE_CENTROIDS = {
    "shopping": None, "scholar": None,
    "local": None, "patents": None, "search": None,
}

FAKE_SHOPPING_RESULT = EngineResponse(
    success=True,
    engine="shopping",
    result_count=2,
    results=[
        EngineResult(
            title="iPhone 15 Pro",
            snippet="$999 from Apple",
            link="https://apple.com",
            thumbnail="https://cdn.example.com/img.jpg",
            metadata={"price": "$999", "extracted_price": 999.0, "source": "Apple"},
        ),
        EngineResult(
            title="iPhone 15",
            snippet="$799 from Best Buy",
            link="https://bestbuy.com",
            thumbnail="https://cdn.example.com/img2.jpg",
            metadata={"price": "$799", "extracted_price": 799.0, "source": "Best Buy"},
        ),
    ],
)

FAKE_SCHOLAR_RESULT = EngineResponse(
    success=True,
    engine="scholar",
    result_count=1,
    results=[
        EngineResult(
            title="Attention Is All You Need",
            snippet="The dominant sequence transduction models...",
            link="https://arxiv.org/abs/1706.03762",
            metadata={
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "year": "2017",
                "cited_by_count": 98765,
            },
        ),
    ],
)

FAKE_ERROR_RESULT = EngineResponse(
    success=False,
    engine="shopping",
    error="Request to SerpApi timed out or failed",
)

FAKE_DUAL_RESULT = EngineResponse(
    success=True,
    engine="dual:shopping+scholar",
    result_count=3,
    results=[
        EngineResult(title="iPhone 15 Pro", snippet="$999", link="https://apple.com",
                     metadata={"source_engine": "shopping"}),
        EngineResult(title="iPhone 15",     snippet="$799", link="https://bestbuy.com",
                     metadata={"source_engine": "shopping"}),
        EngineResult(title="Attention Is All You Need", snippet="Abstract...",
                     link="https://arxiv.org/", metadata={"source_engine": "scholar"}),
    ],
    classified_as="dual",
    confidence=0.585,
    route_detail={"shopping": 0.62, "scholar": 0.55},
)


# ---------------------------------------------------------------------------
# Shared mock setup
# ---------------------------------------------------------------------------


def _setup_single_route(mocker, category: str, score: float, engine_result):
    """Patch centroids, classify_top, decide_route, execute_route for single mode."""
    mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
    mocker.patch(_CLASSIFY_TOP, return_value=[(category, score)])
    mocker.patch(_DECIDE_ROUTE, return_value={
        "mode": "single",
        "categories": [category],
        "scores": [(category, score)],
    })

    async def _fake_execute(query, decision):
        return engine_result

    mocker.patch(_EXECUTE_ROUTE, side_effect=_fake_execute)


# ---------------------------------------------------------------------------
# (a) Shopping routing
# ---------------------------------------------------------------------------


class TestShoppingRouting:
    def _mock(self, mocker, result=None):
        _setup_single_route(
            mocker, "shopping", 0.82,
            (result or FAKE_SHOPPING_RESULT).model_copy()
        )

    def test_returns_json_string(self, mocker):
        self._mock(mocker)
        assert isinstance(run("what's the price of iPhone 15"), str)

    def test_contains_engine_result(self, mocker):
        self._mock(mocker)
        data = json.loads(run("iPhone 15 price"))
        assert data["success"] is True
        assert data["engine"] == "shopping"
        assert data["result_count"] == 2

    def test_execute_route_called(self, mocker):
        self._mock(mocker)

        async def _fake_exec(query, decision):
            return FAKE_SHOPPING_RESULT

        mock_exec = mocker.patch(_EXECUTE_ROUTE, side_effect=_fake_exec)
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("shopping", 0.82)])
        mocker.patch(_DECIDE_ROUTE, return_value={
            "mode": "single", "categories": ["shopping"], "scores": [("shopping", 0.82)]
        })
        run("buy MacBook Pro")
        mock_exec.assert_called_once()

    def test_engine_error_still_serialises(self, mocker):
        self._mock(mocker, result=FAKE_ERROR_RESULT)
        data = json.loads(run("iPhone 15 price"))
        assert data["success"] is False


# ---------------------------------------------------------------------------
# (b) Scholar routing
# ---------------------------------------------------------------------------


class TestScholarRouting:
    def _mock(self, mocker):
        _setup_single_route(mocker, "scholar", 0.74, FAKE_SCHOLAR_RESULT.model_copy())

    def test_returns_json_string(self, mocker):
        self._mock(mocker)
        assert isinstance(run("recent papers on transformers"), str)

    def test_contains_paper_result(self, mocker):
        self._mock(mocker)
        data = json.loads(run("attention mechanism papers"))
        assert data["success"] is True
        assert data["engine"] == "scholar"
        assert data["result_count"] == 1


# ---------------------------------------------------------------------------
# (c) Dual-engine routing
# ---------------------------------------------------------------------------


class TestDualRouting:
    def _mock_dual(self, mocker):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("shopping", 0.62), ("scholar", 0.55)])
        mocker.patch(_DECIDE_ROUTE, return_value={
            "mode": "dual",
            "categories": ["shopping", "scholar"],
            "scores": [("shopping", 0.62), ("scholar", 0.55)],
        })

        async def _fake_execute(query, decision):
            return FAKE_DUAL_RESULT

        mocker.patch(_EXECUTE_ROUTE, side_effect=_fake_execute)

    def test_dual_returns_json_string(self, mocker):
        self._mock_dual(mocker)
        assert isinstance(run("compare iPhone prices and research"), str)

    def test_dual_engine_field_format(self, mocker):
        self._mock_dual(mocker)
        data = json.loads(run("compare iPhone prices and research"))
        assert data["engine"] == "dual:shopping+scholar"

    def test_dual_classified_as_dual(self, mocker):
        self._mock_dual(mocker)
        data = json.loads(run("compare iPhone prices and research"))
        assert data["classified_as"] == "dual"

    def test_dual_route_detail_present(self, mocker):
        self._mock_dual(mocker)
        data = json.loads(run("compare iPhone prices and research"))
        assert data["route_detail"] is not None
        assert "shopping" in data["route_detail"]
        assert "scholar" in data["route_detail"]

    def test_dual_result_count_is_sum(self, mocker):
        self._mock_dual(mocker)
        data = json.loads(run("compare iPhone prices and research"))
        assert data["result_count"] == 3


# ---------------------------------------------------------------------------
# (d) Unimplemented engine stub (search only — local/patents now real)
# ---------------------------------------------------------------------------


class TestUnimplementedEngines:
    @pytest.mark.parametrize("category,score", [
        ("search", 0.48),
    ])
    def test_stub_returned_without_crash(self, mocker, category, score):
        stub = EngineResponse(
            success=False,
            engine=category,
            error="Engine not yet implemented",
            classified_as=category,
            confidence=score,
        )
        _setup_single_route(mocker, category, score, stub)

        result = run("some query")
        data = json.loads(result)

        assert data["success"] is False
        assert data["engine"] == category
        assert data["error"] == "Engine not yet implemented"


# ---------------------------------------------------------------------------
# Helper (module-level, not a test)
# ---------------------------------------------------------------------------


async def _async_return(value):
    return value
