"""Tests for Phase 2 Priority 4: Production Deployment.

Covers:
- Feature flags and gradual rollout
- Safety checks and thresholds
- Deployment orchestration
- A/B testing support
"""

from datetime import datetime

import pytest
from cohezion.deployment.deployment_config import (
    DeploymentConfig,
    DeploymentMetrics,
    Environment,
    Region,
    SafetyCheckManager,
    get_config,
)
from cohezion.deployment.deployment_orchestrator import (
    DeploymentOrchestrator,
)

from cohezion.deployment.feature_flags import (
    FeatureFlag,
    FeatureFlagContext,
    FeatureFlagManager,
    RolloutStage,
)


class TestFeatureFlagManager:
    """Test feature flag management and gradual rollout."""

    @pytest.fixture
    def manager(self):
        """Create feature flag manager."""
        return FeatureFlagManager()

    def test_manager_initialization(self, manager):
        """Test manager initializes with defaults."""
        assert len(manager.flags) > 0
        assert FeatureFlag.HIERARCHICAL_VAULT_SEARCH in manager.flags
        assert FeatureFlag.SEMANTIC_EMBEDDINGS in manager.flags
        assert FeatureFlag.UNIFIED_METRICS in manager.flags

    def test_feature_enabled_by_default(self, manager):
        """Test unified metrics is enabled by default (safe)."""
        assert manager.is_enabled(FeatureFlag.UNIFIED_METRICS)

    def test_feature_canary_rollout(self, manager):
        """Test canary rollout status."""
        config = manager.flags[FeatureFlag.HIERARCHICAL_VAULT_SEARCH]
        assert config.rollout_stage == RolloutStage.CANARY
        assert config.rollout_percentage == 10.0

    def test_feature_check_with_context(self, manager):
        """Test feature evaluation with context."""
        context = FeatureFlagContext(
            session_id="session123",
            region="us",
            tenant_id="tenant1",
        )

        # Unified metrics should be enabled globally
        assert manager.is_enabled(FeatureFlag.UNIFIED_METRICS, context)

    def test_region_filtering(self, manager):
        """Test region-based feature filtering."""
        # Set to full rollout first
        config = manager.flags[FeatureFlag.HIERARCHICAL_VAULT_SEARCH]
        config.rollout_percentage = 100.0
        config.enabled_regions = ["us", "asia"]  # EU excluded

        us_context = FeatureFlagContext(region="us", session_id="test1")
        eu_context = FeatureFlagContext(region="eu", session_id="test1")

        assert manager.is_enabled(FeatureFlag.HIERARCHICAL_VAULT_SEARCH, us_context)
        assert not manager.is_enabled(FeatureFlag.HIERARCHICAL_VAULT_SEARCH, eu_context)

    def test_tenant_filtering(self, manager):
        """Test tenant-based feature filtering."""
        config = manager.flags[FeatureFlag.SEMANTIC_EMBEDDINGS]
        config.rollout_percentage = 100.0  # Full rollout
        config.enabled_tenants = ["tenant1", "tenant2"]  # Only specific tenants

        allowed_context = FeatureFlagContext(tenant_id="tenant1", session_id="test1")
        blocked_context = FeatureFlagContext(tenant_id="tenant3", session_id="test1")

        assert manager.is_enabled(FeatureFlag.SEMANTIC_EMBEDDINGS, allowed_context)
        assert not manager.is_enabled(FeatureFlag.SEMANTIC_EMBEDDINGS, blocked_context)

    def test_rollout_percentage_consistency(self, manager):
        """Test rollout percentage is deterministic per session."""
        config = manager.flags[FeatureFlag.HIERARCHICAL_VAULT_SEARCH]
        config.rollout_percentage = 50.0  # 50% rollout

        context1 = FeatureFlagContext(session_id="session123")
        FeatureFlagContext(session_id="session456")

        # Results should be consistent for same session
        result1a = manager.is_enabled(FeatureFlag.HIERARCHICAL_VAULT_SEARCH, context1)
        result1b = manager.is_enabled(FeatureFlag.HIERARCHICAL_VAULT_SEARCH, context1)
        assert result1a == result1b

        # Different sessions may get different results (non-deterministic without control)

    def test_ramp_up_stages(self, manager):
        """Test ramping up feature rollout."""
        flag = FeatureFlag.SEMANTIC_EMBEDDINGS

        # Start at canary (5%)
        manager.ramp_up(flag, 5.0, "test")
        assert manager.flags[flag].rollout_stage == RolloutStage.CANARY
        assert manager.flags[flag].rollout_percentage == 5.0

        # Ramp to ramping (50%)
        manager.ramp_up(flag, 50.0, "test")
        assert manager.flags[flag].rollout_stage == RolloutStage.RAMPING
        assert manager.flags[flag].rollout_percentage == 50.0

        # Full rollout (100%)
        manager.ramp_up(flag, 100.0, "test")
        assert manager.flags[flag].rollout_stage == RolloutStage.FULL
        assert manager.flags[flag].rollout_percentage == 100.0

    def test_emergency_rollback(self, manager):
        """Test emergency rollback disables feature."""
        flag = FeatureFlag.SEMANTIC_EMBEDDINGS

        # Set to full rollout first
        manager.ramp_up(flag, 100.0, "test")
        assert manager.is_enabled(flag)

        # Rollback
        manager.rollback(flag, "emergency")

        # Should be disabled
        assert not manager.is_enabled(flag)
        assert manager.flags[flag].rollout_stage == RolloutStage.DISABLED

    def test_deployment_health_status(self, manager):
        """Test deployment health calculation."""
        health = manager.get_deployment_health()

        assert "total_flags" in health
        assert "enabled_flags" in health
        assert "full_rollout_count" in health
        assert "overall_rollout_percent" in health
        assert health["deployment_status"] in ["stable", "ramping", "initial"]


