# ruff: noqa: RUF002  # math/physics symbols intentional
"""Feature flags for gradual Phase 2 rollout.

Enables opt-in enablement of Phase 2 optimizations:
- Priority 1: Hierarchical vault search (5-10× query speedup)
- Priority 2: Semantic embeddings (2.3× better discrimination)
- Priority 3: Observability dashboard (real-time monitoring)

Supports gradual rollout with A/B testing and per-environment configuration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class RolloutStage(Enum):
    """Rollout stages for gradual deployment."""

    DISABLED = "disabled"  # Feature completely off
    CANARY = "canary"  # 5-10% of traffic
    RAMPING = "ramping"  # 25-50% of traffic
    FULL = "full"  # 100% of traffic


class FeatureFlag(Enum):
    """Available feature flags for Phase 2."""

    # Priority 1: Hierarchical Vault Search
    HIERARCHICAL_VAULT_SEARCH = "hierarchical_vault_search"
    VAULT_SEARCH_BY_OPERATION = "vault_search_by_operation"
    VAULT_SEARCH_BY_DOMAIN = "vault_search_by_domain"

    # Priority 2: Semantic Embeddings
    SEMANTIC_EMBEDDINGS = "semantic_embeddings"
    SEMANTIC_CACHE_L2 = "semantic_cache_l2"
    ADAPTIVE_CACHE_THRESHOLDS = "adaptive_cache_thresholds"

    # Priority 3: Observability
    UNIFIED_METRICS = "unified_metrics"
    METRICS_ANALYTICS = "metrics_analytics"
    OBSERVABILITY_API = "observability_api"

    # Phase 3: ngrok AI Gateway Integration
    NGROK_AI_GATEWAY = "ngrok_ai_gateway"
    NGROK_FAILOVER_MODE = "ngrok_failover_mode"
    NGROK_COST_OPTIMIZATION = "ngrok_cost_optimization"
    NGROK_RESPONSE_CACHING = "ngrok_response_caching"

    # Rollback / Safety
    FALLBACK_TO_HASH_CACHE = "fallback_to_hash_cache"
    DISABLE_SEMANTIC_CACHE = "disable_semantic_cache"


@dataclass
class FeatureFlagConfig:
    """Configuration for a single feature flag."""

    flag: FeatureFlag
    enabled: bool = True
    rollout_stage: RolloutStage = RolloutStage.FULL
    rollout_percentage: float = 100.0  # 0.0-100.0, percentage of requests
    enabled_regions: list[str] = field(
        default_factory=lambda: ["us", "eu", "asia"]
    )  # Deployment regions
    enabled_tenants: list[str] = field(
        default_factory=list
    )  # Empty = all tenants, otherwise specific list
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_by: str = "system"


@dataclass
class FeatureFlagContext:
    """Context for evaluating feature flags."""

    user_id: str | None = None
    tenant_id: str | None = None
    region: str = "us"
    session_id: str | None = None
    experimental_group: str | None = None  # "control" or "treatment" for A/B tests
    metadata: dict[str, Any] = field(default_factory=dict)


class FeatureFlagManager:
    """Manage feature flags for gradual Phase 2 rollout."""

    def __init__(self):
        """Initialize feature flag manager with production defaults."""
        self.flags: dict[FeatureFlag, FeatureFlagConfig] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize with production-safe defaults (all disabled for gradual rollout)."""
        # Priority 1: Hierarchical Vault Search (safest, enables immediately in canary)
        self.flags[FeatureFlag.HIERARCHICAL_VAULT_SEARCH] = FeatureFlagConfig(
            flag=FeatureFlag.HIERARCHICAL_VAULT_SEARCH,
            enabled=True,
            rollout_stage=RolloutStage.CANARY,
            rollout_percentage=10.0,  # Start at 10%
            metadata={"priority": 1, "impact": "query_latency", "risk": "low"},
        )

        self.flags[FeatureFlag.VAULT_SEARCH_BY_OPERATION] = FeatureFlagConfig(
            flag=FeatureFlag.VAULT_SEARCH_BY_OPERATION,
            enabled=True,
            rollout_stage=RolloutStage.CANARY,
            rollout_percentage=10.0,
            metadata={"priority": 1, "impact": "vault_search", "risk": "low"},
        )

        self.flags[FeatureFlag.VAULT_SEARCH_BY_DOMAIN] = FeatureFlagConfig(
            flag=FeatureFlag.VAULT_SEARCH_BY_DOMAIN,
            enabled=True,
            rollout_stage=RolloutStage.CANARY,
            rollout_percentage=10.0,
            metadata={"priority": 1, "impact": "vault_search", "risk": "low"},
        )

        # Priority 2: Semantic Embeddings (low risk, good discrimination improvement)
        self.flags[FeatureFlag.SEMANTIC_EMBEDDINGS] = FeatureFlagConfig(
            flag=FeatureFlag.SEMANTIC_EMBEDDINGS,
            enabled=True,
            rollout_stage=RolloutStage.CANARY,
            rollout_percentage=5.0,  # Start at 5%, more conservative
            metadata={"priority": 2, "impact": "cache_discrimination", "risk": "low"},
        )

        self.flags[FeatureFlag.SEMANTIC_CACHE_L2] = FeatureFlagConfig(
            flag=FeatureFlag.SEMANTIC_CACHE_L2,
            enabled=True,
            rollout_stage=RolloutStage.CANARY,
            rollout_percentage=5.0,
            metadata={"priority": 2, "impact": "cache_hit_rate", "risk": "low"},
        )

        self.flags[FeatureFlag.ADAPTIVE_CACHE_THRESHOLDS] = FeatureFlagConfig(
            flag=FeatureFlag.ADAPTIVE_CACHE_THRESHOLDS,
            enabled=False,  # Keep disabled initially, enable after validation
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={"priority": 2, "impact": "cache_tuning", "risk": "medium"},
        )

        # Priority 3: Observability (zero production impact, pure monitoring)
        self.flags[FeatureFlag.UNIFIED_METRICS] = FeatureFlagConfig(
            flag=FeatureFlag.UNIFIED_METRICS,
            enabled=True,
            rollout_stage=RolloutStage.FULL,
            rollout_percentage=100.0,  # Safe to enable immediately
            metadata={"priority": 3, "impact": "monitoring", "risk": "none"},
        )

        self.flags[FeatureFlag.METRICS_ANALYTICS] = FeatureFlagConfig(
            flag=FeatureFlag.METRICS_ANALYTICS,
            enabled=True,
            rollout_stage=RolloutStage.FULL,
            rollout_percentage=100.0,
            metadata={"priority": 3, "impact": "analytics", "risk": "none"},
        )

        self.flags[FeatureFlag.OBSERVABILITY_API] = FeatureFlagConfig(
            flag=FeatureFlag.OBSERVABILITY_API,
            enabled=True,
            rollout_stage=RolloutStage.FULL,
            rollout_percentage=100.0,
            metadata={"priority": 3, "impact": "api_endpoints", "risk": "none"},
        )

        # Phase 3: ngrok AI Gateway Integration (gradual rollout, starts disabled)
        self.flags[FeatureFlag.NGROK_AI_GATEWAY] = FeatureFlagConfig(
            flag=FeatureFlag.NGROK_AI_GATEWAY,
            enabled=False,  # Start disabled, enable after validation
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={
                "priority": "phase3",
                "impact": "multi_provider_routing",
                "risk": "medium",
                "description": "Route requests through ngrok AI Gateway for multi-provider support",
            },
        )

        self.flags[FeatureFlag.NGROK_FAILOVER_MODE] = FeatureFlagConfig(
            flag=FeatureFlag.NGROK_FAILOVER_MODE,
            enabled=False,
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={
                "priority": "phase3",
                "impact": "failover",
                "risk": "low",
                "description": "Automatically failover to Ollama if ngrok fails",
            },
        )

        self.flags[FeatureFlag.NGROK_COST_OPTIMIZATION] = FeatureFlagConfig(
            flag=FeatureFlag.NGROK_COST_OPTIMIZATION,
            enabled=False,
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={
                "priority": "phase3",
                "impact": "cost_reduction",
                "risk": "low",
                "description": "Use intelligent routing to optimize model selection by cost",
            },
        )

        self.flags[FeatureFlag.NGROK_RESPONSE_CACHING] = FeatureFlagConfig(
            flag=FeatureFlag.NGROK_RESPONSE_CACHING,
            enabled=False,
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={
                "priority": "phase3",
                "impact": "caching",
                "risk": "none",
                "description": "Cache responses from ngrok gateway (4th tier cache)",
            },
        )

        # Rollback / Safety flags
        self.flags[FeatureFlag.FALLBACK_TO_HASH_CACHE] = FeatureFlagConfig(
            flag=FeatureFlag.FALLBACK_TO_HASH_CACHE,
            enabled=True,  # Always enabled as safety net
            rollout_stage=RolloutStage.FULL,
            rollout_percentage=100.0,
            metadata={"priority": "safety", "impact": "fallback", "risk": "none"},
        )

        self.flags[FeatureFlag.DISABLE_SEMANTIC_CACHE] = FeatureFlagConfig(
            flag=FeatureFlag.DISABLE_SEMANTIC_CACHE,
            enabled=False,  # Use to disable semantic cache if issues detected
            rollout_stage=RolloutStage.DISABLED,
            rollout_percentage=0.0,
            metadata={"priority": "safety", "impact": "disable", "risk": "none"},
        )

    def is_enabled(self, flag: FeatureFlag, context: FeatureFlagContext | None = None) -> bool:
        """Evaluate if a feature flag is enabled for given context.

        Args:
            flag: Feature flag to check
            context: Evaluation context (user, tenant, region, etc.)

        Returns:
            True if feature is enabled for context, False otherwise
        """
        if flag not in self.flags:
            logger.warning("Unknown feature flag: %s", flag)
            return False

        config = self.flags[flag]

        # Check basic enable/disable
        if not config.enabled:
            return False

        # Check rollout stage
        if config.rollout_stage == RolloutStage.DISABLED:
            return False

        # Check rollout percentage (using simple hash for consistency)
        if config.rollout_percentage < 100.0:
            if context and context.session_id:
                # Deterministic rollout based on session ID
                hash_val = hash(context.session_id) % 100
                if hash_val >= config.rollout_percentage:
                    return False
            else:
                # Default: 50% chance if no session ID
                import random

                if random.random() * 100 > config.rollout_percentage:
                    return False

        # Check region
        if context and context.region not in config.enabled_regions:
            return False

        # Check tenant
        if config.enabled_tenants:  # If list is not empty, must match
            if not context or context.tenant_id not in config.enabled_tenants:
                return False

        return True

    def set_flag(
        self,
        flag: FeatureFlag,
        enabled: bool,
        rollout_stage: RolloutStage = RolloutStage.FULL,
        rollout_percentage: float = 100.0,
        updated_by: str = "admin",
    ) -> None:
        """Update feature flag configuration.

        Args:
            flag: Feature flag to update
            enabled: Whether flag is enabled
            rollout_stage: Current rollout stage
            rollout_percentage: Percentage of traffic to enable for
            updated_by: Who is making the change
        """
        if flag not in self.flags:
            logger.warning("Unknown feature flag: %s", flag)
            return

        config = self.flags[flag]
        config.enabled = enabled
        config.rollout_stage = rollout_stage
        config.rollout_percentage = min(max(rollout_percentage, 0.0), 100.0)
        config.updated_at = datetime.now()
        config.updated_by = updated_by

        logger.info(
            "Updated flag %s: enabled=%s, stage=%s, rollout=%.1f%% by %s",
            flag.value,
            enabled,
            rollout_stage.value,
            rollout_percentage,
            updated_by,
        )

    def ramp_up(self, flag: FeatureFlag, percentage: float, updated_by: str = "admin") -> None:
        """Gradually increase rollout percentage.

        Args:
            flag: Feature flag to ramp up
            percentage: New rollout percentage (0-100)
            updated_by: Who is making the change
        """
        if flag not in self.flags:
            logger.warning("Unknown feature flag: %s", flag)
            return

        config = self.flags[flag]
        old_percentage = config.rollout_percentage

        # Determine new stage based on percentage
        if percentage >= 100:
            new_stage = RolloutStage.FULL
        elif percentage >= 50:
            new_stage = RolloutStage.RAMPING
        elif percentage > 0:
            new_stage = RolloutStage.CANARY
        else:
            new_stage = RolloutStage.DISABLED

        self.set_flag(flag, True, new_stage, percentage, updated_by)

        logger.info(
            "Ramped up %s: %.1f%% → %.1f%% by %s",
            flag.value,
            old_percentage,
            percentage,
            updated_by,
        )

    def rollback(self, flag: FeatureFlag, updated_by: str = "admin") -> None:
        """Immediately disable feature flag (emergency rollback).

        Args:
            flag: Feature flag to rollback
            updated_by: Who is making the change
        """
        if flag not in self.flags:
            logger.warning("Unknown feature flag: %s", flag)
            return

        self.set_flag(flag, False, RolloutStage.DISABLED, 0.0, updated_by)
        logger.warning("ROLLBACK: Disabled %s by %s", flag.value, updated_by)

    def get_status(self) -> dict[str, Any]:
        """Get current status of all feature flags.

        Returns:
            Dictionary with all flag statuses
        """
        return {
            flag.value: {
                "enabled": config.enabled,
                "rollout_stage": config.rollout_stage.value,
                "rollout_percentage": config.rollout_percentage,
                "enabled_regions": config.enabled_regions,
                "enabled_tenants": config.enabled_tenants or ["all"],
                "metadata": config.metadata,
                "updated_at": config.updated_at.isoformat(),
                "updated_by": config.updated_by,
            }
            for flag, config in self.flags.items()
        }

    def get_deployment_health(self) -> dict[str, Any]:
        """Get deployment health summary.

        Returns:
            Dictionary with health metrics
        """
        total_flags = len(self.flags)
        enabled_flags = sum(1 for c in self.flags.values() if c.enabled)
        full_rollout = sum(1 for c in self.flags.values() if c.rollout_stage == RolloutStage.FULL)
        canary = sum(1 for c in self.flags.values() if c.rollout_stage == RolloutStage.CANARY)

        return {
            "total_flags": total_flags,
            "enabled_flags": enabled_flags,
            "full_rollout_count": full_rollout,
            "canary_count": canary,
            "overall_rollout_percent": (full_rollout / total_flags) * 100,
            "deployment_status": (
                "stable" if full_rollout == total_flags else "ramping" if canary > 0 else "initial"
            ),
        }


# Global feature flag manager instance
_global_manager: FeatureFlagManager | None = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get or create global feature flag manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = FeatureFlagManager()
    return _global_manager


def is_feature_enabled(flag: FeatureFlag, context: FeatureFlagContext | None = None) -> bool:
    """Convenience function to check if feature is enabled.

    Args:
        flag: Feature flag to check
        context: Evaluation context

    Returns:
        True if enabled, False otherwise
    """
    manager = get_feature_flag_manager()
    return manager.is_enabled(flag, context)
