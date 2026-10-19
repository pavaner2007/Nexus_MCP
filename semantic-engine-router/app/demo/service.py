"""
app/demo/service.py
====================
Phase 13 — Demo query service.

Runs the full real pipeline for one query and returns a single structured
dict the frontend can render directly.

Return shape
------------
{
    "query": str,
    "scores": {                         # all 5 raw cosine scores
        "shopping": float,
        "scholar":  float,
        "local":    float,
        "patents":  float,
        "search":   float,
    },
    "thresholds": {
        "min_confidence": float,        # MIN_CONFIDENCE_THRESHOLD
        "dual_route_gap": float,        # DUAL_ROUTE_THRESHOLD
    },
    "route": {
        "mode":       "single" | "dual" | "fallback",
        "categories": list[str],
    },
    "response": dict,                   # EngineResponse.model_dump()
    "timings_ms": {
        "classification": float,
        "engine_calls":   float,
        "total":          float,
    },
}

Never raises — all errors are caught and returned as a structured failure.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.classifier.centroids import load_centroids
from app.classifier.classify import classify, classify_top
from app.routing.router import (
    MIN_CONFIDENCE_THRESHOLD,
    DUAL_ROUTE_THRESHOLD,
    decide_route,
    execute_route,
)
from app.schemas import EngineResponse, EngineResult

logger = logging.getLogger(__name__)

# Module-level centroid cache — loaded lazily on first demo call.
_centroids: dict | None = None


def _get_centroids() -> dict:
    global _centroids
    if _centroids is None:
        logger.info("demo/service: loading centroids …")
        _centroids = load_centroids()
    return _centroids


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_demo_query(query: str) -> dict[str, Any]:
    """
    Run the full pipeline for *query* and return a render-ready dict.

    Parameters
    ----------
    query:
        Raw natural-language search query from the UI.

    Returns
    -------
    dict
        Always returns the documented shape — never raises.
    """
    t_total_start = time.perf_counter()

    try:
        centroids = _get_centroids()

        # ── Classification ────────────────────────────────────────────────
        t_classify_start = time.perf_counter()

        # Full scores for all 5 categories (for confidence bars)
        all_scores: dict[str, float] = classify(query, centroids)
        # Top-2 for routing decision
        top2 = classify_top(query, centroids, top_n=2)

        classification_ms = (time.perf_counter() - t_classify_start) * 1_000

        # ── Routing decision ──────────────────────────────────────────────
        decision = decide_route(top2)

        # ── Engine execution ──────────────────────────────────────────────
        t_engine_start = time.perf_counter()
        response: EngineResponse = await execute_route(query, decision)
        engine_ms = (time.perf_counter() - t_engine_start) * 1_000

        total_ms = (time.perf_counter() - t_total_start) * 1_000

        return {
            "query": query,
            "scores": {
                "shopping": round(all_scores.get("shopping", 0.0), 4),
                "scholar":  round(all_scores.get("scholar",  0.0), 4),
                "local":    round(all_scores.get("local",    0.0), 4),
                "patents":  round(all_scores.get("patents",  0.0), 4),
                "search":   round(all_scores.get("search",   0.0), 4),
            },
            "thresholds": {
                "min_confidence": MIN_CONFIDENCE_THRESHOLD,
                "dual_route_gap": DUAL_ROUTE_THRESHOLD,
            },
            "route": {
                "mode":       decision["mode"],
                "categories": decision["categories"],
            },
            "response": response.model_dump(),
            "timings_ms": {
                "classification": round(classification_ms, 2),
                "engine_calls":   round(engine_ms, 2),
                "total":          round(total_ms, 2),
            },
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_demo_query(%r) failed: %s", query, exc)
        total_ms = (time.perf_counter() - t_total_start) * 1_000
        # Return structured failure — never raise to the HTTP layer.
        error_response = EngineResponse(
            success=False,
            engine="unknown",
            error=str(exc),
        )
        return {
            "query": query,
            "scores": {k: 0.0 for k in ("shopping", "scholar", "local", "patents", "search")},
            "thresholds": {
                "min_confidence": MIN_CONFIDENCE_THRESHOLD,
                "dual_route_gap": DUAL_ROUTE_THRESHOLD,
            },
            "route": {"mode": "fallback", "categories": ["search"]},
            "response": error_response.model_dump(),
            "timings_ms": {
                "classification": 0.0,
                "engine_calls":   0.0,
                "total":          round(total_ms, 2),
            },
        }
