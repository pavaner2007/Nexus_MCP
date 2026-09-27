"""
app/engines/shopping.py
========================
Google Shopping engine integration via SerpApi.

This module is intentionally self-contained: it reads credentials from
app.config.settings, calls SerpApi, trims the raw payload to a clean
subset of fields, and returns a consistent structured dict — whether the
call succeeds, returns no results, or fails.

No routing / classification logic lives here.  That is Phase 5.

Usage
-----
    from app.engines.shopping import search_shopping

    result = search_shopping("iPhone 15", num_results=5)
    # result["success"] is True/False
    # result["results"] is a list of trimmed product dicts (on success)
"""

from __future__ import annotations

import logging
from typing import Any

from serpapi import GoogleSearch

from app.config import settings

logger = logging.getLogger(__name__)

# Fields to keep from each raw shopping result object.
_KEEP_FIELDS: tuple[str, ...] = (
    "title",
    "price",
    "extracted_price",
    "source",
    "link",
    "thumbnail",
    "rating",
    "reviews",
)


def _trim_product(raw: dict[str, Any]) -> dict[str, Any]:
    """Return only the whitelisted fields from a raw SerpApi product dict."""
    return {field: raw[field] for field in _KEEP_FIELDS if field in raw}


def search_shopping(
    query: str,
    num_results: int = 10,
) -> dict[str, Any]:
    """
    Query the Google Shopping SerpApi engine and return trimmed results.

    Parameters
    ----------
    query:
        Natural-language product search query.
    num_results:
        Maximum number of products to return (passed to SerpApi as ``num``).

    Returns
    -------
    dict
        Always returns a structured dict — never raises.

        Success::

            {
                "success": True,
                "engine": "shopping",
                "result_count": 10,
                "results": [{"title": ..., "price": ..., ...}, ...]
            }

        No results::

            {"success": True, "engine": "shopping", "result_count": 0, "results": []}

        Failure::

            {"success": False, "engine": "shopping", "error": "<reason>"}
    """
    params: dict[str, Any] = {
        "engine": "google_shopping",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num_results,
        "gl": "in",          # Standardise results for India
    }

    try:
        logger.info("search_shopping: querying SerpApi for %r (num=%d)", query, num_results)
        raw: dict[str, Any] = GoogleSearch(params).get_dict()
    except Exception as exc:  # noqa: BLE001 — catch-all for network/timeout errors
        logger.error("search_shopping: request failed — %s", exc)
        return {
            "success": False,
            "engine": "shopping",
            "error": "Request to SerpApi timed out or failed",
        }

    # SerpApi surfaces API-level errors (bad key, quota exceeded, etc.) in
    # the "error" key of the response dict rather than raising an exception.
    if "error" in raw:
        logger.warning("search_shopping: SerpApi returned an error — %s", raw["error"])
        return {
            "success": False,
            "engine": "shopping",
            "error": raw["error"],
        }

    shopping_results: list[dict[str, Any]] = raw.get("shopping_results", [])

    if not shopping_results:
        logger.info("search_shopping: no results returned for %r", query)
        return {
            "success": True,
            "engine": "shopping",
            "result_count": 0,
            "results": [],
        }

    trimmed = [_trim_product(item) for item in shopping_results]
    logger.info("search_shopping: returning %d results for %r", len(trimmed), query)

    return {
        "success": True,
        "engine": "shopping",
        "result_count": len(trimmed),
        "results": trimmed,
    }
