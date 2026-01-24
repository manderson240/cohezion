import asyncio
import logging
from cohezion.swarm.agents.lab_agent import LabAgent

logging.basicConfig(level=logging.INFO)

async def test_recursive_discovery():
    agent = LabAgent()

    # Simulate a successful verified report
    success_report = """
    ✅ VERIFIED: Mechanistic interpretability of toroidal thought vectors.
    We found that the 'stability' dimension corresponds to the Jacobian of the transition matrix.
    Neurons in the hidden layer 4 are responsible for coherence detection.

    This is a key finding for AI safety.
    """

    print("🧪 Testing recursive discovery logic...")
    await agent._process_findings("Test seed", success_report)

    print("📈 Checking if system was updated...")
    # These are handled by agent._system_updates which is called in a real cycle,
    # but we can call it manually here to verify.
    await agent._system_updates(success_report)

    print("📧 Testing email delivery...")
    # This should send the simulated discovery
    await agent.send_summary_report()

    print("✅ Smoke test complete!")

if __name__ == "__main__":
    asyncio.run(test_recursive_discovery())
