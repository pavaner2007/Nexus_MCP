"""
app/main.py
===========
FastAPI application entry point for the Semantic Engine Router.

Phase 1 exposes a single /health endpoint.
All routing logic, MCP server wiring, and SerpApi calls
are implemented in later phases.

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

# Importing settings at startup validates the environment immediately.
# If SERPAPI_KEY is missing the server will refuse to start with a clear error.
from app.config import settings  # noqa: F401  (imported for side-effect validation)

app = FastAPI(
    title="Semantic Engine Router",
    description=(
        "MCP-native routing layer that maps natural-language queries to the "
        "correct SerpApi engine via a lightweight semantic classifier."
    ),
    version="0.1.0",
)


@app.get("/health", tags=["Meta"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns HTTP 200 when the service is up."""
    return {"status": "ok"}
