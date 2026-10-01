"""
tests/test_adapters.py
=======================
Unit tests for app/engines/adapters.py.

Pure function tests — no mocking, no network, no SerpApi calls.
Each adapter receives a raw trimmed dict and must produce a correctly
shaped EngineResult.
"""

from __future__ import annotations

from app.engines.adapters import (
    adapt_shopping_result,
    adapt_scholar_result,
    adapt_local_result,
    adapt_patents_result,
)
from app.schemas import EngineResult


# ---------------------------------------------------------------------------
# Shared input fixtures
# ---------------------------------------------------------------------------

FULL_SHOPPING_PRODUCT = {
    "title": "Apple iPhone 15 128GB",
    "price": "$799.00",
    "extracted_price": 799.0,
    "source": "Best Buy",
    "link": "https://bestbuy.com/iphone15",
    "thumbnail": "https://cdn.example.com/iphone15.jpg",
    "rating": 4.8,
    "reviews": 1234,
}

MINIMAL_SHOPPING_PRODUCT = {
    "title": "Some Gadget",
    "link": "https://example.com/gadget",
}

FULL_SCHOLAR_PAPER = {
    "title": "Attention Is All You Need",
    "snippet": "The dominant sequence transduction models are based on complex recurrent...",
    "link": "https://arxiv.org/abs/1706.03762",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
    "publication": "Advances in neural information processing systems, 2017",
    "year": "2017",
    "cited_by_count": 98765,
    "pdf_link": "https://arxiv.org/pdf/1706.03762",
}

MINIMAL_SCHOLAR_PAPER = {
    "title": "A Minimal Paper",
    "link": "https://example.com/paper",
}


# ---------------------------------------------------------------------------
# adapt_shopping_result
# ---------------------------------------------------------------------------


