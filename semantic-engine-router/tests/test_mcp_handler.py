"""
tests/test_mcp_handler.py
==========================
Unit tests for the Universal_Search MCP tool handler.

All external calls (classify_top, search_shopping, search_scholar,
_get_centroids) are mocked — no real API calls, no model loading.

Run with:
    pytest tests/test_mcp_handler.py -v
"""

from __future__ import annotations

import json

import pytest

# Import the tool function directly — FastMCP's @mcp.tool() decorator
# returns the original function unchanged, so it's callable as a normal function.
from app.mcp.server import universal_search
from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Mock targets (patch at the server module level so all calls are intercepted)
# ---------------------------------------------------------------------------

_GET_CENTROIDS = "app.mcp.server._get_centroids"
_CLASSIFY_TOP  = "app.mcp.server.classify_top"
_SEARCH_SHOPPING = "app.mcp.server.search_shopping"
_SEARCH_SCHOLAR  = "app.mcp.server.search_scholar"

# ---------------------------------------------------------------------------
# Shared fake data — now EngineResponse objects (not raw dicts) so that
# handler's `result.classified_as = ...` attribute setting works correctly.
# ---------------------------------------------------------------------------

FAKE_CENTROIDS = {"shopping": None, "scholar": None, "local": None, "patents": None, "search": None}

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
            metadata={"authors": ["Ashish Vaswani", "Noam Shazeer"], "year": "2017", "cited_by_count": 98765},
        ),
    ],
)

FAKE_ERROR_RESULT = EngineResponse(
    success=False,
    engine="shopping",
    error="Request to SerpApi timed out or failed",
)



# ---------------------------------------------------------------------------
# (a) Shopping routing
# ---------------------------------------------------------------------------

class TestShoppingRouting:
    def _mock_shopping(self, mocker, engine_result=None):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("shopping", 0.82)])
        mocker.patch(_SEARCH_SHOPPING, return_value=(engine_result or FAKE_SHOPPING_RESULT.copy()))

    def test_returns_json_string(self, mocker):
        self._mock_shopping(mocker)
        result = universal_search("what's the price of iPhone 15")
        assert isinstance(result, str)
        # Must be valid JSON
        json.loads(result)

    def test_contains_engine_result(self, mocker):
        self._mock_shopping(mocker)
        data = json.loads(universal_search("iPhone 15 price"))
        assert data["success"] is True
        assert data["engine"] == "shopping"
        assert data["result_count"] == 2
        assert len(data["results"]) == 2

    def test_injects_classified_as(self, mocker):
        self._mock_shopping(mocker)
        data = json.loads(universal_search("iPhone 15 price"))
        assert data["classified_as"] == "shopping"

    def test_injects_confidence(self, mocker):
        self._mock_shopping(mocker)
        data = json.loads(universal_search("iPhone 15 price"))
        assert abs(data["confidence"] - 0.82) < 1e-6

    def test_search_shopping_called_with_query(self, mocker):
        self._mock_shopping(mocker)
        mock_shopping = mocker.patch(_SEARCH_SHOPPING, return_value=FAKE_SHOPPING_RESULT.copy())
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("shopping", 0.82)])
        universal_search("buy MacBook Pro")
        mock_shopping.assert_called_once_with("buy MacBook Pro")

    def test_engine_error_still_includes_metadata(self, mocker):
        """Even on engine failure, classified_as and confidence must be present."""
        self._mock_shopping(mocker, engine_result=FAKE_ERROR_RESULT.copy())
        data = json.loads(universal_search("iPhone 15 price"))
        assert data["success"] is False
        assert "classified_as" in data
        assert "confidence" in data


# ---------------------------------------------------------------------------
# (b) Scholar routing
# ---------------------------------------------------------------------------

class TestScholarRouting:
    def _mock_scholar(self, mocker):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("scholar", 0.74)])
        mocker.patch(_SEARCH_SCHOLAR, return_value=FAKE_SCHOLAR_RESULT.copy())

    def test_returns_json_string(self, mocker):
        self._mock_scholar(mocker)
        result = universal_search("recent papers on transformers")
        assert isinstance(result, str)
        json.loads(result)

    def test_contains_paper_result(self, mocker):
        self._mock_scholar(mocker)
        data = json.loads(universal_search("attention mechanism papers"))
        assert data["success"] is True
        assert data["engine"] == "scholar"
        assert data["result_count"] == 1

    def test_injects_classified_as_scholar(self, mocker):
        self._mock_scholar(mocker)
        data = json.loads(universal_search("NLP research 2024"))
        assert data["classified_as"] == "scholar"

    def test_injects_confidence(self, mocker):
        self._mock_scholar(mocker)
        data = json.loads(universal_search("NLP research 2024"))
        assert abs(data["confidence"] - 0.74) < 1e-6

    def test_search_scholar_called_with_query(self, mocker):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("scholar", 0.74)])
        mock_scholar = mocker.patch(_SEARCH_SCHOLAR, return_value=FAKE_SCHOLAR_RESULT.copy())
        universal_search("papers on reinforcement learning")
        mock_scholar.assert_called_once_with("papers on reinforcement learning")


# ---------------------------------------------------------------------------
# (c) Unimplemented engine stub (local, patents, search)
# ---------------------------------------------------------------------------

class TestUnimplementedEngines:
    @pytest.mark.parametrize("category,score", [
        ("local", 0.61),
        ("patents", 0.55),
        ("search", 0.48),
    ])
    def test_stub_returned_without_crash(self, mocker, category, score):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[(category, score)])

        result = universal_search("some query")

        assert isinstance(result, str)
        data = json.loads(result)

        assert data["success"] is False
        assert data["engine"] == category
        assert data["error"] == "Engine not yet implemented"
        assert data["classified_as"] == category
        assert abs(data["confidence"] - score) < 1e-6

    def test_stub_does_not_call_shopping(self, mocker):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("local", 0.61)])
        mock_shopping = mocker.patch(_SEARCH_SHOPPING)

        universal_search("coffee shops near me")

        mock_shopping.assert_not_called()

    def test_stub_does_not_call_scholar(self, mocker):
        mocker.patch(_GET_CENTROIDS, return_value=FAKE_CENTROIDS)
        mocker.patch(_CLASSIFY_TOP, return_value=[("patents", 0.55)])
        mock_scholar = mocker.patch(_SEARCH_SCHOLAR)

        universal_search("patent for wireless charging")

        mock_scholar.assert_not_called()
