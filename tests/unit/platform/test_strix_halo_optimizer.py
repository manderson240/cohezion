"""Unit tests for AMD Strix Halo Optimizer and Hardware Governor."""

from __future__ import annotations

import pytest

from cohezion.platform.strix_halo_optimizer import (
    PreflightAuditResult,
    StrixHaloOptimizer,
)


class TestStrixHaloOptimizer:
    """Test suite for StrixHaloOptimizer."""

    @pytest.fixture
    def optimizer(self) -> StrixHaloOptimizer:
        """Fixture providing StrixHaloOptimizer instance."""
        return StrixHaloOptimizer(admission_port=13305)

    def test_hardware_profile_attributes(self, optimizer: StrixHaloOptimizer) -> None:
        """Verify hardware specifications match AMD Ryzen AI MAX+ 395."""
        profile = optimizer.profile
        assert profile.soc_name == "AMD Ryzen AI MAX+ 395"
        assert profile.cpu_cores == 16
        assert profile.cpu_threads == 32
        assert "Radeon 8060S" in profile.gpu_silicon
        assert profile.total_uma_gib == 128.0
        assert profile.gateway_port == 13305

    def test_run_preflight_audit(self, optimizer: StrixHaloOptimizer) -> None:
        """Verify preflight audit runs and produces structured telemetry."""
        result = optimizer.run_preflight_audit()
        assert isinstance(result, PreflightAuditResult)
        assert result.available_memory_gib > 0
        assert result.swap_used_percent >= 0
        assert isinstance(result.diagnostics, list)
        assert len(result.diagnostics) > 0

    def test_build_collection_router_policy(self, optimizer: StrixHaloOptimizer) -> None:
        """Verify collection.router policy adheres to Lemonade JSON schema."""
        policy = optimizer.build_collection_router_policy(
            router_model_name="user.test-router",
            default_model="qwen3.5-4b-FLM",
        )
        assert policy["version"] == "1"
        assert policy["model_name"] == "user.test-router"
        assert policy["recipe"] == "collection.router"
        routing = policy["routing"]
        assert routing["default_model"] == "qwen3.5-4b-FLM"
        assert "qwen3.5-4b-FLM" in routing["candidates"]
        rules = routing["rules"]
        rule_ids = [r["id"] for r in rules]
        assert "vision" in rule_ids
        assert "code-generation" in rule_ids
        assert "default-npu-reasoning" in rule_ids

    def test_verify_kaggle_strix_invariants_rsna(self, optimizer: StrixHaloOptimizer) -> None:
        """Verify RSNA Knee invariant checks on CPU."""
        valid_payload = {
            "ledoit_wolf_shrinkage": 0.04,
            "min_probability": 0.005,
            "max_probability": 0.995,
        }
        passed, msg = optimizer.verify_kaggle_strix_invariants(
            "rsna-knee-abnormality-detection", valid_payload
        )
        assert passed
        assert "RSNA Knee" in msg

        # Unclipped probability rejection
        invalid_payload = {
            "ledoit_wolf_shrinkage": 0.04,
            "min_probability": 0.0,
            "max_probability": 1.0,
        }
        passed, err = optimizer.verify_kaggle_strix_invariants(
            "rsna-knee-abnormality-detection", invalid_payload
        )
        assert not passed
        assert "unclipped" in err

    def test_verify_kaggle_strix_invariants_arc(self, optimizer: StrixHaloOptimizer) -> None:
        """Verify ARC-AGI invariant checks on CPU."""
        valid_payload = {
            "d4_symmetry_verified": True,
            "euler_characteristic": 1,
        }
        passed, msg = optimizer.verify_kaggle_strix_invariants(
            "arc-prize-2026-arc-agi-2", valid_payload
        )
        assert passed
        assert "D4 group invariance" in msg

        # Broken D4 symmetry rejection
        invalid_payload = {
            "d4_symmetry_verified": False,
        }
        passed, err = optimizer.verify_kaggle_strix_invariants(
            "arc-prize-2026-arc-agi-2", invalid_payload
        )
        assert not passed
        assert "D4 dihedral" in err
