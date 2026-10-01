"""
app/engines/local.py
=====================
Google Local engine integration via SerpApi.

Self-contained — reads credentials from app.config.settings, calls SerpApi,
trims raw business listings to a clean subset of fields, and returns a
consistent EngineResponse — whether the call succeeds, returns no results,
or fails.

No routing / classification logic lives here.  That is Phase 8/9.

Usage
-----
    from app.engines.local import search_local

    result = search_local("coffee shops in Chennai", num_results=5)
    # result.success is True/False
    # result.results is a list of EngineResult objects (on success)
"""

from __future__ import annotations

import logging
from typing import Any

from serpapi import GoogleSearch

from app.config import settings
from app.schemas import EngineResponse
from app.engines.adapters import adapt_local_result

logger = logging.getLogger(__name__)

# Fields to keep from each raw local result object.
_KEEP_FIELDS: tuple[str, ...] = (
    "title",
    "address",
    "rating",
    "reviews",          # reviews count
    "type",             # business category / type
    "phone",
    "hours",
    "open_now",
    "link",
    "thumbnail",
)


def _trim_place(raw: dict[str, Any]) -> dict[str, Any]:
    """Return only the whitelisted fields from a raw SerpApi local result dict."""
    trimmed: dict[str, Any] = {
        field: raw[field] for field in _KEEP_FIELDS if field in raw
    }

    # SerpApi nests hours information inside an `hours` dict; flatten open_now
    # to the top level if it's buried there and not already present.
    if "open_now" not in trimmed and isinstance(trimmed.get("hours"), dict):
        open_now = trimmed["hours"].get("open_now")
        if open_now is not None:
            trimmed["open_now"] = open_now

    return trimmed


def search_local(
    query: str,
    num_results: int = 10,
) -> EngineResponse:
    """
    Query the Google Local SerpApi engine and return trimmed business results.

    Parameters
    ----------
    query:
        Natural-language local business search query (e.g. "coffee shops in Chennai").
    num_results:
        Maximum number of places to return (passed to SerpApi as ``num``).

    Returns
    -------
    EngineResponse
        Always returns a structured EngineResponse — never raises.

        Success::

            {
                "success": True,
                "engine": "local",
                "result_count": 5,
                "results": [EngineResult(...), ...]
            }

        No results::

            {"success": True, "engine": "local", "result_count": 0, "results": []}

        Failure::

            {"success": False, "engine": "local", "error": "<reason>"}
    """
    params: dict[str, Any] = {
        "engine": "google_local",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num_results,
        "gl": "in",       # Standardise results for India
        "hl": "en",
    }

    try:
        logger.info("search_local: querying SerpApi for %r (num=%d)", query, num_results)
        raw: dict[str, Any] = GoogleSearch(params).get_dict()
    except Exception as exc:  # noqa: BLE001 — catch-all for network/timeout errors
        logger.error("search_local: request failed — %s", exc)
        return EngineResponse(
            success=False,
            engine="local",
            error="Request to SerpApi timed out or failed",
        )

    # SerpApi surfaces API-level errors in the "error" key (not via exception).
    if "error" in raw:
        logger.warning("search_local: SerpApi returned an error — %s", raw["error"])
        return EngineResponse(
            success=False,
            engine="local",
            error=raw["error"],
        )

    local_results: list[dict[str, Any]] = raw.get("local_results", [])

    if not local_results:
        logger.info("search_local: no results returned for %r", query)
        return EngineResponse(
            success=True,
            engine="local",
        )

    results = [adapt_local_result(_trim_place(item)) for item in local_results]
    logger.info("search_local: returning %d results for %r", len(results), query)

    return EngineResponse(
        success=True,
        engine="local",
        result_count=len(results),
        results=results,
    )
