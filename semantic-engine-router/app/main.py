"""
app/main.py
===========
FastAPI application entry point for the Semantic Engine Router.

Phase 13 additions
------------------
* CORS middleware for the Vite dev server (default http://localhost:5173).
  Configure allowed origins via the DEMO_CORS_ORIGINS env var
  (comma-separated list).
* POST /demo/search   — full pipeline + routing metadata for the UI.
* GET  /demo/examples — 5 example queries to populate the UI chips.

Phase 14 additions
------------------
* GET /demo/benchmarks/tokens       — token comparison (cached).
* GET /demo/benchmarks/accuracy     — routing accuracy (cached).
* GET /demo/benchmarks/latency      — latency (cached or unavailable sentinel).
* GET /demo/benchmarks/tool-schemas — raw schema data for the UI.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings  # noqa: F401  — validates SERPAPI_KEY at startup
from app.classifier.centroids import load_centroids
from app.engines.shopping import search_shopping
from app.engines.scholar import search_scholar
from app.engines.local import search_local
from app.engines.patents import search_patents
from app.classifier.classify import classify, classify_top
from app.schemas import EngineResponse
from app.demo.service import run_demo_query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs once at startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load centroids (from cache or by building them) before serving requests."""
    logger.info("Lifespan: loading centroids …")
    app.state.centroids = load_centroids()
    logger.info("Lifespan: centroids ready (%d categories).", len(app.state.centroids))
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Semantic Engine Router",
    description=(
        "MCP-native routing layer that maps natural-language queries to the "
        "correct SerpApi engine via a lightweight semantic classifier."
    ),
    version="0.14.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any extra origins from env
# ---------------------------------------------------------------------------

_raw_origins = os.getenv("DEMO_CORS_ORIGINS", "http://localhost:5173")
_allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic I/O models
# ---------------------------------------------------------------------------


class ClassifyRequest(BaseModel):
    query: str


class ShoppingRequest(BaseModel):
    query: str
    num_results: int = 10


class ClassifyResponse(BaseModel):
    query: str
    scores: dict[str, float]
    top_2: list[tuple[str, float]]


class DemoSearchRequest(BaseModel):
    query: str


# ---------------------------------------------------------------------------
# Endpoints — Meta
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Meta"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns HTTP 200 when the service is up."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoints — Engines
# ---------------------------------------------------------------------------


@app.post("/engines/shopping", response_model=EngineResponse, tags=["Engines"])
async def shopping_search(body: ShoppingRequest) -> EngineResponse:
    """Query the Google Shopping SerpApi engine and return trimmed product results."""
    return search_shopping(body.query, num_results=body.num_results)


@app.post("/engines/scholar", response_model=EngineResponse, tags=["Engines"])
async def scholar_search(body: ShoppingRequest) -> EngineResponse:
    """Query the Google Scholar SerpApi engine and return trimmed paper results."""
    return search_scholar(body.query, num_results=body.num_results)


@app.post("/engines/local", response_model=EngineResponse, tags=["Engines"])
async def local_search(body: ShoppingRequest) -> EngineResponse:
    """Query the Google Local SerpApi engine and return trimmed business results."""
    return search_local(body.query, num_results=body.num_results)


@app.post("/engines/patents", response_model=EngineResponse, tags=["Engines"])
async def patents_search(body: ShoppingRequest) -> EngineResponse:
    """Query the Google Patents SerpApi engine and return trimmed patent records."""
    return search_patents(body.query, num_results=body.num_results)


# ---------------------------------------------------------------------------
# Endpoints — Classifier
# ---------------------------------------------------------------------------


@app.post("/classify", response_model=ClassifyResponse, tags=["Classifier"])
async def classify_query(body: ClassifyRequest, request: Request) -> ClassifyResponse:
    """Classify a natural-language query and return per-engine confidence scores."""
    centroids = request.app.state.centroids

    t0 = time.perf_counter()
    scores = classify(body.query, centroids)
    top_2 = classify_top(body.query, centroids, top_n=2)
    elapsed_ms = (time.perf_counter() - t0) * 1_000

    logger.info(
        "classify() — query=%r  top=%s (%.1f)  elapsed=%.2f ms",
        body.query,
        top_2[0][0] if top_2 else "—",
        top_2[0][1] if top_2 else 0.0,
        elapsed_ms,
    )

    return ClassifyResponse(query=body.query, scores=scores, top_2=top_2)


