"""Template-match cache lookup helper for CompoundExecutor (Wave 2D extract).

Checks the semantic cache (via CacheWarmer) for a high-similarity match
to a task description, allowing the executor to skip an LLM call entirely
when a recent equivalent task is already cached.

All failures are non-blocking — returns None and lets the caller proceed
with normal execution.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def try_template_match(task_description: str) -> dict[str, Any] | None:
    """Check cache for a template match before LLM execution.

    Uses CacheWarmer.find_template_match() if available. Returns cached
    response dict if match found (>0.85 similarity), None otherwise.
    Non-blocking: returns None on any error.

    Args:
        task_description: Free-text task description to match against the cache.

    Returns:
        Dict with at least ``response``, ``similarity``, ``source``, optionally
        ``tokens_saved`` keys when a match is found; ``None`` otherwise.
    """
    try:
        from cohezion.cache.cache_warmer import CacheWarmer
        from cohezion.cache.semantic_cache import SemanticCache

        cache = SemanticCache.get_instance() if hasattr(SemanticCache, "get_instance") else None
        if cache is None:
            return None

        warmer = CacheWarmer(cache)
        # Sync wrapper — find_template_match is async but we need sync here
        import asyncio

        try:
            asyncio.get_running_loop()
            # Already in async context — can't block
            return None
        except RuntimeError:
            # No running loop — safe to run
            return asyncio.run(warmer.find_template_match(task_description))

    except (ImportError, AttributeError, RuntimeError, OSError, ValueError, TypeError, KeyError) as e:
        logger.debug("Template matching failed (non-blocking): %s", e, exc_info=True)
        return None
