# ruff: noqa: SIM102, E501, RUF012, S110, RUF001  # math/physics symbols intentional
"""Cost-aware smart routing across local models with budget enforcement.

Features:
- Query complexity analysis (simple/medium/complex)
- Cost-optimized model routing (Lemonade: Phi-4-mini → Qwen3-8B → Qwen3-14B)
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
import threading
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
    """Decision output from router.

    OI-MAS confidence scoring (arXiv:2601.04861): the confidence field
    represents how well the selected model matches the task requirements.
    Low confidence (<0.7) triggers automatic escalation to a higher-tier model.
    """

    model: str
    complexity: QueryComplexity
    estimated_tokens: int
    estimated_cost_usd: float
    reason: str
    quality_score: float  # 0.0-1.0
    confidence: float = 1.0  # OI-MAS: joint role+scale confidence (0.0-1.0)


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

    def detect_domain(self, query: str) -> str:
        """Detect the domain of a query for routing specialization.

        Args:
            query: User query string

        Returns:
            Domain string: 'coding', 'analysis', 'creative', 'general'
        """
        query_lower = query.lower()
        if any(
            kw in query_lower
            for kw in ["code", "function", "class", "debug", "implement", "refactor"]
        ):
            return "coding"
        if any(kw in query_lower for kw in ["analyze", "data", "metrics", "evaluate", "benchmark"]):
            return "analysis"
        if any(kw in query_lower for kw in ["design", "create", "imagine", "brainstorm", "story"]):
            return "creative"
        return "general"

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

    # ── Model profiles loaded from config/model_profiles.yaml ──────────
    # Replaces hardcoded dicts (Session 96b: Lemonade-first + Ollama Pro Cloud)
    # Fallback defaults retained for resilience if YAML is unavailable.

    _profiles_loaded: bool = False
    _profiles_lock: threading.Lock = threading.Lock()
    _profiles_cache: dict | None = None

    # Fallback defaults (used ONLY if config/model_profiles.yaml is unreadable)
    _FALLBACK_COSTS: dict[str, float] = {
        "Phi-4-mini-instruct-Hybrid": 0.0,
        "Qwen3-8B-Hybrid": 0.0,
        "Qwen3-14B-Hybrid": 0.0,
        "DeepSeek-R1-Distill-Llama-8B-Hybrid": 0.0,
        "Qwen2.5-Coder-7B-Instruct-Hybrid": 0.0,
        "Qwen3-Coder-Next-GGUF": 0.0,
        "Qwen3.5-122B-A10B-GGUF": 0.0,
        "gpt-oss-120b-mxfp-GGUF": 0.0,
        "Gemma-4-31B-it-GGUF": 0.0,
    }

    @classmethod
    def _load_profiles(cls) -> dict:
        """Load model profiles from config/model_profiles.yaml.

        Returns merged dict of all model profiles across all tiers.
        Cached after first load (5-min TTL managed externally).
        """
        if cls._profiles_cache is not None:
            return cls._profiles_cache

        from pathlib import Path

        import yaml

        # __file__ = src/cohezion/swarm/cost_aware_router.py
        # parents[3] = repo root (src/ → cohezion/ → swarm/ → file)
        config_path = Path(__file__).parents[3] / "config" / "model_profiles.yaml"
        if not config_path.exists():
            # Fallback: CWD-relative (works when started from repo root)
            config_path = Path("config/model_profiles.yaml")

        profiles: dict = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    content = f.read()
                # Handle multi-document YAML (e.g., frontmatter + body)
                docs = list(yaml.safe_load_all(content))
                raw = docs[-1] if docs else {}  # Last doc has the profiles
                # Merge all tier sections into flat model dict
                for section_key in (
                    "lemonade_hybrid",
                    "lemonade_cpu",
                    "lemonade_gpu",
                    "lemonade_embeddings",
                    "lemonade_multimodal",
                    "ollama_cloud",
                ):
                    section = raw.get(section_key, {})
                    if isinstance(section, dict):
                        for model_name, model_data in section.items():
                            if isinstance(model_data, dict):
                                profiles[model_name] = model_data
                cls._profiles_cache = profiles
                logger.info(f"Loaded {len(profiles)} model profiles from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load model profiles: {e}")
                cls._profiles_cache = {}  # Memoize failure to prevent repeated I/O
        else:
            logger.warning("config/model_profiles.yaml not found, using fallback defaults")
            cls._profiles_cache = {}

        return profiles

    @classmethod
    def _get_model_attr(cls, attr: str, default_factory: dict | None = None) -> dict:
        """Get a model attribute dict (cost, quality, tps, latency, context) from profiles."""
        profiles = cls._load_profiles()
        result = {}
        for name, data in profiles.items():
            if isinstance(data, dict) and attr in data:
                result[name] = data[attr]
        # Merge with fallback if profiles are empty
        if not result and default_factory:
            return dict(default_factory)
        return result

    # Legacy + Lemonade model entries for routing algorithm compatibility.
    # The router's select_model() compares against these dicts.
    # Primary tier models are Lemonade (Session 96b migration).
    _LEGACY_COSTS: dict[str, float] = {
        # Lemonade tier models ($0 — local inference)
        "Phi-4-mini-instruct-Hybrid": 0.0,
        "Qwen3-8B-Hybrid": 0.0,
        "Qwen3-14B-Hybrid": 0.0,
        # Legacy Ollama names (kept for backward compat)
        "phi3:mini": 0.0,
        "qwen3-coder:32b": 0.0,
        "deepseek-r1:8b": 0.0,
    }
    _LEGACY_QUALITY: dict[str, float] = {
        "Phi-4-mini-instruct-Hybrid": 0.82,
        "Qwen3-8B-Hybrid": 0.85,
        "Qwen3-14B-Hybrid": 0.90,
        "phi3:mini": 0.6,
        "qwen3-coder:32b": 0.85,
        "deepseek-r1:8b": 0.95,
    }
    _LEGACY_TPS: dict[str, float] = {
        "Phi-4-mini-instruct-Hybrid": 20.0,
        "Qwen3-8B-Hybrid": 18.0,
        "Qwen3-14B-Hybrid": 12.0,
        "phi3:mini": 15.0,
        "qwen3-coder:32b": 8.0,
        "deepseek-r1:8b": 2.0,
    }
    _LEGACY_LATENCY: dict[str, float] = {
        "Phi-4-mini-instruct-Hybrid": 50.0,
        "Qwen3-8B-Hybrid": 60.0,
        "Qwen3-14B-Hybrid": 80.0,
        "phi3:mini": 50.0,
        "qwen3-coder:32b": 100.0,
        "deepseek-r1:8b": 300.0,
    }

    @classmethod
    def _ensure_profiles_loaded(cls) -> None:
        """Lazy-load profiles into class-level dicts on first access.

        Merges YAML-loaded Lemonade/Cloud profiles WITH legacy model names.
        Primary tier models are now Lemonade (Phi-4-mini, Qwen3-8B, Qwen3-14B).
        Legacy Ollama names kept for backward compat with existing code paths.
        """
        if cls._profiles_loaded:
            return
        with cls._profiles_lock:
            if cls._profiles_loaded:
                return
            profiles = cls._load_profiles()

            # Start with legacy models (routing logic depends on these)
            cls.MODEL_COSTS = dict(cls._LEGACY_COSTS)
            cls.MODEL_QUALITY = dict(cls._LEGACY_QUALITY)
            cls.MODEL_TPS = dict(cls._LEGACY_TPS)
            cls.MODEL_LATENCY = dict(cls._LEGACY_LATENCY)

            # Overlay YAML-loaded profiles (Lemonade + Ollama Cloud)
            if profiles:
                for name, data in profiles.items():
                    if not isinstance(data, dict):
                        continue
                    if "cost_per_1k" in data:
                        cls.MODEL_COSTS[name] = data["cost_per_1k"]
                    elif "cost" in data:
                        cls.MODEL_COSTS[name] = data["cost"]
                    if "quality" in data:
                        cls.MODEL_QUALITY[name] = data["quality"]
                    if "tps" in data:
                        cls.MODEL_TPS[name] = data["tps"]
                    if "latency_ms" in data:
                        cls.MODEL_LATENCY[name] = data["latency_ms"]

            # Load tier routing config (maps complexity → model name)
            tier_cfg = {}
            # tier_routing may be in the raw YAML (top-level, not in a model section)
            if not tier_cfg:
                # Re-read raw YAML for tier_routing (it's top-level, not in profiles)
                from pathlib import Path

                import yaml

                config_path = Path(__file__).parents[3] / "config" / "model_profiles.yaml"
                if not config_path.exists():
                    config_path = Path("config/model_profiles.yaml")
                if config_path.exists():
                    try:
                        with open(config_path) as f:
                            content = f.read()
                        docs = list(yaml.safe_load_all(content))
                        full_raw = docs[-1] if docs else {}
                        tier_cfg = full_raw.get("tier_routing", {})
                    except Exception:
                        pass

            cls.TIER_SIMPLE = tier_cfg.get("tier_simple", "Phi-4-mini-instruct-Hybrid")
            cls.TIER_MEDIUM = tier_cfg.get("tier_medium", "Qwen3-8B-Hybrid")
            cls.TIER_COMPLEX = tier_cfg.get("tier_complex", "Qwen3-14B-Hybrid")

            cls._profiles_loaded = True

    # Tier routing — which model handles which complexity level
    TIER_SIMPLE: str = "Phi-4-mini-instruct-Hybrid"
    TIER_MEDIUM: str = "Qwen3-8B-Hybrid"
    TIER_COMPLEX: str = "Qwen3-14B-Hybrid"

    # Class-level dicts — populated lazily from legacy + YAML profiles
    MODEL_COSTS: dict[str, float] = {}
    MODEL_QUALITY: dict[str, float] = {}
    MODEL_TPS: dict[str, float] = {}
    MODEL_LATENCY: dict[str, float] = {}

    # Expected token counts by complexity (not model-specific)
    EXPECTED_TOKENS = {
        QueryComplexity.SIMPLE: 80,
        QueryComplexity.MEDIUM: 200,
        QueryComplexity.COMPLEX: 400,
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
        # Load model profiles from YAML on first instantiation
        self._ensure_profiles_loaded()

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

        # ── Improvement 1: Rolling EMA quality + hysteresis ──────────────
        # Source: arXiv:2605.00410 "Agent Capsules" — Quality-Gated Granularity Control
        # EMA of quality per tier prevents threshold oscillation from transient dips.
        # Hysteresis band requires N consecutive below-threshold readings before reducing.
        self._EMA_ALPHA: float = 0.1
        self._ESCALATE_THRESHOLD: float = 0.6  # below this: increment consecutive counter
        self._DE_ESCALATE_THRESHOLD: float = 0.75  # above this: reset + allow threshold increase
        self._HYSTERESIS_CONSEC_REQUIRED: int = 3
        self._ema_quality: dict[str, float] = {
            self.TIER_SIMPLE: 0.7,
            self.TIER_MEDIUM: 0.7,
            self.TIER_COMPLEX: 0.7,
        }
        self._consec_below_escalate: dict[str, int] = {
            self.TIER_SIMPLE: 0,
            self.TIER_MEDIUM: 0,
            self.TIER_COMPLEX: 0,
        }

        # ── Improvement 2: Contextual bandit model selection ──────────────
        # Source: arXiv:2605.14241 "Latency-Quality Routing for Functionally Equivalent Tools"
        # Routes to argmax(q[node] - λ*lat[node]) after sufficient warm-up.
        self._BANDIT_WARMUP: int = 10
        self._BANDIT_LAMBDA: float = 0.001  # quality cost per ms of latency
        self._BANDIT_ALPHA: float = 0.1
        self._bandit_quality_ema: dict[str, float] = {
            m: self.MODEL_QUALITY.get(m, 0.5)
            for m in [self.TIER_SIMPLE, self.TIER_MEDIUM, self.TIER_COMPLEX]
        }
        self._bandit_latency_ema: dict[str, float] = {
            m: self.MODEL_LATENCY.get(m, 100.0)
            for m in [self.TIER_SIMPLE, self.TIER_MEDIUM, self.TIER_COMPLEX]
        }
        self._bandit_exec_count: int = 0

    @classmethod
    def get_default(cls) -> "CostAwareRouter":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton and profiles cache (testing only)."""
        cls._instance = None
        cls._profiles_cache = None
        cls._profiles_loaded = False

    @classmethod
    def reset_singleton(cls) -> None:
        """Alias for reset() — matches conftest reset_singletons() pattern."""
        cls.reset()

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

        # Select model by complexity (reads from YAML tier_routing config)
        if complexity == QueryComplexity.SIMPLE:
            primary_model = self.TIER_SIMPLE
        elif complexity == QueryComplexity.MEDIUM:
            primary_model = self.TIER_MEDIUM
        else:
            primary_model = self.TIER_COMPLEX

        # Optimize model selection based on cost/token ratio if enabled
        model = self._optimize_model_selection(primary_model, complexity, estimated_tokens)

        # Bandit override: after warm-up, use empirical quality-latency tradeoff
        # (Improvement 2 — arXiv:2605.14241)
        bandit_model = self._bandit_select(model, complexity)
        if bandit_model != model:
            logger.info(
                "Bandit override: %s → %s (empirical q-lat score improved)",
                model,
                bandit_model,
            )
            model = bandit_model
            self.token_optimization_swaps += 1

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

        # Compute OI-MAS confidence (joint role+scale scoring)
        confidence = self._compute_routing_confidence(model, complexity)

        # Build decision
        reason = f"Routed {complexity.value} query to {model}"
        if model != primary_model:
            reason += f" (optimized from {primary_model})"
        if confidence < 0.7:
            reason += f" (low confidence: {confidence:.2f})"

        decision = ModelRoutingDecision(
            model=model,
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            reason=reason,
            quality_score=self.MODEL_QUALITY.get(model, 0.5),
            confidence=confidence,
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

    @property
    def MODEL_CONTEXT_LIMITS(self) -> dict[str, int]:
        """Context window limits loaded from model_profiles.yaml."""
        profiles = self._load_profiles()
        result = {}
        for name, data in profiles.items():
            if isinstance(data, dict) and "context" in data:
                result[name] = int(data["context"])
        if not result:
            # Fallback defaults
            return {
                "Phi-4-mini-instruct-Hybrid": 4_096,
                "Qwen3-8B-Hybrid": 32_768,
                "Qwen3-14B-Hybrid": 32_768,
                "Qwen3-Coder-Next-GGUF": 131_072,
                "Qwen3.5-122B-A10B-GGUF": 131_072,
            }
        return result

    # Escalation chain: when context is too large, try these in order
    # Lemonade local first, then Ollama Cloud for massive context
    CONTEXT_ESCALATION = [
        "Qwen3-8B-Hybrid",  # 32K (local, fast)
        "Qwen3-14B-Hybrid",  # 32K (local, quality)
        "Qwen3-Coder-Next-GGUF",  # 131K (local GPU, large)
        "Qwen3.5-122B-A10B-GGUF",  # 131K (local GPU, frontier)
        "qwen3.5:cloud",  # 131K+ (Ollama Pro cloud)
        "kimi-k2.5:cloud",  # Long-context specialist (cloud)
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
            medium_cost_per_token = self._get_cost_per_token(self.TIER_MEDIUM, estimated_tokens)

            # If medium tier is cheaper per token AND latency is acceptable, use it
            if self._is_cheaper_with_acceptable_latency(
                self.TIER_MEDIUM, primary_model, medium_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return self.TIER_MEDIUM

            # If aggressive cost reduction enabled, also check phi3 for complex queries
            if self.aggressive_cost_reduction:
                phi3_cost_per_token = self._get_cost_per_token(self.TIER_SIMPLE, estimated_tokens)
                # Check if phi3 can handle complex queries with acceptable latency/quality tradeoff
                if self._is_cheaper_with_acceptable_latency(
                    self.TIER_SIMPLE,
                    primary_model,
                    phi3_cost_per_token,
                    primary_cost_per_token,
                    aggressive=True,
                ):
                    self.token_optimization_swaps += 1
                    return self.TIER_SIMPLE

        # For medium queries, check if simple model (phi3) is good enough
        if complexity == QueryComplexity.MEDIUM:
            primary_cost_per_token = self._get_cost_per_token(primary_model, estimated_tokens)
            phi3_cost_per_token = self._get_cost_per_token(self.TIER_SIMPLE, estimated_tokens)

            # Standard check
            if self._is_cheaper_with_acceptable_latency(
                self.TIER_SIMPLE, primary_model, phi3_cost_per_token, primary_cost_per_token
            ):
                self.token_optimization_swaps += 1
                return self.TIER_SIMPLE

            # If aggressive cost reduction, be more lenient with phi3 for medium queries
            if self.aggressive_cost_reduction:
                latency_diff = self.MODEL_LATENCY.get(
                    self.TIER_SIMPLE, 50.0
                ) - self.MODEL_LATENCY.get(primary_model, 100.0)
                # Allow phi3 even if latency is slightly higher (up to 200ms for 50% cost savings)
                if latency_diff <= 200.0:
                    self.token_optimization_swaps += 1
                    return self.TIER_SIMPLE

        # For simple queries, strongly prefer phi3 for cost savings
        if complexity == QueryComplexity.SIMPLE:
            # Always prefer phi3 for simple queries unless latency is critical
            if primary_model != self.TIER_SIMPLE:
                latency_diff = self.MODEL_LATENCY.get(
                    self.TIER_SIMPLE, 50.0
                ) - self.MODEL_LATENCY.get(primary_model, 50.0)
                if latency_diff <= 150.0:  # phi3 is still acceptable for simple queries
                    self.token_optimization_swaps += 1
                    return self.TIER_SIMPLE

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
            if model == self.TIER_SIMPLE:
                self._phi3_success_count += 1
            elif model == self.TIER_MEDIUM:
                self._qwen_success_count += 1

        # Track latency for threshold adjustment
        self._cumulative_latency_ms += duration_ms

        # ── Improvement 1: Rolling EMA quality update (arXiv:2605.00410) ────
        quality_signal = 1.0 if success else 0.0
        self._ema_quality[model] = (1.0 - self._EMA_ALPHA) * self._ema_quality.get(
            model, 0.7
        ) + self._EMA_ALPHA * quality_signal

        # ── Improvement 2: Bandit EMA update (arXiv:2605.14241) ──────────────
        self._bandit_quality_ema[model] = (1.0 - self._BANDIT_ALPHA) * self._bandit_quality_ema.get(
            model, 0.5
        ) + self._BANDIT_ALPHA * quality_signal
        self._bandit_latency_ema[model] = (1.0 - self._BANDIT_ALPHA) * self._bandit_latency_ema.get(
            model, 100.0
        ) + self._BANDIT_ALPHA * duration_ms
        self._bandit_exec_count += 1

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

        Improvement 1 addition (arXiv:2605.00410): Rolling EMA hysteresis guard.
        Prevents threshold oscillation by requiring N consecutive below-threshold
        EMA readings before reducing cost_threshold.
        """
        # ── Rolling EMA hysteresis (Improvement 1 — arXiv:2605.00410) ───────
        # Runs INDEPENDENTLY of the sample-size check below (catches quality issues early)
        tier_ema = self._ema_quality.get(self.TIER_SIMPLE, 0.7)
        if tier_ema < self._ESCALATE_THRESHOLD:
            # EMA is below threshold — increment consecutive counter
            self._consec_below_escalate[self.TIER_SIMPLE] = (
                self._consec_below_escalate.get(self.TIER_SIMPLE, 0) + 1
            )
        else:
            # EMA has recovered — reset consecutive counter
            self._consec_below_escalate[self.TIER_SIMPLE] = 0
            if tier_ema > self._DE_ESCALATE_THRESHOLD:
                # Quality is high — gently increase cost threshold
                if self.cost_threshold < 0.25:
                    self.cost_threshold = min(0.25, self.cost_threshold + 0.005)

        # Hysteresis-gated threshold reduction: only trigger after N consecutive readings
        if self._consec_below_escalate.get(self.TIER_SIMPLE, 0) >= self._HYSTERESIS_CONSEC_REQUIRED:
            if self.cost_threshold > 0.05:
                self.cost_threshold = max(0.05, self.cost_threshold - 0.02)

        # ── Existing: cumulative success-rate tuning (kept unchanged) ────────
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

    def _bandit_score(self, model: str) -> float:
        """Compute quality-latency bandit score: q[model] - λ * lat[model].

        Source: arXiv:2605.14241 "Latency-Quality Routing for Functionally Equivalent Tools".
        Higher score = better quality-latency tradeoff.
        """
        q = self._bandit_quality_ema.get(model, self.MODEL_QUALITY.get(model, 0.5))
        lat = self._bandit_latency_ema.get(model, self.MODEL_LATENCY.get(model, 100.0))
        return q - self._BANDIT_LAMBDA * lat

    def _get_bandit_candidates(self, complexity: QueryComplexity) -> list[str]:
        """Get candidate models for bandit selection.

        Never escalates beyond the primary model's tier — only maintains or downgrades.
        This preserves the quality semantics of complexity-based routing.
        """
        if complexity == QueryComplexity.SIMPLE:
            return [self.TIER_SIMPLE]
        elif complexity == QueryComplexity.MEDIUM:
            return [self.TIER_SIMPLE, self.TIER_MEDIUM]
        else:  # COMPLEX
            return [self.TIER_SIMPLE, self.TIER_MEDIUM, self.TIER_COMPLEX]

    def _bandit_select(self, primary_model: str, complexity: QueryComplexity) -> str:
        """Bandit-based model selection using empirical quality-latency scores.

        Returns primary_model until BANDIT_WARMUP executions have been recorded.
        After warmup, selects argmax(q[candidate] - λ*lat[candidate]) from tier-candidates.
        A 0.02 margin prevents spurious swaps from noise.
        """
        if self._bandit_exec_count < self._BANDIT_WARMUP:
            return primary_model

        candidates = self._get_bandit_candidates(complexity)
        if len(candidates) == 1:
            return candidates[0]

        best_model = primary_model
        best_score = self._bandit_score(primary_model)
        for candidate in candidates:
            score = self._bandit_score(candidate)
            if score > best_score + 0.02:  # margin prevents noise-driven swaps
                best_model = candidate
                best_score = score

        return best_model

    def _compute_routing_confidence(self, model: str, complexity: QueryComplexity) -> float:
        """Compute OI-MAS joint role+scale confidence for a routing decision.

        Based on arXiv:2601.04861 — confidence reflects how well the selected
        model (scale) matches the task requirements (role). Combines:
        - Model quality score (from MODEL_QUALITY)
        - Historical success rate (from execution tracking)
        - Complexity-model alignment (simple→small, complex→large)

        Returns:
            Confidence score 0.0-1.0
        """
        # Base confidence from model quality
        quality = self.MODEL_QUALITY.get(model, 0.5)

        # Historical success rate from execution tracking
        total_queries = self.query_count_per_model.get(model, 0)
        success_rate = 1.0  # Assume success if no history
        if total_queries > 5:
            # Use phi3/qwen success counters as proxy
            if model == self.TIER_SIMPLE:
                success_rate = self._phi3_success_count / max(1, total_queries)
            elif model == self.TIER_MEDIUM:
                success_rate = self._qwen_success_count / max(1, total_queries)

        # Complexity-model alignment penalty
        alignment = 1.0
        if complexity == QueryComplexity.COMPLEX and model == self.TIER_SIMPLE:
            alignment = 0.5  # Small model for complex task = low confidence
        elif complexity == QueryComplexity.SIMPLE and model == self.TIER_COMPLEX:
            alignment = 0.8  # Overkill but not harmful

        # Degradation-aware confidence reduction
        # Active degradation cooldown indicates PIVOT-like behavior
        degradation_factor = 0.8 if self._degradation_cooldown > 0 else 1.0

        confidence = (quality * 0.3 + success_rate * 0.4 + alignment * 0.3) * degradation_factor

        # ── Improvement 3: Cold-start confidence annealing (arXiv:2310.15440 routing analogy)
        # During cold start (no session history), confidence is conservatively scaled to 0.75×.
        # Linearly anneals to 1.0× as query count reaches COLD_START_WARMUP.
        # Floor of 0.75 ensures well-aligned models (quality≈0.95) still exceed the 0.7
        # low-confidence threshold even at cold start (0.95 × 0.75 = 0.713 > 0.7).
        _COLD_START_WARMUP = 10
        total_decisions = sum(self.query_count_per_model.values())
        cold_start_factor = min(1.0, total_decisions / _COLD_START_WARMUP)
        confidence = confidence * (0.75 + 0.25 * cold_start_factor)

        return min(1.0, max(0.0, confidence))

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
            if multiplier < 1.0 and model in (self.TIER_SIMPLE, self.TIER_MEDIUM):
                # Local models underperforming — escalate one tier
                if model == self.TIER_SIMPLE:
                    logger.info(
                        "R-Zero: simple tier underperforming (mult=%.1f), upgrading to medium",
                        multiplier,
                    )
                    return self.TIER_MEDIUM
                if model == self.TIER_MEDIUM:
                    logger.info(
                        "R-Zero: medium tier underperforming (mult=%.1f), upgrading to complex",
                        multiplier,
                    )
                    return self.TIER_COMPLEX
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
                        self._degradation_upgrade_model = self.TIER_COMPLEX
                        logger.warning(
                            "Degradation feedback: CRITICAL %s → forcing %s for next 5 queries",
                            metric,
                            self._degradation_upgrade_model,
                        )
                    elif metric == "token_efficiency":
                        self._degradation_cooldown = 3
                        self._degradation_upgrade_model = self.TIER_MEDIUM
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

        phi3_routed = self.query_count_per_model.get(self.TIER_SIMPLE, 0)
        qwen_routed = self.query_count_per_model.get(self.TIER_MEDIUM, 0)
        deepseek_routed = self.query_count_per_model.get(self.TIER_COMPLEX, 0)

        total_cost = sum(self.cost_per_model.values())

        # Calculate cost comparison (hypothetical: all queries with deepseek)
        deepseek_only_cost = (
            sum(d.estimated_tokens for d in self.routing_decisions)
            / 1000.0
            * self.MODEL_COSTS.get(self.TIER_COMPLEX, 0.0)
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
