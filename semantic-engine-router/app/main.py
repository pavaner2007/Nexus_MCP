"""
app/main.py
===========
FastAPI application entry point for the Semantic Engine Router.

Phase 2 additions
-----------------
* FastAPI ``lifespan`` context manager loads centroid vectors once at
  server startup and stores them on ``app.state.centroids``.
* POST /classify endpoint accepts a query string and returns per-engine
  confidence scores plus the top-2 ranked categories.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.config import settings  # noqa: F401  — validates SERPAPI_KEY at startup
from app.classifier.centroids import load_centroids
from app.engines.shopping import search_shopping
from app.engines.scholar import search_scholar
from app.classifier.classify import classify, classify_top
from app.schemas import EngineResponse

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
    # Nothing to clean up on shutdown in Phase 2.


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Semantic Engine Router",
    description=(
        "MCP-native routing layer that maps natural-language queries to the "
        "correct SerpApi engine via a lightweight semantic classifier."
    ),
    version="0.2.0",
    lifespan=lifespan,
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Meta"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns HTTP 200 when the service is up."""
    return {"status": "ok"}


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
