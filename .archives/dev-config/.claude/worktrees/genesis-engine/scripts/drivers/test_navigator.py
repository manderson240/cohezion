import asyncio

from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder
from cohezion.flume.mnm import ManifoldManager
from cohezion.flume.navigator import FlumeNavigator


async def test_navigator():
    print("Initializing components...")
    config = FlumeConfig(z_dim=256)
    encoder = FlumeEncoder(config)
    manifold_mgr = ManifoldManager(z_dim=256)
    navigator = FlumeNavigator(encoder, manifold_mgr=manifold_mgr)

    start_text = "The emergence of consciousness from quantum fluctuations."
    print(f"\nStart Text: {start_text}")

    print("\nTesting Branching Prediction (Scenario: fractal_nexus)...")
    branches = navigator.predict_branches(start_text, num_branches=2, steps=3, scenario="fractal_nexus")

    for i, branch in enumerate(branches):
        print(f"\nBranch {i + 1}:")
        for j, step in enumerate(branch):
            print(f"  Step {j + 1}: {step}")


if __name__ == "__main__":
    asyncio.run(test_navigator())
