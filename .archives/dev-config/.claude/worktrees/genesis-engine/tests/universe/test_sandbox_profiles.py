"""Tests for sandbox resource profiles."""

import pytest
from pydantic import ValidationError

from cohezion.universe.sandbox_profiles import (
    MAX_SYSTEM_MEMORY_MB,
    PROFILES,
    SandboxProfile,
    SandboxTier,
    get_profile,
)


class TestSandboxTier:
    def test_tier_values(self):
        assert SandboxTier.LIGHT == "light"
        assert SandboxTier.MEDIUM == "medium"
        assert SandboxTier.HEAVY == "heavy"
        assert SandboxTier.CUSTOM == "custom"

    def test_all_predefined_tiers_have_profiles(self):
        for tier in SandboxTier:
            if tier != SandboxTier.CUSTOM:
                assert tier in PROFILES


class TestSandboxProfile:
    def test_light_profile_defaults(self):
        profile = get_profile(SandboxTier.LIGHT)
        assert profile.memory_limit_mb == 1024
        assert profile.cpu_quota_percent == 100
        assert profile.timeout_seconds == 60
        assert profile.network_enabled is False
        assert profile.gpu_passthrough is False

    def test_medium_profile_defaults(self):
        profile = get_profile(SandboxTier.MEDIUM)
        assert profile.memory_limit_mb == 4096
        assert profile.cpu_quota_percent == 200
        assert profile.timeout_seconds == 300

    def test_heavy_profile_defaults(self):
        profile = get_profile(SandboxTier.HEAVY)
        assert profile.memory_limit_mb == 65536
        assert profile.cpu_quota_percent == 400
        assert profile.timeout_seconds == 1800
        assert profile.gpu_passthrough is True

    def test_custom_tier_raises_on_get_profile(self):
        with pytest.raises(ValueError, match="CUSTOM tier requires explicit"):
            get_profile(SandboxTier.CUSTOM)

    def test_custom_profile_construction(self):
        profile = SandboxProfile(
            memory_limit_mb=2048,
            cpu_quota_percent=150,
            timeout_seconds=120,
            network_enabled=True,
        )
        assert profile.memory_limit_mb == 2048
        assert profile.network_enabled is True

    def test_memory_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SandboxProfile(
                memory_limit_mb=32,
                cpu_quota_percent=100,
                timeout_seconds=60,
            )

    def test_memory_above_system_cap_rejected(self):
        with pytest.raises(ValidationError):
            SandboxProfile(
                memory_limit_mb=MAX_SYSTEM_MEMORY_MB + 1,
                cpu_quota_percent=100,
                timeout_seconds=60,
            )

    def test_cpu_quota_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SandboxProfile(
                memory_limit_mb=512,
                cpu_quota_percent=5,
                timeout_seconds=60,
            )

    def test_timeout_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            SandboxProfile(
                memory_limit_mb=512,
                cpu_quota_percent=100,
                timeout_seconds=2,
            )

    def test_max_divergence_sigma_minimum(self):
        with pytest.raises(ValidationError):
            SandboxProfile(
                memory_limit_mb=512,
                cpu_quota_percent=100,
                timeout_seconds=60,
                max_divergence_sigma=0.5,
            )


class TestProfileConversion:
    def test_to_docker_kwargs(self):
        profile = get_profile(SandboxTier.LIGHT)
        kwargs = profile.to_docker_kwargs()
        assert kwargs["mem_limit"] == "1024m"
        assert kwargs["cpu_quota"] == 100000
        assert kwargs["cpu_period"] == 100000
        assert kwargs["network_mode"] == "none"

    def test_to_docker_kwargs_network_enabled(self):
        profile = SandboxProfile(
            memory_limit_mb=512,
            cpu_quota_percent=100,
            timeout_seconds=60,
            network_enabled=True,
        )
        kwargs = profile.to_docker_kwargs()
        assert "network_mode" not in kwargs

    def test_to_systemd_args(self):
        profile = get_profile(SandboxTier.MEDIUM)
        args = profile.to_systemd_args()
        assert "MemoryMax=4096M" in args
        assert "CPUQuota=200%" in args

    def test_to_docker_memory_str(self):
        profile = get_profile(SandboxTier.HEAVY)
        assert profile.to_docker_memory_str() == "65536m"


class TestGetProfile:
    def test_returns_copy(self):
        p1 = get_profile(SandboxTier.LIGHT)
        p2 = get_profile(SandboxTier.LIGHT)
        p1.memory_limit_mb = 9999
        assert p2.memory_limit_mb == 1024

    def test_all_tiers(self):
        for tier in [SandboxTier.LIGHT, SandboxTier.MEDIUM, SandboxTier.HEAVY]:
            profile = get_profile(tier)
            assert isinstance(profile, SandboxProfile)
