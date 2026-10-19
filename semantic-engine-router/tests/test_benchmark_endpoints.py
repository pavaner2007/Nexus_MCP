"""
tests/test_benchmark_endpoints.py
====================================
Phase 14 — FastAPI endpoint tests for the 4 benchmark routes.

Uses TestClient with all store functions mocked — no network, no model loading.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

_STORE = "app.demo.benchmark_store"

FAKE_TOKEN = {
    "tokens_20_tools": 7116, "tokens_1_tool": 187, "tokens_saved": 6929,
    "percent_reduction": 97.4, "tool_count_20": 20, "breakdown": [],
    "generated_at": "2026-01-01T00:00:00+00:00",
}
FAKE_ACCURACY = {
    "overall_accuracy": 58.5, "per_category": {}, "misses": [],
    "total": 53, "total_correct": 31, "meta": {},
    "generated_at": "2026-01-01T00:00:00+00:00",
}
FAKE_LATENCY = {
    "available": True,
    "classification_overhead_ms": {"min": 10.0, "mean": 13.0, "median": 12.5, "max": 18.0, "count": 20},
    "single":   {"min": 300.0, "mean": 450.0, "median": 440.0, "max": 620.0, "count": 3},
    "dual":     {"min": 400.0, "mean": 550.0, "median": 530.0, "max": 720.0, "count": 3},
    "fallback": {"min": 280.0, "mean": 420.0, "median": 410.0, "max": 590.0, "count": 3},
    "meta": {"iterations": 3},
    "generated_at": "2026-01-01T00:00:00+00:00",
}
FAKE_UNAVAILABLE = {
    "available": False,
    "message": "Latency benchmark has not been run yet.",
}


@pytest.fixture()
def client(mocker):
    """TestClient with all benchmark store functions mocked."""
    mocker.patch(f"{_STORE}.get_token_benchmark",    return_value=FAKE_TOKEN)
    mocker.patch(f"{_STORE}.get_accuracy_benchmark", return_value=FAKE_ACCURACY)
    mocker.patch(f"{_STORE}.get_latency_benchmark",  return_value=FAKE_LATENCY)
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /demo/benchmarks/tokens
# ---------------------------------------------------------------------------


def test_tokens_endpoint_returns_200(client):
    r = client.get("/demo/benchmarks/tokens")
    assert r.status_code == 200


def test_tokens_endpoint_has_percent_reduction(client):
    data = client.get("/demo/benchmarks/tokens").json()
    assert "percent_reduction" in data


def test_tokens_endpoint_refresh_param_accepted(client):
    r = client.get("/demo/benchmarks/tokens?refresh=true")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /demo/benchmarks/accuracy
# ---------------------------------------------------------------------------


def test_accuracy_endpoint_returns_200(client):
    r = client.get("/demo/benchmarks/accuracy")
    assert r.status_code == 200


def test_accuracy_endpoint_has_overall_accuracy(client):
    data = client.get("/demo/benchmarks/accuracy").json()
    assert "overall_accuracy" in data


def test_accuracy_endpoint_refresh_param_accepted(client):
    r = client.get("/demo/benchmarks/accuracy?refresh=true")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /demo/benchmarks/latency — no refresh
# ---------------------------------------------------------------------------


def test_latency_endpoint_returns_200(client):
    r = client.get("/demo/benchmarks/latency")
    assert r.status_code == 200


def test_latency_endpoint_has_available_key(client):
    data = client.get("/demo/benchmarks/latency").json()
    assert "available" in data


def test_latency_refresh_without_env_var_returns_403(mocker):
    """refresh=true without ALLOW_LIVE_BENCHMARKS=true must return 403."""
    mocker.patch(f"{_STORE}.get_latency_benchmark", return_value=FAKE_LATENCY)
    import os
    mocker.patch.dict(os.environ, {}, clear=False)
    # Ensure ALLOW_LIVE_BENCHMARKS is absent
    os.environ.pop("ALLOW_LIVE_BENCHMARKS", None)
    from app.main import app
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/demo/benchmarks/latency?refresh=true")
    assert r.status_code == 403


def test_latency_refresh_with_env_var_allowed(mocker):
    """refresh=true with ALLOW_LIVE_BENCHMARKS=true should succeed."""
    import os
    mocker.patch.dict(os.environ, {"ALLOW_LIVE_BENCHMARKS": "true"})

    async def _fake_latency(refresh=False):
        return FAKE_LATENCY

    mocker.patch(f"{_STORE}.get_latency_benchmark", side_effect=_fake_latency)
    from app.main import app
    c = TestClient(app)
    r = c.get("/demo/benchmarks/latency?refresh=true")
    assert r.status_code == 200


def test_latency_unavailable_returns_200_not_error(mocker):
    """available=False sentinel is a normal 200, not an error status."""
    mocker.patch(f"{_STORE}.get_latency_benchmark", return_value=FAKE_UNAVAILABLE)
    from app.main import app
    c = TestClient(app)
    r = c.get("/demo/benchmarks/latency")
    assert r.status_code == 200
    assert r.json()["available"] is False


# ---------------------------------------------------------------------------
# GET /demo/benchmarks/tool-schemas
# ---------------------------------------------------------------------------


def test_tool_schemas_endpoint_returns_200(client):
    r = client.get("/demo/benchmarks/tool-schemas")
    assert r.status_code == 200


def test_tool_schemas_has_twenty_schemas(client):
    data = client.get("/demo/benchmarks/tool-schemas").json()
    assert "twenty_schemas" in data
    assert len(data["twenty_schemas"]) == 20


def test_tool_schemas_has_universal_schema(client):
    data = client.get("/demo/benchmarks/tool-schemas").json()
    assert "universal_schema" in data
    assert data["universal_schema"]["name"] == "Universal_Search"


def test_tool_schemas_count_matches_list(client):
    data = client.get("/demo/benchmarks/tool-schemas").json()
    assert data["count"] == len(data["twenty_schemas"])
