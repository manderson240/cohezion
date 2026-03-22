import asyncio

from cohezion.swarm.agents.gaia_agent import GaiaAgent


async def test_narration_flow():
    agent = GaiaAgent()
    # Increase DB timeout for test robustness
    agent._db.timeout = 30
    print("🚀 Running inference to test Journey Narration...")
    res = await agent.process("Perform a rapid homeostasis check on the current latent manifold.")
    print(f"Agent Thought: {str(res)[:100]}...")

    # Print all attributes for debugging
    print(f"DEBUG: Response Type: {type(res)}")
    print(f"DEBUG: Attributes: {dir(res)}")
    print(f"DEBUG: Narration: {getattr(res, 'narration', 'MISSING')[:100]}...")
    print(f"DEBUG: Phi Score: {getattr(res, 'phi_score', 'MISSING')}")
    print(f"DEBUG: Alignment Score: {getattr(res, 'alignment_score', 'MISSING')}")

    # Check if narration exists in the response object
    if hasattr(res, "narration") and res.narration:
        print(f"✅ Narration Generated: {res.narration[:50]}...")
    else:
        print(f"❌ Narration issue. Value: {getattr(res, 'narration', None)!r}")

    if hasattr(res, "alignment_score"):
        print(f"✅ Alignment Audit: {res.alignment_score:.2f}")
    else:
        print(f"❌ Alignment issue. Value: {getattr(res, 'alignment_score', None)!r}")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(test_narration_flow())
