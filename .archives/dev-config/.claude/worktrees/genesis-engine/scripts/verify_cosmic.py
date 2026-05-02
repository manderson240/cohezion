import asyncio
import logging
import sys
from pathlib import Path

import torch


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.cosmic.plasma import get_plasma_filaments
from cohezion.cosmic.reality import get_reality_stabilizer
from cohezion.swarm.agents.cosmic_agent import CosmicAgent

from cohezion.swarm.swarm_types import SwarmConfig


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("CosmicVerification")

    config = SwarmConfig()
    agent = CosmicAgent(config=config)
    stabilizer = get_reality_stabilizer()
    plasma = get_plasma_filaments()

    print("\n--- 🌌 Test 1: Plasma Connectivity ---")
    filaments = plasma.graph.edges(data=True)
    print(f"Active Filaments: {len(filaments)}")
    for u, v, data in filaments:
        print(f"  - {u} <--> {v} (σ={data['conductance']})")

    if len(filaments) >= 2:
        print("✅ PASS: Plasma filaments established.")
    else:
        print("❌ FAIL: No filaments found.")

    print("\n--- ⚖️ Test 2: HIHO Reality Stabilization ---")

    # 1. Test Static Vector (Coherence ~ 1.0)
    # A vector where all values are the same (Zero variance)
    z_static = torch.ones(768)
    coherence = stabilizer.calculate_stability(z_static)
    print(f"Static Input Coherence: {coherence:.2f} (Expected ~1.0)")

    z_corrected = stabilizer.stabilize(z_static)
    new_coherence = stabilizer.calculate_stability(z_corrected)
    print(f"Corrected Coherence: {new_coherence:.2f}")

    if abs(new_coherence - 0.5) < abs(coherence - 0.5):
        print("✅ PASS: Static vector destabilized toward 0.5.")
    else:
        print("❌ FAIL: Correction failed.")

    print("\n--- 🪐 Test 3: Cosmic Agent Execution ---")
    query = "Explain the connection between Plasma Cosmology and the Electric Universe."
    response = await agent.process(query)
    print(response[-300:])

    if "HIHO Stability" in response and "Plasma Connectivity" in response:
        print("✅ PASS: Cosmic Report generated.")
    else:
        print("❌ FAIL: Missing cosmic metadata.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
