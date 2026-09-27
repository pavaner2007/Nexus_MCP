"""
app/schemas.py
==============
Shared Pydantic V2 response schemas for all SerpApi engine modules.

Every engine function (search_shopping, search_scholar, and future engines)
MUST return an ``EngineResponse``.  Every individual result item MUST be
an ``EngineResult``.

This shared contract ensures:
  - FastAPI can declare a single ``response_model=EngineResponse`` on all
    engine endpoints.
  - The MCP tool can call ``.model_dump_json()`` without engine-specific
    serialisation logic.
  - New engines (Local, Patents, Search) are forced into the same shape
    from day one.

EngineResult shape
------------------
Common fields (title, snippet, link, thumbnail) cover what all engines
share.  Engine-specific extras (price, rating, authors, year, …) live in
``metadata`` so the envelope stays stable even as engines are added.

EngineResponse shape
--------------------
``classified_as`` and ``confidence`` are ``None`` when the response comes
from a direct engine endpoint call.  They are populated by the MCP tool
handler (app/mcp/server.py) after classification.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EngineResult(BaseModel):
    """A single normalised result item returned by any engine."""

    title: str
    snippet: str | None = None
    link: str | None = None
    thumbnail: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngineResponse(BaseModel):
    """
    Top-level envelope returned by every engine function and endpoint.

    On success ``success=True``, ``results`` contains one or more
    ``EngineResult`` objects, and ``result_count`` mirrors ``len(results)``.

    On failure ``success=False``, ``error`` contains a human-readable
    reason and ``results`` is an empty list.

    ``classified_as`` and ``confidence`` are populated by the MCP router
    after classification — they are ``None`` when calling engine endpoints
    directly.
    """

    success: bool
    engine: str
    error: str | None = None
    result_count: int = 0
    results: list[EngineResult] = Field(default_factory=list)
    classified_as: str | None = None
    confidence: float | None = None
