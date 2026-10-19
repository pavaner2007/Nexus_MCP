"""
app/main.py
===========
FastAPI application entry point for the Semantic Engine Router.

Phase 13 additions
------------------
* CORS middleware for the Vite dev server (default http://localhost:5173).
  Configure allowed origins via the DEMO_CORS_ORIGINS env var
  (comma-separated list, e.g. "http://localhost:5173,https://my-demo.example.com").
* POST /demo/search   — full pipeline + routing metadata for the UI.
* GET  /demo/examples — 5 example queries to populate the UI chips.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
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
    version="0.13.0",
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
    """
    Query the Google Shopping SerpApi engine and return trimmed product results.

    * **success** — ``true`` if the call succeeded.
    * **results** — list of trimmed product objects (title, price, source, link …).
    * **error** — present only when ``success`` is ``false``.
    """
    return search_shopping(body.query, num_results=body.num_results)


@app.post("/engines/scholar", response_model=EngineResponse, tags=["Engines"])
async def scholar_search(body: ShoppingRequest) -> EngineResponse:
    """
    Query the Google Scholar SerpApi engine and return trimmed paper results.

    * **success** — ``true`` if the call succeeded.
    * **results** — list of trimmed paper objects (title, authors, year, cited_by_count …).
    * **error** — present only when ``success`` is ``false``.
    """
    return search_scholar(body.query, num_results=body.num_results)


@app.post("/engines/local", response_model=EngineResponse, tags=["Engines"])
async def local_search(body: ShoppingRequest) -> EngineResponse:
    """
    Query the Google Local SerpApi engine and return trimmed business results.

    * **success** — ``true`` if the call succeeded.
    * **results** — list of trimmed place objects (title, address, rating, type …).
    * **error** — present only when ``success`` is ``false``.
    """
    return search_local(body.query, num_results=body.num_results)


@app.post("/engines/patents", response_model=EngineResponse, tags=["Engines"])
async def patents_search(body: ShoppingRequest) -> EngineResponse:
    """
    Query the Google Patents SerpApi engine and return trimmed patent records.

    * **success** — ``true`` if the call succeeded.
    * **results** — list of trimmed patent objects (title, inventor, assignee, filing_date …).
    * **error** — present only when ``success`` is ``false``.
    """
    return search_patents(body.query, num_results=body.num_results)


# ---------------------------------------------------------------------------
# Endpoints — Classifier
# ---------------------------------------------------------------------------


@app.post("/classify", response_model=ClassifyResponse, tags=["Classifier"])
async def classify_query(body: ClassifyRequest, request: Request) -> ClassifyResponse:
    """
    Classify a natural-language query and return per-engine confidence scores.

    * **scores** — cosine-similarity score for each of the 5 engine categories.
    * **top_2** — the two highest-scoring categories, sorted descending.
    """
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
    """
    Return 5 representative example queries for the UI chips.

    Each item has ``label`` (display name) and ``query`` (the actual query string).
    """
    return [
        {"label": "Shopping",    "query": "iPhone 15 prices"},
        {"label": "Scholar",     "query": "recent quantum computing breakthroughs"},
        {"label": "Dual-route",  "query": "compare iPhone 15 prices with recent reviews"},
        {"label": "Local",       "query": "best coffee shops in Chennai"},
        {"label": "Fallback",    "query": "who is the president"},
    ]
