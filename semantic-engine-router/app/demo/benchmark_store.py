"""
app/demo/benchmark_store.py
============================
Phase 14 — Benchmark result cache layer.

Results are computed once and stored as JSON under ``app/demo/cache/``.
Subsequent requests read from disk — no recomputation, no SerpApi quota.

Cache files
-----------
  app/demo/cache/tokens.json    — token comparison result
  app/demo/cache/accuracy.json  — routing accuracy result
  app/demo/cache/latency.json   — latency benchmark result (may not exist)

Every cached payload includes a ``"generated_at"`` ISO 8601 timestamp.

Latency-specific behaviour
--------------------------
The latency benchmark makes *real* SerpApi calls, so it is NEVER run
automatically.  ``get_latency_benchmark(refresh=False)`` returns
``{"available": False, "message": "..."}`` if no cache file exists.
Only ``get_latency_benchmark(refresh=True)`` triggers a live run, and only
when the ``ALLOW_LIVE_BENCHMARKS`` env var is ``"true"``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache directory — created on import if it doesn't exist
# ---------------------------------------------------------------------------

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_TOKENS_FILE   = CACHE_DIR / "tokens.json"
_ACCURACY_FILE = CACHE_DIR / "accuracy.json"
_LATENCY_FILE  = CACHE_DIR / "latency.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> dict | None:
    """Return parsed JSON from *path*, or None if missing / corrupt."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write(path: Path, data: dict) -> None:
    """Write *data* (with generated_at timestamp) to *path*."""
    payload = {**data, "generated_at": datetime.now(tz=timezone.utc).isoformat()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("benchmark_store: wrote cache → %s", path.name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_token_benchmark(refresh: bool = False) -> dict[str, Any]:
    """
    Return cached token comparison result, computing it if necessary.

    Parameters
    ----------
    refresh:
        Force recomputation even if a cache file exists.
    """
    cached = _read(_TOKENS_FILE)
    if cached is not None and not refresh:
        return cached

    logger.info("benchmark_store: computing token benchmark …")
    from app.testing.benchmark_tokens import run_token_benchmark
    result = run_token_benchmark()
    _write(_TOKENS_FILE, result)
    return _read(_TOKENS_FILE)  # re-read so caller always gets generated_at


def get_accuracy_benchmark(refresh: bool = False) -> dict[str, Any]:
    """
    Return cached routing accuracy result, computing it if necessary.

    Parameters
    ----------
    refresh:
        Force recomputation even if a cache file exists.
    """
    cached = _read(_ACCURACY_FILE)
    if cached is not None and not refresh:
        return cached

    logger.info("benchmark_store: computing accuracy benchmark …")
    from app.testing.benchmark_accuracy import run_accuracy_benchmark
    result = run_accuracy_benchmark()
    _write(_ACCURACY_FILE, result)
    return _read(_ACCURACY_FILE)


async def get_latency_benchmark(refresh: bool = False) -> dict[str, Any]:
    """
    Return cached latency result, or an ``available=False`` sentinel.

    When *refresh* is True, the caller is responsible for verifying that
    ``ALLOW_LIVE_BENCHMARKS == "true"`` before calling this function.
    The store itself does not re-check that env var.

    Parameters
    ----------
    refresh:
        If True and no cache exists, run the live benchmark and cache it.
        If False and no cache exists, return the unavailable sentinel.
    """
    cached = _read(_LATENCY_FILE)
    if cached is not None and not refresh:
        return cached

    if not refresh:
        return {
            "available": False,
            "message": (
                "Latency benchmark has not been run yet. "
                "Execute: python -m app.testing.benchmark_latency"
            ),
        }

    logger.info("benchmark_store: running live latency benchmark …")
    from app.testing.benchmark_latency import run_latency_benchmark
    result = await run_latency_benchmark(iterations=3)
    result["available"] = True
    _write(_LATENCY_FILE, result)
    return _read(_LATENCY_FILE)
