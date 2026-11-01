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
