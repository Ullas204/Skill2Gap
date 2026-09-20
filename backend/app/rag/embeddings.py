"""Embedding service with lazy loading and fallback chain.

Model loading is deferred to first use to avoid blocking imports.
Tries the configured model first, falls back to pseudo-embeddings.
"""

from __future__ import annotations

import hashlib
import math
import threading

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

_DIMENSION = 384
_model = None
_USE_REAL = False
_model_name = "pseudo-sha256"
_load_attempted = False
_lock = threading.Lock()


def _try_load_model() -> None:
    global _model, _USE_REAL, _model_name, _DIMENSION, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True

    try:
        from sentence_transformers import SentenceTransformer
        for candidate in [settings.embedding_model, "all-MiniLM-L6-v2"]:
            try:
                _model = SentenceTransformer(candidate)
                _DIMENSION = _model.get_sentence_embedding_dimension()
                _USE_REAL = True
                _model_name = candidate
                logger.info("Loaded embedding model: %s (dim=%d)", candidate, _DIMENSION)
                return
            except Exception as exc:
                logger.debug("Failed to load %s: %s", candidate, exc)
                _model = None
        logger.info("No embedding model loaded – using pseudo-embeddings (dim=%d)", _DIMENSION)
    except ImportError:
        logger.info("sentence-transformers not installed – using pseudo-embeddings (dim=%d)", _DIMENSION)


def _ensure_model() -> None:
    if not _load_attempted:
        with _lock:
            _try_load_model()


def _pseudo_embedding(text: str, dim: int = _DIMENSION) -> list[float]:
    h = hashlib.sha256(text.encode()).digest()
    raw = []
    for i in range(dim):
        byte_val = h[i % len(h)]
        raw.append((byte_val / 255.0) * 2 - 1)
    norm = math.sqrt(sum(v * v for v in raw))
    return [v / norm for v in raw] if norm else raw


class EmbeddingService:
    def embed(self, texts: list[str]) -> list[list[float]]:
        _ensure_model()
        if _USE_REAL and _model is not None:
            return _model.encode(texts, show_progress_bar=False).tolist()
        return [_pseudo_embedding(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        _ensure_model()
        return _DIMENSION

    @property
    def model_name(self) -> str:
        _ensure_model()
        return _model_name


embedding_service = EmbeddingService()
