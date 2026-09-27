"""
app/classifier/classify.py
==========================
Core classification logic: given a raw query and a centroid dict,
return a confidence score per engine category.

Cosine similarity is used as the distance metric. Because embed_texts()
normalises all embeddings to unit length (normalize_embeddings=True),
cosine similarity reduces to a plain dot product, which is O(D) and
branch-free.

Returned scores are cast to Python `float` — NOT numpy.float32 — so
FastAPI / json.dumps() can serialise them without a custom encoder.
"""

from __future__ import annotations

import numpy as np


def classify(
    query: str,
    centroids: dict[str, np.ndarray],
) -> dict[str, float]:
    """
    Return a cosine-similarity confidence score for each engine category.

    Parameters
    ----------
    query:
        Raw natural-language query string.
    centroids:
        Dict mapping category name -> centroid vector (unit-norm, shape (384,)).

    Returns
    -------
    dict[str, float]
        ``{"shopping": 0.82, "scholar": 0.31, ...}`` — scores do NOT sum to 1.
    """
    # Import here to avoid a circular import at module level.
    from app.classifier.embedder import embed_texts

    # embed_texts returns shape (1, 384); squeeze to (384,).
    query_vec: np.ndarray = embed_texts([query])[0]

    scores: dict[str, float] = {}
    for category, centroid in centroids.items():
        # Both vectors are unit-norm → dot product == cosine similarity.
        raw_score: np.floating = np.dot(query_vec, centroid)
        # Cast to Python float to ensure JSON serialisability.
        scores[category] = float(raw_score)

    return scores


def classify_top(
    query: str,
    centroids: dict[str, np.ndarray],
    top_n: int = 2,
) -> list[tuple[str, float]]:
    """
    Return the top-*n* categories sorted by confidence score (descending).

    Parameters
    ----------
    query:
        Raw natural-language query string.
    centroids:
        Dict mapping category name -> centroid vector.
    top_n:
        Number of categories to return. Defaults to 2.

    Returns
    -------
    list[tuple[str, float]]
        E.g. ``[("shopping", 0.82), ("search", 0.45)]``
    """
    scores = classify(query, centroids)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:top_n]
