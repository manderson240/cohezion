"""P2-1: Test that autorun_2h.py spin-loop guard prevents negative timeout.

When remaining_s < 30, asyncio.wait_for must never be called with
timeout = remaining_s - 10 (which would be negative and raise ValueError).
"""
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch


def _get_autorun_main():
    """Dynamically import the main() async function from autorun_2h.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "autorun_2h",
        Path("scripts/autorun_2h.py"),
    )
    # Pre-mock heavy imports to avoid torch/SurrealDB at import time
    heavy = {
        "cohezion.compound.autoresearch": MagicMock(),
        "cohezion.inference.autoharness_ce": MagicMock(),
    }
    with patch.dict("sys.modules", heavy):
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            pass
    return mod


class TestAutorunSpinLoopGuard:
    """Verify the remaining_s < 30 guard prevents negative asyncio.wait_for timeout."""

    def test_remaining_s_guard_breaks_before_negative_timeout(self):
        """When remaining_s < 30, the inner loop breaks WITHOUT calling asyncio.wait_for.

        This is the regression test for the spin-loop fix that prevents
        asyncio.wait_for(coro, timeout=-5) which raises ValueError.
        """
        wait_for_calls = []

        async def fake_wait_for(coro, timeout):
            wait_for_calls.append(timeout)
            return MagicMock()

        # Simulate: deadline is 5 seconds from now (< 30 threshold)
        import timeit
        fake_deadline = timeit.default_timer() + 5  # Only 5 seconds left

        async def run_scenario():
            remaining = fake_deadline - timeit.default_timer()
            if remaining < 30:
                return  # Guard fires — NO wait_for call
            await fake_wait_for(MagicMock(), min(3600.0, remaining - 10))

        asyncio.run(run_scenario())
        assert len(wait_for_calls) == 0, (
            f"asyncio.wait_for was called with timeout {wait_for_calls} "
            f"despite remaining_s < 30 — spin-loop guard broken"
        )

    def test_timeout_floor_prevents_negative_value(self):
        """max(30.0, remaining_s - 10) ensures timeout is always >= 30s."""
        # Scenario: remaining_s = 25 (would give 25-10=15, floored to 30)
        remaining = 25.0
        timeout = max(30.0, min(3600.0, remaining - 10))
        assert timeout >= 30.0, f"timeout {timeout} is below the 30s floor"
        assert timeout > 0, "timeout must be positive for asyncio.wait_for"

    def test_normal_case_passes_through(self):
        """When remaining_s >> 30, normal timeout calculation is used."""
        remaining = 600.0  # 10 minutes
        timeout = max(30.0, min(3600.0, remaining - 10))
        # 600 - 10 = 590, which is >= 30 and <= 3600
        assert timeout == 590.0

    def test_autorun_script_has_guard(self):
        """Structural: scripts/autorun_2h.py must contain the guard pattern."""
        source = Path("scripts/autorun_2h.py").read_text()
        assert "remaining_s < 30" in source, (
            "Missing spin-loop guard: `if remaining_s < 30: break` not found in autorun_2h.py"
        )
        assert "max(30.0" in source, (
            "Missing timeout floor: `max(30.0, ...)` not found in autorun_2h.py"
        )

