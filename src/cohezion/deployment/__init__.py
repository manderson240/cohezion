"""Deployment — feature flags and rollout management."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.deployment.feature_flags import FeatureFlag as FeatureFlag
    from cohezion.deployment.feature_flags import FeatureFlagConfig as FeatureFlagConfig
    from cohezion.deployment.feature_flags import FeatureFlagContext as FeatureFlagContext
    from cohezion.deployment.feature_flags import RolloutStage as RolloutStage
