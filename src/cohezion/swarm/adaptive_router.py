"""Adaptive routing engine with self-learning capabilities.

Routes tasks to optimal agents based on:
- Task characteristics (code, reasoning, context length)
- Historical performance (latency, quality, success rate)
- Time patterns (learns time-of-day preferences)
- Confidence scoring with explicit fallbacks
"""

from __future__ import annotations

import json
import re
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.swarm.dynamic_agent_registry import (
    AgentModule,
    DynamicAgentRegistry,
)
from cohezion.swarm.specialist_agents import SpecialistAgent


@dataclass
class RoutingDecision:
    """Routing decision with confidence and explanation."""

    agent_name: str
    confidence: float
    reasoning: str
    alternative_agents: list[str]
    expected_latency_ms: float
    expected_quality: float
    features: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_name": self.agent_name,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternative_agents": self.alternative_agents,
            "expected_latency_ms": self.expected_latency_ms,
            "expected_quality": self.expected_quality,
            "features": self.features,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RoutingHistory:
    """Single routing decision and outcome."""

    decision: RoutingDecision
    outcome: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        return self.outcome.get("success", False)

    @property
    def latency_ms(self) -> float:
        return self.outcome.get("latency_ms", 0)

    @property
    def quality_score(self) -> float:
        return self.outcome.get("quality_score", 0.5)