class TestSafetyCheckManager:
    """Test deployment safety checks."""

    @pytest.fixture
    def config(self):
        """Create test deployment config."""
        return DeploymentConfig(environment=Environment.CANARY, region=Region.US)

    @pytest.fixture
    def checker(self, config):
        """Create safety check manager."""
        return SafetyCheckManager(config)

    @pytest.fixture
    def good_metrics(self):
        """Create metrics for healthy deployment."""
        return DeploymentMetrics(
            environment=Environment.CANARY,
            region=Region.US,
            timestamp=datetime.now().isoformat(),
            cache_hit_rate=92.0,  # Within threshold
            token_efficiency=125.0,  # Good
            error_rate=1.0,  # Low
            latency_p50_ms=100.0,
            latency_p95_ms=500.0,
            latency_p99_ms=2000.0,  # Within threshold
            memory_usage_gb=50.0,  # Within threshold
            throughput_requests_per_sec=1000.0,
            guardrail_block_rate=2.0,  # Within range
        )

    @pytest.fixture
    def bad_metrics(self):
        """Create metrics for unhealthy deployment."""
        return DeploymentMetrics(
            environment=Environment.CANARY,
            region=Region.US,
            timestamp=datetime.now().isoformat(),
            cache_hit_rate=50.0,  # Below threshold
            token_efficiency=80.0,  # Below minimum
            error_rate=5.0,  # Too high
            latency_p50_ms=1000.0,
            latency_p95_ms=3000.0,
            latency_p99_ms=6000.0,  # Above threshold
            memory_usage_gb=110.0,  # At threshold
            throughput_requests_per_sec=500.0,
            guardrail_block_rate=15.0,  # Out of range
        )

    def test_cache_performance_check_pass(self, checker, good_metrics):
        """Test cache performance check passes for good metrics."""
        result = checker.verify_cache_performance(good_metrics)

        assert result.passed
        assert result.check_name == "cache_performance"
        assert "Cache hit rate" in result.message

    def test_cache_performance_check_fail(self, checker, bad_metrics):
        """Test cache performance check fails for bad metrics."""
        result = checker.verify_cache_performance(bad_metrics)

        assert not result.passed
        assert result.severity == "warning"

    def test_token_efficiency_check_pass(self, checker, good_metrics):
        """Test token efficiency check passes."""
        result = checker.verify_token_efficiency(good_metrics)

        assert result.passed

    def test_token_efficiency_check_fail(self, checker, bad_metrics):
        """Test token efficiency check fails."""
        result = checker.verify_token_efficiency(bad_metrics)

        assert not result.passed
        assert result.severity == "error"

    def test_error_rate_check(self, checker, good_metrics, bad_metrics):
        """Test error rate checking."""
        # Good
        result_good = checker.verify_error_rate(good_metrics)
        assert result_good.passed

        # Bad
        result_bad = checker.verify_error_rate(bad_metrics)
        assert not result_bad.passed

    def test_latency_check(self, checker, good_metrics, bad_metrics):
        """Test latency checking."""
        # Good
        result_good = checker.verify_latency(good_metrics)
        assert result_good.passed

        # Bad
        result_bad = checker.verify_latency(bad_metrics)
        assert not result_bad.passed

    def test_memory_check(self, checker, good_metrics, bad_metrics):
        """Test memory usage checking."""
        # Good
        result_good = checker.verify_memory_usage(good_metrics)
        assert result_good.passed

        # Bad
        result_bad = checker.verify_memory_usage(bad_metrics)
        assert not result_bad.passed

    def test_all_checks_pass(self, checker, good_metrics):
        """Test all checks pass for healthy metrics."""
        all_passed = checker.run_all_checks(good_metrics)

        assert all_passed
        status = checker.get_check_status()
        assert status["failed_checks"] == 0

    def test_all_checks_fail(self, checker, bad_metrics):
        """Test checks fail for unhealthy metrics."""
        all_passed = checker.run_all_checks(bad_metrics)

        assert not all_passed
        status = checker.get_check_status()
        assert status["failed_checks"] > 0


