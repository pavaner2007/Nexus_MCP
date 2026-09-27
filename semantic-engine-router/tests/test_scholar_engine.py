"""
tests/test_scholar_engine.py
=============================
Tests for app/engines/scholar.py.

Mirrors test_shopping_engine.py exactly in structure:

1. Unit tests — _trim_paper / _extract helpers
2. Mocked unit tests — search_scholar() covering all 3 response types
3. Mocked endpoint tests — POST /engines/scholar
4. Live tests (``pytest -m live``) — hit real SerpApi Google Scholar API

Run only mocked tests (no network/API key required):
    pytest -m "not live"

Run live tests (requires real SERPAPI_KEY in .env):
    pytest -m live
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.engines.scholar import (
    _extract_authors,
    _extract_pdf_link,
    _trim_paper,
    search_scholar,
)

# ---------------------------------------------------------------------------
# Shared fake data
# ---------------------------------------------------------------------------

FAKE_PAPERS: list[dict[str, Any]] = [
    {
        "title": "Attention Is All You Need",
        "link": "https://arxiv.org/abs/1706.03762",
        "snippet": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "publication_info": {
            "summary": "A Vaswani, N Shazeer, N Parmar - Advances in neural information processing, 2017",
            "authors": [
                {"name": "Ashish Vaswani", "link": "https://scholar.google.com/citations?user=oR9sCGYAAAAJ"},
                {"name": "Noam Shazeer", "link": "https://scholar.google.com/citations?user=SnQnQEgAAAAJ"},
                {"name": "Niki Parmar", "link": "https://scholar.google.com/citations?user=VVIAoY0AAAAJ"},
            ],
        },
        "inline_links": {
            "cited_by": {
                "total": 98765,
                "link": "https://scholar.google.com/scholar?cites=...",
            }
        },
        "resources": [
            {
                "title": "arxiv.org",
                "file_format": "PDF",
                "link": "https://arxiv.org/pdf/1706.03762",
            }
        ],
        # Extra noise fields that must be stripped:
        "result_id": "abc123",
        "type": "Html",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "link": "https://arxiv.org/abs/1810.04805",
        "snippet": "We introduce a new language representation model called BERT...",
        "publication_info": {
            "summary": "J Devlin, MW Chang, K Lee - arXiv preprint, 2018",
            # No "authors" key — must be handled gracefully
        },
        # No inline_links — cited_by_count must be absent (not None)
        # No resources — pdf_link must be absent (not None)
    },
]

FAKE_SUCCESS_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    "organic_results": FAKE_PAPERS,
}

FAKE_ERROR_RESPONSE: dict[str, Any] = {
    "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key",
}

FAKE_EMPTY_RESPONSE: dict[str, Any] = {
    "search_metadata": {"status": "Success"},
    # "organic_results" key deliberately absent
}

MOCK_TARGET = "app.engines.scholar.GoogleSearch"


# ---------------------------------------------------------------------------
# Unit tests — helper functions
# ---------------------------------------------------------------------------


class TestExtractAuthors:
    def test_returns_name_list(self):
        pub_info = {
            "authors": [
                {"name": "Alice Smith", "link": "https://scholar.google.com/..."},
                {"name": "Bob Jones"},
            ]
        }
        assert _extract_authors(pub_info) == ["Alice Smith", "Bob Jones"]

    def test_empty_when_no_authors_key(self):
        assert _extract_authors({}) == []

    def test_empty_when_authors_list_is_empty(self):
        assert _extract_authors({"authors": []}) == []

    def test_skips_entries_without_name(self):
        pub_info = {"authors": [{"link": "http://..."}, {"name": "Alice"}]}
        assert _extract_authors(pub_info) == ["Alice"]


class TestExtractPdfLink:
    def test_returns_pdf_link(self):
        resources = [
            {"title": "HTML", "file_format": "HTML", "link": "https://example.com/paper.html"},
            {"title": "PDF", "file_format": "PDF", "link": "https://example.com/paper.pdf"},
        ]
        assert _extract_pdf_link(resources) == "https://example.com/paper.pdf"

    def test_returns_none_when_no_pdf(self):
        resources = [{"file_format": "HTML", "link": "https://example.com/paper.html"}]
        assert _extract_pdf_link(resources) is None

    def test_returns_none_on_empty_list(self):
        assert _extract_pdf_link([]) is None

    def test_case_insensitive_format(self):
        resources = [{"file_format": "pdf", "link": "https://example.com/paper.pdf"}]
        assert _extract_pdf_link(resources) == "https://example.com/paper.pdf"


class TestTrimPaper:
    def test_keeps_top_level_fields(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert trimmed["title"] == "Attention Is All You Need"
        assert trimmed["link"] == "https://arxiv.org/abs/1706.03762"
        assert "snippet" in trimmed

    def test_extracts_authors_list(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert "authors" in trimmed
        assert "Ashish Vaswani" in trimmed["authors"]
        assert len(trimmed["authors"]) == 3

    def test_extracts_publication_summary(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert "publication" in trimmed
        assert "2017" in trimmed["publication"]

    def test_extracts_year_from_summary(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert trimmed.get("year") == "2017"

    def test_extracts_cited_by_count(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert trimmed["cited_by_count"] == 98765

    def test_extracts_pdf_link(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert trimmed["pdf_link"] == "https://arxiv.org/pdf/1706.03762"

    def test_strips_noise_fields(self):
        trimmed = _trim_paper(FAKE_PAPERS[0])
        assert "result_id" not in trimmed
        assert "type" not in trimmed

    def test_absent_optional_fields_are_missing_not_none(self):
        """Paper 2 has no authors key, no inline_links, no resources."""
        trimmed = _trim_paper(FAKE_PAPERS[1])
        assert "authors" not in trimmed
        assert "cited_by_count" not in trimmed
        assert "pdf_link" not in trimmed

    def test_year_absent_when_no_summary(self):
        raw = {"title": "Some Paper", "link": "http://example.com"}
        trimmed = _trim_paper(raw)
        assert "year" not in trimmed


# ---------------------------------------------------------------------------
# Mocked unit tests — search_scholar()
# ---------------------------------------------------------------------------


class TestSearchScholarMocked:

    # ── (1) Successful response ──────────────────────────────────────────────

    def test_success_shape(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_scholar("attention is all you need")

        assert result["success"] is True
        assert result["engine"] == "scholar"
        assert result["result_count"] == 2
        assert isinstance(result["results"], list)
        assert len(result["results"]) == 2

    def test_success_nested_field_trimming(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        result = search_scholar("attention is all you need")
        first = result["results"][0]

        assert first["title"] == "Attention Is All You Need"
        assert "authors" in first
        assert "Ashish Vaswani" in first["authors"]
        assert first["cited_by_count"] == 98765
        assert "pdf_link" in first
        assert "result_id" not in first   # noise stripped

    def test_correct_serpapi_params_sent(self, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE

        search_scholar("test query", num_results=7)

        call_params: dict = mock_gs.call_args[0][0]
        assert call_params["engine"] == "google_scholar"
        assert call_params["q"] == "test query"
        assert call_params["num"] == 7

    # ── (2) API-level error response ─────────────────────────────────────────

    def test_api_error_returns_failure(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_scholar("anything")

        assert result["success"] is False
        assert result["engine"] == "scholar"
        assert "Invalid API key" in result["error"]

    def test_api_error_has_no_results_key(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE

        result = search_scholar("anything")
        assert "results" not in result

    # ── (3) Empty / no results ───────────────────────────────────────────────

    def test_empty_results_returns_success_with_empty_list(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_EMPTY_RESPONSE

        result = search_scholar("extremely obscure paper xyzzy123")

        assert result["success"] is True
        assert result["engine"] == "scholar"
        assert result["result_count"] == 0
        assert result["results"] == []

    # ── Network / exception ──────────────────────────────────────────────────

    def test_network_error_returns_failure(self, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.side_effect = Exception("Connection refused")

        result = search_scholar("anything")

        assert result["success"] is False
        assert result["engine"] == "scholar"
        assert "timed out or failed" in result["error"]


# ---------------------------------------------------------------------------
# Mocked endpoint tests — POST /engines/scholar
# ---------------------------------------------------------------------------


class TestScholarEndpoint:
    @pytest.fixture(scope="class")
    def client(self):
        from app.main import app
        with TestClient(app) as c:
            yield c

    def test_endpoint_returns_200_on_success(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        resp = client.post("/engines/scholar", json={"query": "attention transformer"})
        assert resp.status_code == 200

    def test_endpoint_response_shape(self, client, mocker):
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        body = client.post("/engines/scholar", json={"query": "attention transformer"}).json()
        assert body["success"] is True
        assert body["engine"] == "scholar"
        assert "results" in body
        assert "result_count" in body

    def test_endpoint_returns_200_on_api_error(self, client, mocker):
        """Errors must never crash the endpoint — always HTTP 200 with success=False."""
        mocker.patch(MOCK_TARGET).return_value.get_dict.return_value = FAKE_ERROR_RESPONSE
        resp = client.post("/engines/scholar", json={"query": "bad key test"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_endpoint_default_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/scholar", json={"query": "BERT"})
        assert mock_gs.call_args[0][0]["num"] == 10

    def test_endpoint_custom_num_results(self, client, mocker):
        mock_gs = mocker.patch(MOCK_TARGET)
        mock_gs.return_value.get_dict.return_value = FAKE_SUCCESS_RESPONSE
        client.post("/engines/scholar", json={"query": "BERT", "num_results": 4})
        assert mock_gs.call_args[0][0]["num"] == 4


# ---------------------------------------------------------------------------
# LIVE tests — require a real SERPAPI_KEY and network access
# Run with:  pytest -m live
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestScholarLive:
    def test_transformer_paper_returns_results(self):
        result = search_scholar(
            "attention is all you need transformer", num_results=5
        )
        assert result["success"] is True, (
            f"Live call failed: {result.get('error')}"
        )
        assert result["engine"] == "scholar"
        assert result["result_count"] > 0
        assert len(result["results"]) > 0

    def test_live_result_has_required_fields(self):
        result = search_scholar(
            "attention is all you need transformer", num_results=3
        )
        assert result["success"] is True

        for paper in result["results"]:
            assert "title" in paper, f"Missing 'title' in paper: {paper}"
            assert "link" in paper, f"Missing 'link' in paper: {paper}"

    def test_live_no_noise_fields(self):
        result = search_scholar("BERT language model", num_results=3)
        assert result["success"] is True

        for paper in result["results"]:
            assert "result_id" not in paper
            assert "type" not in paper
            assert "inline_links" not in paper    # should be extracted, not raw
            assert "publication_info" not in paper  # should be extracted, not raw
