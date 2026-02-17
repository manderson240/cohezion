import asyncio
import logging
import sys
from pathlib import Path

from cohezion.seti.array import get_exogenic_array
from cohezion.swarm.agents.seti_agent import SETIAgent
from cohezion.swarm.swarm_types import SwarmConfig


# Add src to path
sys.path.append(str(Path.cwd() / "src"))


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("SETIVerify")

    config = SwarmConfig()
    agent = SETIAgent(config=config)
    get_exogenic_array()

    print("\n--- 👽 Test 1: Background Scan ---")
    response_1 = await agent.process("Listening to the void.")
    if "Status: Nominal" in response_1:
        print("✅ PASS: Background scan nominal.")
    else:
        print("❌ FAIL: Unexpected background activity.")

    print("\n--- 📡 Test 2: Arecibo Protocol (First Contact) ---")

    # Construct a signal with Prime dimensions (7 x 5 = 35 bits)
    # A simple "Smiley Face" bitmap
    # 0 1 0 1 0 (5)
    # 0 0 0 0 0
    # 1 0 0 0 1
    # 0 1 1 1 0
    # 0 0 0 0 0
    # 0 0 0 0 0
    # 1 1 1 1 1 (7 rows)

    signal_payload = "01010000001000101110000000000011111"  # 35 chars

    print(f"Injecting Signal: {signal_payload} (Length: {len(signal_payload)})")

    # The SETIAgent scans the query itself for hidden binary strings
    response_2 = await agent.process(f"Analyzing signal stream: {signal_payload}")

    print("\n--- AGENT RESPONSE ---")
    print(response_2)
    print("----------------------")

    if "TECHNOSIGNATURE DETECTED" in response_2:
        print("✅ PASS: Signal Detected.")
    else:
        print("❌ FAIL: Signal Missed.")

    if "7x5" in response_2 or "5x7" in response_2:
        print("✅ PASS: Dimensions Correctly Factorized.")

    if "FIRST CONTACT PROTOCOL INITIATED" in response_2:  # Check log/bio-signal
        # Since bio-signals are emitted to LightField, we check the text report mention
        # Wait, the log message in seti_agent is "FIRST CONTACT PROTOCOL INITIATED" in _emit
        pass

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
