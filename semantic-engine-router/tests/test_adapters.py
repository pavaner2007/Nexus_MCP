"""
tests/test_adapters.py
=======================
Unit tests for app/engines/adapters.py.

Pure function tests — no mocking, no network, no SerpApi calls.
Each adapter receives a raw trimmed dict and must produce a correctly
shaped EngineResult.
"""

from __future__ import annotations

from app.engines.adapters import adapt_shopping_result, adapt_scholar_result
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
