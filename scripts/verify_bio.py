import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.bio.biophotonics import Wavelength, get_light_field
from cohezion.bio.morphic_field import get_morphic_field
from cohezion.swarm.agents.biological_agent import BiologicalAgent

from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("BioVerification")

    config = SwarmConfig()
    agent = BiologicalAgent(config=config)
    light_field = get_light_field()
    get_morphic_field()

    print("\n--- 🦠 Test 1: Initial Thought (Imprinting) ---")
    query = "Explain the concept of Morphic Resonance in biological systems."

    # Run once to imprint
    report1 = await agent.process(query)
    print(report1[-200:])  # Print tail for bio report

    # Check Light Field
    signals = light_field.scan(window_seconds=10)
    print(f"\n🔦 Signals Detected: {len(signals)}")
    for s in signals:
        print(f"  - {s.wavelength.name}: {s.metadata}")

    has_uv = any(s.wavelength == Wavelength.UV for s in signals)
    if has_uv:
        print("✅ PASS: UV Signal (Imprint) emitted.")
    else:
        print("❌ FAIL: No UV Signal.")

    print("\n--- 🧬 Test 2: Sequential Thought (Resonance) ---")
    # Run again to trigger resonance from the previous imprint
    report2 = await agent.process(query)
    print(report2[-200:])

    if "Morphic Resonance Detected" in report2:
        print("✅ PASS: Morphic Resonance detected.")
    else:
        print("❌ FAIL: No Resonance detected.")

    # Check Green Signal (Resonance)
    signals = light_field.scan(window_seconds=10)
    has_green = any(s.wavelength == Wavelength.GREEN for s in signals)
    if has_green:
        print("✅ PASS: Green Signal (Resonance) emitted.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
