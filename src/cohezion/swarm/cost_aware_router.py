"""Cost-aware smart routing across local models with budget enforcement.

Features:
- Query complexity analysis (simple/medium/complex)
- Cost-optimized model routing (phi3:mini → qwen3-coder → deepseek-r1)
- Integration with BudgetEnforcer for hard stops
- Cost tracking per query and aggregation
- Chaos testing support with cost bounds

Architecture:
  Query Analysis (complexity)
       ↓
  Model Selection (cost-optimized)
       ↓
  Budget Check (enforcer integration)
       ↓
  Execute + Track Costs

Usage:
    router = CostAwareRouter.get_default()
    model, cost_est = router.select_model(
        query="Write a Python function",
        max_cost_usd=0.01
    )
    # Execute with selected model
    cost = tracker.track_usage_fast(model, tokens)
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity tiers for routing."""

    SIMPLE = "simple"  # Basic queries, few operations
    MEDIUM = "medium"  # Moderate complexity, reasoning required
    COMPLEX = "complex"  # Advanced tasks, multi-step reasoning


@dataclass
class ModelRoutingDecision:
    """Decision output from router."""

    model: str
    complexity: QueryComplexity
    estimated_tokens: int
    estimated_cost_usd: float
    reason: str
    quality_score: float  # 0.0-1.0


@dataclass
class RoutingStatistics:
    """Aggregated routing statistics."""

    total_queries: int
    simple_count: int
    medium_count: int
    complex_count: int
    phi3_routed: int  # Percentage: phi3_routed / total_queries
    qwen_routed: int
    deepseek_routed: int
    total_cost_usd: float
    avg_cost_per_query: float
    cost_vs_deepseek_only: float  # Percentage: (1 - actual/deepseek) * 100


