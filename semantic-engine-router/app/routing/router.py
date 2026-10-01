"""
app/routing/router.py
======================
Three-mode routing logic for Universal_Search.

Decision algorithm
------------------
``classify_top`` returns a ranked list of ``(category, score)`` pairs.

1. **Fallback** — if the top score is strictly below ``MIN_CONFIDENCE_THRESHOLD``,
   none of the specialist engines is trustworthy.  Route to the base Google
   Search fallback immediately.
2. **Dual** — if the gap between #1 and #2 scores is <= ``DUAL_ROUTE_THRESHOLD``,
   both engines are queried concurrently and results merged.
3. **Single** — the top-1 specialist engine is called.

ENGINE_MAP
----------
Maps each category name to its synchronous engine function.

Adding a new engine in a future phase?
  1. Implement ``search_<engine>(query, num_results) -> EngineResponse``
  2. Add it to ``ENGINE_MAP``.
  3. No changes needed here — routing picks it up automatically.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.schemas import EngineResponse, EngineResult
from app.engines.shopping import search_shopping
from app.engines.scholar import search_scholar
from app.engines.local import search_local
from app.engines.patents import search_patents
from app.engines.fallback import search_fallback

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------

DUAL_ROUTE_THRESHOLD: float = 0.15
"""
Gap (top-1 score − top-2 score) at or below which BOTH engines are queried.
Raise this to make dual-routing more aggressive; lower it to make it rarer.
"""

MIN_CONFIDENCE_THRESHOLD: float = 0.35
"""
Minimum top-1 score for any specialist engine to be trusted.
Below this, the query is ambiguous / out-of-domain and falls back to plain
Google Search.  Raise to make fallback more frequent; lower to reduce it.
"""

# ---------------------------------------------------------------------------
# Engine map
# ---------------------------------------------------------------------------

ENGINE_MAP: dict[str, Callable | None] = {
    "shopping": search_shopping,
    "scholar":  search_scholar,
    "local":    search_local,
    "patents":  search_patents,
    "search":   search_fallback,   # Phase 9 — now implemented
}


# ---------------------------------------------------------------------------
# Route decision
# ---------------------------------------------------------------------------


def decide_route(scores: list[tuple[str, float]]) -> dict[str, Any]:
    """
    Decide between fallback, single-engine, and dual-engine routing.

    Parameters
    ----------
    scores:
        Ordered list of ``(category, score)`` pairs, highest score first.
        Must have at least one entry.

    Returns
    -------
    dict with keys:
        ``mode``       — ``"fallback"``, ``"single"``, or ``"dual"``
        ``categories`` — ``["search"]`` (fallback), ``[cat]`` (single),
                         or ``[cat1, cat2]`` (dual)
        ``scores``     — the original scores list (carried forward for
                         ``route_detail`` and ``confidence`` injection)

    Priority order
    --------------
    1. Fallback check (top score < MIN_CONFIDENCE_THRESHOLD) — evaluated first.
    2. Dual check (gap ≤ DUAL_ROUTE_THRESHOLD).
    3. Single (default).
    """
    if not scores:
        raise ValueError("scores must be non-empty")

    top1_cat, top1_score = scores[0]

    # ── 1. Fallback: low-confidence top score ─────────────────────────────
    if top1_score < MIN_CONFIDENCE_THRESHOLD:
        logger.info(
            "decide_route: FALLBACK — top=%r score=%.3f < threshold=%.2f",
            top1_cat, top1_score, MIN_CONFIDENCE_THRESHOLD,
        )
        return {"mode": "fallback", "categories": ["search"], "scores": scores}

    # ── 2. Only one score: must be single ─────────────────────────────────
    if len(scores) < 2:
        return {"mode": "single", "categories": [top1_cat], "scores": scores}

    top2_cat, top2_score = scores[1]
    gap = round(top1_score - top2_score, 10)

    # ── 3. Dual: top-2 are close ──────────────────────────────────────────
    if gap <= DUAL_ROUTE_THRESHOLD:
        logger.info(
            "decide_route: DUAL — %r=%.3f, %r=%.3f (gap=%.3f ≤ threshold=%.2f)",
            top1_cat, top1_score, top2_cat, top2_score, gap, DUAL_ROUTE_THRESHOLD,
        )
        return {"mode": "dual", "categories": [top1_cat, top2_cat], "scores": scores}

    # ── 4. Single ─────────────────────────────────────────────────────────
    logger.info(
        "decide_route: SINGLE — %r=%.3f (gap=%.3f > threshold=%.2f)",
        top1_cat, top1_score, gap, DUAL_ROUTE_THRESHOLD,
    )
    return {"mode": "single", "categories": [top1_cat], "scores": scores}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _stub_response(category: str) -> EngineResponse:
    """Return a 'not yet implemented' stub for unmapped engines."""
    return EngineResponse(
        success=False,
        engine=category,
        error="Engine not yet implemented",
    )


async def _run_engine(category: str, query: str) -> EngineResponse:
    """
    Call a single engine asynchronously.

    Synchronous engine functions are offloaded to a thread via
    ``asyncio.to_thread`` so they never block the event loop.
    A ``None`` mapping in ``ENGINE_MAP`` returns a stub immediately.
    """
    engine_func = ENGINE_MAP.get(category)
    if engine_func is None:
        return _stub_response(category)
    return await asyncio.to_thread(engine_func, query)


def _inject_source_engine(result: EngineResult, category: str) -> EngineResult:
    """Return a copy of ``result`` with ``source_engine`` added to ``metadata``."""
    return result.model_copy(
        update={"metadata": {**result.metadata, "source_engine": category}}
    )


# ---------------------------------------------------------------------------
# Route executor
# ---------------------------------------------------------------------------


async def execute_route(query: str, route_decision: dict[str, Any]) -> EngineResponse:
    """
    Execute a routing decision and return a fully populated ``EngineResponse``.

    Single mode
    -----------
    Calls the top-1 engine (or returns a stub if unmapped), then injects
    ``classified_as`` and ``confidence`` from the classifier scores.

    Dual mode
    ---------
    Calls BOTH engines concurrently via ``asyncio.gather`` with
    ``return_exceptions=True`` (no engine failure can crash the merge).

    Merged response fields:
      * ``engine``       — ``"dual:<cat1>+<cat2>"``
      * ``results``      — cat1 results + cat2 results, each tagged with
                           ``source_engine`` in their ``metadata``
      * ``result_count`` — total results from both engines
      * ``classified_as``— ``"dual"``
      * ``confidence``   — average of both scores (4 dp)
      * ``route_detail`` — per-engine score dict; on partial failure also
                           includes ``"<cat>_error"`` keys

    Partial failure is preferred over total failure — if one engine errors,
    the other engine's results are still returned.
    """
    mode: str = route_decision["mode"]
    categories: list[str] = route_decision["categories"]
    raw_scores: list[tuple[str, float]] = route_decision["scores"]
    score_map: dict[str, float] = {cat: sc for cat, sc in raw_scores}

    # ── Fallback mode ────────────────────────────────────────────────────────
    if mode == "fallback":
        top_cat, top_score = raw_scores[0] if raw_scores else ("unknown", 0.0)
        logger.info(
            "execute_route: fallback — top category was %r (%.3f), routing to search",
            top_cat, top_score,
        )
        result = await asyncio.to_thread(search_fallback, query)
        result.classified_as = "search (fallback)"
        result.confidence = round(top_score, 4)
        route_detail: dict[str, Any] = {cat: round(sc, 4) for cat, sc in raw_scores[:2]}
        route_detail["fallback_reason"] = (
            f"top score {top_score:.3f} < threshold {MIN_CONFIDENCE_THRESHOLD}"
        )
        result.route_detail = route_detail
        return result

    # ── Single mode ──────────────────────────────────────────────────────────
    if mode == "single":
        category = categories[0]
        engine_func = ENGINE_MAP.get(category)

        if engine_func is None:
            return EngineResponse(
                success=False,
                engine=category,
                error="Engine not yet implemented",
                classified_as=category,
                confidence=score_map.get(category),
            )

        result = await asyncio.to_thread(engine_func, query)
        result.classified_as = category
        result.confidence = score_map.get(category)
        return result

    # ── Dual mode ────────────────────────────────────────────────────────────
    cat1, cat2 = categories[0], categories[1]
    score1 = score_map.get(cat1, 0.0)
    score2 = score_map.get(cat2, 0.0)

    logger.info(
        "execute_route: dual — querying %r (%.3f) and %r (%.3f) concurrently",
        cat1, score1, cat2, score2,
    )

    raw1, raw2 = await asyncio.gather(
        _run_engine(cat1, query),
        _run_engine(cat2, query),
        return_exceptions=True,
    )

    route_detail: dict[str, Any] = {cat1: score1, cat2: score2}
    merged_results: list[EngineResult] = []

    for cat, raw in ((cat1, raw1), (cat2, raw2)):
        if isinstance(raw, Exception):
            logger.warning("execute_route: %r raised %s — %s", cat, type(raw).__name__, raw)
            route_detail[f"{cat}_error"] = str(raw)
        elif not raw.success:
            logger.warning("execute_route: %r returned failure: %s", cat, raw.error)
            route_detail[f"{cat}_error"] = raw.error or "engine returned failure"
        else:
            for item in raw.results:
                merged_results.append(_inject_source_engine(item, cat))

    return EngineResponse(
        success=True,
        engine=f"dual:{cat1}+{cat2}",
        result_count=len(merged_results),
        results=merged_results,
        classified_as="dual",
        confidence=round((score1 + score2) / 2, 4),
        route_detail=route_detail,
    )
