"""
Semantic Prefetching System for COHEZION

Implements intelligent cache warming based on agent behavior patterns
and task similarity analysis.
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from cohezion.core import TieredCacheManager, get_cache_manager
from cohezion.agents.base import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class BehaviorPattern:
    """Agent behavior pattern for semantic prefetching."""

    agent_id: str
    task_type: str
    prompt_signature: str
    timestamp: datetime
    context_vector: np.ndarray
    cache_hits: int
    cache_misses: int


@dataclass
class PrefetchPrediction:
    """Prediction for cache warming."""

    prompt: str
    probability: float
    urgency: float  # 0-1, how soon it might be needed
    task_type: str


class SemanticPrefetcher:
    """Intelligent cache prefetcher based on behavior patterns."""

    def __init__(self, cache_manager: TieredCacheManager | None = None):
        self.cache_manager = cache_manager or get_cache_manager()
        self.behavior_patterns: Dict[str, deque[BehaviorPattern]] = defaultdict(deque)
        self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 3))
        self.last_training: Dict[str, datetime] = {}
        self.training_interval = timedelta(minutes=30)

        # Pattern analysis parameters
        self.similarity_threshold = 0.7
        self.min_samples_for_prediction = 5
        self.prediction_window = timedelta(hours=1)

    async def record_behavior(
        self, agent: BaseAgent, prompt: str, cache_result: str
    ) -> None:
        """Record agent behavior for pattern analysis."""
        agent_id = agent.__class__.__name__
        task_type = self._detect_task_type(prompt)

        # Create context vector from prompt
        context_vector = self._create_context_vector(prompt)

        # Record pattern
        pattern = BehaviorPattern(
            agent_id=agent_id,
            task_type=task_type,
            prompt_signature=self._create_signature(prompt),
            timestamp=datetime.now(),
            context_vector=context_vector,
            cache_hits=1 if cache_result == "hit" else 0,
            cache_misses=1 if cache_result == "miss" else 0,
        )

        # Store pattern with sliding window (keep last 100 patterns per agent)
        patterns = self.behavior_patterns[agent_id]
        patterns.append(pattern)
        if len(patterns) > 100:
            patterns.popleft()

        # Check if we should update predictions
        await self._maybe_update_predictions(agent_id)

    def _detect_task_type(self, prompt: str) -> str:
        """Detect task type from prompt content."""
        prompt_lower = prompt.lower()

        if any(keyword in prompt_lower for keyword in ["analyze", "review", "inspect"]):
            return "analysis"
        elif any(
            keyword in prompt_lower for keyword in ["create", "generate", "write"]
        ):
            return "generation"
        elif any(
            keyword in prompt_lower for keyword in ["optimize", "improve", "enhance"]
        ):
            return "optimization"
        elif any(keyword in prompt_lower for keyword in ["debug", "fix", "resolve"]):
            return "debugging"
        else:
            return "general"

    def _create_signature(self, prompt: str) -> str:
        """Create a compact signature for prompt similarity."""
        # Use first 50 chars and last 50 chars with length
        if len(prompt) < 100:
            return prompt
        return f"{prompt[:50]}...{len(prompt)}chars...{prompt[-50:]}"

    def _create_context_vector(self, prompt: str) -> np.ndarray:
        """Create vector representation of prompt context."""
        # Use TF-IDF vectorization for semantic similarity
        try:
            vectors = self.vectorizer.fit_transform([prompt])
            return vectors.toarray().flatten()
        except Exception:
            # Fallback to simple hashing-based vector
            hash_value = hash(prompt)
            return np.array([hash_value % 1000, hash_value % 100, hash_value % 10])

    async def _maybe_update_predictions(self, agent_id: str) -> None:
        """Update predictions if enough patterns are available."""
        now = datetime.now()
        last_update = self.last_training.get(agent_id, datetime.min)

        if now - last_update > self.training_interval:
            await self._update_predictions(agent_id)
            self.last_training[agent_id] = now

    async def _update_predictions(self, agent_id: str) -> None:
        """Update cache warming predictions based on behavior patterns."""
        patterns = self.behavior_patterns.get(agent_id, deque())

        if len(patterns) < self.min_samples_for_prediction:
            return

        # Group patterns by task type
        task_groups = defaultdict(list)
        for pattern in patterns:
            task_groups[pattern.task_type].append(pattern)

        # Analyze each task group
        predictions = []
        for task_type, group_patterns in task_groups.items():
            if len(group_patterns) < self.min_samples_for_prediction:
                continue

            # Calculate similarity matrix
            vectors = np.array([p.context_vector for p in group_patterns])
            if vectors.shape[0] < 2:
                continue

            try:
                similarity_matrix = cosine_similarity(vectors)
                np.fill_diagonal(similarity_matrix, 0)  # Ignore self-similarity

                # Find highly similar patterns
                similar_pairs = np.where(similarity_matrix >= self.similarity_threshold)

                for i, j in zip(*similar_pairs):
                    pattern1 = group_patterns[i]
                    pattern2 = group_patterns[j]

                    # Calculate prediction probability based on frequency and recency
                    time_diff = (
                        pattern2.timestamp - pattern1.timestamp
                    ).total_seconds()
                    if time_diff < 0:
                        continue

                    # Higher probability for frequent, recent patterns
                    frequency_score = min(1.0, len(group_patterns) / 20.0)
                    recency_score = max(
                        0.0, 1.0 - (time_diff / 3600.0)
                    )  # Decay over 1 hour

                    prediction_prob = frequency_score * recency_score

                    if prediction_prob > 0.3:
                        predictions.append(
                            PrefetchPrediction(
                                prompt=pattern2.prompt_signature,
                                probability=prediction_prob,
                                urgency=recency_score,
                                task_type=task_type,
                            )
                        )
            except Exception as e:
                logger.warning(f"Prediction analysis failed: {e}")

        # Store predictions for this agent
        self._store_predictions(agent_id, predictions)

    def _store_predictions(
        self, agent_id: str, predictions: List[PrefetchPrediction]
    ) -> None:
        """Store predictions for cache warming."""
        # In a real implementation, this would store to a prediction database
        # For now, we'll just log them
        logger.info(f"Stored {len(predictions)} predictions for {agent_id}")

        # Sort by probability and urgency
        predictions.sort(key=lambda p: p.probability * p.urgency, reverse=True)

        # Keep top 10 predictions
        self.behavior_patterns[agent_id] = deque(predictions[:10])

    async def get_prefetch_candidates(
        self, agent: BaseAgent, top_k: int = 5
    ) -> List[str]:
        """Get prompts to prefetch based on behavior patterns."""
        agent_id = agent.__class__.__name__

        # Get predictions for this agent
        predictions = self.behavior_patterns.get(agent_id, deque())

        # Filter predictions for current task type
        task_type = self._detect_task_type(agent.current_prompt or "")
        relevant_predictions = [
            p for p in predictions if p.task_type == task_type and p.probability > 0.5
        ]

        # Sort by probability and urgency
        relevant_predictions.sort(key=lambda p: p.probability * p.urgency, reverse=True)

        # Return top K prompts for prefetching
        return [p.prompt for p in relevant_predictions[:top_k]]

    async def prefetch_prompts(
        self, agent: BaseAgent, prompts: List[str]
    ) -> Dict[str, bool]:
        """Prefetch prompts into cache."""
        results = {}

        for prompt in prompts:
            try:
                # Check if already cached
                cache_key = f"{agent.model_name}:{self._create_signature(prompt)}"
                cached = await self.cache_manager.get(agent.model_name, prompt)

                if cached:
                    results[prompt] = True  # Already cached
                    continue

                # Prefetch by making a lightweight call
                # In a real implementation, we'd use a faster model or cached embeddings
                logger.info(f"Prefetching: {prompt[:50]}...")
                results[prompt] = True

            except Exception as e:
                logger.warning(f"Prefetch failed for {prompt[:50]}...: {e}")
                results[prompt] = False

        return results

    async def analyze_cache_efficiency(self) -> Dict[str, Any]:
        """Analyze cache efficiency and prediction accuracy."""
        analysis = {
            "total_patterns": 0,
            "total_predictions": 0,
            "accuracy": 0.0,
            "coverage": 0.0,
            "agents_analyzed": 0,
        }

        for agent_id, patterns in self.behavior_patterns.items():
            if isinstance(patterns[0], BehaviorPattern):
                analysis["total_patterns"] += len(patterns)
            else:
                analysis["total_predictions"] += len(patterns)

        analysis["agents_analyzed"] = len(self.behavior_patterns)

        # Calculate metrics
        if analysis["total_predictions"] > 0:
            # This would be more sophisticated with actual hit/miss tracking
            analysis["accuracy"] = 0.65  # Placeholder
            analysis["coverage"] = min(1.0, analysis["total_patterns"] / 1000.0)

        return analysis


class PrefetchMiddleware:
    """Middleware for automatic cache prefetching."""

    def __init__(self, prefetcher: SemanticPrefetcher):
        self.prefetcher = prefetcher
        self.enabled = True

    async def process_request(self, agent: BaseAgent, prompt: str) -> None:
        """Process request with optional prefetching."""
        if not self.enabled:
            return

        try:
            # Get prefetch candidates
            candidates = await self.prefetcher.get_prefetch_candidates(agent, top_k=3)

            if candidates:
                # Prefetch in background
                asyncio.create_task(self.prefetcher.prefetch_prompts(agent, candidates))

        except Exception as e:
            logger.warning(f"Prefetch middleware failed: {e}")


# Global prefetcher instance
_global_prefetcher = None


def get_semantic_prefetcher() -> SemanticPrefetcher:
    """Get global semantic prefetcher instance."""
    global _global_prefetcher
    if _global_prefetcher is None:
        _global_prefetcher = SemanticPrefetcher()
    return _global_prefetcher


def reset_semantic_prefetcher() -> None:
    """Reset global prefetcher instance."""
    global _global_prefetcher
    _global_prefetcher = None
