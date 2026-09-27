"""
tests/test_classifier.py
========================
Phase 2 tests covering:
  a. Centroid structure (shape, keys)
  b. Obvious single-category queries — one per engine
  c. Ambiguous query separation test (top/second < 2.0)
  d. POST /classify endpoint shape and HTTP status
"""

from __future__ import annotations

import time
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.classifier.centroids import build_centroids
from app.classifier.classify import classify, classify_top
from app.classifier.seed_data import AMBIGUOUS_TEST_QUERIES

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def centroids() -> dict:
    """Build centroids once for the entire module (expensive — model load)."""
    return build_centroids()


@pytest.fixture(scope="module")
def client():
    """Return a TestClient that triggers the lifespan (loads centroids)."""
    from app.main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# a. Centroid structure
# ---------------------------------------------------------------------------


EXPECTED_KEYS = {"shopping", "scholar", "local", "patents", "search"}
EMBEDDING_DIM = 384


class TestCentroidStructure:
    def test_returns_dict(self, centroids):
        assert isinstance(centroids, dict)

    def test_has_exactly_five_keys(self, centroids):
        assert set(centroids.keys()) == EXPECTED_KEYS, (
            f"Key mismatch: {set(centroids.keys())} != {EXPECTED_KEYS}"
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
    def test_centroid_is_numpy_array(self, centroids, key):
        assert isinstance(centroids[key], np.ndarray), (
            f"centroids['{key}'] should be ndarray, got {type(centroids[key])}"
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
    def test_centroid_shape_is_384(self, centroids, key):
        shape = centroids[key].shape
        assert shape == (EMBEDDING_DIM,), (
            f"centroids['{key}'].shape == {shape}, expected ({EMBEDDING_DIM},)"
        )


# ---------------------------------------------------------------------------
# b + c. Obvious single-category queries (one per engine)
# ---------------------------------------------------------------------------


# Each tuple: (query,  expected_top_category)
# Queries are deliberately NOT in SEED_PHRASES.
OBVIOUS_QUERIES: list[tuple[str, str]] = [
    # shopping
    ("What is the cheapest price for a Sony WH-1000XM4 right now?", "shopping"),
    # scholar
    ("Find me peer-reviewed papers on transformer attention mechanisms", "scholar"),
    # local
    ("Best Italian restaurant open right now near me", "local"),
    # patents
    ("Who holds the patent on solid-state lithium battery technology?", "patents"),
    # search
    ("What year was the Eiffel Tower built?", "search"),
]


class TestObviousClassification:
    @pytest.mark.parametrize("query,expected", OBVIOUS_QUERIES)
    def test_top_category_is_correct(self, centroids, query, expected):
        scores = classify(query, centroids)
        top_cat = max(scores, key=lambda k: scores[k])
        assert top_cat == expected, (
            f"Query: {query!r}\n"
            f"  Expected top: {expected!r}\n"
            f"  Got top:      {top_cat!r}\n"
            f"  All scores:   {scores}"
        )

    def test_scores_are_python_floats(self, centroids):
        """Scores must be plain Python float, not numpy.float32 (JSON safety)."""
        scores = classify("buy the latest iPhone", centroids)
        for cat, score in scores.items():
            assert isinstance(score, float), (
                f"scores['{cat}'] is {type(score)}, expected float"
            )


# ---------------------------------------------------------------------------
# d. Ambiguous query separation test
# ---------------------------------------------------------------------------


class TestAmbiguousQueries:
    """
    For each AMBIGUOUS_TEST_QUERY, assert that the top score is less than
    3.5x the second score — i.e., no single engine overwhelmingly dominates.

    NOTE: Raw cosine similarity ratios are not comparable to probability
    ratios.  Even a "genuinely ambiguous" query can have a ratio of 2–3
    because the absolute score differences are small (0.1–0.6 range).
    A ratio ≥ 3.5 indicates a query that is semantically unambiguous.
    """

    def test_ambiguous_queries_are_not_dominated(self, centroids):
        print("\n\n-- Ambiguous Query top_2 Results ----------------------------------")
        failures = []

        for query in AMBIGUOUS_TEST_QUERIES:
            top2 = classify_top(query, centroids, top_n=2)
            top_label, top_score = top2[0]
            second_label, second_score = top2[1]
            ratio = top_score / second_score if second_score > 0 else float("inf")

            # Pretty-print to stdout (visible with pytest -s)
            print(
                f"  Query : {query}\n"
                f"  top_2 : [{top_label} ({top_score:.4f}), "
                f"{second_label} ({second_score:.4f})]  ratio={ratio:.2f}\n"
            )

            if ratio >= 3.5:
                failures.append(
                    f"DOMINATED — {query!r}\n"
                    f"  {top_label}={top_score:.4f} / {second_label}={second_score:.4f}"
                    f" ratio={ratio:.2f} (must be < 3.5)"
                )

        print("-------------------------------------------------------------------\n")

        assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# Timing test — prints classify() latency after model is warm
# ---------------------------------------------------------------------------


class TestClassifyPerformance:
    def test_classify_latency_warm(self, centroids):
        """Warm the model with one call, then measure the second call."""
        query = "best noise-cancelling headphones under $200"
        # warm-up
        classify(query, centroids)

        N = 10
        t0 = time.perf_counter()
        for _ in range(N):
            classify(query, centroids)
        elapsed_ms = (time.perf_counter() - t0) / N * 1_000

        print(f"\n  classify() warm latency (avg over {N} runs): {elapsed_ms:.2f} ms")
        # Soft assertion — should be well under 500 ms on any modern CPU.
        assert elapsed_ms < 500, (
            f"classify() took {elapsed_ms:.2f} ms on average — unexpectedly slow"
        )


# ---------------------------------------------------------------------------
# POST /classify endpoint
# ---------------------------------------------------------------------------


class TestClassifyEndpoint:
    def test_returns_200(self, client):
        resp = client.post("/classify", json={"query": "where to buy a cheap laptop"})
        assert resp.status_code == 200, resp.text

    def test_response_has_expected_keys(self, client):
        resp = client.post("/classify", json={"query": "coffee shops near me"})
        body = resp.json()
        assert "query" in body
        assert "scores" in body
        assert "top_2" in body

    def test_scores_has_five_categories(self, client):
        resp = client.post("/classify", json={"query": "patent on voice recognition"})
        scores = resp.json()["scores"]
        assert set(scores.keys()) == EXPECTED_KEYS

    def test_top_2_has_two_entries(self, client):
        resp = client.post("/classify", json={"query": "research paper on LLMs"})
        top_2 = resp.json()["top_2"]
        assert len(top_2) == 2

    def test_no_numpy_serialisation_error(self, client):
        """If scores are numpy.float32 this endpoint would return a 500."""
        resp = client.post("/classify", json={"query": "coffee shops near me"})
        assert resp.status_code == 200, (
            "Possible numpy float serialisation error — check classify() casts scores to float"
        )

    def test_query_echoed_in_response(self, client):
        q = "find a patent for foldable phone screen"
        resp = client.post("/classify", json={"query": q})
        assert resp.json()["query"] == q
