"""
app/mcp/server.py
==================
FastMCP server exposing the `Universal_Search` tool.

This is the single public interface that LLM agents (Claude Desktop, Cursor,
etc.) interact with.  Internally it:

  1. Classifies the query with the centroid-based embedding classifier.
  2. Routes to the appropriate SerpApi engine function.
  3. Returns a JSON string with the trimmed engine result + classifier metadata.

Centroid Loading
----------------
Centroids are loaded lazily on the first tool call via `_get_centroids()`.
A module-level cache (`_centroids`) ensures the model and disk read happen
only once per process — matching the singleton pattern used in the FastAPI app.

Unimplemented Engines
---------------------
"local", "patents", and "search" engines are Phase 6+ work.  They return a
clean stub so the tool never crashes or returns an empty string.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from app.classifier.centroids import load_centroids
from app.classifier.classify import classify_top
from app.engines.shopping import search_shopping
from app.engines.scholar import search_scholar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP("SemanticEngineRouter")

# ---------------------------------------------------------------------------
# Module-level centroid cache — loaded lazily on first tool call
# ---------------------------------------------------------------------------

_centroids: dict | None = None


def _get_centroids() -> dict:
    """Return centroids, loading from disk (or building) on the first call."""
    global _centroids
    if _centroids is None:
        logger.info("MCP: loading centroids …")
        _centroids = load_centroids()
        logger.info("MCP: centroids ready (%d categories).", len(_centroids))
    return _centroids


# ---------------------------------------------------------------------------
# Universal_Search tool
# ---------------------------------------------------------------------------

_UNIMPLEMENTED = {"local", "patents", "search"}


@mcp.tool()
def universal_search(query: str) -> str:
    """Search the web for any query — products, prices, academic papers, research, local businesses, patents, or general information. Automatically returns the most relevant structured data for the query."""

    centroids = _get_centroids()

    # Step 1 — classify
    top = classify_top(query, centroids, top_n=1)
    category: str = top[0][0]
    score: float = top[0][1]

    logger.info(
        "universal_search: query=%r → category='%s' (confidence=%.3f)",
        query, category, score,
    )

    # Step 2 — route
    if category == "shopping":
        result = search_shopping(query)
    elif category == "scholar":
        result = search_scholar(query)
    elif category in _UNIMPLEMENTED:
        return json.dumps({
            "success": False,
            "engine": category,
            "error": "Engine not yet implemented",
            "classified_as": category,
            "confidence": score,
        })
    else:
        # Defensive fallback for any unknown category label
        return json.dumps({
            "success": False,
            "engine": category,
            "error": f"Unknown engine category: {category!r}",
            "classified_as": category,
            "confidence": score,
        })

    # Step 3 — inject classifier metadata into successful engine response
    result["classified_as"] = category
    result["confidence"] = score

    return json.dumps(result)
