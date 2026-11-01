"""F4: CacheWarmer.find_template_match must respect the L2 partition (system prompt + model).

The executor skips the LLM entirely on a template match, so an answer stored under another
system prompt or model must never come back through this path (4fbcd0040 partitioned get()).
"""

from __future__ import annotations

import asyncio

from cohezion.cache.cache_warmer import CacheWarmer
from cohezion.cache.semantic_cache import SemanticCache


QUERY = "reset the production router now"
NEAR = "reset the production router"  # paraphrase: below the cache's own threshold, above 0.85


def _match(cache: SemanticCache, query: str):
    return asyncio.run(CacheWarmer(cache).find_template_match(query))


def test_template_match_ignores_entries_from_another_system_and_model():
    cache = SemanticCache(similarity_threshold=0.99)
    asyncio.run(cache.put(QUERY, response="ANSWER-S1-M1", system="S1", model="M1"))
    assert asyncio.run(cache.get(QUERY)) is None  # precondition: get() already refuses it
    assert _match(cache, QUERY) is None  # exact text
    assert _match(cache, NEAR) is None  # semantic neighbour


def test_template_match_still_serves_unpartitioned_semantic_neighbour():
    """Positive control: the L2 branch is reachable and serves the unpartitioned entry."""
    cache = SemanticCache(similarity_threshold=0.99)
    asyncio.run(cache.put(QUERY, response="PLAIN"))
    assert asyncio.run(cache.get(NEAR)) is None  # get() misses, so only the L2 branch can answer
    hit = _match(cache, NEAR)
    assert hit is not None and hit["response"] == "PLAIN" and hit["source"] == "L2_semantic"


def test_template_match_prefers_unpartitioned_entry_over_a_closer_partitioned_one():
    cache = SemanticCache(similarity_threshold=0.99)
    asyncio.run(cache.put(QUERY, response="OTHER", system="S1", model="M1"))
    asyncio.run(cache.put("reset production router", response="PLAIN"))
    hit = _match(cache, NEAR)
    assert hit is not None and hit["response"] == "PLAIN"
