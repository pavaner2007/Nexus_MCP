"""
app/mcp/server.py
==================
FastMCP server exposing the `Universal_Search` tool.

This is the single public interface that LLM agents (Claude Desktop, Cursor,
etc.) interact with.  Internally it:

  1. Classifies the query with the centroid-based embedding classifier.
  2. Calls ``decide_route`` to choose single or dual-engine routing.
  3. Calls ``execute_route`` (async) to run engine(s) concurrently.
  4. Returns a JSON string with the trimmed engine results + routing metadata.

Phase 8 changes
---------------
- ``universal_search`` is now ``async`` — FastMCP supports async tools natively.
- Routing is top-2-aware: queries whose top-2 scores are within
  ``DUAL_ROUTE_THRESHOLD`` trigger concurrent dual-engine execution.
- All four engines (shopping, scholar, local, patents) are now real — no stubs.
- ``"search"`` (base Google Search) remains a Phase 9 stub.

Centroid Loading
----------------
Centroids are loaded lazily on the first tool call via ``_get_centroids()``.
A module-level cache ensures the model and disk read happen only once per
process — matching the singleton pattern used in the FastAPI app.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from app.classifier.centroids import load_centroids
from app.classifier.classify import classify_top
from app.routing.router import decide_route, execute_route

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


@mcp.tool()
async def universal_search(query: str) -> str:
    """Search the web for any query — products, prices, academic papers, research, local businesses, patents, or general information. Automatically returns the most relevant structured data for the query. Supports dual-engine routing for ambiguous queries."""

    centroids = _get_centroids()

    # Step 1 — classify (top-2 for dual-route awareness)
    scores = classify_top(query, centroids, top_n=2)

    logger.info(
        "universal_search: query=%r → top scores: %s",
        query,
        [(cat, f"{sc:.3f}") for cat, sc in scores],
    )

    # Step 2 — decide routing mode
    decision = decide_route(scores)

    logger.info(
        "universal_search: mode=%r categories=%r",
        decision["mode"], decision["categories"],
    )

    # Step 3 — execute (async, possibly concurrent dual-engine)
    response = await execute_route(query, decision)

    # Step 4 — serialise and return
    return response.model_dump_json()
