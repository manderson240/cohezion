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

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
from cohezion.cost_optimization.cost_tracker import SessionCostTracker


if __import__("typing").TYPE_CHECKING:
    from cohezion.swarm.model_pool_manager import ModelPoolManager

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

        # Keyword analysis (word-boundary matching to avoid substring matches)
        query_lower = query.lower()
        simple_matches = sum(
            1
            for kw in self.SIMPLE_KEYWORDS
            if f" {kw} " in f" {query_lower} "
            or query_lower.startswith(f"{kw} ")
            or query_lower.endswith(f" {kw}")
        )
        complex_matches = sum(
            1
            for kw in self.COMPLEX_KEYWORDS
            if f" {kw} " in f" {query_lower} "
            or query_lower.startswith(f"{kw} ")
            or query_lower.endswith(f" {kw}")
        )

        # Heuristics
        has_code = any(
            pattern in query for pattern in ["```", "def ", "class ", "import", "function"]
        )
        has_data_processing = any(
            word in query_lower for word in ["process", "analyze", "transform", "pipeline"]
        )
        has_logic = " and " in query_lower or " or " in query_lower or "if " in query_lower
        _is_short = token_count < 30
        is_long = token_count > 200

        # Determine complexity tier
        # SIMPLE: very short (< 10 tokens) without complex keywords, or has simple keywords + no complex keywords + short
        if (token_count < 10 and complex_matches == 0 and not has_code) or (
            simple_matches > 0 and complex_matches == 0 and not has_code and token_count < 50
        ):
            complexity = QueryComplexity.SIMPLE
        # COMPLEX: has multiple complex keywords, code, or is long with logic
        elif (
            (complex_matches >= 2) or (has_code and has_logic) or (is_long and has_data_processing)
        ):
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
        simple_count = sum(
            1 for h in self.history if h["complexity"] == QueryComplexity.SIMPLE.value
        )
        medium_count = sum(
            1 for h in self.history if h["complexity"] == QueryComplexity.MEDIUM.value
        )
        complex_count = sum(
            1 for h in self.history if h["complexity"] == QueryComplexity.COMPLEX.value
        )

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

    # Model costs per 1K tokens (local models = $0.00, cloud = priced)
    MODEL_COSTS = {
        "phi3:mini": 0.0,  # Local, 100x cheaper than deepseek
        "qwen3-coder:32b": 0.0,  # Local
        "deepseek-r1:8b": 0.0,  # Local
        "alibayram/smollm3:latest": 0.0,  # Local, 3B reasoning + 128k context
        "gpt-oss:20b": 0.0,  # Local
        "phi4:latest": 0.0,  # Local
        "gemma3:4b": 0.0,  # Local
        # Gemini cloud fallback tiers (cost per 1K tokens)
        "gemini-2.0-flash-lite": 0.000075,  # $0.075/M = near-free (70% simple)
        "gemini-2.5-flash": 0.0003,  # $0.30/M (20% medium)
        "gemini-2.5-pro": 0.002,  # $2.00/M (10% hard)
    }

    # Expected token counts by complexity (refined estimates)
    EXPECTED_TOKENS = {
        QueryComplexity.SIMPLE: 80,  # Simple queries: ~80 tokens
        QueryComplexity.MEDIUM: 200,  # Medium: ~200 tokens (reduced for better cost ratio)
        QueryComplexity.COMPLEX: 400,  # Complex: ~400 tokens (reduced from 500)
    }

    # Quality scores per model (0.0 - 1.0)
    MODEL_QUALITY = {
        "phi3:mini": 0.6,  # Fast, basic tasks
        "qwen3-coder:32b": 0.85,  # Good balance
        "deepseek-r1:8b": 0.95,  # Best quality
        "alibayram/smollm3:latest": 0.72,  # Dual-mode reasoning, 128k context, tool calling
        "gpt-oss:20b": 0.88,  # Large accurate model
        "phi4:latest": 0.82,  # Strong reasoning
        "gemma3:4b": 0.65,  # Fast baseline
        # Gemini cloud models
        "gemini-2.0-flash-lite": 0.70,  # Cloud, fast, basic
        "gemini-2.5-flash": 0.88,  # Cloud, balanced
        "gemini-2.5-pro": 0.97,  # Cloud, best quality + 2M context
    }

    # TPS (tokens per second) for cost-time tradeoff
    MODEL_TPS = {
        "phi3:mini": 15.0,  # Fastest
        "qwen3-coder:32b": 8.0,  # Moderate
        "deepseek-r1:8b": 2.0,  # Slowest but best
        "alibayram/smollm3:latest": 14.0,  # Similar speed to phi3:mini
        "gpt-oss:20b": 5.0,  # Large model, slower
        "phi4:latest": 10.0,  # Medium speed
        "gemma3:4b": 14.0,  # Fast, small model
        # Gemini cloud models (TPS varies with load, API latency)
        "gemini-2.0-flash-lite": 50.0,  # Cloud, very fast
        "gemini-2.5-flash": 40.0,  # Cloud, fast
        "gemini-2.5-pro": 20.0,  # Cloud, moderate
    }

    # Expected latency (ms) by model
    MODEL_LATENCY = {
        "phi3:mini": 50.0,  # Fastest: ~50ms
        "qwen3-coder:32b": 100.0,  # Moderate: ~100ms
        "deepseek-r1:8b": 300.0,  # Slower: ~300ms
        "alibayram/smollm3:latest": 55.0,  # Similar to phi3:mini
        "gpt-oss:20b": 200.0,  # Larger model, higher latency
        "phi4:latest": 80.0,  # Medium latency
        "gemma3:4b": 55.0,  # Fast, similar to phi3
    }

    _instance: Optional["CostAwareRouter"] = None

    def __init__(
        self,
        cost_tracker: SessionCostTracker | None = None,
        budget_enforcer: BudgetEnforcer | None = None,
        prefer_longer_models_if_cheaper_per_token: bool = True,
        cost_threshold: float = 0.10,  # 10% cost threshold
        latency_threshold: float = 150.0,  # 150ms latency threshold (increased tolerance)
        aggressive_cost_reduction: bool = True,  # Enable aggressive phi3 routing
        dynamic_threshold_tuning: bool = True,  # Enable auto-tuning based on patterns
        pool_manager: "ModelPoolManager | None" = None,
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
            pool_manager: Optional ModelPoolManager for availability-aware routing
        """
        self.cost_tracker = cost_tracker or SessionCostTracker.get_current()
        self.budget_enforcer = budget_enforcer or BudgetEnforcer.get_current()
        self._pool_manager = pool_manager
        self.complexity_analyzer = QueryComplexityAnalyzer()

        # Token optimization parameters
        self.prefer_longer_models_if_cheaper_per_token = prefer_longer_models_if_cheaper_per_token
        self.cost_threshold = cost_threshold
        self.latency_threshold = latency_threshold
        self.aggressive_cost_reduction = aggressive_cost_reduction
        self.dynamic_threshold_tuning = dynamic_threshold_tuning

        # Statistics tracking
        self.routing_decisions: list[ModelRoutingDecision] = []
        self.cost_per_model: dict[str, float] = dict.fromkeys(self.MODEL_COSTS.keys(), 0.0)
        self.query_count_per_model: dict[str, int] = dict.fromkeys(self.MODEL_COSTS.keys(), 0)
        self.token_optimization_swaps: int = 0  # Track optimization improvements

        # Dynamic threshold tracking
        self._phi3_success_count = 0  # Track successful phi3 completions
        self._qwen_success_count = 0  # Track successful qwen completions
        self._cumulative_latency_ms = 0.0  # Track cumulative latency for tuning

        # R-Zero optimization integration (non-blocking)
        self._r_zero_optimizer: Any = None
        self._r_zero_loaded = False

        # Degradation feedback (wired via callback from DegradationDetector)
        self._degradation_cooldown: int = 0
        self._degradation_upgrade_model: str | None = None

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
        self,
        query: str,
        max_cost_usd: float | None = None,
        cache_hit_rate: float | None = None,
    ) -> tuple[ModelRoutingDecision, bool]:
        """Select optimal model for query with cost/token optimization.

        Args:
            query: User query
            max_cost_usd: Maximum allowed cost (optional)
            cache_hit_rate: Current cache hit rate from DegradationDetector (0.0-1.0).
                When >0.9, bias toward cheaper/faster models (cache handles quality).
                When <0.5, bias toward larger-context models (more cache-friendly).

        Returns:
            Tuple of (decision, can_proceed)
            - decision: ModelRoutingDecision with selected model
            - can_proceed: False if budget enforcer blocks (decision still returned)
        """
        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(query)
        estimated_tokens = self.EXPECTED_TOKENS[complexity]

        # Cache-aware complexity adjustment
        if cache_hit_rate is not None:
            if cache_hit_rate > 0.9 and complexity != QueryComplexity.SIMPLE:
                # High cache hits → cache is handling quality, downgrade to cheaper model
                logger.info(
                    "Cache feedback: %.0f%% hit rate → downgrading %s to SIMPLE routing",
                    cache_hit_rate * 100,
                    complexity.value,
                )
                complexity = QueryComplexity.SIMPLE
            elif cache_hit_rate < 0.3 and complexity == QueryComplexity.SIMPLE:
                # Very low cache hits → need better model for cache-miss handling
                logger.info(
                    "Cache feedback: %.0f%% hit rate → upgrading SIMPLE to MEDIUM routing",
                    cache_hit_rate * 100,
                )
                complexity = QueryComplexity.MEDIUM

        # Select model by complexity
        if complexity == QueryComplexity.SIMPLE:
            primary_model = "phi3:mini"
        elif complexity == QueryComplexity.MEDIUM:
            primary_model = "qwen3-coder:32b"
        else:
            primary_model = "deepseek-r1:8b"

        # Optimize model selection based on cost/token ratio if enabled
        model = self._optimize_model_selection(primary_model, complexity, estimated_tokens)

        # Check pool availability (if pool_manager is configured)
        if self._pool_manager is not None:
            available = {m.name for m in self._pool_manager.get_available_models()}
            if not available:
                logger.warning(
                    "No healthy models in pool, proceeding with best-effort routing to %s",
                    model,
                )
            elif model not in available:
                fallback = self._find_available_fallback(model, available)
                if fallback:
                    logger.info(
                        "Pool manager: %s unavailable, falling back to %s",
                        model,
                        fallback,
                    )
                    model = fallback

        # Context-window guard: prevent overflow by escalating to larger-context model
        model = self._check_context_window(model, estimated_tokens)

        # R-Zero adjustment: escalate if local models underperforming
        model = self._apply_r_zero_adjustment(model)

        # Degradation override: force upgraded model if in cooldown period
        if self._degradation_cooldown > 0 and self._degradation_upgrade_model:
            logger.info(
                "Degradation override: forcing %s (cooldown=%d remaining)",
                self._degradation_upgrade_model,
                self._degradation_cooldown,
            )
            model = self._degradation_upgrade_model

        # Calculate estimated cost
        cost_per_1k = self.MODEL_COSTS.get(model, 0.0)
        estimated_cost = (estimated_tokens / 1000.0) * cost_per_1k

        # Check budget constraint
        can_proceed = True
        if max_cost_usd and estimated_cost > max_cost_usd:
            can_proceed = False

        # Check budget enforcer (if available)
        if self.budget_enforcer and self.cost_tracker:
            enforcer_ok, _enforcer_msg = self.budget_enforcer.check_budget(
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
            quality_score=self.MODEL_QUALITY.get(model, 0.5),
        )

        # Record decision
        self.routing_decisions.append(decision)
        self.query_count_per_model.setdefault(model, 0)
        self.query_count_per_model[model] += 1

        logger.info(
            f"Cost router: {complexity.value} query → {model} "
            f"(est. {estimated_tokens} tokens, ${estimated_cost:.6f})"
        )

        return decision, can_proceed

    # Context window limits per model (tokens). Local models from Ollama metadata,
    # cloud models from provider specs. Used by _check_context_window().
    MODEL_CONTEXT_LIMITS = {
        "phi3:mini": 4_096,
        "qwen3-coder:32b": 32_768,
        "deepseek-r1:8b": 64_000,
        "alibayram/smollm3:latest": 128_000,
        "gpt-oss:20b": 32_768,
        "phi4:latest": 16_384,
        "gemma3:4b": 8_192,
        "gemini-2.0-flash-lite": 1_000_000,
        "gemini-2.5-flash": 1_000_000,
        "gemini-2.5-pro": 2_000_000,
    }

    # Escalation chain: when context is too large for current model, try these in order
    CONTEXT_ESCALATION = [
        "qwen3-coder:32b",  # 32K
        "deepseek-r1:8b",  # 64K
        "alibayram/smollm3:latest",  # 128K
        "gemini-2.0-flash-lite",  # 1M (cloud, near-free)
        "gemini-2.5-flash",  # 1M (cloud)
    ]

    def _check_context_window(self, model: str, estimated_tokens: int) -> str:
        """Guard against context overflow by escalating to larger-context model.

        If estimated tokens exceed 80% of the model's context window, escalate
        to the next model in the chain that can fit the request.

        Args:
            model: Currently selected model
            estimated_tokens: Estimated token count for this request

        Returns:
            Same model if it fits, or escalated model if context would overflow
        """
        limit = self.MODEL_CONTEXT_LIMITS.get(model, 32_768)
        threshold = int(limit * 0.8)

        if estimated_tokens <= threshold:
            return model  # Fits fine

        # Need a bigger model
        for candidate in self.CONTEXT_ESCALATION:
            candidate_limit = self.MODEL_CONTEXT_LIMITS.get(candidate, 32_768)
            if estimated_tokens <= int(candidate_limit * 0.8):
                logger.info(
                    "Context guard: %s (%d tokens > %d limit×0.8) → escalating to %s (%d limit)",
                    model,
                    estimated_tokens,
                    limit,
                    candidate,
                    candidate_limit,
                )
                return candidate

        # Nothing fits — return original and let it fail gracefully
        logger.warning(
            "Context guard: %d tokens exceeds all model limits, proceeding with %s",
            estimated_tokens,
            model,
        )
        return model

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
            # Check if medium model (qwen) has acceptable cost/token ratio
            primary_cost_per_token = self._get_cost_per_token(primary_model, estimated_tokens)
            qwen_cost_per_token = self._get_cost_per_token("qwen3-coder:32b", estimated_tokens)

            # If qwen is cheaper per token AND latency is acceptable, use it
            if self._is_cheaper_with_acceptable_latency(
                "qwen3-coder:32b", primary_model, qwen_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return "qwen3-coder:32b"

            # If aggressive cost reduction enabled, also check phi3 for complex queries
            if self.aggressive_cost_reduction:
                phi3_cost_per_token = self._get_cost_per_token("phi3:mini", estimated_tokens)
                # Check if phi3 can handle complex queries with acceptable latency/quality tradeoff
                if self._is_cheaper_with_acceptable_latency(
                    "phi3:mini",
                    primary_model,
                    phi3_cost_per_token,
                    primary_cost_per_token,
                    aggressive=True,
                ):
                    self.token_optimization_swaps += 1
                    return "phi3:mini"

        # For medium queries, check if simple model (phi3) is good enough
        if complexity == QueryComplexity.MEDIUM:
            primary_cost_per_token = self._get_cost_per_token(primary_model, estimated_tokens)
            phi3_cost_per_token = self._get_cost_per_token("phi3:mini", estimated_tokens)

            # Standard check
            if self._is_cheaper_with_acceptable_latency(
                "phi3:mini", primary_model, phi3_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return "phi3:mini"

            # If aggressive cost reduction, be more lenient with phi3 for medium queries
            if self.aggressive_cost_reduction:
                latency_diff = self.MODEL_LATENCY.get("phi3:mini", 50.0) - self.MODEL_LATENCY.get(
                    primary_model, 100.0
                )
                # Allow phi3 even if latency is slightly higher (up to 200ms for 50% cost savings)
                if latency_diff <= 200.0:
                    self.token_optimization_swaps += 1
                    return "phi3:mini"

        # For simple queries, strongly prefer phi3 for cost savings
        if complexity == QueryComplexity.SIMPLE:
            # Always prefer phi3 for simple queries unless latency is critical
            if primary_model != "phi3:mini":
                latency_diff = self.MODEL_LATENCY.get("phi3:mini", 50.0) - self.MODEL_LATENCY.get(
                    primary_model, 50.0
                )
                if latency_diff <= 150.0:  # phi3 is still acceptable for simple queries
                    self.token_optimization_swaps += 1
                    return "phi3:mini"

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
            cost_ratio = (
                candidate_cost_per_token / primary_cost_per_token
                if primary_cost_per_token > 0
                else 1.0
            )
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

    def _find_available_fallback(self, preferred: str, available: set[str]) -> str | None:
        """Find the best available model as a fallback.

        Selects from available models in order of quality score (highest first).
        Falls back to any available model if none are in MODEL_QUALITY.
        """
        # Score available models by quality
        scored = []
        for name in available:
            quality = self.MODEL_QUALITY.get(name, 0.5)
            scored.append((quality, name))
        scored.sort(reverse=True)
        return scored[0][1] if scored else None

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
            if model == "phi3:mini":
                self._phi3_success_count += 1
            elif model == "qwen3-coder:32b":
                self._qwen_success_count += 1

        # Track latency for threshold adjustment
        self._cumulative_latency_ms += duration_ms

        # Auto-tune thresholds if enabled
        if self.dynamic_threshold_tuning:
            self._tune_thresholds_based_on_success()

        # Feed R-Zero optimizer (non-blocking)
        try:
            r_zero = self._get_r_zero()
            if r_zero is not None:
                r_zero.record_execution(model, success, 1)
        except Exception:
            pass

        # Decrement degradation cooldown
        if self._degradation_cooldown > 0:
            self._degradation_cooldown -= 1
            if self._degradation_cooldown == 0:
                self._degradation_upgrade_model = None
                logger.info("Degradation routing cooldown expired, resuming normal routing")

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
        phi3_total = self._phi3_success_count
        qwen_total = self._qwen_success_count
        total_tracked = phi3_total + qwen_total

        if total_tracked < 10:  # Need minimum sample size
            return

        phi3_rate = phi3_total / total_tracked if total_tracked > 0 else 0.0

        # If phi3 has >85% success rate, we can be more aggressive
        if phi3_rate >= 0.85:
            # Increase cost threshold (more aggressive cost cutting)
            if self.cost_threshold < 0.25:
                self.cost_threshold = min(0.25, self.cost_threshold + 0.01)
            # Increase latency threshold tolerance
            if self.latency_threshold < 250.0:
                self.latency_threshold = min(250.0, self.latency_threshold + 5.0)

        # If phi3 success rate is too low (<60%), be more conservative
        elif phi3_rate < 0.60:
            # Reduce cost threshold
            if self.cost_threshold > 0.05:
                self.cost_threshold = max(0.05, self.cost_threshold - 0.01)
            # Reduce latency threshold tolerance
            if self.latency_threshold > 100.0:
                self.latency_threshold = max(100.0, self.latency_threshold - 5.0)

    def _get_r_zero(self) -> Any:
        """Lazy-load R-Zero LocalModelOptimizer (non-blocking)."""
        if not self._r_zero_loaded:
            self._r_zero_loaded = True
            try:
                from cohezion.optimization.r_zero import LocalModelOptimizer

                self._r_zero_optimizer = LocalModelOptimizer()
            except ImportError:
                pass
        return self._r_zero_optimizer

    def _apply_r_zero_adjustment(self, model: str) -> str:
        """Adjust model selection based on R-Zero success rate history.

        When local model success rate drops below 80%, R-Zero returns 0.8
        multiplier, indicating we should escalate to a higher-quality model.
        """
        try:
            r_zero = self._get_r_zero()
            if r_zero is None:
                return model

            multiplier = r_zero.get_current_multiplier()
            if multiplier < 1.0 and model in ("phi3:mini", "qwen3-coder:32b"):
                # Local models underperforming — escalate one tier
                if model == "phi3:mini":
                    logger.info(
                        "R-Zero: phi3 underperforming (mult=%.1f), upgrading to qwen3", multiplier
                    )
                    return "qwen3-coder:32b"
                if model == "qwen3-coder:32b":
                    logger.info(
                        "R-Zero: qwen3 underperforming (mult=%.1f), upgrading to deepseek",
                        multiplier,
                    )
                    return "deepseek-r1:8b"
        except Exception:
            pass
        return model

    def apply_degradation_feedback(self, alerts: list) -> None:
        """Receive degradation alerts and adjust routing for next N queries.

        Called by DegradationDetector via callback. CRITICAL alerts force
        higher-tier model routing for the next 5 queries.

        Args:
            alerts: List of DegradationAlert objects
        """
        try:
            for alert in alerts:
                severity = getattr(alert, "severity", None)
                metric = getattr(alert, "metric", "")
                severity_value = getattr(severity, "value", "") if severity else ""

                if severity_value == "CRITICAL":
                    if metric in ("success_rate", "coherence"):
                        self._degradation_cooldown = 5
                        self._degradation_upgrade_model = "deepseek-r1:8b"
                        logger.warning(
                            "Degradation feedback: CRITICAL %s → forcing %s for next 5 queries",
                            metric,
                            self._degradation_upgrade_model,
                        )
                    elif metric == "token_efficiency":
                        self._degradation_cooldown = 3
                        self._degradation_upgrade_model = "qwen3-coder:32b"
                        logger.warning(
                            "Degradation feedback: CRITICAL %s → upgrading to %s for next 3 queries",
                            metric,
                            self._degradation_upgrade_model,
                        )
        except Exception:
            logger.debug("Degradation feedback processing failed (non-blocking)", exc_info=True)

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
        deepseek_only_cost = (
            sum(d.estimated_tokens for d in self.routing_decisions)
            / 1000.0
            * self.MODEL_COSTS["deepseek-r1:8b"]
        )

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
        self.cost_per_model = dict.fromkeys(self.MODEL_COSTS.keys(), 0.0)
        self.query_count_per_model = dict.fromkeys(self.MODEL_COSTS.keys(), 0)
        self.token_optimization_swaps = 0


def get_cost_aware_router() -> CostAwareRouter:
    """Get or create cost-aware router instance."""
    return CostAwareRouter.get_default()


def reset_cost_aware_router() -> None:
    """Reset router instance (testing only)."""
    CostAwareRouter.reset()
