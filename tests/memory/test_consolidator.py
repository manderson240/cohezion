"""Falsification-first tests for MemoryConsolidator (episode -> semantic-fact consolidation).

Written BEFORE the implementation (watch RED), per verification-depth.md. Each test is
DISCRIMINATING: a no-op / wrong consolidator fails it.

  T1  N episodes about the same fact -> exactly ONE semantic fact, supporting_episode_ids populated
  T2  dedup    -> re-running an already-known fact does NOT add a duplicate (>= 0.90 similarity)
  T3  supersession -> a contradicting fact sets the prior's valid_to (UPDATE); both rows retained (no DELETE)
  T4  fail-open    -> lemonade-down (chat_fn raises) -> no-op [], caller not crashed
  T5  consumption  -> LoopCoordinator._consolidate_episodes actually CALLS consolidate (not dormant)
"""

from __future__ import annotations

import json

import numpy as np

from cohezion.memory.consolidator import ConsolidatedFact, MemoryConsolidator
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy, TrustTier


# Deterministic keyword embedder: same topic -> identical vector, different topic -> orthogonal.
# Order matters: distinctive words (paris/lyon) BEFORE the shared word (capital).
_VOCAB = ["paris", "lyon", "sky", "weather", "capital", "other"]


def kw_embed(text: str) -> np.ndarray:
    t = (text or "").lower()
    vec = np.zeros(len(_VOCAB), dtype=np.float64)
    for i, kw in enumerate(_VOCAB):
        if kw in t:
            vec[i] = 1.0
            return vec
    vec[-1] = 1.0
    return vec


def test_t1_same_fact_emits_single_provenanced_fact():
    """N episodes about the same fact -> exactly one fact, supporting_episode_ids = all N."""
    episodes = [
        {"id": "e1", "text": "User remarked the sky looked blue this morning"},
        {"id": "e2", "text": "Discussion about why the sky appears blue"},
        {"id": "e3", "text": "Confirmed the sky color is blue at noon"},
    ]
    # LLM distils the three episodes to one fact (no ids -> whole-batch provenance fallback).
    chat = lambda _prompt: json.dumps([{"text": "The sky is blue.", "confidence": 0.8}])  # noqa: E731

    h = GroundTruthHierarchy()
    c = MemoryConsolidator(h, chat_fn=chat, embed_fn=kw_embed, persist=False)
    facts = c.consolidate(episodes)

    assert len(facts) == 1, f"expected exactly one consolidated fact, got {len(facts)}"
    assert isinstance(facts[0], ConsolidatedFact)
    # provenance MUST be populated (a no-op consolidator leaves this empty)
    assert set(facts[0].supporting_episode_ids) == {"e1", "e2", "e3"}
    assert len(h) == 1
    assert facts[0].fact.tier == TrustTier.STRUCTURED_FACT


def test_t2_dedup_does_not_readd_known_fact():
    """Re-running with the same already-known fact adds nothing the second time (>= 0.90)."""
    episodes = [{"id": "e1", "text": "Note about the sky"}]
    chat = lambda _p: json.dumps([{"text": "The sky is blue.", "confidence": 0.8}])  # noqa: E731

    h = GroundTruthHierarchy()
    c = MemoryConsolidator(h, chat_fn=chat, embed_fn=kw_embed, persist=False)

    first = c.consolidate(episodes)
    assert len(first) == 1
    assert len(h) == 1

    second = c.consolidate(episodes)
    assert second == [], "duplicate fact was re-added — dedup failed"
    assert len(h) == 1, "hierarchy grew on a duplicate"


def test_t3_supersession_sets_valid_to_and_retains_both():
    """A contradicting fact UPDATEs the prior's valid_to; both rows retained (no DELETE)."""
    queries: list[str] = []

    def db_post(q: str):
        queries.append(q)
        return [{"status": "OK", "result": []}]

    h = GroundTruthHierarchy()
    h.add("The capital is Lyon.", TrustTier.STRUCTURED_FACT)  # prior fact already known

    chat = lambda _p: json.dumps(  # noqa: E731
        [{"text": "The capital is Paris.", "confidence": 0.9, "supersedes": "The capital is Lyon."}]
    )
    c = MemoryConsolidator(h, chat_fn=chat, db_post=db_post, embed_fn=kw_embed, persist=True)

    episodes = [{"id": "e9", "text": "Correction: the capital is Paris"}]
    facts = c.consolidate(episodes)

    assert len(facts) == 1 and "Paris" in facts[0].fact.content
    joined = "\n".join(queries)
    # supersession = UPDATE setting valid_to on the prior, NOT a delete
    assert any("UPDATE" in q and "valid_to" in q and "Lyon" in q for q in queries), queries
    assert "DELETE" not in joined.upper(), "supersession must not delete the prior row"
    # new fact persisted (CREATE) — both rows retained
    assert any("CREATE" in q and "Paris" in q for q in queries), queries
    # prior fact still present in the in-memory hierarchy (retained, contradiction recorded)
    assert any("Lyon" in f.content for f in h.rank())


def test_t4_fail_open_when_llm_down():
    """chat_fn raising (lemonade down) -> no-op [], caller is NOT crashed."""

    def boom(_prompt):
        raise ConnectionError("lemonade :13305 unreachable")

    h = GroundTruthHierarchy()
    c = MemoryConsolidator(h, chat_fn=boom, embed_fn=kw_embed, persist=False)

    facts = c.consolidate([{"id": "e1", "text": "anything"}])
    assert facts == []
    assert len(h) == 0


def test_t4b_empty_episodes_is_noop():
    h = GroundTruthHierarchy()
    c = MemoryConsolidator(h, chat_fn=lambda _p: "[]", embed_fn=kw_embed, persist=False)
    assert c.consolidate([]) == []


def test_t5_loop_coordinator_calls_consolidate(monkeypatch):
    """CONSUMPTION (not declaration): LoopCoordinator._consolidate_episodes fires consolidate()."""
    import cohezion.memory.consolidator as consolidator_mod
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator, RunReport

    called: dict = {}

    class SpyConsolidator:
        def __init__(self, *a, **k):
            pass

        def consolidate(self, episodes):
            called["episodes"] = episodes
            return []

    monkeypatch.setattr(consolidator_mod, "MemoryConsolidator", SpyConsolidator)

    coord = LoopCoordinator(LoopConfig(use_local_inference=False))
    coord._episodes = [{"id": "t1", "text": "do the thing", "operation_type": "synthesis"}]
    coord._consolidate_episodes(RunReport())

    assert called.get("episodes") == coord._episodes, "coordinator did not call consolidate()"
