# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Central orchestrator for sandboxed simulation execution.

Provides a singleton ``SandboxManager`` that:
- Tracks active sandboxes and enforces a system-wide 100GB memory budget.
- Selects the best isolation backend automatically.
- Integrates with ``get_circuit("sandbox_manager")`` for fault isolation.
- Queries ``get_resource_monitor()`` for backpressure (delays launch if
  dilation_factor < 0.3).
- Attaches a ``DivergenceDetector`` to each running sandbox.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from cohezion.reliability import get_circuit
from cohezion.universe.divergence import DivergenceDetector
from cohezion.universe.sandbox_backends import (
    BackendResult,
    IsolationBackend,
    select_backend,
)
from cohezion.universe.sandbox_profiles import (
    SandboxProfile,
    SandboxTier,
    get_profile,
)


logger = logging.getLogger(__name__)

# System-wide memory budget for all sandboxes (85GB of 128GB)
# Desktop baseline ~60GB (Chrome, Obsidian, etc.) leaves ~65GB headroom;
# 85GB ceiling prevents OOM while allowing burst simulation workloads.
SYSTEM_MEMORY_BUDGET_MB = 85 * 1024


@dataclass
class SandboxInstance:
    """Tracks a running sandbox and its attached divergence detector.

    Parameters
    ----------
    sandbox_id : str
        Unique identifier for this sandbox instance.
    tier : SandboxTier
        The tier this sandbox was launched with.
    profile : SandboxProfile
        The resource profile applied to this sandbox.
    detector : DivergenceDetector
        Per-sandbox divergence detector.
    started_at : float
        Timestamp when the sandbox was launched.
    """

    sandbox_id: str
    tier: SandboxTier
    profile: SandboxProfile
    detector: DivergenceDetector
    started_at: float = field(default_factory=time.time)


