"""
Step 15 Integration Tests: VLIW Context Harness Enforcement.

Verifies:
1. Core Rule: Block execution if N_CORES != 1.
2. Timeout Rule: Detect build/sim timeouts (> 300s).
3. Result Accuracy: Harness returns structured performance data.
"""

import pytest

from cohezion.reliability.vliw_context_harness import VLIWContextHarness, VLIWEnvironment


class TestVLIWHarnessEnforcement:
    """Verifies the harness is a strict arbiter of the rules."""

    def test_n_cores_enforcement(self):
        """Step 15.1: Harness must reject non-compliant core counts."""
        env = VLIWEnvironment(n_cores=32)
        harness = VLIWContextHarness(env)

        def mock_builder():
            return []

        with pytest.raises(PermissionError) as exc:
            harness.execute_with_constraints(mock_builder)
        assert "N_CORES must be 1" in str(exc.value)

    def test_successful_harness_execution(self):
        """Step 15.2: Harness must structured report for compliant runs."""
        env = VLIWEnvironment(n_cores=1)
        harness = VLIWContextHarness(env)

        def mock_builder():
            return [{}, {}]  # 2 instructions

        result = harness.execute_with_constraints(mock_builder)

        assert result["status"] == "SUCCESS"
        assert result["instructions"] == 2
        assert "build_time_ms" in result
        assert result["environment"].n_cores == 1

    def test_timeout_detection(self):
        """Step 15.3: Harness must detect build timeouts."""
        env = VLIWEnvironment(n_cores=1, timeout_seconds=0.001)  # Ultra short timeout
        harness = VLIWContextHarness(env)

        def slow_builder():
            import time

            time.sleep(0.01)
            return []

        result = harness.execute_with_constraints(slow_builder)
        assert result["status"] == "TIMEOUT"
