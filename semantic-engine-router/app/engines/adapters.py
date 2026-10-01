"""
app/engines/adapters.py
========================
Thin adapter layer that maps engine-specific trimmed dicts into the shared
``EngineResult`` schema.

Each adapter receives the dict already returned by the engine's internal
trimming function (``_trim_product`` / ``_trim_paper`` / etc.) and maps it
into ``EngineResult``.  No SerpApi calls, no field-trimming logic — only
shape translation.

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


# ---------------------------------------------------------------------------
# Local adapter
# ---------------------------------------------------------------------------


def adapt_local_result(raw: dict[str, Any]) -> EngineResult:
    """
    Map a trimmed local business dict (from ``_trim_place``) into an
    ``EngineResult``.

    Field mapping
    -------------
    * title      → ``EngineResult.title``  (business name)
    * link       → ``EngineResult.link``
    * thumbnail  → ``EngineResult.thumbnail``
    * snippet    → synthesised as "{rating}★ · {type}"
                   (e.g. "4.5★ · Coffee Shop"); falls back to type or
                   address if rating / type are absent.
    * address, phone, rating, reviews, type, hours, open_now
                 → ``EngineResult.metadata``  (engine-specific extras)
    """
    title: str = raw.get("title", "Unknown Place")

    rating = raw.get("rating")
    place_type = raw.get("type", "")
    if rating is not None and place_type:
        snippet: str | None = f"{rating}★ · {place_type}"
    elif rating is not None:
        snippet = f"{rating}★"
    elif place_type:
        snippet = place_type
    elif raw.get("address"):
        snippet = raw["address"]
    else:
        snippet = None

    metadata: dict[str, Any] = {}
    for field in ("address", "phone", "rating", "reviews", "type", "hours", "open_now"):
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
# Patents adapter
# ---------------------------------------------------------------------------


def adapt_patents_result(raw: dict[str, Any]) -> EngineResult:
    """
    Map a trimmed patent dict (from ``_trim_patent``) into an
    ``EngineResult``.

    Field mapping
    -------------
    * title         → ``EngineResult.title``
    * snippet       → ``EngineResult.snippet``  (abstract excerpt)
    * link          → ``EngineResult.link``
    * thumbnail     → ``None``  (patents rarely have thumbnails)
    * patent_id, publication_number, inventor, assignee,
      filing_date, publication_date, pdf_link
                    → ``EngineResult.metadata``  (engine-specific extras)
    """
    title: str = raw.get("title", "Unknown Patent")

    metadata: dict[str, Any] = {}
    for field in (
        "patent_id",
        "publication_number",
        "inventor",
        "assignee",
        "filing_date",
        "publication_date",
        "pdf_link",
    ):
        if field in raw:
            metadata[field] = raw[field]

    return EngineResult(
        title=title,
        snippet=raw.get("snippet"),
        link=raw.get("link"),
        thumbnail=None,
        metadata=metadata,
    )
