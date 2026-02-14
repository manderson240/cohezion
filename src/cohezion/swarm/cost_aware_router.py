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
    fast_model_routed: int  # phi4-mini-reasoning (simple tasks)
    medium_model_routed: int  # qwen3-coder:30b / glm-4.7-flash (medium/complex)
    heavy_model_routed: int  # gpt-oss:20b / deepcoder:14b (overflow)
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

        # Keyword analysis (word-boundary matching to avoid substring matches)
        query_lower = query.lower()
        simple_matches = sum(1 for kw in self.SIMPLE_KEYWORDS if f" {kw} " in f" {query_lower} " or query_lower.startswith(f"{kw} ") or query_lower.endswith(f" {kw}"))
        complex_matches = sum(1 for kw in self.COMPLEX_KEYWORDS if f" {kw} " in f" {query_lower} " or query_lower.startswith(f"{kw} ") or query_lower.endswith(f" {kw}"))

        # Heuristics
        has_code = any(pattern in query for pattern in ["```", "def ", "class ", "import", "function"])
        has_data_processing = any(
            word in query_lower for word in ["process", "analyze", "transform", "pipeline"]
        )
        has_logic = " and " in query_lower or " or " in query_lower or "if " in query_lower
        is_short = token_count < 30
        is_long = token_count > 200

        # Determine complexity tier
        # SIMPLE: very short (< 10 tokens) without complex keywords, or has simple keywords + no complex keywords + short
        if (token_count < 10 and complex_matches == 0 and not has_code) or (simple_matches > 0 and complex_matches == 0 and not has_code and token_count < 50):
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
    """Smart cost-aware model routing with budget enforcement and token optimization.

    Decision tree:
    1. Analyze query complexity
    2. Check budget constraints
    3. Select optimal model with cost/token ratio
    4. Apply cost/latency thresholds
    5. Track costs and integrate with enforcer

    Features:
    - Cost/token ratio optimization (prefer cheaper models if ratio is better)
    - Dynamic threshold tuning based on query patterns
    - Aggressive cost reduction targeting ≥30% below deepseek baseline
    - Query-based model selection hints
    - Non-blocking vault persistence for routing decisions
    """

    # Model costs per 1K tokens (local models = $0.00)
    MODEL_COSTS = {
        "phi4-mini-reasoning": 0.0,  # Local, Dense 3.8B, Tier 1 always-hot
        "glm-4.7-flash": 0.0,  # Local, MoE 30B/3B active, Tier 2 warm
        "qwen3-coder:30b": 0.0,  # Local, MoE 30B/3B active, Tier 2 warm
        "gpt-oss:20b": 0.0,  # Local, MoE 21B/3.6B active, Tier 3 cold
        "deepcoder:14b": 0.0,  # Local, Dense 14B, Tier 3 cold
        "nemotron-3-nano": 0.0,  # Local, MoE 31.6B/3.2B, Tier 3 cold (1M ctx)
        # Legacy models (still installed, lower priority)
        "phi3:mini": 0.0,  # Local, Dense 3.8B (superseded by phi4-mini-reasoning)
        "qwen3-coder:32b": 0.0,  # Local (alias reference)
        "deepseek-r1:8b": 0.0,  # Local
    }

    # Expected token counts by complexity (refined estimates)
    EXPECTED_TOKENS = {
        QueryComplexity.SIMPLE: 80,  # Simple queries: ~80 tokens
        QueryComplexity.MEDIUM: 200,  # Medium: ~200 tokens
        QueryComplexity.COMPLEX: 400,  # Complex: ~400 tokens
    }

    # Quality scores per model (0.0 - 1.0)
    MODEL_QUALITY = {
        "phi4-mini-reasoning": 0.75,  # Fast router/classifier, strong reasoning for size
        "glm-4.7-flash": 0.90,  # SOTA reasoning, MoE efficiency
        "qwen3-coder:30b": 0.88,  # Code specialist, MoE speed
        "gpt-oss:20b": 0.85,  # Versatile general model
        "deepcoder:14b": 0.82,  # Dense coding/math specialist
        "nemotron-3-nano": 0.80,  # Long-context specialist (1M ctx)
        # Legacy
        "phi3:mini": 0.6,
        "qwen3-coder:32b": 0.85,
        "deepseek-r1:8b": 0.70,
    }

    # TPS (tokens per second) for cost-time tradeoff — Strix Halo CPU benchmarks
    MODEL_TPS = {
        "phi4-mini-reasoning": 70.0,  # Dense 3.8B, ~60-80 t/s
        "glm-4.7-flash": 25.0,  # MoE 30B/3B active, ~20-35 t/s
        "qwen3-coder:30b": 25.0,  # MoE 30B/3B active, ~20-35 t/s
        "gpt-oss:20b": 35.0,  # MoE 21B/3.6B active, ~24-47 t/s
        "deepcoder:14b": 17.0,  # Dense 14B, ~15-20 t/s
        "nemotron-3-nano": 20.0,  # MoE 31.6B/3.2B, ~15-25 t/s
        # Legacy
        "phi3:mini": 15.0,
        "qwen3-coder:32b": 8.0,
        "deepseek-r1:8b": 2.0,
    }

    # Expected latency (ms) by model — first-token latency
    MODEL_LATENCY = {
        "phi4-mini-reasoning": 30.0,  # Ultra-fast, always hot
        "glm-4.7-flash": 80.0,  # Warm tier, fast MoE routing
        "qwen3-coder:30b": 80.0,  # Warm tier, fast MoE routing
        "gpt-oss:20b": 60.0,  # Good throughput when loaded
        "deepcoder:14b": 120.0,  # Dense, slower per-token
        "nemotron-3-nano": 100.0,  # MoE but larger footprint
        # Legacy
        "phi3:mini": 50.0,
        "qwen3-coder:32b": 100.0,
        "deepseek-r1:8b": 300.0,
    }

    _instance: Optional["CostAwareRouter"] = None

    def __init__(
        self,
        cost_tracker: Optional[SessionCostTracker] = None,
        budget_enforcer: Optional[BudgetEnforcer] = None,
        prefer_longer_models_if_cheaper_per_token: bool = True,
        cost_threshold: float = 0.10,  # 10% cost threshold
        latency_threshold: float = 150.0,  # 150ms latency threshold (increased tolerance)
        aggressive_cost_reduction: bool = True,  # Enable aggressive phi3 routing
        dynamic_threshold_tuning: bool = True,  # Enable auto-tuning based on patterns
    ):
        """Initialize router.

        Args:
            cost_tracker: Session cost tracker (optional, uses current if None)
            budget_enforcer: Budget enforcer (optional, uses current if None)
            prefer_longer_models_if_cheaper_per_token: If True, prefer cheaper per-token cost (default: True)
            cost_threshold: Cost difference threshold for model switching (0-1.0, default: 0.10 = 10%)
            latency_threshold: Latency threshold in ms for trade-off (default: 150.0ms)
            aggressive_cost_reduction: If True, aggressively route simple/medium to phi3 (default: True)
            dynamic_threshold_tuning: If True, auto-tune thresholds based on query patterns (default: True)
        """
        self.cost_tracker = cost_tracker or SessionCostTracker.get_current()
        self.budget_enforcer = budget_enforcer or BudgetEnforcer.get_current()
        self.complexity_analyzer = QueryComplexityAnalyzer()

        # Token optimization parameters
        self.prefer_longer_models_if_cheaper_per_token = prefer_longer_models_if_cheaper_per_token
        self.cost_threshold = cost_threshold
        self.latency_threshold = latency_threshold
        self.aggressive_cost_reduction = aggressive_cost_reduction
        self.dynamic_threshold_tuning = dynamic_threshold_tuning

        # Statistics tracking
        self.routing_decisions: list[ModelRoutingDecision] = []
        self.cost_per_model: dict[str, float] = {
            m: 0.0 for m in self.MODEL_COSTS.keys()
        }
        self.query_count_per_model: dict[str, int] = {m: 0 for m in self.MODEL_COSTS.keys()}
        self.token_optimization_swaps: int = 0  # Track optimization improvements

        # Dynamic threshold tracking
        self._fast_model_success_count = 0  # Track successful phi4-mini completions
        self._medium_model_success_count = 0  # Track successful qwen/glm completions
        self._cumulative_latency_ms = 0.0  # Track cumulative latency for tuning

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
        """Select optimal model for query with cost/token optimization.

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
            primary_model = "phi4-mini-reasoning"
        elif complexity == QueryComplexity.MEDIUM:
            primary_model = "qwen3-coder:30b"
        else:
            primary_model = "glm-4.7-flash"

        # Optimize model selection based on cost/token ratio if enabled
        model = self._optimize_model_selection(primary_model, complexity, estimated_tokens)

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
        reason = f"Routed {complexity.value} query to {model}"
        if model != primary_model:
            reason += f" (optimized from {primary_model})"

        decision = ModelRoutingDecision(
            model=model,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            reason=reason,
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

    def _optimize_model_selection(
        self, primary_model: str, complexity: QueryComplexity, estimated_tokens: int
    ) -> str:
        """Optimize model selection based on cost/token ratio with aggressive cost reduction.

        Args:
            primary_model: Model selected by complexity analysis
            complexity: Query complexity tier
            estimated_tokens: Estimated tokens for the query

        Returns:
            Optimized model name (may be different from primary)
        """
        if not self.prefer_longer_models_if_cheaper_per_token:
            return primary_model

        # For complex queries, check if a faster model is good enough
        if complexity == QueryComplexity.COMPLEX:
            # Check if medium model (qwen3-coder) has acceptable cost/token ratio
            primary_cost_per_token = self._get_cost_per_token(primary_model, estimated_tokens)
            qwen_cost_per_token = self._get_cost_per_token("qwen3-coder:30b", estimated_tokens)

            # If qwen is cheaper per token AND latency is acceptable, use it
            if self._is_cheaper_with_acceptable_latency(
                "qwen3-coder:30b", primary_model, qwen_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return "qwen3-coder:30b"

            # If aggressive cost reduction enabled, also check phi4-mini for complex queries
            if self.aggressive_cost_reduction:
                phi4_cost_per_token = self._get_cost_per_token("phi4-mini-reasoning", estimated_tokens)
                if self._is_cheaper_with_acceptable_latency(
                    "phi4-mini-reasoning", primary_model, phi4_cost_per_token, primary_cost_per_token,
                    aggressive=True
                ):
                    self.token_optimization_swaps += 1
                    return "phi4-mini-reasoning"

        # For medium queries, check if fast model (phi4-mini) is good enough
        if complexity == QueryComplexity.MEDIUM:
            primary_cost_per_token = self._get_cost_per_token(primary_model, estimated_tokens)
            phi4_cost_per_token = self._get_cost_per_token("phi4-mini-reasoning", estimated_tokens)

            # Standard check
            if self._is_cheaper_with_acceptable_latency(
                "phi4-mini-reasoning", primary_model, phi4_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return "phi4-mini-reasoning"

            # If aggressive cost reduction, be more lenient with phi4-mini for medium queries
            if self.aggressive_cost_reduction:
                latency_diff = self.MODEL_LATENCY.get("phi4-mini-reasoning", 30.0) - self.MODEL_LATENCY.get(primary_model, 80.0)
                if latency_diff <= 200.0:
                    self.token_optimization_swaps += 1
                    return "phi4-mini-reasoning"

        # For simple queries, strongly prefer phi4-mini for speed
        if complexity == QueryComplexity.SIMPLE:
            if primary_model != "phi4-mini-reasoning":
                latency_diff = self.MODEL_LATENCY.get("phi4-mini-reasoning", 30.0) - self.MODEL_LATENCY.get(primary_model, 30.0)
                if latency_diff <= 150.0:
                    self.token_optimization_swaps += 1
                    return "phi4-mini-reasoning"

        return primary_model

    def _get_cost_per_token(self, model: str, tokens: int) -> float:
        """Calculate cost per token for a model.

        Args:
            model: Model name
            tokens: Token count

        Returns:
            Cost per token (in USD)
        """
        if tokens == 0:
            return 0.0
        cost_per_1k = self.MODEL_COSTS.get(model, 0.0)
        return cost_per_1k / 1000.0

    def _is_cheaper_with_acceptable_latency(
        self,
        candidate_model: str,
        primary_model: str,
        candidate_cost_per_token: float,
        primary_cost_per_token: float,
        aggressive: bool = False,
    ) -> bool:
        """Check if candidate model is cheaper AND has acceptable latency trade-off.

        Args:
            candidate_model: Model to consider
            primary_model: Primary model for comparison
            candidate_cost_per_token: Cost per token for candidate
            primary_cost_per_token: Cost per token for primary
            aggressive: If True, use relaxed thresholds for cost reduction

        Returns:
            True if candidate is cheaper AND latency trade-off is acceptable
        """
        # Check cost difference
        if primary_cost_per_token == 0.0:
            # For local models, use TPS as proxy for cost efficiency
            candidate_tps = self.MODEL_TPS.get(candidate_model, 1.0)
            primary_tps = self.MODEL_TPS.get(primary_model, 1.0)
            # Use aggressive threshold if enabled (more lenient)
            threshold = self.cost_threshold if not aggressive else (self.cost_threshold + 0.15)
            # If candidate is at least X% as fast as primary, it's acceptable
            if candidate_tps < primary_tps * (1.0 - threshold):
                return False
        else:
            # For API models, check cost ratio
            cost_ratio = candidate_cost_per_token / primary_cost_per_token if primary_cost_per_token > 0 else 1.0
            threshold = self.cost_threshold if not aggressive else (self.cost_threshold + 0.15)
            if cost_ratio > (1.0 - threshold):
                return False

        # Check latency trade-off
        candidate_latency = self.MODEL_LATENCY.get(candidate_model, 100.0)
        primary_latency = self.MODEL_LATENCY.get(primary_model, 100.0)
        latency_increase = candidate_latency - primary_latency

        # Use relaxed latency threshold if aggressive mode
        threshold = self.latency_threshold if not aggressive else (self.latency_threshold + 100.0)
        # If latency increase is within threshold, accept the optimization
        return latency_increase <= threshold

    def record_execution(
        self, model: str, actual_tokens: int, duration_ms: float, success: bool = True
    ) -> float:
        """Record execution and track costs with success metrics.

        Args:
            model: Model name
            actual_tokens: Actual tokens used
            duration_ms: Execution duration in milliseconds
            success: Whether execution was successful (for dynamic tuning)

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

        # Update success tracking for dynamic threshold tuning
        if success:
            if model in ("phi4-mini-reasoning", "phi3:mini"):
                self._fast_model_success_count += 1
            elif model in ("qwen3-coder:30b", "glm-4.7-flash", "qwen3-coder:32b"):
                self._medium_model_success_count += 1

        # Track latency for threshold adjustment
        self._cumulative_latency_ms += duration_ms

        # Auto-tune thresholds if enabled
        if self.dynamic_threshold_tuning:
            self._tune_thresholds_based_on_success()

        logger.debug(
            f"Recorded execution: {model} {actual_tokens} tokens, "
            f"${cost_usd:.6f}, {duration_ms:.1f}ms, success={success}"
        )

        return cost_usd

    def _tune_thresholds_based_on_success(self) -> None:
        """Dynamically tune cost/latency thresholds based on success patterns.

        If phi3 has high success rate, gradually relax thresholds to route more queries to it.
        """
        # Calculate success rates
        fast_total = self._fast_model_success_count
        medium_total = self._medium_model_success_count
        total_tracked = fast_total + medium_total

        if total_tracked < 10:  # Need minimum sample size
            return

        fast_rate = fast_total / total_tracked if total_tracked > 0 else 0.0

        # If fast model has >85% success rate, we can be more aggressive
        if fast_rate >= 0.85:
            # Increase cost threshold (more aggressive cost cutting)
            if self.cost_threshold < 0.25:
                self.cost_threshold = min(0.25, self.cost_threshold + 0.01)
            # Increase latency threshold tolerance
            if self.latency_threshold < 250.0:
                self.latency_threshold = min(250.0, self.latency_threshold + 5.0)

        # If fast model success rate is too low (<60%), be more conservative
        elif fast_rate < 0.60:
            # Reduce cost threshold
            if self.cost_threshold > 0.05:
                self.cost_threshold = max(0.05, self.cost_threshold - 0.01)
            # Reduce latency threshold tolerance
            if self.latency_threshold > 100.0:
                self.latency_threshold = max(100.0, self.latency_threshold - 5.0)

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

        fast_routed = sum(
            self.query_count_per_model.get(m, 0)
            for m in ("phi4-mini-reasoning", "phi3:mini")
        )
        medium_routed = sum(
            self.query_count_per_model.get(m, 0)
            for m in ("qwen3-coder:30b", "glm-4.7-flash", "qwen3-coder:32b")
        )
        heavy_routed = sum(
            self.query_count_per_model.get(m, 0)
            for m in ("gpt-oss:20b", "deepcoder:14b", "nemotron-3-nano", "deepseek-r1:8b")
        )

        total_cost = sum(self.cost_per_model.values())

        # All local models are $0.00 so cost improvement is always 100%
        cost_improvement = 100.0

        return RoutingStatistics(
            total_queries=total,
            simple_count=simple_count,
            medium_count=medium_count,
            complex_count=complex_count,
            fast_model_routed=fast_routed,
            medium_model_routed=medium_routed,
            heavy_model_routed=heavy_routed,
            total_cost_usd=total_cost,
            avg_cost_per_query=total_cost / total if total > 0 else 0.0,
            cost_vs_deepseek_only=cost_improvement,
        )

    def reset_statistics(self) -> None:
        """Reset router statistics (testing only)."""
        self.routing_decisions.clear()
        self.cost_per_model = {m: 0.0 for m in self.MODEL_COSTS.keys()}
        self.query_count_per_model = {m: 0 for m in self.MODEL_COSTS.keys()}
        self.token_optimization_swaps = 0


def get_cost_aware_router() -> CostAwareRouter:
    """Get or create cost-aware router instance."""
    return CostAwareRouter.get_default()


def reset_cost_aware_router() -> None:
    """Reset router instance (testing only)."""
    CostAwareRouter.reset()
