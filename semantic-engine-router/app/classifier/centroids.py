"""
app/classifier/centroids.py
============================
Build, save, and load per-category centroid vectors.

A centroid is the mean embedding of all seed phrases for a given engine
category. At classification time we compare a query embedding to each
centroid via cosine similarity.

File paths are always resolved relative to THIS file using pathlib so
that the cached .npz is stored alongside the source regardless of which
directory the test runner or server is launched from.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from app.classifier.seed_data import SEED_PHRASES

logger = logging.getLogger(__name__)

# Default on-disk cache lives next to this source file.
_DEFAULT_PATH: Path = Path(__file__).parent / "centroids.npz"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_centroids() -> dict[str, np.ndarray]:
    """
    Compute mean embedding (centroid) for every category in SEED_PHRASES.

    Logs the wall-clock time taken so you can track model warm-up cost.

    Returns
    -------
    dict[str, np.ndarray]
        Mapping of category name -> centroid vector of shape (384,).
    """
    # Import here to decouple build-time from import-time model loading.
    from app.classifier.embedder import embed_texts

    logger.info("Building centroids for %d categories …", len(SEED_PHRASES))
    t0 = time.perf_counter()

    centroids: dict[str, np.ndarray] = {}
    for category, phrases in SEED_PHRASES.items():
        logger.debug("  Embedding %d phrases for category '%s' …", len(phrases), category)
        embeddings = embed_texts(phrases)            # shape (N, 384)
        centroid = embeddings.mean(axis=0)           # shape (384,)
        # Re-normalise the centroid so dot-product == cosine similarity.
        norm = np.linalg.norm(centroid)
        centroid = centroid / norm if norm > 0 else centroid
        centroids[category] = centroid

    elapsed = time.perf_counter() - t0
    logger.info("build_centroids() completed in %.3f s", elapsed)
    return centroids


def save_centroids(
    path: Path | str,
    centroids: dict[str, np.ndarray],
) -> None:
    """
    Persist *centroids* to *path* in NumPy's compressed .npz format.

    Parameters
    ----------
    path:
        Destination file path (will be created / overwritten).
    centroids:
        Dict mapping category name -> centroid ndarray.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(str(path), **centroids)
    logger.info("Centroids saved to '%s'.", path)


def load_centroids(
    path: Path | str | None = None,
) -> dict[str, np.ndarray]:
    """
    Load centroids from *path*.  If the file doesn't exist, build and
    save them first (cold-start behaviour).

    Parameters
    ----------
    path:
        Path to the .npz file.  Defaults to the sibling ``centroids.npz``.

    Returns
    -------
    dict[str, np.ndarray]
        Mapping of category name -> centroid ndarray.
    """
    if path is None:
        path = _DEFAULT_PATH
    path = Path(path)

    if path.exists():
        logger.info("Loading cached centroids from '%s' …", path)
        data = np.load(str(path))
        centroids = {key: data[key] for key in data.files}
        logger.info("Centroids loaded (%d categories).", len(centroids))
        return centroids

    logger.info("No cached centroids found at '%s'. Building from scratch …", path)
    centroids = build_centroids()
    save_centroids(path, centroids)
    return centroids
