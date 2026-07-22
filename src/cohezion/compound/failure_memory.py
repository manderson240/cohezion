"""Failure-conditioned retrieval memory for SkillRefiner.

Stores (failure_text, fix_text) pairs from past FAPO L1 refinements and
retrieves the most semantically similar past fix for a NEW failure — so the
self-improvement loop learns from the TEXT of analogous past failures, not
just aggregate quality metrics.

Convergent finding (2607.13104 self-improving-agent survey + MSCE 2607.16617
evidence-calibrated trace value + GenAI_Agents self_healing_code pattern):
retrieval-augmented recommendation over a small local failure corpus compounds
— every fix reduces the cost of the next analogous failure.

Local-first ($0): embeds via LemonadeEmbedBridge (nomic-embed-text-v2-moe-GGUF
at the :13305 OmniRouter). Fail-open at every boundary — no SurrealDB vector
index is assumed to exist (grounding check, 2026-07-22: none found in this
codebase), so kNN runs in-Python over an in-memory list; when the embed
bridge is unreachable, retrieval falls back to deterministic keyword overlap
(zero network calls, same shape as SkillRefiner's own `_autodata_select`
self-consistency scoring) rather than silently returning nothing.

## KNOWN DORMANCY (verified 2026-07-22, pre-existing — not introduced by this module)
`_generate_failure_signal`'s retrieval only fires on the FAPO L1 branch of
`SkillRefiner.refine(..., failure_attribution=...)`. Grepping the whole repo
(`grep -rn "failure_attribution=" src/cohezion` outside skill_refiner.py, and
`grep -rln "FailureAttributor" src/cohezion`) shows **zero production call
sites** construct a `FailureAttribution` or pass `failure_attribution=` into
`refine()` — only tests do. Both live `refine()` call sites
(`executor.py:1523`, `post_execution.py:159`) additionally gate on
`if success and ...:`, so even `refine()`'s own `not metrics.success` branch
is unreachable from production today. This predates this feature — FA1-FA3 in
harness.md test `FailureAttributor` in isolation, never its wiring — but it
means the new retrieval keystone is CORRECT and TESTED, not yet REACHABLE, in
the live compound loop until a follow-on wires: (1) `FailureAttributor().
classify()` on failed executions inside `executor.py`/`post_execution.py`,
and (2) a `refine(..., failure_attribution=...)` call for failures. That is a
larger, separate change (touches the core execution pipeline) deliberately
left out of this additive-only pass.

## FUTURE HOOKS
- Cross-session persistence: add to_dict()/from_dict() and wire into
  SkillRefiner's existing durable spine (SRS1-3, `save_state`/`restore_state`)
  once the corpus is large enough to be worth surviving a process restart.
  Deliberately NOT done in this pass — SRS is an already-tested invariant
  surface and this feature ships fully additive without touching it.
- SurrealDB vector index: if/when a `surreal-db` vector-search table exists
  for this project, swap the in-Python cosine loop for a `SELECT ... <|k|>`
  kNN query — the `retrieve()` call signature would not need to change.
- Utility-weighting by downstream success (MSCE "evidence-calibrated trace
  value"): `quality_score` is already captured per record; a future pass can
  fold it into the ranking score instead of using similarity alone.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

# CA1-adjacent starting point: LemonadeEmbedBridge subsamples nomic-embed's
# 768D output to 256D (unit-normalized) preserving cosine rank ordering, but
# that subsampled space has not been independently calibrated the way CA1
# calibrated SemanticCache's raw 768D threshold (0.58). 0.5 is a conservative
# starting default pending a real calibration pass — see FUTURE HOOKS.
_DEFAULT_SIMILARITY_THRESHOLD = 0.5

# Keyword-overlap fallback ignores short/stop-ish words, mirroring the >3-char
# filter already used by SkillRefiner._autodata_select's self-consistency scoring.
_MIN_KEYWORD_LEN = 3


_bridge_singleton: Any = None
_bridge_import_failed = False


def _default_embed_fn(text: str) -> np.ndarray | None:
    """Lazy $0 embed via LemonadeEmbedBridge (:13305 nomic-embed). None on any failure."""
    global _bridge_singleton, _bridge_import_failed
    if _bridge_import_failed:
        return None
    if _bridge_singleton is None:
        try:
            from cohezion.inference.lemonade_embed_bridge import LemonadeEmbedBridge

            _bridge_singleton = LemonadeEmbedBridge()
        except ImportError:
            _bridge_import_failed = True
            return None

    try:
        if not _bridge_singleton.is_available():
            return None
        vec = _bridge_singleton.encode(text)
        if vec is None or not np.any(vec):
            return None
        return vec
    except Exception:
        logger.debug("FailureConditionedMemory: embed failed, falling back", exc_info=True)
        return None


@dataclass
class FailureMemoryRecord:
    """A single stored (failure, successful fix) pair."""

    failure_text: str
    fix_text: str
    skill_name: str = ""
    category: str = ""
    quality_score: float | None = None
    embedding: list[float] | None = None


@dataclass
class FailureConditionedMemory:
    """kNN memory over past failure→fix pairs, embed-first with a $0 keyword-overlap fallback.

    Interface:
        record(failure_text, fix_text, skill_name="", category="", quality_score=None)
        retrieve(query_text, k=3) -> list[tuple[FailureMemoryRecord, float]]

    Fail-open: an unreachable embed bridge never raises and never blocks
    recommendation generation — retrieve() degrades to keyword overlap and,
    if nothing clears the similarity threshold, returns an empty list so the
    caller falls back to its existing generic behaviour.
    """

    embed_fn: Callable[[str], Any] = field(default=_default_embed_fn)
    max_records: int = 200
    similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD
    _records: list[FailureMemoryRecord] = field(default_factory=list, init=False, repr=False)

    def record(
        self,
        failure_text: str,
        fix_text: str,
        skill_name: str = "",
        category: str = "",
        quality_score: float | None = None,
    ) -> None:
        """Append a (failure, fix) pair, embedding it if the bridge is available."""
        embedding = self._safe_embed(failure_text)
        self._records.append(
            FailureMemoryRecord(
                failure_text=failure_text,
                fix_text=fix_text,
                skill_name=skill_name,
                category=category,
                quality_score=quality_score,
                embedding=embedding.tolist() if embedding is not None else None,
            )
        )
        if len(self._records) > self.max_records:
            self._records.pop(0)

    def retrieve(self, query_text: str, k: int = 3) -> list[tuple[FailureMemoryRecord, float]]:
        """Return up to k (record, similarity) pairs above similarity_threshold, best-first.

        Uses cosine similarity when both the query and a given record have an
        embedding; otherwise falls back to keyword-overlap for that record
        (mixed corpora are supported — a partially-embedded store still works).
        """
        if not self._records:
            return []

        query_vec = self._safe_embed(query_text)
        scored: list[tuple[FailureMemoryRecord, float]] = []
        for rec in self._records:
            if query_vec is not None and rec.embedding is not None:
                sim = self._cosine(query_vec, np.array(rec.embedding, dtype=np.float32))
            else:
                sim = _keyword_overlap(query_text, rec.failure_text)
            scored.append((rec, sim))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [pair for pair in scored[:k] if pair[1] >= self.similarity_threshold]

    def _safe_embed(self, text: str) -> np.ndarray | None:
        try:
            vec = self.embed_fn(text)
        except Exception:
            logger.debug("FailureConditionedMemory.embed_fn raised (non-blocking)", exc_info=True)
            return None
        if vec is None:
            return None
        arr = np.asarray(vec, dtype=np.float32)
        if arr.size == 0 or not np.any(arr):
            return None
        return arr

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom < 1e-9:
            return 0.0
        return float(np.dot(a, b) / denom)


def _keyword_overlap(a: str, b: str) -> float:
    """Deterministic $0 fallback similarity — Jaccard over words longer than 3 chars."""
    words_a = {w for w in re.findall(r"\w+", a.lower()) if len(w) > _MIN_KEYWORD_LEN}
    words_b = {w for w in re.findall(r"\w+", b.lower()) if len(w) > _MIN_KEYWORD_LEN}
    if not words_a or not words_b:
        return 0.0
    union = words_a | words_b
    if not union:
        return 0.0
    return len(words_a & words_b) / len(union)
