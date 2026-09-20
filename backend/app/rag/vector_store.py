"""In-memory vector store with optional FAISS acceleration.

Falls back to brute-force cosine similarity when FAISS is not installed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import faiss
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False
    logger.info("FAISS not available – using brute-force similarity search")


@dataclass
class VectorEntry:
    id: str
    embedding: list[float]
    content: str
    source_type: str = ""
    source_id: str = ""
    metadata: dict = field(default_factory=dict)


class VectorStore:
    def __init__(self) -> None:
        self._entries: list[VectorEntry] = []
        self._index = None
        self._dimension = 0
        self._dirty = True

    def add(self, entry: VectorEntry) -> None:
        self._entries.append(entry)
        self._dirty = True

    def add_batch(self, entries: list[VectorEntry]) -> None:
        self._entries.extend(entries)
        self._dirty = True

    def _build_index(self) -> None:
        if not self._entries:
            return
        self._dimension = len(self._entries[0].embedding)
        vectors = np.array([e.embedding for e in self._entries], dtype=np.float32)

        if _HAS_FAISS:
            self._index = faiss.IndexFlatIP(self._dimension)
            faiss.normalize_L2(vectors)
            self._index.add(vectors)
        else:
            self._index = vectors

        self._dirty = False

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[VectorEntry, float]]:
        if not self._entries:
            return []

        if self._dirty or self._index is None:
            self._build_index()

        q = np.array([query_embedding], dtype=np.float32)

        if _HAS_FAISS and self._index is not None:
            faiss.normalize_L2(q)
            k = min(top_k, len(self._entries))
            distances, indices = self._index.search(q, k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self._entries):
                    results.append((self._entries[idx], float(dist)))
            return results

        if isinstance(self._index, np.ndarray):
            norms = np.linalg.norm(self._index, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            normed = self._index / norms
            q_norm = q / (np.linalg.norm(q) or 1)
            scores = normed @ q_norm.T
            scores = scores.flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [(self._entries[i], float(scores[i])) for i in top_indices]

        return []

    def remove(self, entry_id: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.id != entry_id]
        if len(self._entries) < before:
            self._dirty = True
            return True
        return False

    def clear(self) -> None:
        self._entries.clear()
        self._index = None
        self._dirty = True

    def __len__(self) -> int:
        return len(self._entries)


vector_store = VectorStore()
