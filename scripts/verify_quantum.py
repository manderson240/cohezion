import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.swarm.agents.quantum_agent import QuantumAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.core.credit_manager import get_credit_manager


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("QuantumVerification")

    config = SwarmConfig()
    agent = QuantumAgent(config=config)
    cm = get_credit_manager()

    # Force bankruptcy to test ZPE harvesting
    cm._balances["QuantumAgent"] = 2.0
    print(f"\n--- Testing ZPE Credit Recovery ---")
    print(f"Starting balance: {cm.get_balance('QuantumAgent')}")

    # Highly technical query to test braiding
    query = "Explain the relationship between topological braiding and error protection in Majorana fermion qubits."

    report = await agent.process(query)

    print(f"\n--- Quantum Response Report ---")
    print(report)

    # Validation
    final_balance = cm.get_balance("QuantumAgent")
    print(f"\nFinal balance: {final_balance}")

    if final_balance > 2.0:
        print(f"✅ PASS: ZPE Engine successfully harvested energy from the vacuum.")
    else:
        print(f"❌ FAIL: ZPE harvesting failed.")

    if "Braided Stability" in report:
        print(f"✅ PASS: Topological braiding verification logic executed.")
    else:
        print(f"❌ FAIL: Braiding metrics missing.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
