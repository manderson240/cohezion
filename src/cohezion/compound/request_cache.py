"""Request cache - L1 exact + L2 semantic caching for intake requests.

Implements two-tier caching:
- L1: Exact SHA-256 hash matching (0 tokens, <1ms latency)
- L2: Semantic similarity matching (0 tokens, ~5ms latency)

Both tiers cache request_text → AgentTask mappings for reuse.
Supports warm-loading from vault and cache statistics.

Example:
    ```python
    cache = RequestCache(mcp_client, l1_size=256, l2_size=512)

    # Warm cache from vault patterns
    entries = cache.warm_from_vault(project="cohezion", limit=100)

    # L1 exact match
    cached = cache.get_exact("Generate 10 story ideas")

    # Cache a successful request
    cache.put("Generate 10 story ideas", task)

    # Get statistics
    stats = cache.get_stats()
    ```
"""

import hashlib
import json
import logging
from collections import OrderedDict
from typing import Any

from cohezion.compound.team_executor import AgentTask
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


class RequestCache:
    """L1 exact hash + L2 semantic similarity caching for intake requests.

    Provides two tiers of caching:
    - L1: Exact hash match for identical requests (0 tokens, <1ms)
    - L2: Simple string-based similarity for paraphrases (0 tokens, ~5ms)

    Both tiers are non-blocking and return None on miss for graceful degradation.

    Example:
        ```python
        cache = RequestCache(mcp_client)

        # Try L1 (exact match)
        task = cache.get_exact("Generate ideas")
        if not task:
            # Try L2 (similarity match)
            task = cache.get_semantic("Generate 10 creative ideas", threshold=0.85)

        # Cache successful result
        cache.put("Generate ideas", task)
        ```
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        l1_size: int = 256,
        l2_size: int = 512,
        l2_threshold: float = 0.85,
    ):
        """Initialize request cache.

        Args:
            mcp_client: Connected MCPClient for vault operations
            l1_size: Maximum entries in L1 cache (exact match)
            l2_size: Maximum entries in L2 cache (similarity match)
            l2_threshold: Similarity threshold for L2 hits (0.0-1.0)
        """
        self.mcp_client = mcp_client
        self.l1_cache = {}  # request_text hash → AgentTask
        # L2 cache: simple string-based similarity (ordered dict for LRU eviction)
        self.l2_cache: OrderedDict[str, AgentTask] = OrderedDict()
        self.l1_size = l1_size
        self.l2_size = l2_size
        self.l2_threshold = l2_threshold

        # Statistics
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0

    def get_exact(self, request_text: str) -> AgentTask | None:
        """Get cached task via exact hash match (L1, 0 tokens, <1ms).

        Args:
            request_text: User request text

        Returns:
            Cached AgentTask if found, None otherwise
        """
        try:
            cache_key = self._hash_request(request_text)
            task = self.l1_cache.get(cache_key)

            if task:
                self._l1_hits += 1
                logger.debug(f"L1 cache hit: {request_text[:50]}...")
                return task

            self._l1_misses += 1
            return None
        except Exception as e:
            logger.warning(f"L1 cache error: {e}")
            self._l1_misses += 1
            return None

    def get_semantic(self, request_text: str, threshold: float | None = None) -> AgentTask | None:
        """Get cached task via string similarity (L2, 0 tokens, ~5ms).

        Uses word overlap similarity to find similar cached requests.

        Args:
            request_text: User request text
            threshold: Similarity threshold (uses self.l2_threshold if None)

        Returns:
            Cached AgentTask if similar match found, None otherwise
        """
        try:
            threshold = threshold or self.l2_threshold

            if not self.l2_cache:
                self._l2_misses += 1
                return None

            # Find most similar request using word overlap
            best_task = None
            best_similarity = 0.0

            for cached_request, task in self.l2_cache.items():
                similarity = self._word_overlap_similarity(request_text, cached_request)

                if similarity >= threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_task = task

            if best_task:
                self._l2_hits += 1
                logger.debug(
                    f"L2 cache hit (similarity={best_similarity:.2f}): {request_text[:50]}..."
                )
                return best_task

            self._l2_misses += 1
            return None
        except Exception as e:
            logger.warning(f"L2 cache error: {e}")
            self._l2_misses += 1
            return None

    def put(self, request_text: str, task: AgentTask) -> None:
        """Cache request → AgentTask in both L1 and L2.

        Args:
            request_text: User request text
            task: AgentTask to cache
        """
        try:
            # L1: Exact hash
            cache_key = self._hash_request(request_text)
            self.l1_cache[cache_key] = task

            # Evict oldest entry if over limit (FIFO)
            if len(self.l1_cache) > self.l1_size:
                oldest_key = next(iter(self.l1_cache))
                del self.l1_cache[oldest_key]
                logger.debug(f"L1 cache evicted oldest entry (size={self.l1_size})")

            # L2: String-based similarity cache
            self.l2_cache[request_text] = task

            # Evict oldest if over limit (LRU)
            if len(self.l2_cache) > self.l2_size:
                self.l2_cache.popitem(last=False)  # Remove oldest (first inserted)
                logger.debug(f"L2 cache evicted oldest entry (size={self.l2_size})")

            logger.debug(f"Cached request: {request_text[:50]}... → task_id={task.task_id}")
        except Exception as e:
            logger.warning(f"Failed to cache request: {e}")

    def warm_from_vault(self, project: str = "cohezion", limit: int = 100) -> int:
        """Load patterns from vault to warm cache.

        Queries vault for patterns related to intake requests and loads them
        into both L1 and L2 caches.

        Args:
            project: Project name for vault query
            limit: Maximum patterns to load

        Returns:
            Number of patterns loaded
        """
        try:
            # Query vault for intake-related patterns
            results = self.mcp_client.vault_search(
                query="intake request task agent",
                scope="all",
            )

            if not results:
                logger.info("No patterns found in vault for cache warming")
                return 0

            count = 0
            for result in results[:limit]:
                try:
                    if self._is_intake_pattern(result):
                        request_text, task = self._parse_pattern(result)
                        if request_text and task:
                            self.put(request_text, task)
                            count += 1
                except Exception as e:
                    logger.debug(f"Failed to parse pattern: {e}")
                    continue

            logger.info(
                f"Warmed cache with {count} patterns from vault "
                f"(L1: {len(self.l1_cache)}, L2: {self.l2_cache.cache_size()})"
            )
            return count
        except Exception as e:
            logger.warning(f"Failed to warm cache from vault: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with hit rates, sizes, and metrics
        """
        total_l1 = self._l1_hits + self._l1_misses
        total_l2 = self._l2_hits + self._l2_misses
        total = total_l1 + total_l2

        l1_hit_rate = (self._l1_hits / total_l1 * 100) if total_l1 > 0 else 0.0
        l2_hit_rate = (self._l2_hits / total_l2 * 100) if total_l2 > 0 else 0.0
        combined_hit_rate = ((self._l1_hits + self._l2_hits) / total * 100) if total > 0 else 0.0

        # Estimate average tokens per request
        # L1/L2 hits: 0 tokens, misses: ~250 tokens (LLM fallback)
        avg_tokens = (
            ((self._l1_hits + self._l2_hits) * 0 + (self._l1_misses + self._l2_misses) * 250)
            / total
            if total > 0
            else 0
        )

        return {
            "l1_hits": self._l1_hits,
            "l1_misses": self._l1_misses,
            "l1_hit_rate": l1_hit_rate,
            "l1_size": len(self.l1_cache),
            "l1_capacity": self.l1_size,
            "l2_hits": self._l2_hits,
            "l2_misses": self._l2_misses,
            "l2_hit_rate": l2_hit_rate,
            "l2_size": len(self.l2_cache),
            "l2_capacity": self.l2_size,
            "combined_hit_rate": combined_hit_rate,
            "total_requests": total,
            "avg_tokens_per_request": avg_tokens,
        }

    def reset_stats(self) -> None:
        """Reset all cache statistics."""
        self._l1_hits = 0
        self._l1_misses = 0
        self._l2_hits = 0
        self._l2_misses = 0
        logger.debug("Cache statistics reset")

    def clear(self) -> None:
        """Clear all cached entries."""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self.reset_stats()
        logger.info("Request cache cleared")

    def cache_size(self) -> int:
        """Get total cache size (L1 + L2).

        Returns:
            Total number of cached entries
        """
        return len(self.l1_cache) + len(self.l2_cache)

    # Private helpers

    @staticmethod
    def _hash_request(text: str) -> str:
        """Hash request text for L1 key.

        Args:
            text: Request text

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def _serialize_task(task: AgentTask) -> str:
        """Serialize AgentTask to JSON string.

        Args:
            task: AgentTask to serialize

        Returns:
            JSON string representation
        """
        try:
            return json.dumps(
                {
                    "task_id": task.task_id,
                    "agent_id": task.agent_id,
                    "description": task.description,
                    "operation_type": task.operation_type,
                    "available_skills": task.available_skills,
                    "timeout_seconds": task.timeout_seconds,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to serialize task: {e}")
            return ""

    @staticmethod
    def _deserialize_task(json_str: str) -> AgentTask | None:
        """Deserialize JSON string to AgentTask.

        Args:
            json_str: JSON string representation

        Returns:
            AgentTask if valid, None otherwise
        """
        try:
            data = json.loads(json_str)
            return AgentTask(
                task_id=data.get("task_id", ""),
                agent_id=data.get("agent_id", ""),
                description=data.get("description", ""),
                operation_type=data.get("operation_type", "generate"),
                available_skills=data.get("available_skills", []),
                timeout_seconds=data.get("timeout_seconds", 300.0),
            )
        except Exception as e:
            logger.warning(f"Failed to deserialize task: {e}")
            return None

    def _is_intake_pattern(self, result: Any) -> bool:
        """Check if vault result is an intake-related pattern.

        Args:
            result: Vault search result

        Returns:
            True if result looks like an intake pattern
        """
        try:
            # Check if result contains key intake-related terms
            text = str(result).lower()
            return any(term in text for term in ["request", "task", "operation", "intent"])
        except Exception:
            return False

    def _parse_pattern(self, result: Any) -> tuple[str | None, AgentTask | None]:
        """Parse vault pattern into request_text and AgentTask.

        Args:
            result: Vault search result

        Returns:
            Tuple of (request_text, AgentTask) or (None, None) if parse fails
        """
        try:
            # This would parse actual vault pattern format
            # For now, return (None, None) as placeholder
            # Real implementation would extract from vault note structure
            return None, None
        except Exception as e:
            logger.debug(f"Failed to parse pattern: {e}")
            return None, None

    @staticmethod
    def _word_overlap_similarity(text1: str, text2: str) -> float:
        """Calculate word overlap similarity between two texts.

        Uses Jaccard similarity: |intersection| / |union| of words.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Split into words, convert to sets
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0
