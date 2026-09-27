"""
tests/test_shopping_engine.py
==============================
Tests for app/engines/shopping.py.

Test groups
-----------
1. Unit tests (mocked) — run with  ``pytest -m "not live"``
   - Successful response with 2 fake products
   - API-level error response (SerpApi "error" field)
   - Empty results response (missing "shopping_results" key)
   - /engines/shopping endpoint returns valid JSON

2. Live tests — run with  ``pytest -m live``
   - Requires a real SERPAPI_KEY in .env
   - Hits the actual SerpApi Google Shopping API
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.engines.shopping import search_shopping, _trim_product

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FAKE_PRODUCTS: list[dict[str, Any]] = [
    {
        "title": "Apple iPhone 15 128GB",
        "price": "$799.00",
        "extracted_price": 799.0,
        "source": "Best Buy",
        "link": "https://bestbuy.com/iphone15",
        "thumbnail": "https://cdn.example.com/iphone15.jpg",
        "rating": 4.8,
        "reviews": 1234,
        # Extra fields that should be stripped by _trim_product:
        "serpapi_link": "https://serpapi.com/...",
        "position": 1,
    },
    {
        "title": "iPhone 15 Pro 256GB",
        "price": "$999.00",
        "extracted_price": 999.0,
        "source": "Apple Store",
        "link": "https://apple.com/iphone15pro",
        "thumbnail": "https://cdn.example.com/iphone15pro.jpg",
        # rating/reviews intentionally absent — must be gracefully omitted
    },
]

FAKE_SUCCESS_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    "shopping_results": FAKE_PRODUCTS,
}

FAKE_ERROR_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

FAKE_EMPTY_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    # "shopping_results" key deliberately absent
}

EXPECTED_FIELDS_ALWAYS = {"title", "price", "extracted_price", "source", "link", "thumbnail"}
OPTIONAL_FIELDS = {"rating", "reviews"}


# ---------------------------------------------------------------------------
# Unit tests — helper: _trim_product
# ---------------------------------------------------------------------------


class TestTrimProduct:
    def test_keeps_whitelisted_fields(self):
        trimmed = _trim_product(FAKE_PRODUCTS[0])
        assert "title" in trimmed
        assert "price" in trimmed
        assert "extracted_price" in trimmed
        assert "source" in trimmed
        assert "link" in trimmed
        assert "thumbnail" in trimmed
        assert "rating" in trimmed
        assert "reviews" in trimmed

    def test_strips_non_whitelisted_fields(self):
        trimmed = _trim_product(FAKE_PRODUCTS[0])
        assert "serpapi_link" not in trimmed
        assert "position" not in trimmed

    def test_missing_optional_fields_are_absent(self):
        """rating/reviews not in product dict must simply be absent, not None."""
        trimmed = _trim_product(FAKE_PRODUCTS[1])
        assert "rating" not in trimmed
        assert "reviews" not in trimmed


# ---------------------------------------------------------------------------
# Unit tests — search_shopping() with mocked GoogleSearch
# ---------------------------------------------------------------------------


MOCK_TARGET = "app.engines.shopping.GoogleSearch"


class TestSearchShoppingMocked:
    """All GoogleSearch calls are mocked — no network access required."""

    # ── (1) Successful response ──────────────────────────────────────────────

    def test_success_shape(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_shopping("iPhone 15", num_results=2)

        assert result["success"] is True
        assert result["engine"] == "shopping"
        assert result["result_count"] == 2
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 2

    def test_success_product_trimming(self, mocker):
        """Raw extra fields must not appear in returned results."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_shopping("iPhone 15")
        first = result["results"][0]

        # Required fields present
        for field in EXPECTED_FIELDS_ALWAYS:
            assert field in first, f"Field '{field}' missing from trimmed product"

        # Noise fields stripped
        assert "serpapi_link" not in first
        assert "position" not in first

    def test_success_optional_fields_present_when_available(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_shopping("iPhone 15")
        first = result["results"][0]
        assert "rating" in first
        assert "reviews" in first

    def test_success_optional_fields_absent_when_missing(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_shopping("iPhone 15")
        second = result["results"][1]
        assert "rating" not in second
        assert "reviews" not in second

    def test_correct_serpapi_params_sent(self, mocker):
        """Verify engine=google_shopping and gl=in are passed to SerpApi."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        search_shopping("test query", num_results=5)

        call_params: dict = mock_gs.call_args[0][0]
        assert call_params["engine"] == "google_shopping"
        assert call_params["gl"] == "in"
        assert call_params["q"] == "test query"
        assert call_params["num"] == 5

    # ── (2) API-level error response ─────────────────────────────────────────

    def test_api_error_returns_failure(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_shopping("iPhone 15")

        assert result["success"] is False
        assert result["engine"] == "shopping"
        assert "error" in result
        assert "Invalid API key" in result["error"]

    def test_api_error_no_results_key(self, mocker):
        """Error responses must not have a 'results' key."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_shopping("iPhone 15")
        assert "results" not in result

    # ── (3) Empty / no results ───────────────────────────────────────────────

    def test_empty_results_returns_success_with_empty_list(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_EMPTY_RESPONSE

        result = search_shopping("extremely obscure product xyz123")

        assert result["success"] is True
        assert result["engine"] == "shopping"
        assert result["result_count"] == 0
        assert result["results"] == []

    # ── Network / exception ──────────────────────────────────────────────────

    def test_network_error_returns_failure(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.side_effect = Exception("Connection refused")

        result = search_shopping("iPhone 15")

        assert result["success"] is False
        assert result["engine"] == "shopping"
        assert "error" in result
        assert "timed out or failed" in result["error"]


# ---------------------------------------------------------------------------
# Endpoint unit test (mocked) — POST /engines/shopping
# ---------------------------------------------------------------------------


class TestShoppingEndpoint:
    @pytest.fixture(scope="class")
    def client(self):
        from app.main import app
        with TestClient(app) as c:
            yield c

    def test_endpoint_returns_200_on_success(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        resp = client.post("/engines/shopping", json={"query": "iPhone 15"})
        assert resp.status_code == 200

    def test_endpoint_response_shape(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        body = client.post("/engines/shopping", json={"query": "iPhone 15"}).json()
        assert body["success"] is True
        assert body["engine"] == "shopping"
        assert "results" in body
        assert "result_count" in body

    def test_endpoint_returns_200_on_api_error(self, client, mocker):
        """Errors must never crash the endpoint — always HTTP 200 with success=False."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE
        resp = client.post("/engines/shopping", json={"query": "bad key test"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_endpoint_default_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/shopping", json={"query": "laptop"})
        call_params = mock_gs.call_args[0][0]
        assert call_params["num"] == 10   # default

    def test_endpoint_custom_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/shopping", json={"query": "laptop", "num_results": 3})
        call_params = mock_gs.call_args[0][0]
        assert call_params["num"] == 3


# ---------------------------------------------------------------------------
# LIVE tests — require a real SERPAPI_KEY and network access
# Run with:  pytest -m live
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestShoppingLive:
    def test_iphone_15_returns_results(self):
        result = search_shopping("iPhone 15", num_results=5)

        assert result["success"] is True, (
            f"Live call failed: {result.get('error')}"
        )
        assert result["engine"] == "shopping"
        assert result["result_count"] > 0
        assert len(result["results"]) > 0

    def test_live_result_has_expected_fields(self):
        result = search_shopping("iPhone 15", num_results=3)
        assert result["success"] is True

        for product in result["results"]:
            # title and link must always be present in real Shopping results
            assert "title" in product, f"Missing 'title' in product: {product}"
            assert "link" in product, f"Missing 'link' in product: {product}"

    def test_live_no_raw_serpapi_noise_fields(self):
        result = search_shopping("Samsung Galaxy S24", num_results=3)
        assert result["success"] is True

        for product in result["results"]:
            assert "serpapi_link" not in product
            assert "position" not in product
