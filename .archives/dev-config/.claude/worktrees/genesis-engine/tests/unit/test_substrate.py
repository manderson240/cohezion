"""Tests for substrate module imports and exports.

Ensures the substrate layer modules can be imported and exported correctly.
"""

from __future__ import annotations


class TestSubstrateImports:
    """Test substrate module imports."""

    def test_overload_coordinator_import(self) -> None:
        """Test that OverloadCoordinator can be imported from substrate."""
        from cohezion.substrate import OverloadCoordinator
        from cohezion.substrate.overload_coordinator import OverloadCoordinator as DirectImport

        assert OverloadCoordinator is DirectImport

    def test_kv_cache_tracker_import(self) -> None:
        """Test that KVCacheTracker can be imported from substrate."""
        from cohezion.substrate import KVCacheTracker
        from cohezion.substrate.kv_cache_tracker import KVCacheTracker as DirectImport

        assert KVCacheTracker is DirectImport

    def test_all_exports_available(self) -> None:
        """Test that all expected exports are available."""
        from cohezion import substrate

        expected_exports = [
            "OverloadCoordinator",
            "OverloadError",
            "ProtectionAction",
            "ProtectionConfig",
            "ProtectionLevel",
            "AllocationResult",
            "KVCacheEntry",
            "KVCacheTracker",
        ]

        for export in expected_exports:
            assert hasattr(substrate, export), f"Missing export: {export}"


class TestModelContextProfile:
    """Test ModelContextProfile integration."""

    def test_model_context_profile_import(self) -> None:
        """Test that ModelContextProfile can be imported."""
        from cohezion.swarm.context_model_router import ModelContextProfile

        profile = ModelContextProfile(
            name="test-model",
            total_params_b=7.0,
            size_gb=3.5,
        )

        assert profile.name == "test-model"
        assert profile.total_params_b == 7.0
        assert profile.size_gb == 3.5

    def test_model_context_profile_defaults(self) -> None:
        """Test ModelContextProfile default values."""
        from cohezion.swarm.context_model_router import ModelContextProfile

        profile = ModelContextProfile(
            name="test-model",
            total_params_b=7.0,
        )

        assert profile.quantization == "Q4"
        assert profile.is_moe is False
        assert profile.active_params_b == 7.0

    def test_model_context_profile_to_dict(self) -> None:
        """Test ModelContextProfile serialization."""
        from cohezion.swarm.context_model_router import ModelContextProfile

        profile = ModelContextProfile(
            name="test-model",
            total_params_b=7.0,
            size_gb=3.5,
            quantization="Q8",
            is_moe=True,
            active_params_b=2.0,
        )

        data = profile.to_dict()
        assert data["name"] == "test-model"
        assert data["total_params_b"] == 7.0
        assert data["quantization"] == "Q8"
        assert data["is_moe"] is True
        assert data["active_params_b"] == 2.0