# ---------------------------------------------------------------------------
# Endpoints — Demo (Phase 13)
# ---------------------------------------------------------------------------


@app.post("/demo/search", tags=["Demo"])
async def demo_search(body: DemoSearchRequest) -> dict:
    """
    Run the full routing pipeline and return everything the UI needs.

    Returns classification scores for all 5 engines, the routing decision,
    engine results, and split timing data (classification vs engine-call ms).
    """
    return await run_demo_query(body.query)


@app.get("/demo/examples", tags=["Demo"])
async def demo_examples() -> list[dict[str, str]]:
    """Return 5 representative example queries for the UI chips."""
    return [
        {"label": "Shopping",   "query": "iPhone 15 prices"},
        {"label": "Scholar",    "query": "recent quantum computing breakthroughs"},
        {"label": "Dual-route", "query": "compare iPhone 15 prices with recent reviews"},
        {"label": "Local",      "query": "best coffee shops in Chennai"},
        {"label": "Fallback",   "query": "who is the president"},
    ]


# ---------------------------------------------------------------------------
# Endpoints — Benchmarks (Phase 14)
# ---------------------------------------------------------------------------


@app.get("/demo/benchmarks/tokens", tags=["Benchmarks"])
def benchmark_tokens(refresh: bool = False) -> dict:
    """
    Return cached token comparison benchmark result.

    Computes on first call and caches to disk. Subsequent calls are instant.
    Pass ``?refresh=true`` to force recomputation.
    """
    from app.demo.benchmark_store import get_token_benchmark
    return get_token_benchmark(refresh=refresh)


@app.get("/demo/benchmarks/accuracy", tags=["Benchmarks"])
def benchmark_accuracy(refresh: bool = False) -> dict:
    """
    Return cached routing-accuracy benchmark result.

    Computes on first call (loads embedding model — ~30 s).
    Subsequent calls are instant. Pass ``?refresh=true`` to force recomputation.
    """
    from app.demo.benchmark_store import get_accuracy_benchmark
    return get_accuracy_benchmark(refresh=refresh)


@app.get("/demo/benchmarks/latency", tags=["Benchmarks"])
async def benchmark_latency(refresh: bool = False) -> dict:
    """
    Return cached latency benchmark result.

    If no cache exists and ``refresh=false`` (default), returns
    ``{"available": false}`` — no SerpApi calls are made.

    ``refresh=true`` runs the live benchmark (real SerpApi calls, consumes
    quota) and is only permitted when ``ALLOW_LIVE_BENCHMARKS=true``.
    """
    if refresh and os.getenv("ALLOW_LIVE_BENCHMARKS") != "true":
        raise HTTPException(
            status_code=403,
            detail=(
                "Live latency benchmark is disabled. "
                "Set ALLOW_LIVE_BENCHMARKS=true to enable."
            ),
        )
    from app.demo.benchmark_store import get_latency_benchmark
    return await get_latency_benchmark(refresh=refresh)


@app.get("/demo/benchmarks/tool-schemas", tags=["Benchmarks"])
def benchmark_tool_schemas() -> dict:
    """
    Return the 20 mock engine schemas and the Universal_Search schema.

    Used by the UI's "Show what was counted" expandable section.
    """
    from app.testing.mock_tool_schemas import TWENTY_ENGINE_SCHEMAS, UNIVERSAL_SEARCH_SCHEMA
    return {
        "twenty_schemas": TWENTY_ENGINE_SCHEMAS,
        "universal_schema": UNIVERSAL_SEARCH_SCHEMA,
        "count": len(TWENTY_ENGINE_SCHEMAS),
    }
