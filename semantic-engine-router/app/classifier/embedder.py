"""
app/classifier/embedder.py
==========================
Lazy-loading singleton wrapper around the SentenceTransformer model.

The model is loaded ONCE per process and reused for all subsequent calls.
`lru_cache(maxsize=None)` on a no-arg function is the cleanest way to
achieve a module-level singleton without managing a mutable global.

Model: all-MiniLM-L6-v2
  - 384-dimensional output
  - ~22 MB on disk (CPU-friendly)
  - Fast enough for real-time single-query inference
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=None)
def get_model() -> SentenceTransformer:
    """Load and return the SentenceTransformer model (cached after first call)."""
    logger.info("Loading SentenceTransformer model '%s' …", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded successfully.")
    return model


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Return a 2-D numpy array of shape (len(texts), 384) containing
    the sentence embeddings for *texts*.

    Parameters
    ----------
    texts:
        A list of raw strings to encode.

    Returns
    -------
    np.ndarray
        Float32 array of shape (N, 384).
    """
    model = get_model()
    # show_progress_bar=False keeps logs clean during tests / server startup.
    embeddings: np.ndarray = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True,  # unit-norm → cosine sim == dot product
    )
    return embeddings  # type: ignore[return-value]
