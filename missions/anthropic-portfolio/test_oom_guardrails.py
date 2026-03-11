"""
Step 16 Integration Tests: OOM Guardrail Verification.

Verifies:
1. Profile Validation: Reject profiles > 96GB.
2. Manager Enforcement: Reject simulations that exceed the 90GB total budget.
3. System Safety: Ensure headroom for OS and background services.
"""

import pytest
from cohezion.universe.sandbox_profiles import SandboxProfile, MAX_SYSTEM_MEMORY_MB
from cohezion.universe.sandbox_manager import get_sandbox_manager, SYSTEM_MEMORY_BUDGET_MB

class TestOOMGuardrails:
    """Verifies that the system prevents memory-based lockups."""

    def test_max_profile_limit_enforcement(self):
        """Step 16.1: SandboxProfile must reject requests > 96GB."""
        # This should succeed (90GB)
        p_safe = SandboxProfile(
            memory_limit_mb=90 * 1024,
            cpu_quota_percent=100,
            timeout_seconds=60
        )
        assert p_safe.memory_limit_mb == 92160
        
        # This should fail (97GB)
        with pytest.raises(ValueError) as exc:
            SandboxProfile(
                memory_limit_mb=97 * 1024,
                cpu_quota_percent=100,
                timeout_seconds=60
            )
        # Pydantic 2.x uses internal validation errors, we just check for the limit
        assert "98304" in str(exc.value) # 96 * 1024 = 98304

    @pytest.mark.asyncio
    async def test_manager_budget_enforcement(self):
        """Step 16.2: SandboxManager must reject requests exceeding 90GB total budget."""
        manager = get_sandbox_manager()
        manager.reset() # Clear active sandboxes
        manager = get_sandbox_manager()
        
        # 1. Start a heavy simulation (64GB)
        # We manually inject an instance to avoid full execution
        from cohezion.universe.sandbox_manager import SandboxInstance, SandboxTier
        from cohezion.universe.divergence import DivergenceDetector
        
        p64 = SandboxProfile(memory_limit_mb=64 * 1024, cpu_quota_percent=100, timeout_seconds=60)
        inst = SandboxInstance(
            sandbox_id="heavy_1",
            tier=SandboxTier.HEAVY,
            profile=p64,
            detector=DivergenceDetector()
        )
        manager._active["heavy_1"] = inst
        
        # Budget remaining: 90 - 64 = 26GB
        assert manager.budget_remaining_mb == 26 * 1024
        
        # 2. Attempt to launch another 32GB simulation (Total 96GB > 90GB)
        p32 = SandboxProfile(memory_limit_mb=32 * 1024, cpu_quota_percent=100, timeout_seconds=60)
        
        with pytest.raises(RuntimeError) as exc:
            await manager.run_simulation("print('too big')", profile=p32)
            
        assert "Memory budget exceeded" in str(exc.value)
        assert "92160MB" in str(exc.value) # Verifies the 90GB threshold in the error message
