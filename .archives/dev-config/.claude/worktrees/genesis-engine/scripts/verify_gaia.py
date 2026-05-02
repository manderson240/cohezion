import asyncio
import logging
import sys
from pathlib import Path

from cohezion.gaia.interface import get_planetary_interface
from cohezion.swarm.agents.gaia_agent import GaiaAgent

from cohezion.swarm.swarm_types import SwarmConfig


# Add src to path
sys.path.append(str(Path.cwd() / "src"))


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("GaiaVerify")

    config = SwarmConfig()
    agent = GaiaAgent(config=config)
    interface = get_planetary_interface()

    print("\n--- 🌍 Test 1: Baseline Vital Signs ---")
    response_1 = await agent.process("Initial health check.")
    print(response_1[-300:])

    if "Vacuum Energy" in response_1:
        print("✅ PASS: Vital Signs Reported.")
    else:
        print("❌ FAIL: No Gaia Report.")

    print("\n--- 🔥 Test 2: Immunity (Overheating) ---")
    # Artificially spike temperature
    interface.request_timestamps = [0] * 120  # Simulate 120 requests in last minute

    response_2 = await agent.process("Stress test.")
    print(response_2[-300:])

    if "Emitted RED signal" in response_2:
        print("✅ PASS: Immune Response Triggered (Red Light).")
    else:
        print("❌ FAIL: No Immune Response.")

    print("\n--- 🌱 Test 3: Parthenogenesis (Creation) ---")
    # Reset temp, Maximize Energy, Minimize Entropy
    interface.request_timestamps = []
    # Mocking psutil logic via interface overrides is hard,
    # so we rely on the VacuumEnergy calculation being naturally high on this unused machine
    # We inject low entropy samples
    import torch

    low_entropy = torch.ones(10)  # Variance = 0
    interface.report_entropy_flux(low_entropy)

    response_3 = await agent.process("Expand universe.")
    print(response_3[-300:])

    if "Parthenogenesis Triggered" in response_3:
        print("✅ PASS: Parthenogenesis Triggered.")
    else:
        print("⚠️ SKIP/FAIL: Parthenogenesis Inhibited (Check Vacuum Energy)")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
