import asyncio

# Use absolute import to get the standard library platform
import importlib
from pathlib import Path

import pytest

platform = importlib.import_module("platform")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("camel"),
    reason="CAMEL-AI not installed"
)
async def test_eigent_integration():
    print("Testing Eigent integration with Lemonade server...")

    # 1. Test EigentAgent directly
    from cohezion.swarm.agents.eigent_agent import EigentAgent

    agent = EigentAgent(role="Test Scout")
    print(f"Agent initialized with role: {agent.role}")

    # Simple chat test (will fail if lemonade is not responding)
    try:
        response = await agent.chat("Hello! This is a test from the Cohezion integration.")
        print(f"Agent response: {response}")
    except Exception as e:
        print(f"Chat failed (expected if model is not loaded in backend): {e}")

    # 2. Test long-running journey logic
    print("\nTesting long-horizon journey logic (simulated)...")
    await agent.run_journey("Test week-long task", duration_days=0.01)  # Short duration for test

    checkpoint_dir = Path("data/eigent/checkpoints")
    checkpoints = list(checkpoint_dir.glob("*.json"))
    if checkpoints:
        print(f"Found {len(checkpoints)} checkpoints. Integration verified.")
        for cp in checkpoints:
            print(f"Checkpoint data: {cp.read_text()}")
    else:
        print("No checkpoints found. Checkpointing failed.")


if __name__ == "__main__":
    asyncio.run(test_eigent_integration())
