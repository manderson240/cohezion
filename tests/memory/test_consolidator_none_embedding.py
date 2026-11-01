"""H2: a None embedding in the consolidator is visible and never merges facts."""

import logging

from cohezion.memory.consolidator import MemoryConsolidator
from cohezion.memory.trust_hierarchy import TrustTier


def test_consolidator_none_embedding_is_visible_and_never_dedups(caplog):
    """H2: _embed_fn returning None used to give nan cosines (dedup silently off)."""

    c = MemoryConsolidator(embed_fn=lambda t: None, persist=False)
    with caplog.at_level(logging.WARNING, logger="cohezion.memory.consolidator"):
        assert c._cosine(c._embed("a"), c._embed("a")) == 0.0
    assert c.embed_missing == 2
    assert sum("no embedding available" in r.message for r in caplog.records) == 1
    c._hierarchy.add("existing fact", TrustTier.STRUCTURED_FACT)
    assert c._nearest_existing("existing fact") is None  # stated behaviour: not merged


# ---- N2: the missing-embedding state must reach the reader of the result ----------------------

import json  # noqa: E402

import numpy as np  # noqa: E402

from cohezion.memory.consolidator import ConsolidatedFact  # noqa: E402


def _chat_two_identical_facts(_prompt):
    return json.dumps(
        [
            {"text": "postgres listens on port 5433", "supporting_episode_ids": ["e1"]},
            {"text": "postgres listens on port 5433", "supporting_episode_ids": ["e1"]},
        ]
    )


def _bag(text):
    v = np.zeros(8)
    for w in text.lower().split():
        v[hash(w) % 8] += 1.0
    return v


EPISODES = [{"id": "e1", "text": "ran the db"}]


def test_result_marks_facts_promoted_without_a_dedup_check():
    """N2: with no embedding the duplicate is promoted twice AND the result says so; with a working
    embedding the same input is deduped and nothing is flagged."""
    c = MemoryConsolidator(
        chat_fn=_chat_two_identical_facts, embed_fn=lambda t: None, persist=False
    )
    out = c.consolidate(EPISODES)
    assert len(out) == 2
    assert [f.dedup_unchecked for f in out] == [False, True]  # first: empty store, nothing to check

    ok = MemoryConsolidator(chat_fn=_chat_two_identical_facts, embed_fn=_bag, persist=False)
    out_ok = ok.consolidate(EPISODES)
    assert len(out_ok) == 1 and not any(f.dedup_unchecked for f in out_ok)


def test_long_episode_text_alone_does_not_claim_dedup_is_disabled(caplog):
    """N2: a refused LONG EPISODE text (strict window) must not report dedup as disabled or flag
    facts, because short-fact dedup is unaffected."""

    def embed(text):
        return None if text.startswith("LONG") else _bag(text)

    c = MemoryConsolidator(chat_fn=_chat_two_identical_facts, embed_fn=embed, persist=False)
    episodes = [{"id": "e1", "text": "LONG " + "word " * 500}]
    # no named ids -> provenance embeds the long episode text, which is refused
    chat = lambda _p: json.dumps(  # noqa: E731
        [{"text": "postgres listens on port 5433"}, {"text": "postgres listens on port 5433"}]
    )
    c._chat_fn = chat
    with caplog.at_level(logging.WARNING, logger="cohezion.memory.consolidator"):
        out = c.consolidate(episodes)
    assert c.embed_missing > 0  # the long text really was refused
    assert len(out) == 1  # short-fact dedup still worked
    assert not any(f.dedup_unchecked for f in out)
    assert not any("dedup is disabled" in r.message for r in caplog.records)


def test_loop_coordinator_report_carries_consolidation_state(monkeypatch, caplog):
    """N2 consumption: the only production caller reads the return value into RunReport."""
    import cohezion.memory.consolidator as consolidator_mod
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig, LoopCoordinator, RunReport
    from cohezion.memory.trust_hierarchy import TrustedFact

    def fact(unchecked):
        tf = TrustedFact(content="x", tier=TrustTier.STRUCTURED_FACT)
        return ConsolidatedFact(tf, ["t1"], 0.6, dedup_unchecked=unchecked)

    class Spy:
        def consolidate(self, episodes):
            return [fact(False), fact(True), fact(True)]

    monkeypatch.setattr(consolidator_mod, "MemoryConsolidator", Spy)
    coord = LoopCoordinator(LoopConfig(use_local_inference=False))
    coord._episodes = [{"id": "t1", "text": "x"}]
    report = RunReport()
    with caplog.at_level(logging.WARNING):
        coord._consolidate_episodes(report)
    assert (report.facts_promoted, report.facts_dedup_unchecked) == (3, 2)
    assert any("not dedup-checked" in r.message for r in caplog.records)
