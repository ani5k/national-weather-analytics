"""
duplicate_detection/embeddings.py

Converts cleaned report text into semantic embeddings.

Prefers multilingual MiniLM (sentence-transformers) when available;
falls back to hashing so the pipeline still runs without the model.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

import numpy as np

_model = None
_backend = None  # "st" | "hash"
_cache: dict[str, np.ndarray] = {}

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "paraphrase-multilingual-MiniLM-L12-v2",
)
FORCE_ST = os.getenv("FORCE_MULTILINGUAL_ST", "1").strip() not in {"0", "false", "False"}


def _get_model():
    global _model, _backend
    if _backend is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
        _backend = "st"
    except Exception:
        if FORCE_ST:
            # Still allow hash fallback so demos don't crash; callers can check backend.
            _model = None
            _backend = "hash"
        else:
            _model = None
            _backend = "hash"
    return _model


def embedding_backend() -> str:
    _get_model()
    return _backend or "hash"


def _hash_embedding(text: str, dims: int = 256) -> np.ndarray:
    """Deterministic bag-of-tokens hash embedding (no external model)."""
    tokens = re.findall(r"[a-z0-9\u0900-\u097f]+", (text or "").lower())
    vec = np.zeros(dims, dtype=float)
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dims
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm:
        vec /= norm
    return vec


def get_embedding(text: str) -> Optional[np.ndarray]:
    """
    Convert report text into a semantic embedding (cached).

    Returns:
        A numerical vector representing the meaning of the text.
    """
    if not text:
        return None

    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]

    model = _get_model()
    if _backend == "st" and model is not None:
        vec = np.asarray(model.encode(text), dtype=float)
    else:
        vec = _hash_embedding(text)

    if len(_cache) > 4000:
        _cache.clear()
    _cache[key] = vec
    return vec


if __name__ == "__main__":
    text = "Heavy rain reported in Whitefield, Bengaluru"
    embedding = get_embedding(text)
    print("backend:", embedding_backend())
    print("Embedding generated successfully!")
    print("Vector size:", len(embedding))
    print("First 10 values:", embedding[:10])
