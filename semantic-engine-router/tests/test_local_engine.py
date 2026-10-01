"""
tests/test_local_engine.py
===========================
Tests for app/engines/local.py.

Test groups
-----------
1. Unit tests (mocked) — run with  ``pytest -m "not live"``
   - Helper: _trim_place
   - search_local() — success / API error / empty / network error
   - /engines/local endpoint returns valid EngineResponse JSON

2. Live tests — run with  ``pytest -m live``
   - Requires a real SERPAPI_KEY in .env
   - Hits the actual SerpApi Google Local API
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.engines.local import search_local, _trim_place

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FAKE_PLACES: list[dict[str, Any]] = [
    {
        "title": "Kumbakonam Degree Coffee",
        "address": "12, Anna Salai, Chennai, Tamil Nadu 600002",
        "rating": 4.5,
        "reviews": 3210,
        "type": "Coffee Shop",
        "phone": "+91 44 2345 6789",
        "hours": {"open_now": True},
        "link": "https://maps.google.com/?cid=123456",
        "thumbnail": "https://cdn.example.com/coffee.jpg",
        # Noise fields that should be stripped:
        "place_id": "ChIJXyz",
        "serpapi_link": "https://serpapi.com/...",
        "position": 1,
    },
    {
        "title": "Filter Coffee House",
        "address": "45, T Nagar, Chennai",
        "rating": 4.2,
        "reviews": 890,
        "type": "Cafe",
        "link": "https://maps.google.com/?cid=654321",
        # phone / hours intentionally absent
    },
]

FAKE_SUCCESS_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    "local_results": FAKE_PLACES,
}

FAKE_ERROR_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

FAKE_EMPTY_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    # "local_results" key deliberately absent
}

MOCK_TARGET = "app.engines.local.GoogleSearch"


# ---------------------------------------------------------------------------
# Unit tests — helper: _trim_place
# ---------------------------------------------------------------------------


class TestTrimPlace:
    def test_keeps_whitelisted_fields(self):
        trimmed = _trim_place(FAKE_PLACES[0])
        for field in ("title", "address", "rating", "reviews", "type", "phone", "link", "thumbnail"):
            assert field in trimmed, f"'{field}' missing from trimmed place"

    def test_strips_non_whitelisted_fields(self):
        trimmed = _trim_place(FAKE_PLACES[0])
        assert "place_id" not in trimmed
        assert "serpapi_link" not in trimmed
        assert "position" not in trimmed

    def test_missing_optional_fields_are_absent(self):
        """phone and hours not in dict must simply be absent, not None."""
        trimmed = _trim_place(FAKE_PLACES[1])
        assert "phone" not in trimmed
        assert "hours" not in trimmed

    def test_flattens_open_now_from_hours_dict(self):
        """open_now nested inside hours dict should be promoted to top level."""
        raw = {"title": "Cafe", "hours": {"open_now": True}}
        trimmed = _trim_place(raw)
        assert trimmed.get("open_now") is True


# ---------------------------------------------------------------------------
# Unit tests — search_local() with mocked GoogleSearch
# ---------------------------------------------------------------------------


class TestSearchLocalMocked:
    """All GoogleSearch calls are mocked — no network access required."""

    # ── (1) Successful response ──────────────────────────────────────────────

    def test_success_shape(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_local("coffee shops in Chennai", num_results=2)

        assert result.success is True
        assert result.engine == "local"
        assert result.result_count == 2
        assert isinstance(result.results, list)
        assert len(result.results) == 2

    def test_success_place_fields(self, mocker):
        """Core fields in EngineResult; engine extras in metadata; noise absent."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_local("coffee shops in Chennai")
        first = result.results[0]

        # Top-level EngineResult fields
        assert first.title == "Kumbakonam Degree Coffee"
        assert first.link is not None
        assert first.thumbnail is not None
        assert first.snippet is not None  # synthesised from rating + type

        # Engine-specific extras in metadata
        assert "address" in first.metadata
        assert "rating" in first.metadata
        assert "type" in first.metadata

        # Noise absent
        assert "place_id" not in first.metadata
        assert "serpapi_link" not in first.metadata
        assert "position" not in first.metadata

    def test_snippet_synthesised_from_rating_and_type(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_local("coffee shops in Chennai")
        first = result.results[0]
        assert "4.5" in first.snippet
        assert "Coffee Shop" in first.snippet

    def test_optional_fields_absent_when_missing(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_local("coffee shops in Chennai")
        second = result.results[1]
        assert "phone" not in second.metadata

    def test_correct_serpapi_params_sent(self, mocker):
        """Verify engine=google_local is passed to SerpApi."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        search_local("pharmacies in Bangalore", num_results=5)

        call_params: dict = mock_gs.call_args[0][0]
        assert call_params["engine"] == "google_local"
        assert call_params["q"] == "pharmacies in Bangalore"
        assert call_params["num"] == 5

    # ── (2) API-level error response ─────────────────────────────────────────

    def test_api_error_returns_failure(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_local("coffee shops in Chennai")

        assert result.success is False
        assert result.engine == "local"
        assert result.error is not None
        assert "Invalid API key" in result.error

    def test_api_error_results_is_empty_list(self, mocker):
        """EngineResponse always has results; on error it must be empty."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_local("coffee shops in Chennai")
        assert result.results == []
        assert result.result_count == 0

    # ── (3) Empty / no results ───────────────────────────────────────────────

    def test_empty_results_returns_success_with_empty_list(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_EMPTY_RESPONSE

        result = search_local("businesses in xyzzy nonexistent place")

        assert result.success is True
        assert result.engine == "local"
        assert result.result_count == 0
        assert result.results == []

    # ── Network / exception ──────────────────────────────────────────────────

    def test_network_error_returns_failure(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.side_effect = Exception("Connection refused")

        result = search_local("coffee shops in Chennai")

        assert result.success is False
        assert result.engine == "local"
        assert result.error is not None
        assert "timed out or failed" in result.error


# ---------------------------------------------------------------------------
# Endpoint unit tests (mocked) — POST /engines/local
# ---------------------------------------------------------------------------


class TestLocalEndpoint:
    @pytest.fixture(scope="class")
    def client(self):
        from app.main import app
        with TestClient(app) as c:
            yield c

    def test_endpoint_returns_200_on_success(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        resp = client.post("/engines/local", json={"query": "coffee shops in Chennai"})
        assert resp.status_code == 200

    def test_endpoint_response_shape(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        body = client.post("/engines/local", json={"query": "coffee shops in Chennai"}).json()
        assert body["success"] is True
        assert body["engine"] == "local"
        assert "results" in body
        assert "result_count" in body

    def test_endpoint_returns_200_on_api_error(self, client, mocker):
        """Errors must never crash the endpoint — always HTTP 200 with success=False."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE
        resp = client.post("/engines/local", json={"query": "bad key test"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_endpoint_default_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/local", json={"query": "restaurants"})
        assert mock_gs.call_args[0][0]["num"] == 10   # default

    def test_endpoint_custom_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/local", json={"query": "restaurants", "num_results": 4})
        assert mock_gs.call_args[0][0]["num"] == 4


# ---------------------------------------------------------------------------
# LIVE tests — require a real SERPAPI_KEY and network access
# Run with:  pytest -m live
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLocalLive:
    def test_coffee_shops_chennai_returns_results(self):
        result = search_local("coffee shops in Chennai", num_results=5)

        assert result.success is True, f"Live call failed: {result.error}"
        assert result.engine == "local"
        assert result.result_count > 0
        assert len(result.results) > 0

    def test_live_result_has_expected_fields(self):
        result = search_local("coffee shops in Chennai", num_results=3)
        assert result.success is True

        for place in result.results:
            assert place.title, f"Missing title in place: {place}"

    def test_live_no_raw_serpapi_noise_fields(self):
        result = search_local("restaurants in Bangalore", num_results=3)
        assert result.success is True

        for place in result.results:
            assert "place_id" not in place.metadata
            assert "serpapi_link" not in place.metadata
            assert "position" not in place.metadata