class TestAdaptShoppingResult:
    def test_returns_engine_result_instance(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert isinstance(result, EngineResult)

    def test_title_mapped_correctly(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.title == "Apple iPhone 15 128GB"

    def test_link_mapped_correctly(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.link == "https://bestbuy.com/iphone15"

    def test_thumbnail_mapped_correctly(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.thumbnail == "https://cdn.example.com/iphone15.jpg"

    def test_snippet_synthesised_from_price_and_source(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.snippet is not None
        assert "$799.00" in result.snippet
        assert "Best Buy" in result.snippet

    def test_snippet_only_price_when_no_source(self):
        raw = {"title": "Widget", "price": "$5.00", "link": "http://x.com"}
        result = adapt_shopping_result(raw)
        assert result.snippet == "$5.00"

    def test_snippet_only_source_when_no_price(self):
        raw = {"title": "Widget", "source": "Amazon", "link": "http://x.com"}
        result = adapt_shopping_result(raw)
        assert "Amazon" in result.snippet

    def test_snippet_none_when_no_price_or_source(self):
        raw = {"title": "Widget", "link": "http://x.com"}
        result = adapt_shopping_result(raw)
        assert result.snippet is None

    def test_price_in_metadata(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.metadata["price"] == "$799.00"

    def test_extracted_price_in_metadata(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.metadata["extracted_price"] == 799.0

    def test_source_in_metadata(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.metadata["source"] == "Best Buy"

    def test_rating_in_metadata_when_present(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.metadata["rating"] == 4.8

    def test_reviews_in_metadata_when_present(self):
        result = adapt_shopping_result(FULL_SHOPPING_PRODUCT)
        assert result.metadata["reviews"] == 1234

    def test_optional_metadata_absent_when_missing(self):
        """rating/reviews must be absent from metadata, not None."""
        result = adapt_shopping_result(MINIMAL_SHOPPING_PRODUCT)
        assert "rating" not in result.metadata
        assert "reviews" not in result.metadata

    def test_missing_title_defaults_to_unknown(self):
        result = adapt_shopping_result({})
        assert result.title == "Unknown Product"

    def test_no_raw_engine_noise_in_metadata(self):
        raw = {**FULL_SHOPPING_PRODUCT, "serpapi_link": "https://serpapi.com/...", "position": 1}
        result = adapt_shopping_result(raw)
        assert "serpapi_link" not in result.metadata
        assert "position" not in result.metadata


# ---------------------------------------------------------------------------
# adapt_scholar_result
# ---------------------------------------------------------------------------


class TestAdaptScholarResult:
    def test_returns_engine_result_instance(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert isinstance(result, EngineResult)

    def test_title_mapped_correctly(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.title == "Attention Is All You Need"

    def test_link_mapped_correctly(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.link == "https://arxiv.org/abs/1706.03762"

    def test_thumbnail_always_none(self):
        """Scholar results have no thumbnail."""
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.thumbnail is None

    def test_snippet_mapped_from_raw(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.snippet == FULL_SCHOLAR_PAPER["snippet"]

    def test_snippet_none_when_absent(self):
        result = adapt_scholar_result(MINIMAL_SCHOLAR_PAPER)
        assert result.snippet is None

    def test_authors_in_metadata(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.metadata["authors"] == ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"]

    def test_publication_in_metadata(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert "2017" in result.metadata["publication"]

    def test_year_in_metadata(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.metadata["year"] == "2017"

    def test_cited_by_count_in_metadata(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.metadata["cited_by_count"] == 98765

    def test_pdf_link_in_metadata(self):
        result = adapt_scholar_result(FULL_SCHOLAR_PAPER)
        assert result.metadata["pdf_link"] == "https://arxiv.org/pdf/1706.03762"

    def test_optional_metadata_absent_when_missing(self):
        result = adapt_scholar_result(MINIMAL_SCHOLAR_PAPER)
        assert "authors" not in result.metadata
        assert "year" not in result.metadata
        assert "cited_by_count" not in result.metadata
        assert "pdf_link" not in result.metadata

    def test_missing_title_defaults_to_unknown(self):
        result = adapt_scholar_result({})
        assert result.title == "Unknown Paper"

    def test_raw_noise_not_in_metadata(self):
        raw = {**FULL_SCHOLAR_PAPER, "result_id": "abc123", "type": "Html"}
        result = adapt_scholar_result(raw)
        assert "result_id" not in result.metadata
        assert "type" not in result.metadata


# ---------------------------------------------------------------------------
# Shared fixtures — Local
# ---------------------------------------------------------------------------

FULL_LOCAL_PLACE = {
    "title": "Kumbakonam Degree Coffee",
    "address": "12, Anna Salai, Chennai, Tamil Nadu 600002",
    "rating": 4.5,
    "reviews": 3210,
    "type": "Coffee Shop",
    "phone": "+91 44 2345 6789",
    "hours": {"open_now": True},
    "open_now": True,
    "link": "https://maps.google.com/?cid=123456",
    "thumbnail": "https://cdn.example.com/coffee.jpg",
}

MINIMAL_LOCAL_PLACE = {
    "title": "Unnamed Shop",
    "link": "https://maps.google.com/?cid=000",
}


# ---------------------------------------------------------------------------
# adapt_local_result
# ---------------------------------------------------------------------------


class TestAdaptLocalResult:
    def test_returns_engine_result_instance(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert isinstance(result, EngineResult)

    def test_title_mapped_correctly(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.title == "Kumbakonam Degree Coffee"

    def test_link_mapped_correctly(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.link == "https://maps.google.com/?cid=123456"

    def test_thumbnail_mapped_correctly(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.thumbnail == "https://cdn.example.com/coffee.jpg"

    def test_snippet_synthesised_from_rating_and_type(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.snippet is not None
        assert "4.5" in result.snippet
        assert "Coffee Shop" in result.snippet

    def test_snippet_only_rating_when_no_type(self):
        raw = {"title": "Place", "rating": 3.8, "link": "http://x.com"}
        result = adapt_local_result(raw)
        assert "3.8" in result.snippet

    def test_snippet_only_type_when_no_rating(self):
        raw = {"title": "Place", "type": "Bakery", "link": "http://x.com"}
        result = adapt_local_result(raw)
        assert result.snippet == "Bakery"

    def test_snippet_falls_back_to_address(self):
        raw = {"title": "Place", "address": "5, Main St", "link": "http://x.com"}
        result = adapt_local_result(raw)
        assert result.snippet == "5, Main St"

    def test_snippet_none_when_no_clues(self):
        raw = {"title": "Place", "link": "http://x.com"}
        result = adapt_local_result(raw)
        assert result.snippet is None

    def test_address_in_metadata(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.metadata["address"] == "12, Anna Salai, Chennai, Tamil Nadu 600002"

    def test_phone_in_metadata(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.metadata["phone"] == "+91 44 2345 6789"

    def test_rating_in_metadata(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.metadata["rating"] == 4.5

    def test_reviews_in_metadata(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.metadata["reviews"] == 3210

    def test_type_in_metadata(self):
        result = adapt_local_result(FULL_LOCAL_PLACE)
        assert result.metadata["type"] == "Coffee Shop"

    def test_optional_metadata_absent_when_missing(self):
        result = adapt_local_result(MINIMAL_LOCAL_PLACE)
        assert "address" not in result.metadata
        assert "phone" not in result.metadata
        assert "rating" not in result.metadata

    def test_missing_title_defaults_to_unknown(self):
        result = adapt_local_result({})
        assert result.title == "Unknown Place"

    def test_noise_fields_not_in_metadata(self):
        raw = {**FULL_LOCAL_PLACE, "place_id": "ChIJXyz", "serpapi_link": "https://...", "position": 1}
        result = adapt_local_result(raw)
        assert "place_id" not in result.metadata
        assert "serpapi_link" not in result.metadata
        assert "position" not in result.metadata


# ---------------------------------------------------------------------------
# Shared fixtures — Patents
# ---------------------------------------------------------------------------

FULL_PATENT = {
    "title": "Lithium-ion battery with improved cycle life",
    "patent_id": "US10123456B2",
    "publication_number": "US10123456B2",
    "inventor": "John A. Doe, Jane B. Smith",
    "assignee": "Acme Energy Corp",
    "filing_date": "2018-03-15",
    "publication_date": "2020-11-03",
    "link": "https://patents.google.com/patent/US10123456B2",
    "pdf_link": "https://patents.google.com/patent/US10123456B2/en.pdf",
    "snippet": "A lithium-ion battery comprising an improved cathode material...",
}

MINIMAL_PATENT = {
    "title": "A Simple Invention",
    "link": "https://patents.google.com/patent/US000",
}


# ---------------------------------------------------------------------------
# adapt_patents_result
# ---------------------------------------------------------------------------


class TestAdaptPatentsResult:
    def test_returns_engine_result_instance(self):
        result = adapt_patents_result(FULL_PATENT)
        assert isinstance(result, EngineResult)

    def test_title_mapped_correctly(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.title == "Lithium-ion battery with improved cycle life"

    def test_link_mapped_correctly(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.link == "https://patents.google.com/patent/US10123456B2"

    def test_thumbnail_always_none(self):
        """Patents have no thumbnails."""
        result = adapt_patents_result(FULL_PATENT)
        assert result.thumbnail is None

    def test_snippet_mapped_from_abstract(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.snippet == FULL_PATENT["snippet"]

    def test_snippet_none_when_absent(self):
        result = adapt_patents_result(MINIMAL_PATENT)
        assert result.snippet is None

    def test_patent_id_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.metadata["patent_id"] == "US10123456B2"

    def test_publication_number_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.metadata["publication_number"] == "US10123456B2"

    def test_inventor_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert "John A. Doe" in result.metadata["inventor"]

    def test_assignee_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.metadata["assignee"] == "Acme Energy Corp"

    def test_filing_date_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.metadata["filing_date"] == "2018-03-15"

    def test_publication_date_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert result.metadata["publication_date"] == "2020-11-03"

    def test_pdf_link_in_metadata(self):
        result = adapt_patents_result(FULL_PATENT)
        assert "pdf_link" in result.metadata

    def test_optional_metadata_absent_when_missing(self):
        result = adapt_patents_result(MINIMAL_PATENT)
        assert "patent_id" not in result.metadata
        assert "inventor" not in result.metadata
        assert "assignee" not in result.metadata
        assert "pdf_link" not in result.metadata

    def test_missing_title_defaults_to_unknown(self):
        result = adapt_patents_result({})
        assert result.title == "Unknown Patent"
