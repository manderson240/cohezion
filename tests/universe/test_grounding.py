import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cohezion.universe.engine import UniverseSimulationEngine


async def test_grounding():
    engine = UniverseSimulationEngine()
    print("Testing Kinetic Manifold Grounding...")

    # Start a journey
    journey = await engine.start_journey(
        agent_name="TestGrounder",
        intent="Audit the kinetic manifold for Anthropic readiness.",
    )

    axiomatic = journey.initial_axiomatic
    print("Physical Projection (Axiomatic 12D):")
    print(f"  Physics (CPU): {axiomatic.physics:.3f}")
    print(f"  Control (Dilation): {axiomatic.control:.3f}")
    print(f"  Field (VRAM): {axiomatic.field:.3f}")
    print(f"  Logic (RAM/Semantic): {axiomatic.logic:.3f}")

    # Since we can't easily fake load here without external tools,
    # we just check that they are not the default 0.5 static values if load exists
    print(f"  Coherence: {axiomatic.coherence_score():.3f}")

    # Stop the monitor to allow clean exit
    from cohezion.reliability.monitor import get_resource_monitor

    await get_resource_monitor().stop()

    assert axiomatic.physics != 0.5 or axiomatic.field != 0.5
    print("Grounding Verified (Telemetry detected).")


if __name__ == "__main__":
    asyncio.run(test_grounding())
