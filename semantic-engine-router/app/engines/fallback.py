"""
app/engines/fallback.py
========================
Google base Search fallback engine via SerpApi.

Used when the classifier's top score falls below ``MIN_CONFIDENCE_THRESHOLD``
in ``app/routing/router.py`` — i.e., when no specialist engine is confident
enough.  Returns clean, markdown-formatted EngineResult objects so the LLM
gets readable snippets rather than raw JSON.

Special SerpApi result types handled
--------------------------------------
* ``answer_box``      — direct answers (weather, calculations, definitions).
  Placed FIRST in the results list and prefixed with 📌 to signal high
  relevance.
* ``knowledge_graph`` — entity cards (people, places, organisations).
  Placed second (before organic results) and prefixed with 📚.
* ``organic_results`` — standard web results.  Snippet is formatted as
  a markdown string: ``"<snippet text> ([source](link))"``

No routing / classification logic lives here.

Usage
-----
    from app.engines.fallback import search_fallback

    result = search_fallback("who invented CRISPR", num_results=5)
    # result.success is True/False
    # result.results is a list of EngineResult objects (on success)
"""

from __future__ import annotations

import logging
from typing import Any

from serpapi import GoogleSearch

from app.config import settings
from app.schemas import EngineResponse, EngineResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal result adapters
# ---------------------------------------------------------------------------


def _adapt_answer_box(raw: dict[str, Any]) -> EngineResult:
    """Convert a SerpApi answer_box dict into an EngineResult.

    SerpApi answer boxes come in many shapes (weather, calculation, definition,
    featured snippet …).  We try common fields in priority order.
    """
    title: str = raw.get("title", "Answer")
    snippet: str | None = (
        raw.get("snippet")
        or raw.get("answer")
        or raw.get("result")
        or raw.get("contents")
        or None
    )
    link: str | None = raw.get("link")
    answer_type: str = raw.get("type", "answer_box")

    return EngineResult(
        title=f"📌 {title}",
        snippet=snippet,
        link=link,
        thumbnail=raw.get("thumbnail"),
        metadata={"source_type": "answer_box", "type": answer_type},
    )


def _adapt_knowledge_graph(raw: dict[str, Any]) -> EngineResult:
    """Convert a SerpApi knowledge_graph dict into an EngineResult."""
    title: str = raw.get("title", "Knowledge Panel")
    description: str | None = raw.get("description")
    link: str | None = raw.get("website") or (raw.get("source") or {}).get("link")
    thumbnail: str | None = raw.get("image") or raw.get("thumbnail")

    return EngineResult(
        title=f"📚 {title}",
        snippet=description,
        link=link,
        thumbnail=thumbnail,
        metadata={"source_type": "knowledge_graph"},
    )


def _adapt_organic_result(raw: dict[str, Any]) -> EngineResult:
    """Convert a standard organic result dict into a markdown-snippet EngineResult.

    Markdown snippet format:
        "<snippet text> ([source](link))"
    """
    title: str = raw.get("title", "Unknown")
    snippet_text: str = raw.get("snippet", "")
    link: str | None = raw.get("link")
    source: str = raw.get("displayed_link", "")

    # Build markdown snippet
    parts: list[str] = []
    if snippet_text:
        parts.append(snippet_text)
    if source and link:
        parts.append(f"([{source}]({link}))")
    elif source:
        parts.append(f"— {source}")

    md_snippet: str | None = " ".join(parts) if parts else None

    return EngineResult(
        title=title,
        snippet=md_snippet,
        link=link,
        thumbnail=raw.get("thumbnail"),
        metadata={
            "source_type": "organic",
            "source": source,
            "position": raw.get("position"),
        },
    )


# ---------------------------------------------------------------------------
# Public engine function
# ---------------------------------------------------------------------------


def search_fallback(
    query: str,
    num_results: int = 10,
) -> EngineResponse:
    """
    Query SerpApi's base Google Search engine and return formatted results.

    This is the fallback path used when the classifier is not confident
    enough to route to a specialist engine.

    Parameters
    ----------
    query:
        Natural-language query.
    num_results:
        Maximum number of organic results to include.

    Returns
    -------
    EngineResponse
        Always returns a structured EngineResponse — never raises.

        Success::

            {
                "success": True,
                "engine": "search",
                "result_count": N,
                "results": [EngineResult(...), ...]
            }

        Result list is ordered:
          1. ``answer_box`` result (if present)
          2. ``knowledge_graph`` result (if present and no answer_box)
          3. organic results

        Empty::

            {"success": True, "engine": "search", "result_count": 0, "results": []}

        Failure::

            {"success": False, "engine": "search", "error": "<reason>"}
    """
    params: dict[str, Any] = {
        "engine": "google",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num_results,
    }

    try:
        logger.info("search_fallback: querying SerpApi for %r (num=%d)", query, num_results)
        raw: dict[str, Any] = GoogleSearch(params).get_dict()
    except Exception as exc:  # noqa: BLE001
        logger.error("search_fallback: request failed — %s", exc)
        return EngineResponse(
            success=False,
            engine="search",
            error="Request to SerpApi timed out or failed",
        )

    # SerpApi surfaces API-level errors in the "error" key.
    if "error" in raw:
        logger.warning("search_fallback: SerpApi returned an error — %s", raw["error"])
        return EngineResponse(
            success=False,
            engine="search",
            error=raw["error"],
        )

    answer_box: dict | None = raw.get("answer_box")
    knowledge_graph: dict | None = raw.get("knowledge_graph")
    organic_results: list[dict] = raw.get("organic_results", [])

    # Empty check: none of the three result types present
    if not answer_box and not knowledge_graph and not organic_results:
        logger.info("search_fallback: no results returned for %r", query)
        return EngineResponse(
            success=True,
            engine="search",
        )

    results: list[EngineResult] = []

    # 1. Answer box — highest priority, placed first
    if answer_box:
        results.append(_adapt_answer_box(answer_box))

    # 2. Knowledge graph — only if no answer box (avoid double high-relevance blocks)
    if knowledge_graph and not answer_box:
        results.append(_adapt_knowledge_graph(knowledge_graph))

    # 3. Organic results
    for item in organic_results:
        results.append(_adapt_organic_result(item))

    logger.info("search_fallback: returning %d results for %r", len(results), query)

    return EngineResponse(
        success=True,
        engine="search",
        result_count=len(results),
        results=results,
    )
