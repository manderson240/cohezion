"""MemoryConsolidator — automated episode -> semantic-fact consolidation (the Elastic gap).

Cohezion has every primitive for cognitive memory (episodic JourneyTracker trajectories, the
trust-scored `GroundTruthHierarchy` semantic store, SurrealDB bi-temporal `valid_from/valid_to`
supersession, the `SemanticCache` cosine encoder) but no POLICY that runs promotion automatically —
raw session episodes become durable curated facts only via the manual `/learn` + retro rituals.
This module is the missing scheduled pass (Elastic "deferred consolidation", report
``elastic-agent-memory-research-2026-06-30.md``): a local-Gemma ($0) read over recent episodic
records that promotes them to SEMANTIC facts via ``GroundTruthHierarchy.add()``, each fact carrying
provenance (``supporting_episode_ids``) + a confidence, deduped at >= 0.90 against existing facts,
persisted with SurrealDB ``valid_from``, with supersession-not-deletion on contradiction.

It EXTENDS, never duplicates:
  * facts go into ``GroundTruthHierarchy`` (memory/trust_hierarchy.py) — the existing semantic store;
  * dedup similarity uses ``SemanticCache._text_to_embedding`` + cosine (cache/semantic_cache.py);
  * persistence reuses the parameterized SurrealQL builder (``_surql_set``/``_surql_lit``/``_NOW``)
    from compound/prompt_version_registry.py — the injection-safe path. Import only.

Discipline: idempotent (dedup) + fail-open. lemonade or SurrealDB unreachable -> no-op, never raises
into the caller. The consolidation model is a 4B local model, so promotion quality is modest; errors
bias toward NOT promoting (parse failure / low confidence / dedup all drop facts), which is the safe
direction for a ground-truth store.
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from cohezion.cache.semantic_cache import SemanticCache
from cohezion.compound.prompt_version_registry import (
    _NOW,
    _SURREAL_HEADERS,
    _SURREAL_URL,
    _surql_lit,
    _surql_set,
)
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy, TrustedFact, TrustTier


logger = logging.getLogger(__name__)

__all__ = ["ConsolidatedFact", "MemoryConsolidator"]

_DEDUP_THRESHOLD = 0.90  # >= this cosine similarity to an existing fact => duplicate, skip
_SUPPORT_THRESHOLD = 0.5  # episode supports a fact if cosine(fact, episode) >= this
_CONFIDENCE_FLOOR = 0.0  # facts below this confidence are dropped (not promoted)
_SEMANTIC_FACT_TABLE = "semantic_fact"
_FACT_CHAT_URL = "http://localhost:13305/api/v1/chat/completions"
_FACT_MODEL = "Gemma-4-E4B-it-GGUF"


@dataclass
class ConsolidatedFact:
    """A newly promoted semantic fact plus its episode provenance and confidence."""

    fact: TrustedFact
    supporting_episode_ids: list[str]
    confidence: float

    @property
    def content(self) -> str:
        return self.fact.content


def _default_chat(prompt: str) -> str:
    """Local-Gemma ($0) consolidation pass via the :13305 OmniRouter. Raises on any failure so the
    consolidator's fail-open wrapper turns an unreachable model into a clean no-op."""
    import httpx

    r = httpx.post(
        _FACT_CHAT_URL,
        json={
            "model": _FACT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            # N5: thinking models (Gemma-4-E4B) spend budget on a reasoning phase and emit empty
            # content if max_tokens is exhausted mid-reasoning; >=1024 lets it clear reasoning and
            # actually emit the JSON. Empty content -> _parse_facts([]) -> safe no-op regardless.
            "max_tokens": 1024,
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _default_db_post(query: str) -> Any:
    """POST a SurrealQL statement to the bi-temporal store. Raises on failure (caller suppresses)."""
    import httpx

    r = httpx.post(
        _SURREAL_URL, content=query, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0
    )
    r.raise_for_status()
    return r.json()


_PROMPT_TEMPLATE = (
    "You are a memory-consolidation pass. Below are recent episodic records (agent/session "
    "events). Distil them into a SMALL set of STABLE, durable semantic facts worth remembering. "
    "Merge episodes that express the same fact into ONE fact. Drop chit-chat and one-offs.\n"
    "Return ONLY a JSON array. Each element: "
    '{"text": "<the fact>", "confidence": <0..1>, '
    '"supporting_episode_ids": ["<episode id>", ...], '
    '"supersedes": "<exact text of a prior fact this contradicts, or omit>"}.\n'
    "If nothing is worth promoting, return [].\n\n"
    "EPISODES:\n__EPISODES__\n\nJSON:"
)


class MemoryConsolidator:
    """Promote recent episodic records to durable semantic facts (deferred-consolidation policy)."""

    def __init__(
        self,
        hierarchy: GroundTruthHierarchy | None = None,
        *,
        chat_fn: Callable[[str], str] | None = None,
        db_post: Callable[[str], Any] | None = None,
        embed_fn: Callable[[str], Any] | None = None,
        dedup_threshold: float = _DEDUP_THRESHOLD,
        support_threshold: float = _SUPPORT_THRESHOLD,
        confidence_floor: float = _CONFIDENCE_FLOOR,
        persist: bool = True,
    ) -> None:
        self._hierarchy = hierarchy if hierarchy is not None else GroundTruthHierarchy()
        self._chat_fn = chat_fn or _default_chat
        self._db_post = db_post or _default_db_post
        self._embed_fn = embed_fn or SemanticCache._text_to_embedding
        self._dedup_threshold = dedup_threshold
        self._support_threshold = support_threshold
        self._confidence_floor = confidence_floor
        self._persist = persist

    # ── public API ────────────────────────────────────────────────────────────
    def consolidate(self, episodes: list[dict]) -> list[ConsolidatedFact]:
        """Read recent episodic records, promote distinct durable facts to the semantic store.

        Returns the list of NEWLY promoted facts (deduped + above the confidence floor). Idempotent
        (a re-run over the same episodes promotes nothing new) and fail-open (LLM/DB down -> [])."""
        if not episodes:
            return []
        try:
            raw = self._chat_fn(self._build_prompt(episodes))
        except Exception as exc:  # lemonade down / timeout -> safe no-op
            logger.warning("consolidation LLM unavailable — no-op: %s", exc)
            return []

        candidates = self._parse_facts(raw)
        if not candidates:
            return []

        promoted: list[ConsolidatedFact] = []
        for cand in candidates:
            text = str(cand.get("text") or "").strip()
            if len(text) < 3:
                continue
            confidence = self._coerce_confidence(cand.get("confidence"))
            if confidence < self._confidence_floor:
                continue

            # dedup (>= threshold) against the existing semantic store — corroborate, don't re-add
            existing = self._nearest_existing(text)
            if existing is not None:
                self._hierarchy.corroborate(existing.content, True)
                continue

            # supersession-not-deletion: a contradicting fact flags the prior's valid_to
            supersedes = str(cand.get("supersedes") or "").strip()
            if supersedes:
                self._hierarchy.corroborate(supersedes, False)  # record contradiction (retained)
                if self._persist:
                    with contextlib.suppress(Exception):
                        self._supersede(supersedes)

            support_ids = self._supporting_episode_ids(text, cand, episodes)
            fact = self._hierarchy.add(text, TrustTier.STRUCTURED_FACT)
            if self._persist:
                with contextlib.suppress(Exception):
                    self._persist_fact(fact, confidence, support_ids)
            promoted.append(
                ConsolidatedFact(
                    fact=fact, supporting_episode_ids=support_ids, confidence=confidence
                )
            )
        return promoted

    # ── internals ─────────────────────────────────────────────────────────────
    def _build_prompt(self, episodes: list[dict]) -> str:
        lines = []
        for ep in episodes:
            eid = ep.get("id", "?")
            text = ep.get("text") or ep.get("task_description") or ""
            lines.append(f"- [{eid}] {text}")
        return _PROMPT_TEMPLATE.replace("__EPISODES__", "\n".join(lines))

    @staticmethod
    def _coerce_confidence(value: Any) -> float:
        try:
            c = float(value)
        except (TypeError, ValueError):
            return 0.6  # neutral default when the model omits / mangles it
        return max(0.0, min(1.0, c))

    @staticmethod
    def _parse_facts(raw: str) -> list[dict]:
        """Extract a JSON array of fact dicts from a (possibly prose-wrapped) model reply."""
        if not raw:
            return []
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1 or end < start:
            return []
        try:
            data = json.loads(raw[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        out: list[dict] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                out.append({"text": item})
        return out

    def _embed(self, text: str) -> np.ndarray:
        return np.asarray(self._embed_fn(text), dtype=np.float64)

    def _nearest_existing(self, text: str) -> TrustedFact | None:
        """Return an existing fact within dedup_threshold of ``text`` (most similar), else None."""
        facts = self._hierarchy.rank()
        if not facts:
            return None
        target = self._embed(text)
        best: TrustedFact | None = None
        best_sim = -1.0
        for f in facts:
            sim = self._cosine(target, self._embed(f.content))
            if sim > best_sim:
                best_sim, best = sim, f
        return best if best_sim >= self._dedup_threshold else None

    def _supporting_episode_ids(self, text: str, cand: dict, episodes: list[dict]) -> list[str]:
        """Provenance: prefer LLM-named ids (filtered to known episodes); else episodes whose
        embedding supports the fact; else the whole batch (the input that produced this fact)."""
        known = {str(ep.get("id")) for ep in episodes if ep.get("id") is not None}

        named = cand.get("supporting_episode_ids")
        if isinstance(named, list):
            filtered = [str(i) for i in named if str(i) in known]
            if filtered:
                return filtered

        target = self._embed(text)
        matched = [
            str(ep["id"])
            for ep in episodes
            if ep.get("id") is not None
            and self._cosine(
                target, self._embed(ep.get("text") or ep.get("task_description") or "")
            )
            >= self._support_threshold
        ]
        if matched:
            return matched
        return [str(ep["id"]) for ep in episodes if ep.get("id") is not None]

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _persist_fact(self, fact: TrustedFact, confidence: float, support_ids: list[str]) -> None:
        """CREATE the semantic fact with valid_from (bi-temporal). Parameterized via _surql_set."""
        q = (
            f"CREATE {_SEMANTIC_FACT_TABLE} SET "
            + _surql_set(
                {
                    "content": fact.content,
                    "confidence": round(confidence, 4),
                    "tier": int(fact.tier),
                    "supporting_episode_ids": list(support_ids),
                    "valid_from": _NOW,
                }
            )
            + ";"
        )
        self._db_post(q)

    def _supersede(self, prior_content: str) -> None:
        """Supersession-not-deletion: set the prior fact's valid_to (the row is RETAINED)."""
        q = (
            f"UPDATE {_SEMANTIC_FACT_TABLE} SET valid_to={_surql_lit(_NOW)} "
            f"WHERE content={_surql_lit(prior_content)} AND valid_to IS NONE;"
        )
        self._db_post(q)
