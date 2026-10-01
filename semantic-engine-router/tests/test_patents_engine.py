"""
tests/test_patents_engine.py
=============================
Tests for app/engines/patents.py.

Test groups
-----------
1. Unit tests (mocked) — run with  ``pytest -m "not live"``
   - Helper: _trim_patent
   - search_patents() — success / API error / empty / network error
   - /engines/patents endpoint returns valid EngineResponse JSON

2. Live tests — run with  ``pytest -m live``
   - Requires a real SERPAPI_KEY in .env
   - Hits the actual SerpApi Google Patents API
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.engines.patents import search_patents, _trim_patent

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FAKE_PATENTS: list[dict[str, Any]] = [
    {
        "title": "Lithium-ion battery with improved cycle life",
        "patent_id": "US10123456B2",
        "publication_number": "US10123456B2",
        "inventor": "John A. Doe, Jane B. Smith",
        "assignee": "Acme Energy Corp",
        "filing_date": "2018-03-15",
        "publication_date": "2020-11-03",
        "link": "https://patents.google.com/patent/US10123456B2",
        "pdf": "https://patents.google.com/patent/US10123456B2/en.pdf",
        "snippet": "A lithium-ion battery comprising an improved cathode material...",
        # Noise fields that should be stripped:
        "priority_date": "2017-01-01",
        "position": 1,
    },
    {
        "title": "Solid-state electrolyte for lithium batteries",
        "patent_id": "US10987654B1",
        "publication_number": "US10987654B1",
        "assignee": "Tech Batteries Inc",
        "filing_date": "2019-07-22",
        "publication_date": "2021-04-20",
        "link": "https://patents.google.com/patent/US10987654B1",
        "snippet": "A solid-state electrolyte composition...",
        # inventor intentionally absent
    },
]

FAKE_SUCCESS_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    "organic_results": FAKE_PATENTS,
}

FAKE_ERROR_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

FAKE_EMPTY_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    # "organic_results" key deliberately absent
}

MOCK_TARGET = "app.engines.patents.GoogleSearch"


# ---------------------------------------------------------------------------
# Unit tests — helper: _trim_patent
# ---------------------------------------------------------------------------


class TestTrimPatent:
    def test_keeps_whitelisted_fields(self):
        trimmed = _trim_patent(FAKE_PATENTS[0])
        for field in ("title", "patent_id", "publication_number",
                      "inventor", "assignee", "filing_date",
                      "publication_date", "link", "snippet"):
            assert field in trimmed, f"'{field}' missing from trimmed patent"

    def test_strips_non_whitelisted_fields(self):
        trimmed = _trim_patent(FAKE_PATENTS[0])
        assert "priority_date" not in trimmed
        assert "position" not in trimmed

    def test_missing_optional_inventor_is_absent(self):
        """inventor not in dict must simply be absent, not None."""
        trimmed = _trim_patent(FAKE_PATENTS[1])
        assert "inventor" not in trimmed

    def test_pdf_normalised_to_pdf_link(self):
        """'pdf' key should be renamed to 'pdf_link' during trim."""
        trimmed = _trim_patent(FAKE_PATENTS[0])
        assert "pdf_link" in trimmed
        assert "pdf" not in trimmed

    def test_flattens_inventor_from_patent_sub_object(self):
        """Inventor nested inside patent{} sub-object should be promoted."""
        raw = {
            "title": "Test Patent",
            "link": "https://patents.google.com/patent/US999",
            "patent": {"inventor": "Alice Wonder", "assignee": "Acme Corp"},
        }
        trimmed = _trim_patent(raw)
        assert trimmed.get("inventor") == "Alice Wonder"
        assert trimmed.get("assignee") == "Acme Corp"


# ---------------------------------------------------------------------------
# Unit tests — search_patents() with mocked GoogleSearch
# ---------------------------------------------------------------------------


class TestSearchPatentsMocked:
    """All GoogleSearch calls are mocked — no network access required."""

    # ── (1) Successful response ──────────────────────────────────────────────

    def test_success_shape(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_patents("lithium battery patent", num_results=2)

        assert result.success is True
        assert result.engine == "patents"
        assert result.result_count == 2
        assert isinstance(result.results, list)
        assert len(result.results) == 2

    def test_success_patent_fields(self, mocker):
        """Core fields in EngineResult; engine extras in metadata; noise absent."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_patents("lithium battery patent")
        first = result.results[0]

        # Top-level EngineResult fields
        assert first.title == "Lithium-ion battery with improved cycle life"
        assert first.snippet is not None   # abstract excerpt
        assert first.link is not None
        assert first.thumbnail is None     # patents have no thumbnail

        # Engine-specific extras in metadata
        assert "patent_id" in first.metadata
        assert "assignee" in first.metadata
        assert "filing_date" in first.metadata
        assert "publication_date" in first.metadata
        assert "pdf_link" in first.metadata

        # Noise absent
        assert "priority_date" not in first.metadata
        assert "position" not in first.metadata

    def test_optional_inventor_absent_when_missing(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_patents("lithium battery patent")
        second = result.results[1]
        assert "inventor" not in second.metadata

    def test_correct_serpapi_params_sent(self, mocker):
        """Verify engine=google_patents is passed to SerpApi."""
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        search_patents("solar panel efficiency", num_results=7)

        call_params: dict = mock_gs.call_args[0][0]
        assert call_params["engine"] == "google_patents"
        assert call_params["q"] == "solar panel efficiency"
        assert call_params["num"] == 7

    # ── (2) API-level error response ─────────────────────────────────────────

    def test_api_error_returns_failure(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_patents("lithium battery patent")

        assert result.success is False
        assert result.engine == "patents"
        assert result.error is not None
        assert "Invalid API key" in result.error

    def test_api_error_results_is_empty_list(self, mocker):
        """EngineResponse always has results; on error it must be empty."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_patents("lithium battery patent")
        assert result.results == []
        assert result.result_count == 0

    # ── (3) Empty / no results ───────────────────────────────────────────────

    def test_empty_results_returns_success_with_empty_list(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_EMPTY_RESPONSE

        result = search_patents("xyzzy nonexistent invention 99999")

        assert result.success is True
        assert result.engine == "patents"
        assert result.result_count == 0
        assert result.results == []

    # ── Network / exception ──────────────────────────────────────────────────

    def test_network_error_returns_failure(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.side_effect = Exception("Connection refused")

        result = search_patents("lithium battery patent")

        assert result.success is False
        assert result.engine == "patents"
        assert result.error is not None
        assert "timed out or failed" in result.error


# ---------------------------------------------------------------------------
# Endpoint unit tests (mocked) — POST /engines/patents
# ---------------------------------------------------------------------------


class TestPatentsEndpoint:
    @pytest.fixture(scope="class")
    def client(self):
        from app.main import app
        with TestClient(app) as c:
            yield c

    def test_endpoint_returns_200_on_success(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        resp = client.post("/engines/patents", json={"query": "lithium battery"})
        assert resp.status_code == 200

    def test_endpoint_response_shape(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        body = client.post("/engines/patents", json={"query": "lithium battery"}).json()
        assert body["success"] is True
        assert body["engine"] == "patents"
        assert "results" in body
        assert "result_count" in body

    def test_endpoint_returns_200_on_api_error(self, client, mocker):
        """Errors must never crash the endpoint — always HTTP 200 with success=False."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE
        resp = client.post("/engines/patents", json={"query": "bad key test"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_endpoint_default_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/patents", json={"query": "semiconductor"})
        assert mock_gs.call_args[0][0]["num"] == 10   # default

    def test_endpoint_custom_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/patents", json={"query": "semiconductor", "num_results": 3})
        assert mock_gs.call_args[0][0]["num"] == 3


# ---------------------------------------------------------------------------
# LIVE tests — require a real SERPAPI_KEY and network access
# Run with:  pytest -m live
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestPatentsLive:
    def test_lithium_battery_returns_results(self):
        result = search_patents("lithium battery patent", num_results=5)

        assert result.success is True, f"Live call failed: {result.error}"
        assert result.engine == "patents"
        assert result.result_count > 0
        assert len(result.results) > 0

    def test_live_result_has_expected_fields(self):
        result = search_patents("lithium battery patent", num_results=3)
        assert result.success is True

        for patent in result.results:
            assert patent.title, f"Missing title in patent: {patent}"
            assert patent.link is not None, f"Missing link in patent: {patent}"
            assert patent.thumbnail is None  # patents never have thumbnails

    def test_live_no_raw_serpapi_noise_fields(self):
        result = search_patents("solar cell efficiency", num_results=3)
        assert result.success is True

        for patent in result.results:
            assert "priority_date" not in patent.metadata
            assert "position" not in patent.metadata