class TaskAnalyzer:
    """Analyze task characteristics for routing decisions."""

    # Pattern matching for task classification
    CODE_PATTERNS = [
        r"\b(code|program|function|class|script|bug|debug|error|exception)\b",
        r"\b(python|javascript|rust|go|c\+\+|java|typescript)\b",
        r"\b(implementation|algorithm|refactor|optimize|compile|build)\b",
        r"\b(write|create|generate)\s+(?:a|an)?\s*(?:code|function|class|script)\b",
    ]

    LONG_CONTEXT_PATTERNS = [
        r"\b(summarize|summary|document|paper|article|report|transcript)\b",
        r"\b(long|extensive|comprehensive|detailed|thorough)\b",
        r"\b(context|history|conversation|dialogue)\b",
        r"\b(analyze|review)\s+(?:this|the)\s+(?:document|text|file)\b",
    ]

    REASONING_PATTERNS = [
        r"\b(analyze|analysis|reason|evaluate|compare|contrast|assess)\b",
        r"\b(solve|solution|problem|explain|why|how does|what if)\b",
        r"\b(break down|step by step|step-by-step|logic)\b",
    ]

    NOVEL_PATTERNS = [
        r"\b(experiment|research|explore|novel|innovative|creative)\b",
        r"\b(try|test|prototype|validate|hypothesis)\b",
    ]

    URGENCY_PATTERNS = [
        r"\b(urgent|asap|immediately|critical|emergency|quickly)\b",
    ]

    def analyze(self, task: str, context: dict | None = None) -> dict[str, Any]:
        """Extract features from task for routing.

        Returns feature dictionary with:
        - text: Lowercase task text
        - length: Character length
        - has_code: Boolean
        - has_reasoning: Boolean
        - has_long_context: Boolean
        - has_novel: Boolean
        - urgency: 0.0-1.0 score
        - context_tokens: Estimated token count
        - time_of_day: Hour (0-23)
        """
        text_lower = task.lower()

        features = {
            "text": text_lower,
            "length": len(task),
            "has_code": self._matches_any(text_lower, self.CODE_PATTERNS),
            "has_reasoning": self._matches_any(text_lower, self.REASONING_PATTERNS),
            "has_long_context": self._matches_any(text_lower, self.LONG_CONTEXT_PATTERNS),
            "has_novel": self._matches_any(text_lower, self.NOVEL_PATTERNS),
            "urgency": self._detect_urgency(text_lower),
            "context_tokens": self._estimate_tokens(context),
            "time_of_day": datetime.now().hour,
        }

        return features

    def _matches_any(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any pattern."""
        return any(re.search(pattern, text) for pattern in patterns)

    def _detect_urgency(self, text: str) -> float:
        """Detect urgency level from text."""
        urgency_count = sum(1 for pattern in self.URGENCY_PATTERNS if re.search(pattern, text))
        return min(urgency_count / len(self.URGENCY_PATTERNS), 1.0)

    def _estimate_tokens(self, context: dict | None) -> int:
        """Estimate token count from context."""
        if not context:
            return 0

        history = context.get("history", [])
        if isinstance(history, list):
            # Rough estimate: 4 chars per token
            total_chars = sum(len(str(item)) for item in history)
            return total_chars // 4
        return 0


class AdaptiveRouter:
    """Self-learning router that improves over time.

    Features:
    - Rule-based initial routing
    - Historical performance tracking
    - Success matrix per agent/task combination
    - Automatic threshold adjustment
    - Explicit confidence scoring
    """

    def __init__(
        self,
        registry: DynamicAgentRegistry,
        history_size: int = 1000,
        learning_rate: float = 0.3,
    ):
        self.registry = registry
        self.analyzer = TaskAnalyzer()
        self._history: deque = deque(maxlen=history_size)
        self._learning_rate = learning_rate

        # Success matrix: agent_name -> task_feature_hash -> score
        self._success_matrix: dict[str, dict[str, float]] = {}

        # Adaptive thresholds
        self._thresholds = {
            "latency_ms": 500,
            "quality_score": 0.8,
            "success_rate": 0.95,
            "confidence": 0.7,
        }

        # Load historical data if exists
        self._load_weights()

    async def route(
        self,
        task: str,
        context: dict | None = None,
        strategy: str = "adaptive",
    ) -> RoutingDecision:
        """Route task to optimal agent using adaptive strategy.

        Args:
            task: Task description/prompt
            context: Optional context information
            strategy: Routing strategy ("adaptive", "greedy", "explore")

        Returns:
            RoutingDecision with confidence and alternatives
        """
        # Extract features
        features = self.analyzer.analyze(task, context)

        # Get all active agents
        candidates = self.registry.list_agents(active_only=True)

        if not candidates:
            return self._fallback_decision("No active agents available")

        # Score candidates
        scores = self._score_candidates(candidates, features, strategy)

        # Select best with alternatives
        ranked = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)

        if not ranked:
            return self._fallback_decision("No suitable agents found")

        best_agent, best_score = ranked[0]
        alternatives = [name for name, _ in ranked[1:3]]  # Top 2 alternatives

        # Calculate expected metrics
        expected_latency = self._estimate_latency(best_agent, features)
        expected_quality = self._estimate_quality(best_agent, features)

        # Generate reasoning
        reasoning = self._generate_reasoning(best_agent, best_score, features)

        decision = RoutingDecision(
            agent_name=best_agent,
            confidence=best_score["confidence"],
            reasoning=reasoning,
            alternative_agents=alternatives,
            expected_latency_ms=expected_latency,
            expected_quality=expected_quality,
            features=features,
        )

        # Log decision (no-op for now, could be extended)
        # await self._log_decision(decision, features)

        return decision

    async def _log_decision(self, decision: RoutingDecision, features: dict[str, Any]):
        """Log routing decision for analytics (placeholder)."""
        # Placeholder for logging infrastructure
        pass

    def _score_candidates(
        self,
        candidates: list[AgentModule],
        features: dict[str, Any],
        strategy: str,
    ) -> dict[str, dict[str, float]]:
        """Score all candidate agents."""
        scores = {}

        for agent_module in candidates:
            agent_name = agent_module.name
            agent = agent_module.create_instance()

            # Base score from rule matching
            base_score = self._calculate_match_score(agent, features)

            # Historical performance
            perf_score = self._get_performance_score(agent_name, features)

            # Confidence based on data availability
            confidence = self._calculate_confidence(agent_name)

            # Combine scores based on strategy
            if strategy == "greedy":
                total = base_score * 0.2 + perf_score * 0.8
            elif strategy == "explore":
                total = base_score * 0.8 + perf_score * 0.2
            else:  # adaptive (balanced)
                total = base_score * 0.4 + perf_score * 0.6

            scores[agent_name] = {
                "total": total,
                "base": base_score,
                "performance": perf_score,
                "confidence": confidence,
                "agent": agent_module,
            }

        return scores

    def _calculate_match_score(
        self,
        agent: SpecialistAgent,
        features: dict[str, Any],
    ) -> float:
        """Calculate rule-based match score."""
        score = 0.5  # Base score

        # Long context tasks
        if features.get("has_long_context") and features.get("context_tokens", 0) > 64000:
            if "long_context" in agent.capabilities:
                score += 0.3
            # Gemma-4-E2B has 256K context
            if "Gemma-4" in agent.model:
                score += 0.2

        # Code tasks
        if features.get("has_code"):
            if any(cap in agent.capabilities for cap in ["code_generation", "code"]):
                score += 0.3

        # Reasoning tasks
        if features.get("has_reasoning") and "complex_reasoning" in agent.capabilities:
            score += 0.3

        # Novel tasks
        if features.get("has_novel") and "novel_architecture" in agent.capabilities:
            score += 0.3

        # Urgency - prefer faster agents
        if features.get("urgency", 0) > 0.7 and agent.performance_stats.get("tps", 0) > 80:
            score += 0.1

        return min(score, 1.0)

    def _get_performance_score(
        self,
        agent_name: str,
        features: dict[str, Any],
    ) -> float:
        """Get historical performance score."""
        if agent_name not in self._success_matrix:
            return 0.5  # Neutral for new agents

        # Use simplified feature key
        task_key = self._feature_hash(features)

        if task_key in self._success_matrix[agent_name]:
            return self._success_matrix[agent_name][task_key]

        # Fall back to overall average
        values = list(self._success_matrix[agent_name].values())
        return statistics.mean(values) if values else 0.5

    def _feature_hash(self, features: dict[str, Any]) -> str:
        """Create simplified hash for feature-based lookup."""
        key_parts = [
            "1" if features.get("has_code") else "0",
            "1" if features.get("has_reasoning") else "0",
            str(min(features.get("context_tokens", 0) // 10000, 10)),
        ]
        return "-".join(key_parts)

    def _calculate_confidence(self, agent_name: str) -> float:
        """Calculate confidence based on data availability."""
        if agent_name not in self._success_matrix:
            return 0.3  # Low confidence for new agents

        num_samples = len(self._success_matrix[agent_name])

        if num_samples >= 50:
            return 0.95
        elif num_samples >= 20:
            return 0.8
        elif num_samples >= 10:
            return 0.6
        else:
            return 0.4

    def _estimate_latency(
        self,
        agent_name: str,
        features: dict[str, Any],
    ) -> float:
        """Estimate expected latency."""
        agent_module = self.registry.get_agent(agent_name)
        if not agent_module:
            return 500.0

        agent = agent_module.create_instance()
        base_latency = agent.performance_stats.get("latency_ms", 500)

        # Adjust for context length
        tokens = features.get("context_tokens", 0)
        if tokens > 100000:
            return base_latency * 1.5
        elif tokens > 50000:
            return base_latency * 1.2

        return base_latency

    def _estimate_quality(
        self,
        agent_name: str,
        features: dict[str, Any],
    ) -> float:
        """Estimate expected quality."""
        perf_score = self._get_performance_score(agent_name, features)
        # Convert to quality estimate
        return 0.5 + (perf_score * 0.5)  # Scale to 0.5-1.0

    def _generate_reasoning(
        self,
        agent_name: str,
        score: dict[str, float],
        features: dict[str, Any],
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        if score["base"] > 0.7:
            reasons.append("strong capability match")

        if score["performance"] > 0.8:
            reasons.append("excellent historical performance")
        elif score["performance"] > 0.6:
            reasons.append("good historical performance")

        if features.get("has_code"):
            reasons.append("code-specialized")
        elif features.get("has_reasoning"):
            reasons.append("reasoning-optimized")

        if features.get("context_tokens", 0) > 64000:
            reasons.append("long-context capable")

        if not reasons:
            reasons.append("best available match")

        return f"Selected {agent_name}: {', '.join(reasons)}"

    def _fallback_decision(self, reason: str) -> RoutingDecision:
        """Create fallback decision when no good option."""
        # Try to get any available agent
        agents = self.registry.list_agents(active_only=True)
        fallback = agents[0].name if agents else "unknown"

        return RoutingDecision(
            agent_name=fallback,
            confidence=0.1,
            reasoning=f"Fallback: {reason}",
            alternative_agents=[],
            expected_latency_ms=1000,
            expected_quality=0.5,
        )

    # ═══════════════════════════════════════════════════════════════════
    # Feedback Loop (Learning)
    # ═══════════════════════════════════════════════════════════════════

    async def feedback(
        self,
        decision: RoutingDecision,
        outcome: dict[str, Any],
    ):
        """Receive feedback to improve routing.

        Args:
            decision: The routing decision that was made
            outcome: Execution outcome with latency, quality, success
        """
        actual_latency = outcome.get("latency_ms", 0)
        actual_quality = outcome.get("quality_score", 0.5)
        success = outcome.get("success", False)

        # Calculate performance score
        task_key = self._feature_hash(decision.features)

        if decision.agent_name not in self._success_matrix:
            self._success_matrix[decision.agent_name] = {}

        # Exponential moving average update
        alpha = self._learning_rate
        old_score = self._success_matrix[decision.agent_name].get(task_key, 0.5)

        # Composite performance score
        latency_error = abs(actual_latency - decision.expected_latency_ms) / max(
            decision.expected_latency_ms, 1
        )
        latency_score = 1 - min(latency_error, 1)

        # Success is binary, quality is continuous
        success_score = 1.0 if success else 0.0

        performance = latency_score * 0.3 + actual_quality * 0.3 + success_score * 0.4

        new_score = (1 - alpha) * old_score + alpha * performance
        self._success_matrix[decision.agent_name][task_key] = new_score

        # Log to history
        self._history.append(
            RoutingHistory(
                decision=decision,
                outcome=outcome,
            )
        )

        # Persist weights
        await self._save_weights()

        # Periodic retraining
        if len(self._history) % 100 == 0:
            await self._retrain_model()

    async def _retrain_model(self):
        """Retrain routing model on accumulated data."""
        if len(self._history) < 50:
            return

        recent = list(self._history)[-100:]

        # Calculate optimal thresholds
        latencies = [h.latency_ms for h in recent]
        if latencies:
            self._thresholds["latency_ms"] = np.percentile(latencies, 90)

        qualities = [h.quality_score for h in recent]
        if qualities:
            self._thresholds["quality_score"] = np.mean(qualities)

        successes = [h.success for h in recent]
        if successes:
            self._thresholds["success_rate"] = np.mean(successes)

    # ═══════════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════════

    async def _save_weights(self):
        """Save learned weights to disk."""
        weights_file = Path("data/routing_weights.json")
        weights_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "success_matrix": self._success_matrix,
            "thresholds": self._thresholds,
            "last_updated": datetime.now().isoformat(),
            "history_size": len(self._history),
        }

        weights_file.write_text(json.dumps(data, indent=2))

    def _load_weights(self):
        """Load learned weights from disk."""
        weights_file = Path("data/routing_weights.json")
        if not weights_file.exists():
            return

        try:
            data = json.loads(weights_file.read_text())
            self._success_matrix = data.get("success_matrix", {})
            self._thresholds.update(data.get("thresholds", {}))
        except Exception as e:
            print(f"Failed to load routing weights: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # Analytics
    # ═══════════════════════════════════════════════════════════════════

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        if not self._history:
            return {"status": "no_data"}

        recent = list(self._history)

        return {
            "total_routings": len(recent),
            "success_rate": sum(h.success for h in recent) / len(recent),
            "avg_confidence": sum(h.decision.confidence for h in recent) / len(recent),
            "avg_latency_ms": statistics.mean(h.latency_ms for h in recent),
            "avg_quality": statistics.mean(h.quality_score for h in recent),
            "top_agents": self._get_top_agents(),
            "learning_progress": len(self._success_matrix),
        }

    def _get_top_agents(self, n: int = 5) -> list[tuple[str, float]]:
        """Get top performing agents."""
        agent_scores = []

        for agent_name, scores in self._success_matrix.items():
            if scores:
                avg_score = statistics.mean(scores.values())
                agent_scores.append((agent_name, avg_score))

        return sorted(agent_scores, key=lambda x: x[1], reverse=True)[:n]


# Convenience function
async def route_task(
    task: str,
    context: dict | None = None,
    registry: DynamicAgentRegistry | None = None,
) -> RoutingDecision:
    """Quick routing function."""
    from cohezion.swarm.dynamic_agent_registry import get_global_registry

    if registry is None:
        registry = get_global_registry()

    router = AdaptiveRouter(registry)
    return await router.route(task, context)
