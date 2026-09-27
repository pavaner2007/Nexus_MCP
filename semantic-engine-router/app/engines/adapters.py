"""
app/engines/adapters.py
========================
Thin adapter layer that maps engine-specific trimmed dicts into the shared
``EngineResult`` schema.

Each adapter receives the dict already returned by the engine's internal
trimming function (``_trim_product`` / ``_trim_paper``) and maps it into
``EngineResult``.  No SerpApi calls, no field-trimming logic — only shape
translation.

Adding a new engine?  Add one ``adapt_<engine>_result()`` function here
and wire it into the engine module.  The shared contract handles the rest.
"""

from __future__ import annotations

from typing import Any

from app.schemas import EngineResult


# ---------------------------------------------------------------------------
# Shopping adapter
# ---------------------------------------------------------------------------


def adapt_shopping_result(raw: dict[str, Any]) -> EngineResult:
    """
    Map a trimmed shopping product dict (from ``_trim_product``) into
    an ``EngineResult``.

    Field mapping
    -------------
    * title      → ``EngineResult.title``
    * link       → ``EngineResult.link``
    * thumbnail  → ``EngineResult.thumbnail``
    * snippet    → synthesised as "{price} from {source}" (no natural
                   snippet exists in Shopping results)
    * price, extracted_price, source, rating, reviews
                 → ``EngineResult.metadata``  (engine-specific extras)
    """
    title: str = raw.get("title", "Unknown Product")

    price: str = raw.get("price", "")
    source: str = raw.get("source", "")
    if price and source:
        snippet: str | None = f"{price} from {source}"
    elif price:
        snippet = price
    elif source:
        snippet = f"From {source}"
    else:
        snippet = None

    metadata: dict[str, Any] = {}
    for field in ("price", "extracted_price", "source", "rating", "reviews"):
        if field in raw:
            metadata[field] = raw[field]

    return EngineResult(
        title=title,
        snippet=snippet,
        link=raw.get("link"),
        thumbnail=raw.get("thumbnail"),
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Scholar adapter
# ---------------------------------------------------------------------------


def adapt_scholar_result(raw: dict[str, Any]) -> EngineResult:
    """
    Map a trimmed scholar paper dict (from ``_trim_paper``) into an
    ``EngineResult``.

    Field mapping
    -------------
    * title      → ``EngineResult.title``
    * snippet    → ``EngineResult.snippet``  (the abstract excerpt)
    * link       → ``EngineResult.link``
    * thumbnail  → ``None``  (Scholar results have no thumbnail)
    * authors, publication, year, cited_by_count, pdf_link
                 → ``EngineResult.metadata``  (engine-specific extras)
    """
    title: str = raw.get("title", "Unknown Paper")

    metadata: dict[str, Any] = {}
    for field in ("authors", "publication", "year", "cited_by_count", "pdf_link"):
        if field in raw:
            metadata[field] = raw[field]

    return EngineResult(
        title=title,
        snippet=raw.get("snippet"),
        link=raw.get("link"),
        thumbnail=None,
        metadata=metadata,
    )