class SandboxManager:
    """Central orchestrator for sandboxed simulation execution.

    Singleton pattern consistent with ResourceMonitor and SelfHealingSystem.
    """

    _instance: SandboxManager | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> SandboxManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._active: dict[str, SandboxInstance] = {}
        self._backend: IsolationBackend | None = None
        self._circuit = get_circuit("sandbox_manager", failure_threshold=3)
        self._initialized = True
        logger.info("SandboxManager initialized")

    @property
    def backend(self) -> IsolationBackend:
        """Lazily select the isolation backend."""
        if self._backend is None:
            self._backend = select_backend()
        return self._backend

    @property
    def allocated_memory_mb(self) -> int:
        """Total memory currently allocated across active sandboxes."""
        return sum(inst.profile.memory_limit_mb for inst in self._active.values())

    @property
    def budget_remaining_mb(self) -> int:
        """Memory budget remaining before new sandboxes would be rejected."""
        return SYSTEM_MEMORY_BUDGET_MB - self.allocated_memory_mb

    async def run_simulation(
        self,
        script: str,
        tier: SandboxTier = SandboxTier.MEDIUM,
        profile: SandboxProfile | None = None,
        files: dict[str, str | bytes] | None = None,
        env: dict[str, str] | None = None,
    ) -> BackendResult:
        """Run a simulation in an isolated sandbox.

        Parameters
        ----------
        script : str
            Python script content to execute.
        tier : SandboxTier
            Predefined tier (ignored if profile is provided).
        profile : SandboxProfile, optional
            Custom profile. If None, uses the tier's predefined profile.
        files : dict, optional
            Additional files to inject into the sandbox.
        env : dict, optional
            Environment variables for the sandbox.

        Returns
        -------
        BackendResult
            Execution result with stdout, stderr, exit code, duration.

        Raises
        ------
        RuntimeError
            If the circuit breaker is open or memory budget is exhausted.
        """
        # 1. Circuit breaker check
        if not self._circuit.allow_request():
            raise RuntimeError("Sandbox circuit breaker is OPEN — too many recent failures")

        # 2. Resolve profile
        effective_profile = profile if profile is not None else get_profile(tier)

        # 3. Memory budget check
        if effective_profile.memory_limit_mb > self.budget_remaining_mb:
            raise RuntimeError(
                f"Memory budget exceeded: requesting {effective_profile.memory_limit_mb}MB, "
                f"only {self.budget_remaining_mb}MB remaining "
                f"(budget={SYSTEM_MEMORY_BUDGET_MB}MB)"
            )

        # 4. Backpressure check via ResourceMonitor
        await self._wait_for_backpressure()

        # 5. Create sandbox instance with detector
        sandbox_id = f"sandbox_{uuid4().hex[:8]}"
        detector = DivergenceDetector(
            max_sigma=effective_profile.max_divergence_sigma,
            window_size=100,
        )
        instance = SandboxInstance(
            sandbox_id=sandbox_id,
            tier=tier,
            profile=effective_profile,
            detector=detector,
        )

        # 6. Register with ResourceMonitor
        self._active[sandbox_id] = instance
        self._register_with_monitor(instance)

        logger.info(
            f"Launching sandbox {sandbox_id} (tier={tier.value}, "
            f"mem={effective_profile.memory_limit_mb}MB, "
            f"cpu={effective_profile.cpu_quota_percent}%)"
        )

        try:
            # 7. Execute via backend
            result = await self.backend.execute(script, effective_profile, files=files, env=env)

            if result.success:
                self._circuit.record_success()
            else:
                self._circuit.record_failure()

            return result

        except Exception as e:
            self._circuit.record_failure()
            logger.error(f"Sandbox {sandbox_id} execution failed: {e}")
            raise

        finally:
            # 8. Deregister and clean up
            self._deregister_from_monitor(instance)
            self._active.pop(sandbox_id, None)

    async def _wait_for_backpressure(self) -> None:
        """Delay launch if system is under heavy pressure."""
        try:
            from cohezion.reliability.monitor import get_resource_monitor

            monitor = get_resource_monitor()
            dilation = monitor.get_dilation_factor()

            if dilation < 0.3:
                wait_time = max(2.0, (1.0 - dilation) * 10)
                logger.warning(
                    f"System under pressure (dilation={dilation:.2f}), delaying sandbox launch by {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.debug(f"Backpressure check skipped: {e}")

    def _register_with_monitor(self, instance: SandboxInstance) -> None:
        """Register sandbox with ResourceMonitor for tracking."""
        try:
            from cohezion.reliability.monitor import get_resource_monitor

            monitor = get_resource_monitor()
            if hasattr(monitor, "register_sandbox"):
                monitor.register_sandbox(instance.sandbox_id, instance.profile.memory_limit_mb)
        except Exception as e:
            logger.debug(f"Monitor registration skipped: {e}")

    def _deregister_from_monitor(self, instance: SandboxInstance) -> None:
        """Deregister sandbox from ResourceMonitor."""
        try:
            from cohezion.reliability.monitor import get_resource_monitor

            monitor = get_resource_monitor()
            if hasattr(monitor, "deregister_sandbox"):
                monitor.deregister_sandbox(instance.sandbox_id)
        except Exception as e:
            logger.debug(f"Monitor deregistration skipped: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Return current sandbox manager statistics.

        Returns
        -------
        dict
            Active count, memory usage, budget remaining, circuit state.
        """
        return {
            "active_count": len(self._active),
            "allocated_memory_mb": self.allocated_memory_mb,
            "budget_remaining_mb": self.budget_remaining_mb,
            "budget_total_mb": SYSTEM_MEMORY_BUDGET_MB,
            "circuit_state": self._circuit.get_stats(),
            "active_sandboxes": [
                {
                    "id": inst.sandbox_id,
                    "tier": inst.tier.value,
                    "memory_mb": inst.profile.memory_limit_mb,
                    "started_at": inst.started_at,
                }
                for inst in self._active.values()
            ],
        }

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None


def get_sandbox_manager() -> SandboxManager:
    """Get the global SandboxManager instance."""
    return SandboxManager()
