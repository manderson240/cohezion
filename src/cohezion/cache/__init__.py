"""Caching infrastructure for token efficiency."""

from cohezion.cache.semantic_cache import SemanticCache

# Redis cache module not present on this branch
# from cohezion.cache.redis_cache import RedisSemanticCache

__all__ = ["SemanticCache"]  # "RedisSemanticCache" commented out