class TestDeploymentOrchestrator:
    """Test deployment orchestration."""

    @pytest.fixture
    def setup(self):
        """Set up orchestrator with defaults."""
        config = DeploymentConfig(environment=Environment.CANARY, region=Region.US)
        manager = FeatureFlagManager()
        orchestrator = DeploymentOrchestrator(Environment.CANARY, manager, config)
        return orchestrator, config, manager

    def test_orchestrator_initialization(self, setup):
        """Test orchestrator initializes."""
        orchestrator, _config, _manager = setup

        assert orchestrator.environment == Environment.CANARY
        assert orchestrator.rollout_progress is None

    def test_create_rollout_plan(self, setup):
        """Test creating rollout plan."""
        orchestrator, _, _ = setup

        plan = orchestrator.create_rollout_plan()

        assert plan is not None
        assert len(plan.stages) > 0
        assert plan.environment == Environment.CANARY

    def test_start_rollout(self, setup):
        """Test starting rollout."""
        orchestrator, _, _ = setup

        plan = orchestrator.create_rollout_plan()
        progress = orchestrator.start_rollout(plan)

        assert progress is not None
        assert progress.current_stage_index == 0
        assert orchestrator.rollout_progress is not None

    @pytest.mark.asyncio
    async def test_advance_stage(self, setup):
        """Test advancing rollout stage."""
        orchestrator, _, _ = setup

        plan = orchestrator.create_rollout_plan()
        orchestrator.start_rollout(plan)

        initial_stage = orchestrator.rollout_progress.current_stage_index

        advanced = await orchestrator.advance_stage()

        assert advanced
        assert orchestrator.rollout_progress.current_stage_index == initial_stage + 1

    @pytest.mark.asyncio
    async def test_trigger_rollback(self, setup):
        """Test emergency rollback."""
        orchestrator, _, _ = setup

        plan = orchestrator.create_rollout_plan()
        orchestrator.start_rollout(plan)

        await orchestrator.trigger_rollback("Test rollback")

        assert orchestrator.rollout_progress.rollback_triggered

    def test_rollout_status(self, setup):
        """Test getting rollout status."""
        orchestrator, _, _ = setup

        # Before rollout
        status_before = orchestrator.get_rollout_status()
        assert status_before["status"] == "no_active_rollout"

        # After rollout start
        plan = orchestrator.create_rollout_plan()
        orchestrator.start_rollout(plan)
        status_after = orchestrator.get_rollout_status()
        assert status_after["status"] == "active"


class TestProductionDeploymentIntegration:
    """Integration tests for production deployment."""

    def test_production_config_defaults(self):
        """Test production environment has good defaults."""
        config = get_config(Environment.PRODUCTION)

        assert config.replicas == 3  # HA setup
        assert config.monitoring_enabled
        assert config.auto_rollback_enabled

    def test_canary_config_is_conservative(self):
        """Test canary has conservative settings."""
        config = DeploymentConfig(environment=Environment.CANARY, region=Region.US)

        assert config.replicas == 1
        assert config.auto_rollback_enabled

    def test_feature_flag_safety_defaults(self):
        """Test feature flags have safe defaults."""
        manager = FeatureFlagManager()

        # Observability should be fully enabled (zero risk)
        assert manager.is_enabled(FeatureFlag.UNIFIED_METRICS)
        assert manager.is_enabled(FeatureFlag.OBSERVABILITY_API)

        # Semantic features should be in canary (low risk)
        assert manager.flags[FeatureFlag.SEMANTIC_EMBEDDINGS].rollout_stage == RolloutStage.CANARY

        # Adaptive thresholds should be disabled (higher risk)
        assert not manager.is_enabled(FeatureFlag.ADAPTIVE_CACHE_THRESHOLDS)
