"""Semantic retrieval over pre-embedded reference corpora on disk.

Corpora live in ``~/.cohezion/corpora`` as a pair of files per corpus:
  ``<name>_vectors.npy``  L2-normalised float32 embeddings, one row per chunk
  ``<name>_meta.json``    list of dicts, same order, each with at least ``text``

They are built offline (see ``scratchpad`` build scripts) using the same
``nomic-embed-text-v2-moe-GGUF`` model this module queries with, so query and corpus vectors
share a space. Nothing here embeds at build time; this is the READ side only.

Why this exists: two corpora were embedded and written to disk with no consumer — a producer
with no reader is dormant capability, not capability. ``KnowledgeMCP.search_knowledge`` is the
consumer; it was doing substring matching while documenting itself as "semantic search", so
wiring this in closes the producer→consumer gap and makes the docstring true at the same time.

Fail-soft by design: a missing corpus directory, an absent embedding endpoint, or a
vector/meta length mismatch all yield an empty result rather than raising. Retrieval is an
enrichment, and must never take down the caller that merely wanted to look something up.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

CORPORA_DIR = Path.home() / ".cohezion" / "corpora"
_MIN_SIMILARITY = 0.30


@dataclass
class Chunk:
    """One retrieved passage plus whatever provenance its corpus recorded."""

    corpus: str
    text: str
    score: float
    meta: dict[str, Any] = field(default_factory=dict)


def available_corpora(root: Path | None = None) -> list[str]:
    """Names of corpora with BOTH a vectors and a meta file present."""
    root = root or CORPORA_DIR
    if not root.is_dir():
        return []
    names = []
    for vec in sorted(root.glob("*_vectors.npy")):
        name = vec.name[: -len("_vectors.npy")]
        if (root / f"{name}_meta.json").exists():
            names.append(name)
    return names


@dataclass
class KnowledgeCorpus:
    """Cosine search over one or more on-disk corpora.

    Loads lazily and caches, so constructing this is cheap even when no search follows.
    """

    root: Path = CORPORA_DIR
    min_similarity: float = _MIN_SIMILARITY
    _loaded: dict[str, tuple[np.ndarray, list[dict[str, Any]]]] = field(default_factory=dict)

    def load(self, name: str) -> bool:
        """Load one corpus into memory. Returns False (never raises) if unusable."""
        if name in self._loaded:
            return True
        vec_path = self.root / f"{name}_vectors.npy"
        meta_path = self.root / f"{name}_meta.json"
        try:
            vectors = np.load(vec_path)
            meta = json.loads(meta_path.read_text())
        except Exception as exc:
            logger.debug("corpus %r unavailable: %s", name, exc)
            return False
        if len(vectors) != len(meta):
            # Silently truncating here would return text attributed to the wrong vector,
            # which is worse than returning nothing.
            logger.warning(
                "corpus %r vector/meta length mismatch (%d vs %d) — skipping",
                name,
                len(vectors),
                len(meta),
            )
            return False
        self._loaded[name] = (vectors, meta)
        return True

    def load_all(self) -> list[str]:
        return [n for n in available_corpora(self.root) if self.load(n)]

    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 5,
        corpora: list[str] | None = None,
    ) -> list[Chunk]:
        """Rank chunks across corpora by cosine similarity to an ALREADY-EMBEDDED query.

        Takes a vector rather than text so the caller owns the embedding call — that keeps
        this module free of any network dependency and makes it trivially testable.
        """
        names = corpora if corpora is not None else self.load_all()
        q = np.asarray(query_vector, dtype=np.float32).ravel()
        norm = float(np.linalg.norm(q))
        if norm < 1e-9:
            return []
        q = q / norm

        hits: list[Chunk] = []
        for name in names:
            if not self.load(name):
                continue
            vectors, meta = self._loaded[name]
            if vectors.shape[1] != q.shape[0]:
                logger.debug("corpus %r dim %d != query dim %d", name, vectors.shape[1], q.shape[0])
                continue
            scores = vectors @ q
            for idx in np.argsort(-scores)[: limit * 2]:
                score = float(scores[idx])
                if score < self.min_similarity:
                    break
                entry = meta[int(idx)]
                hits.append(
                    Chunk(
                        corpus=name,
                        text=entry.get("text", ""),
                        score=score,
                        meta={k: v for k, v in entry.items() if k != "text"},
                    )
                )
        hits.sort(key=lambda c: c.score, reverse=True)
        return hits[:limit]
