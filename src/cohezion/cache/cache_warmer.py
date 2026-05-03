"""Proactive cache warming from vault execution history.

Strategies:
    1. Most frequently executed skills
    2. Skills with highest token cost
    3. Patterns from successful compound cycles
    4. Recent high-coherence executions
"""

import json
import logging
from typing import Any

from cohezion.cache.semantic_cache import SemanticCache


logger = logging.getLogger(__name__)


class CacheWarmer:
    """Warm cache from vault patterns and execution history.

    Strategies:
        1. Most frequently executed skills
        2. Skills with highest token cost
        3. Patterns from successful compound cycles
        4. Recent high-coherence executions
    """

    def __init__(self, semantic_cache: SemanticCache, mcp_client: Any = None):
        """Initialize cache warmer.

        Args:
            semantic_cache: SemanticCache instance to warm
            mcp_client: Optional MCPClient for vault operations
        """
        self.cache = semantic_cache
        self.mcp_client = mcp_client

    async def warm_from_vault(self, limit: int = 100) -> int:
        """Load top N cache patterns from vault into cache.

        Searches vault for cache_patterns directory and loads
        successful prompt-response pairs into L1 and L2 caches.

        Args:
            limit: Maximum patterns to load (default: 100)

        Returns:
            Number of entries loaded
        """
        if not self.mcp_client:
            logger.debug("Cache warming disabled (no MCPClient)")
            return 0

        try:
            # List all cache pattern files from vault
            pattern_files = self.mcp_client.vault_list(directory="cache_patterns", recursive=True)

            if not pattern_files:
                logger.debug("No cache patterns found in vault")
                return 0

            # Load patterns (limit to N most recent)
            loaded = 0
            for file_path in pattern_files[:limit]:
                try:
                    # Read pattern file
                    content = self.mcp_client.vault_read(path=file_path)
                    pattern = json.loads(content)

                    # Load into cache
                    if "prompt" in pattern and "response" in pattern:
                        await self.cache.put(
                            prompt=pattern["prompt"],
                            response=pattern["response"],
                        )
                        loaded += 1

                except Exception as e:
                    logger.debug(f"Failed to load pattern {file_path}: {e}")
                    continue

            logger.info(f"Warmed cache with {loaded} patterns from vault")
            return loaded

        except Exception as e:
            logger.debug(f"Cache warming from vault failed: {e}")
            return 0

    async def find_template_match(
        self,
        task_description: str,
        similarity_threshold: float = 0.85,
    ) -> dict[str, Any] | None:
        """Query cache for a template match before executing an LLM call.

        If a sufficiently similar task has been completed before, return the
        cached response. This skips the LLM entirely for known patterns.

        Args:
            task_description: The task to match against
            similarity_threshold: Minimum cosine similarity (default 0.85)

        Returns:
            Dict with {response, similarity, source} if match found, None otherwise
        """
        # Try L1 exact match first (fastest)
        l1_result = await self.cache.get(task_description)
        if l1_result:
            logger.info("Template match: L1 exact hit for '%s'", task_description[:50])
            return {
                "response": l1_result,
                "similarity": 1.0,
                "source": "L1_exact",
                "tokens_saved": len(task_description.split()) * 4,  # rough estimate
            }

        # Try L2 semantic match (cosine similarity)
        if hasattr(self.cache, "_l2_cache") and self.cache._l2_cache:
            try:
                embedding = self.cache._embed(task_description)
                if embedding is not None:
                    best_match = None
                    best_sim = 0.0

                    for entry in self.cache._l2_cache.values():
                        if entry.embedding is not None:
                            sim = self.cache._cosine_similarity(embedding, entry.embedding)
                            if sim > best_sim:
                                best_sim = sim
                                best_match = entry

                    if best_match and best_sim >= similarity_threshold:
                        logger.info(
                            "Template match: L2 semantic hit (%.2f similarity) for '%s'",
                            best_sim,
                            task_description[:50],
                        )
                        return {
                            "response": best_match.response,
                            "similarity": best_sim,
                            "source": "L2_semantic",
                            "tokens_saved": len(task_description.split()) * 4,
                        }
            except Exception as e:
                logger.debug("L2 template search failed: %s", e)

        return None

    async def warm_from_history(self, skill_name: str, min_coherence: float = 0.7) -> int:
        """Warm cache for specific skill from execution history.

        Queries vault for all executions of the specified skill,
        filters by coherence score, and loads top performers into cache.

        Args:
            skill_name: Name of skill to warm cache for
            min_coherence: Minimum coherence threshold (default: 0.7)

        Returns:
            Number of entries loaded
        """
        if not self.mcp_client:
            logger.debug("Cache warming disabled (no MCPClient)")
            return 0

        try:
            # Query vault for execution traces of this skill
            trace_path = f"execution_traces/{skill_name}/"
            trace_files = self.mcp_client.vault_list(directory=trace_path, recursive=True)

            if not trace_files:
                logger.debug(f"No execution traces found for skill: {skill_name}")
                return 0

            loaded = 0
            execution_data = []

            # Load all traces and extract coherence scores
            for file_path in trace_files:
                try:
                    content = self.mcp_client.vault_read(path=file_path)
                    trace = json.loads(content)

                    # Extract coherence and execution data
                    coherence = trace.get("coherence", 0.0)
                    success = trace.get("success", False)

                    # Only consider successful, high-coherence executions
                    if success and coherence >= min_coherence:
                        execution_data.append(
                            {
                                "coherence": coherence,
                                "trace": trace,
                                "path": file_path,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Failed to load trace {file_path}: {e}")
                    continue

            # Sort by coherence (highest first)
            execution_data.sort(key=lambda x: x["coherence"], reverse=True)

            # Load top performers into cache
            for item in execution_data:
                try:
                    trace = item["trace"]
                    task_description = trace.get("task_description", "")
                    output_summary = trace.get("output_summary", "")

                    if task_description and output_summary:
                        await self.cache.put(
                            prompt=task_description,
                            response=output_summary,
                            metadata={
                                "coherence": item["coherence"],
                                "source": f"vault_history_{skill_name}",
                                "trace_path": item["path"],
                            },
                        )
                        loaded += 1
                except Exception as e:
                    logger.debug(f"Failed to cache entry from {item['path']}: {e}")
                    continue

            logger.info(
                f"Warmed cache with {loaded} high-coherence executions for skill '{skill_name}'"
            )
            return loaded

        except Exception as e:
            logger.debug(f"Cache warming from history failed for {skill_name}: {e}")
            return 0

    async def warm_from_recent_executions(self, limit: int = 50, min_coherence: float = 0.7) -> int:
        """Warm cache from recent successful executions.

        Queries vault for recent high-coherence executions across all skills,
        extracts (prompt, response) pairs, and loads them into cache.

        Args:
            limit: Maximum recent executions to use (default: 50)
            min_coherence: Minimum coherence threshold (default: 0.7)

        Returns:
            Number of entries loaded
        """
        if not self.mcp_client:
            logger.debug("Cache warming disabled (no MCPClient)")
            return 0

        try:
            # List all execution traces from vault
            trace_files = self.mcp_client.vault_list(directory="execution_traces/", recursive=True)

            if not trace_files:
                logger.debug("No execution traces found in vault")
                return 0

            loaded = 0
            execution_data = []

            # Load all traces and extract metadata
            for file_path in trace_files:
                try:
                    content = self.mcp_client.vault_read(path=file_path)
                    trace = json.loads(content)

                    # Extract coherence and timestamp
                    coherence = trace.get("coherence", 0.0)
                    success = trace.get("success", False)
                    end_time = trace.get("end_time", "")

                    # Only consider successful, high-coherence executions
                    if success and coherence >= min_coherence:
                        execution_data.append(
                            {
                                "coherence": coherence,
                                "end_time": end_time,
                                "trace": trace,
                                "path": file_path,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Failed to load trace {file_path}: {e}")
                    continue

            # Sort by end_time (most recent first), then by coherence
            execution_data.sort(key=lambda x: (x["end_time"], x["coherence"]), reverse=True)

            # Load top N recent executions into cache
            for item in execution_data[:limit]:
                try:
                    trace = item["trace"]
                    task_description = trace.get("task_description", "")
                    output_summary = trace.get("output_summary", "")
                    skill_name = trace.get("skill_name", "unknown")

                    if task_description and output_summary:
                        await self.cache.put(
                            prompt=task_description,
                            response=output_summary,
                            metadata={
                                "coherence": item["coherence"],
                                "source": f"vault_recent_{skill_name}",
                                "trace_path": item["path"],
                                "end_time": item["end_time"],
                            },
                        )
                        loaded += 1
                except Exception as e:
                    logger.debug(f"Failed to cache entry from {item['path']}: {e}")
                    continue

            logger.info(
                f"Warmed cache with {loaded} recent high-coherence executions "
                f"(from {len(execution_data)} candidates)"
            )
            return loaded

        except Exception as e:
            logger.debug(f"Cache warming from recent executions failed: {e}")
            return 0

    def analyze_cache_effectiveness(self) -> dict:
        """Analyze current cache effectiveness.

        Returns:
            Dict with cache metrics and recommendations
        """
        stats = self.cache.get_stats()
        return {
            "current_hit_rate": stats["overall_hit_rate"],
            "l1_hit_rate": stats["l1_hit_rate"],
            "l2_hit_rate": stats["l2_hit_rate"],
            "cache_fullness_l1": stats["l1_size"] / 512 * 100,
            "cache_fullness_l2": stats["l2_size"] / 1024 * 100,
            "recommendation": (
                "L1 cache is full, consider increasing max_l1_size"
                if stats["l1_size"] >= 512
                else "Cache performance is good"
            ),
        }
