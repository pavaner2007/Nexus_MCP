"""
app/engines/patents.py
=======================
Google Patents engine integration via SerpApi.

Self-contained — reads credentials from app.config.settings, calls SerpApi,
trims raw patent records to a clean subset of fields, and returns a
consistent EngineResponse — whether the call succeeds, returns no results,
or fails.

No routing / classification logic lives here.  That is Phase 8/9.

Usage
-----
    from app.engines.patents import search_patents

    result = search_patents("lithium battery patent", num_results=5)
    # result.success is True/False
    # result.results is a list of EngineResult objects (on success)
"""

from __future__ import annotations

import logging
from typing import Any

from serpapi import GoogleSearch

from app.config import settings
from app.schemas import EngineResponse
from app.engines.adapters import adapt_patents_result

logger = logging.getLogger(__name__)

# Fields to keep from each raw patent result object.
_KEEP_FIELDS: tuple[str, ...] = (
    "title",
    "patent_id",
    "publication_number",
    "inventor",
    "assignee",
    "filing_date",
    "publication_date",
    "link",
    "pdf",              # pdf download link, if available
    "snippet",          # abstract excerpt
)


def _trim_patent(raw: dict[str, Any]) -> dict[str, Any]:
    """Return only the whitelisted fields from a raw SerpApi patent result dict."""
    trimmed: dict[str, Any] = {
        field: raw[field] for field in _KEEP_FIELDS if field in raw
    }

    # SerpApi sometimes nests inventor/assignee inside a `patent` sub-object.
    # Flatten them to the top level if not already present.
    patent_sub: dict[str, Any] = raw.get("patent", {})
    for field in ("inventor", "assignee", "filing_date", "publication_date"):
        if field not in trimmed and field in patent_sub:
            trimmed[field] = patent_sub[field]

    # Normalise the PDF link — SerpApi may return it as "pdf" or "pdf_link".
    if "pdf" in trimmed and "pdf_link" not in trimmed:
        trimmed["pdf_link"] = trimmed.pop("pdf")

    return trimmed


def search_patents(
    query: str,
    num_results: int = 10,
) -> EngineResponse:
    """
    Query the Google Patents SerpApi engine and return trimmed patent records.

    Parameters
    ----------
    query:
        Natural-language patent search query (e.g. "lithium battery patent").
    num_results:
        Maximum number of patents to return (passed to SerpApi as ``num``).

    Returns
    -------
    EngineResponse
        Always returns a structured EngineResponse — never raises.

        Success::

            {
                "success": True,
                "engine": "patents",
                "result_count": 5,
                "results": [EngineResult(...), ...]
            }

        No results::

            {"success": True, "engine": "patents", "result_count": 0, "results": []}

        Failure::

            {"success": False, "engine": "patents", "error": "<reason>"}
    """
    params: dict[str, Any] = {
        "engine": "google_patents",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num_results,
    }

    try:
        logger.info("search_patents: querying SerpApi for %r (num=%d)", query, num_results)
        raw: dict[str, Any] = GoogleSearch(params).get_dict()
    except Exception as exc:  # noqa: BLE001 — catch-all for network/timeout errors
        logger.error("search_patents: request failed — %s", exc)
        return EngineResponse(
            success=False,
            engine="patents",
            error="Request to SerpApi timed out or failed",
        )

    # SerpApi surfaces API-level errors in the "error" key (not via exception).
    if "error" in raw:
        logger.warning("search_patents: SerpApi returned an error — %s", raw["error"])
        return EngineResponse(
            success=False,
            engine="patents",
            error=raw["error"],
        )

    organic_results: list[dict[str, Any]] = raw.get("organic_results", [])

    if not organic_results:
        logger.info("search_patents: no results returned for %r", query)
        return EngineResponse(
            success=True,
            engine="patents",
        )

    results = [adapt_patents_result(_trim_patent(item)) for item in organic_results]
    logger.info("search_patents: returning %d results for %r", len(results), query)

    return EngineResponse(
        success=True,
        engine="patents",
        result_count=len(results),
        results=results,
    )
