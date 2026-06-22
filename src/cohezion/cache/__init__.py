"""Caching infrastructure for token efficiency."""

from cohezion.cache.redis_cache import RedisSemanticCache
from cohezion.cache.semantic_cache import SemanticCache


__all__ = ["RedisSemanticCache", "SemanticCache"]

import contextlib

# Wiring-sweep 2026-06-22: cache_warmer, sentence_encoder, text_encoder were genuine orphans.
with contextlib.suppress(Exception):
    from cohezion.cache.cache_warmer import CacheWarmer as CacheWarmer

with contextlib.suppress(Exception):
    from cohezion.cache.sentence_encoder import (
        SentenceTransformerEncoder as SentenceTransformerEncoder,
    )
    from cohezion.cache.sentence_encoder import get_encoder as get_encoder

with contextlib.suppress(Exception):
    from cohezion.cache.text_encoder import (
        SemanticTextEncoder as SemanticTextEncoder,
    )
    from cohezion.cache.text_encoder import get_text_encoder as get_text_encoder
