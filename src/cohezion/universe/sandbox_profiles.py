"""Sandbox resource profiles for simulation workloads.

Defines typed resource envelopes (SandboxProfile) that constrain memory, CPU,
timeout, network, and GPU access for containerized or process-isolated simulations.
Profiles are hardware-validated against the Strix Halo's 128GB unified memory pool.
"""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


logger = logging.getLogger(__name__)

# Maximum memory budget leaves 8GB headroom on 128GB system
MAX_SYSTEM_MEMORY_MB = 120 * 1024  # 120 GB


class SandboxTier(StrEnum):
    """Predefined simulation resource tiers."""

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    CUSTOM = "custom"


class SandboxProfile(BaseModel):
    """Resource envelope for a sandboxed simulation.

    Parameters
    ----------
    memory_limit_mb : int
        Maximum memory in megabytes.
    cpu_quota_percent : int
        CPU quota as percentage of one core (100 = 1 full core, 400 = 4 cores).
    timeout_seconds : int
        Hard timeout before the sandbox is killed.
    network_enabled : bool
        Whether the sandbox has network access.
    gpu_passthrough : bool
        Whether the sandbox can access GPU/iGPU resources.
    coherence_check_interval : float
        Seconds between HIHO coherence checks (0 = disabled).
    max_divergence_sigma : float
        Maximum standard deviations from running mean before divergence is flagged.
    """

    memory_limit_mb: int = Field(ge=64, le=MAX_SYSTEM_MEMORY_MB)
    cpu_quota_percent: int = Field(ge=10, le=3200)
    timeout_seconds: int = Field(ge=5, le=7200)
    network_enabled: bool = False
    gpu_passthrough: bool = False
    coherence_check_interval: float = Field(default=0.0, ge=0.0)
    max_divergence_sigma: float = Field(default=3.0, ge=1.0)

    @model_validator(mode="after")
    def validate_against_hardware(self) -> SandboxProfile:
        """Ensure profile fits within system memory headroom."""
        if self.memory_limit_mb > MAX_SYSTEM_MEMORY_MB:
            msg = (
                f"Memory request {self.memory_limit_mb}MB exceeds system cap "
                f"of {MAX_SYSTEM_MEMORY_MB}MB (128GB - 8GB headroom)"
            )
            raise ValueError(msg)
        return self

    def to_docker_kwargs(self) -> dict:
        """Convert profile to docker-py container.run() keyword arguments."""
        kwargs: dict = {
            "mem_limit": f"{self.memory_limit_mb}m",
            "cpu_quota": self.cpu_quota_percent * 1000,
            "cpu_period": 100000,
        }
        if not self.network_enabled:
            kwargs["network_mode"] = "none"
        return kwargs

    def to_systemd_args(self) -> list[str]:
        """Convert profile to systemd-run property arguments."""
        args = [
            f"MemoryMax={self.memory_limit_mb}M",
            f"CPUQuota={self.cpu_quota_percent}%",
        ]
        return args

    def to_docker_memory_str(self) -> str:
        """Return Docker-compatible memory limit string."""
        return f"{self.memory_limit_mb}m"


# Predefined profiles for common simulation tiers
PROFILES: dict[SandboxTier, SandboxProfile] = {
    SandboxTier.LIGHT: SandboxProfile(
        memory_limit_mb=1024,
        cpu_quota_percent=100,
        timeout_seconds=60,
        network_enabled=False,
        gpu_passthrough=False,
        coherence_check_interval=10.0,
        max_divergence_sigma=3.0,
    ),
    SandboxTier.MEDIUM: SandboxProfile(
        memory_limit_mb=4096,
        cpu_quota_percent=200,
        timeout_seconds=300,
        network_enabled=False,
        gpu_passthrough=False,
        coherence_check_interval=5.0,
        max_divergence_sigma=3.0,
    ),
    SandboxTier.HEAVY: SandboxProfile(
        memory_limit_mb=65536,
        cpu_quota_percent=400,
        timeout_seconds=1800,
        network_enabled=False,
        gpu_passthrough=True,
        coherence_check_interval=2.0,
        max_divergence_sigma=4.0,
    ),
}


def get_profile(tier: SandboxTier) -> SandboxProfile:
    """Get a copy of the predefined profile for the given tier.

    Parameters
    ----------
    tier : SandboxTier
        The simulation tier.

    Returns
    -------
    SandboxProfile
        A new SandboxProfile instance (safe to mutate).

    Raises
    ------
    ValueError
        If tier is CUSTOM (must be constructed explicitly).
    """
    if tier == SandboxTier.CUSTOM:
        raise ValueError("CUSTOM tier requires explicit SandboxProfile construction")
    return PROFILES[tier].model_copy()