class QueryComplexityAnalyzer:
    """Analyze query complexity for routing decisions."""

    # Keywords indicating simple queries
    SIMPLE_KEYWORDS = {
        "what",
        "when",
        "where",
        "how many",
        "explain",
        "define",
        "list",
        "is",
        "are",
        "how",
    }

    # Keywords indicating complex queries (must be >= 2 for complex)
    COMPLEX_KEYWORDS = {
        "design",
        "implement",
        "build",
        "architecture",
        "debug",
        "optimize",
        "refactor",
        "production",
        "scalable",
        "distributed",
        "algorithm",
        "security",
        "performance",
        "research",
    }

    def __init__(self):
        """Initialize analyzer."""
        self.history: list[dict] = []

    def analyze(self, query: str) -> QueryComplexity:
        """Analyze query complexity.

        Args:
            query: User query string

        Returns:
            QueryComplexity tier (SIMPLE, MEDIUM, or COMPLEX)
        """
        # Token estimation (rough)
        token_count = self._estimate_tokens(query)

        # Keyword analysis
        query_lower = query.lower()
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)

        # Heuristics
        has_code = any(pattern in query for pattern in ["```", "def ", "class ", "import", "function"])
        has_data_processing = any(
            word in query_lower for word in ["process", "analyze", "transform", "pipeline"]
        )
        has_logic = " and " in query_lower or " or " in query_lower or "if " in query_lower
        is_short = token_count < 30
        is_long = token_count > 200

        # Determine complexity tier
        # SIMPLE: very short, mostly simple keywords, no code
        if is_short and simple_matches > 0 and complex_matches == 0 and not has_code:
            complexity = QueryComplexity.SIMPLE
        # COMPLEX: has multiple complex keywords, code, or is long with logic
        elif (complex_matches >= 2) or (has_code and has_logic) or (is_long and has_data_processing):
            complexity = QueryComplexity.COMPLEX
        # MEDIUM: everything else
        else:
            complexity = QueryComplexity.MEDIUM

        # Record for analytics
        self.history.append(
            {
                "timestamp": time.time(),
                "query_len": len(query),
                "token_count": token_count,
                "simple_matches": simple_matches,
                "complex_matches": complex_matches,
                "complexity": complexity.value,
            }
        )

        return complexity

    def _estimate_tokens(self, query: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars).

        Args:
            query: Query string

        Returns:
            Estimated token count
        """
        # Remove markdown code blocks
        clean = re.sub(r"```[\s\S]*?```", "", query)
        # Estimate tokens
        return max(1, len(clean) // 4)

    def get_stats(self) -> dict:
        """Get analyzer statistics.

        Returns:
            Dictionary with complexity distribution
        """
        if not self.history:
            return {
                "total_queries": 0,
                "simple_pct": 0.0,
                "medium_pct": 0.0,
                "complex_pct": 0.0,
            }

        total = len(self.history)
        simple_count = sum(1 for h in self.history if h["complexity"] == QueryComplexity.SIMPLE.value)
        medium_count = sum(1 for h in self.history if h["complexity"] == QueryComplexity.MEDIUM.value)
        complex_count = sum(1 for h in self.history if h["complexity"] == QueryComplexity.COMPLEX.value)

        return {
            "total_queries": total,
            "simple_pct": (simple_count / total) * 100,
            "medium_pct": (medium_count / total) * 100,
            "complex_pct": (complex_count / total) * 100,
            "avg_token_count": sum(h["token_count"] for h in self.history) / total,
        }


class CostAwareRouter:
    """Smart cost-aware model routing with budget enforcement.

    Decision tree:
    1. Analyze query complexity
    2. Check budget constraints
    3. Select optimal model
    4. Track costs and integrate with enforcer
    """

    # Model costs per 1K tokens (local models = $0.00)
    MODEL_COSTS = {
        "phi3:mini": 0.0,  # Local, 100x cheaper than deepseek
        "qwen3-coder:32b": 0.0,  # Local
        "deepseek-r1:8b": 0.0,  # Local
    }

    # Expected token counts by complexity
    EXPECTED_TOKENS = {
        QueryComplexity.SIMPLE: 100,  # Simple queries: ~100 tokens
        QueryComplexity.MEDIUM: 250,  # Medium: ~250 tokens
        QueryComplexity.COMPLEX: 500,  # Complex: ~500 tokens
    }

    # Quality scores per model (0.0 - 1.0)
    MODEL_QUALITY = {
        "phi3:mini": 0.6,  # Fast, basic tasks
        "qwen3-coder:32b": 0.85,  # Good balance
        "deepseek-r1:8b": 0.95,  # Best quality
    }

    # TPS (tokens per second) for cost-time tradeoff
    MODEL_TPS = {
        "phi3:mini": 15.0,  # Fastest
        "qwen3-coder:32b": 8.0,  # Moderate
        "deepseek-r1:8b": 2.0,  # Slowest but best
    }

    _instance: Optional["CostAwareRouter"] = None

    def __init__(
        self,
        cost_tracker: Optional[SessionCostTracker] = None,
        budget_enforcer: Optional[BudgetEnforcer] = None,
    ):
        """Initialize router.

        Args:
            cost_tracker: Session cost tracker (optional, uses current if None)
            budget_enforcer: Budget enforcer (optional, uses current if None)
        """
        self.cost_tracker = cost_tracker or SessionCostTracker.get_current()
        self.budget_enforcer = budget_enforcer or BudgetEnforcer.get_current()
        self.complexity_analyzer = QueryComplexityAnalyzer()

        # Statistics tracking
        self.routing_decisions: list[ModelRoutingDecision] = []
        self.cost_per_model: dict[str, float] = {
            m: 0.0 for m in self.MODEL_COSTS.keys()
        }
        self.query_count_per_model: dict[str, int] = {m: 0 for m in self.MODEL_COSTS.keys()}

    @classmethod
    def get_default(cls) -> "CostAwareRouter":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (testing only)."""
        cls._instance = None

    def select_model(
        self, query: str, max_cost_usd: Optional[float] = None
    ) -> Tuple[ModelRoutingDecision, bool]:
        """Select optimal model for query.

        Args:
            query: User query
            max_cost_usd: Maximum allowed cost (optional)

        Returns:
            Tuple of (decision, can_proceed)
            - decision: ModelRoutingDecision with selected model
            - can_proceed: False if budget enforcer blocks (decision still returned)
        """
        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(query)
        estimated_tokens = self.EXPECTED_TOKENS[complexity]

        # Select model by complexity
        if complexity == QueryComplexity.SIMPLE:
            model = "phi3:mini"
        elif complexity == QueryComplexity.MEDIUM:
            model = "qwen3-coder:32b"
        else:
            model = "deepseek-r1:8b"

        # Calculate estimated cost
        cost_per_1k = self.MODEL_COSTS[model]
        estimated_cost = (estimated_tokens / 1000.0) * cost_per_1k

        # Check budget constraint
        can_proceed = True
        if max_cost_usd and estimated_cost > max_cost_usd:
            can_proceed = False

        # Check budget enforcer (if available)
        if self.budget_enforcer and self.cost_tracker:
            enforcer_ok, enforcer_msg = self.budget_enforcer.check_budget(
                self.cost_tracker.total_cost_usd + estimated_cost
            )
            if not enforcer_ok:
                can_proceed = False

        # Build decision
        decision = ModelRoutingDecision(
            model=model,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            reason=f"Routed {complexity.value} query to {model}",
            quality_score=self.MODEL_QUALITY[model],
        )

        # Record decision
        self.routing_decisions.append(decision)
        self.query_count_per_model[model] += 1

        logger.info(
            f"Cost router: {complexity.value} query → {model} "
            f"(est. {estimated_tokens} tokens, ${estimated_cost:.6f})"
        )

        return decision, can_proceed

    def record_execution(
        self, model: str, actual_tokens: int, duration_ms: float
    ) -> float:
        """Record execution and track costs.

        Args:
            model: Model name
            actual_tokens: Actual tokens used
            duration_ms: Execution duration in milliseconds

        Returns:
            Cost in USD
        """
        # Track with cost tracker
        cost_usd = 0.0
        if self.cost_tracker:
            cost_usd = self.cost_tracker.track_usage_fast(
                model=model, tokens=actual_tokens, duration_ms=duration_ms
            )
        else:
            # Fallback calculation
            cost_per_1k = self.MODEL_COSTS.get(model, 0.0)
            cost_usd = (actual_tokens / 1000.0) * cost_per_1k

        # Update aggregated costs
        self.cost_per_model[model] += cost_usd

        logger.debug(
            f"Recorded execution: {model} {actual_tokens} tokens, "
            f"${cost_usd:.6f}, {duration_ms:.1f}ms"
        )

        return cost_usd

    def get_statistics(self) -> RoutingStatistics:
        """Get routing statistics.

        Returns:
            RoutingStatistics with aggregated metrics
        """
        total = len(self.routing_decisions)
        if total == 0:
            total = 1  # Avoid division by zero

        simple_count = sum(
            1 for d in self.routing_decisions if d.complexity == QueryComplexity.SIMPLE
        )
        medium_count = sum(
            1 for d in self.routing_decisions if d.complexity == QueryComplexity.MEDIUM
        )
        complex_count = sum(
            1 for d in self.routing_decisions if d.complexity == QueryComplexity.COMPLEX
        )

        phi3_routed = self.query_count_per_model.get("phi3:mini", 0)
        qwen_routed = self.query_count_per_model.get("qwen3-coder:30b", 0)
        deepseek_routed = self.query_count_per_model.get("deepseek-r1:70b", 0)

        total_cost = sum(self.cost_per_model.values())

        # Calculate cost comparison (hypothetical: all queries with deepseek)
        deepseek_only_cost = sum(d.estimated_tokens for d in self.routing_decisions) / 1000.0 * self.MODEL_COSTS[
            "deepseek-r1:8b"
        ]

        cost_improvement = 0.0
        if deepseek_only_cost > 0:
            cost_improvement = ((deepseek_only_cost - total_cost) / deepseek_only_cost) * 100

        return RoutingStatistics(
            total_queries=total,
            simple_count=simple_count,
            medium_count=medium_count,
            complex_count=complex_count,
            phi3_routed=phi3_routed,
            qwen_routed=qwen_routed,
            deepseek_routed=deepseek_routed,
            total_cost_usd=total_cost,
            avg_cost_per_query=total_cost / total if total > 0 else 0.0,
            cost_vs_deepseek_only=cost_improvement,
        )

    def reset_statistics(self) -> None:
        """Reset router statistics (testing only)."""
        self.routing_decisions.clear()
        self.cost_per_model = {m: 0.0 for m in self.MODEL_COSTS.keys()}
        self.query_count_per_model = {m: 0 for m in self.MODEL_COSTS.keys()}


def get_cost_aware_router() -> CostAwareRouter:
    """Get or create cost-aware router instance."""
    return CostAwareRouter.get_default()


def reset_cost_aware_router() -> None:
    """Reset router instance (testing only)."""
    CostAwareRouter.reset()
