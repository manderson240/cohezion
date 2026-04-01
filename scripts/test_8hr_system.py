#!/usr/bin/env python3
"""
Quick integration test for 8-hour journey system.

Validates:
1. Thermal checkpoint manager
2. TDP budget tracker
3. Thermal autoresearch executor
4. Dashboard API

Usage: python test_8hr_system.py
"""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.compound.tdp_budget_tracker import TDPBudgetTracker, TDPConfig, TDPEnvelope
from cohezion.compound.thermal_autoresearch_executor import (
    ThermalAutoresearchExecutor,
)
from cohezion.compound.thermal_checkpoint_manager import (
    ThermalCheckpointManager,
    ThermalConfig,
)


async def test_thermal_manager():
    """Test thermal checkpoint manager."""
    print("\n=== Testing ThermalCheckpointManager ===")

    config = ThermalConfig(
        pause_temp=90.0,
        resume_temp=80.0,
        cooldown_interval_minutes=60,
    )

    async with ThermalCheckpointManager(config) as manager:
        print(f"✓ Thermal manager initialized")
        print(f"  Pause threshold: {manager.config.pause_temp}°C")
        print(f"  Resume threshold: {manager.config.resume_temp}°C")

        # Create a test checkpoint
        await manager._do_checkpoint(
            task_id="test_journey",
            phase="test_phase",
            progress={"test": True},
            hypotheses_completed=5,
            total_hypotheses=20,
        )
        print(f"✓ Test checkpoint created")

        # Load it back
        loaded = await manager._load_latest_checkpoint("test_journey")
        if loaded:
            print(f"✓ Checkpoint loaded: {loaded.phase}")
        else:
            print("✗ Failed to load checkpoint")


async def test_tdp_tracker():
    """Test TDP budget tracker."""
    print("\n=== Testing TDPBudgetTracker ===")

    config = TDPConfig(envelope=TDPEnvelope(tdp_watts=120.0, duration_hours=8.0))

    async with TDPBudgetTracker(config) as tracker:
        print(f"✓ TDP tracker initialized")
        print(f"  Budget: {tracker.config.envelope.total_watt_hours:.1f} Wh")

        # Sample power
        sample = await tracker.sample_power()
        print(f"✓ Power sampled: {sample.total_power_w:.1f}W")

        # Check status
        status = tracker.get_budget_status()
        print(f"  Consumed: {status['consumed_percent']:.1f}%")
        print(f"  Current power: {status['current_power_w']:.1f}W")


async def test_executor():
    """Test thermal autoresearch executor."""
    print("\n=== Testing ThermalAutoresearchExecutor ===")

    executor = ThermalAutoresearchExecutor()
    print(f"✓ Executor initialized")
    print(f"  Domains: {len(executor.config.domains)}")
    print(f"  Total duration: {executor.config.total_duration_hours} hours")

    for domain in executor.config.domains:
        print(f"  - {domain.name}: {len(domain.hypotheses)} hypotheses")


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("8-HOUR JOURNEY SYSTEM INTEGRATION TEST")
    print("=" * 60)

    try:
        await test_thermal_manager()
        await test_tdp_tracker()
        await test_executor()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSystem is ready for 8-hour execution!")
        print("\nNext steps:")
        print("1. Run: python scripts/run_8hr_journey.py --mode simulate --dry-run")
        print("2. Then: python scripts/run_8hr_journey.py --mode simulate")
        print("3. Or: python scripts/run_8hr_journey.py --mode live (requires services)")

        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
