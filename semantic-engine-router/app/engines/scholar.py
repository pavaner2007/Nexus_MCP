"""
app/engines/scholar.py
======================
Google Scholar engine integration via SerpApi.

Follows the EXACT same contract as app/engines/shopping.py:
  - Always returns a structured dict — never raises.
  - Three possible outcomes: success-with-results, success-empty, failure.
  - Field trimming: only a whitelisted subset of each paper is returned.

Scholar-specific notes
-----------------------
  - SerpApi Scholar results live under the ``organic_results`` key.
  - Author names are nested inside ``publication_info.authors[].name``.
  - Publication summary / year come from ``publication_info.summary``.
  - Cited-by count lives at ``inline_links.cited_by.total``.
  - PDF link is in ``resources[].link`` where ``file_format == "PDF"``.

No routing / classification logic lives here.  That is Phase 5.

Usage
-----
    from app.engines.scholar import search_scholar

    result = search_scholar("attention is all you need", num_results=5)
    # result["success"] is True/False
    # result["results"] is a list of trimmed paper dicts (on success)
"""

from __future__ import annotations

import logging
from typing import Any

from serpapi import GoogleSearch

from app.config import settings
from app.schemas import EngineResponse
from app.engines.adapters import adapt_scholar_result

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_authors(publication_info: dict[str, Any]) -> list[str]:
    """
    Return a flat list of author name strings from ``publication_info``.

    SerpApi Scholar nests authors as::

        publication_info.authors = [{"name": "...", "link": "..."}, ...]

    If the key is absent (e.g. anonymous / unknown authors), returns [].
    """
    authors_raw: list[dict[str, Any]] = publication_info.get("authors", [])
    return [a["name"] for a in authors_raw if "name" in a]


def _extract_pdf_link(resources: list[dict[str, Any]]) -> str | None:
    """
    Return the URL of the first PDF resource, or None if not available.

    SerpApi Scholar exposes file links as::

        resources = [{"title": "...", "file_format": "PDF", "link": "..."}, ...]
    """
    for resource in resources:
        if resource.get("file_format", "").upper() == "PDF":
            return resource.get("link")
    return None


def _trim_paper(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and return only the whitelisted fields from a raw SerpApi
    Scholar ``organic_results`` item.

    Fields attempted (absent ones are simply omitted):
        title, link, snippet, authors, publication, year,
        cited_by_count, pdf_link
    """
    paper: dict[str, Any] = {}

    # Top-level flat fields
    for field in ("title", "link", "snippet"):
        if field in raw:
            paper[field] = raw[field]

    # Nested: publication_info
    pub_info: dict[str, Any] = raw.get("publication_info", {})
    authors = _extract_authors(pub_info)
    if authors:
        paper["authors"] = authors

    summary: str = pub_info.get("summary", "")
    if summary:
        paper["publication"] = summary

    # Year: try to pull the last 4-digit number out of the summary string.
    # Scholar summaries typically end with "- YYYY" e.g. "Nature, 2017".
    year: str | None = None
    for token in reversed(summary.split()):
        token_clean = token.strip(",-")
        if token_clean.isdigit() and len(token_clean) == 4:
            year = token_clean
            break
    if year:
        paper["year"] = year

    # Nested: cited_by count
    cited_by_total = (
        raw.get("inline_links", {})
        .get("cited_by", {})
        .get("total")
    )
    if cited_by_total is not None:
        paper["cited_by_count"] = cited_by_total

    # Nested: PDF link from resources list
    pdf_link = _extract_pdf_link(raw.get("resources", []))
    if pdf_link is not None:
        paper["pdf_link"] = pdf_link

    return paper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_scholar(
    query: str,
    num_results: int = 10,
) -> EngineResponse:
    """
    Query the Google Scholar SerpApi engine and return trimmed paper results.

    Parameters
    ----------
    query:
        Natural-language academic search query.
    num_results:
        Maximum number of papers to return (passed to SerpApi as ``num``).

    Returns
    -------
    dict
        Always returns a structured dict — never raises.

        Success::

            {
                "success": True,
                "engine": "scholar",
                "result_count": 10,
                "results": [{"title": ..., "authors": [...], ...}, ...]
            }

        No results::

            {"success": True, "engine": "scholar", "result_count": 0, "results": []}

        Failure::

            {"success": False, "engine": "scholar", "error": "<reason>"}
    """
    params: dict[str, Any] = {
        "engine": "google_scholar",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num_results,
    }

    try:
        logger.info("search_scholar: querying SerpApi for %r (num=%d)", query, num_results)
        raw: dict[str, Any] = GoogleSearch(params).get_dict()
    except Exception as exc:  # noqa: BLE001 — catch-all for network/timeout errors
        logger.error("search_scholar: request failed — %s", exc)
        return EngineResponse(
            success=False,
            engine="scholar",
            error="Request to SerpApi timed out or failed",
        )

    # SerpApi surfaces API-level errors in the "error" key (not via exception).
    if "error" in raw:
        logger.warning("search_scholar: SerpApi returned an error — %s", raw["error"])
        return EngineResponse(
            success=False,
            engine="scholar",
            error=raw["error"],
        )

    organic_results: list[dict[str, Any]] = raw.get("organic_results", [])

    if not organic_results:
        logger.info("search_scholar: no results returned for %r", query)
        return EngineResponse(
            success=True,
            engine="scholar",
        )

    results = [adapt_scholar_result(_trim_paper(item)) for item in organic_results]
    logger.info("search_scholar: returning %d results for %r", len(results), query)

    return EngineResponse(
        success=True,
        engine="scholar",
        result_count=len(results),
        results=results,
    )
