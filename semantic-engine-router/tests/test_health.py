"""
tests/test_health.py
====================
Smoke test for the /health endpoint.

Uses the HTTPX-based TestClient so the test runs fully synchronously
without needing a running server.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a synchronous HTTPX test client wrapping the FastAPI app."""
    return TestClient(app)


def test_health_returns_200(client: TestClient) -> None:
    """GET /health must respond with HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200, (
        f"Expected 200 but got {response.status_code}. Body: {response.text}"
    )


def test_health_returns_ok_payload(client: TestClient) -> None:
    """GET /health must return exactly {\"status\": \"ok\"}."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}, (
        f"Unexpected payload: {response.json()}"
    )
