"""Item 111: Local-inference storage index — $0-local cosine recall over all storage.

Embeds arbitrary local-storage records (vault notes / SurrealDB rows / files) via an
INJECTED encoder and builds a queryable in-memory cosine-similarity index, so recall
over ALL storage tiers is end-to-end local (no cloud embeddings needed).

Composable with:
  - item-108 ``loop_recall_context`` (vault/neuron recall backend)
  - item-109 ``decay_weighted_rank`` (recency-decay on retrieved hits)
  - CA1 ``SemanticCache`` cosine infrastructure (same encoder contract)

The encoder contract: ``Callable[[str], np.ndarray]`` — same type as the CA1 cache
tests use.  Pass the ``nomic-embed-text-v2-moe`` encoder from lemonade :13305 in
production; pass a deterministic stub in pytest (no live :13305 / SurrealDB needed).

Report-only / additive (the index BUILD — wiring it as the live recall backend is the
gated behaviour-change step for a future item).  Pure given the injected encoder.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

# Encoder contract: text → unit-normalised embedding vector.
Encoder = Callable[[str], np.ndarray]


@dataclass(frozen=True)
class RetrievedRecord:
    """A record retrieved from the local storage index with its cosine score (item 111).

    Attributes
    ----------
    record:
        The original record object from the indexed corpus.
    score:
        Cosine similarity between the query embedding and this record's embedding.
        Range: [-1, 1]; higher is more similar.
    """

    record: Any
    score: float


class LocalStorageIndex:
    """In-memory cosine-similarity index over local-storage records (item 111).

    Encodes each record at build time via the injected encoder.  At query time,
    encodes the query and returns the top-k nearest records by cosine similarity
    in descending order.

    Pure given the encoder (no live DB call, no network).  Use a stub encoder in
    pytest and the nomic-embed lemonade encoder in production.
    """

    def __init__(
        self,
        records: list[Any],
        *,
        encoder: Encoder,
    ) -> None:
        """Build the index from a list of records.

        Args:
            records:
                The corpus to index.  Each record is passed to ``str()`` before
                encoding (consistent with how ``SemanticCache`` encodes cache keys).
            encoder:
                Callable that maps a string to a (possibly unnormalised) numpy vector.
                The index normalises all vectors internally.
        """
        self._records: list[Any] = list(records)
        self._matrix: np.ndarray | None = None  # (N, D) float32 after build

        if self._records:
            vecs = np.stack(
                [_normalise(encoder(str(r))) for r in self._records],
                axis=0,
            ).astype(np.float32)
            self._matrix = vecs
        self._encoder = encoder

    def query(self, text: str, *, k: int = 5) -> list[RetrievedRecord]:
        """Return the top-k most-similar records to ``text`` by cosine similarity.

        Args:
            text:
                The query string (encoded via the same injected encoder).
            k:
                Maximum number of results to return.  Clamped to the corpus size.

        Returns:
            List of :class:`RetrievedRecord` sorted by ``score`` descending.
            Empty corpus → ``[]``.  ``k > len(corpus)`` → returns all records.
        """
        if self._matrix is None or len(self._records) == 0:
            return []

        q_vec = _normalise(self._encoder(str(text))).astype(np.float32)
        # Cosine similarities: (N,) dot product of each row with the query vector.
        scores: np.ndarray = self._matrix @ q_vec  # shape (N,)

        top_k = min(k, len(self._records))
        # Stable descending sort: argsort of negated scores (np.argsort is stable).
        indices = np.argsort(-scores, kind="stable")[:top_k]

        return [RetrievedRecord(record=self._records[i], score=float(scores[i])) for i in indices]


def _normalise(vec: np.ndarray) -> np.ndarray:
    """Return the L2-normalised vector; return the zero vector unchanged."""
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        return vec.astype(np.float32)
    return (vec / norm).astype(np.float32)
