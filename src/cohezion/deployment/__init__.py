"""Deployment utilities: feature flags and gradual rollout management."""

from cohezion.deployment.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    RolloutStage,
    get_feature_flag_manager,
    is_feature_enabled,
)

__all__ = [
    "FeatureFlag",
    "FeatureFlagManager",
    "RolloutStage",
    "get_feature_flag_manager",
    "is_feature_enabled",
]
