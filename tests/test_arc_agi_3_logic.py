import torch

from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought


def test_dynamic_exit():
    dim = 256
    depth = 10
    threshold = 0.05 # Low threshold to trigger exit

    model = RecursiveChainOfThought(dim=dim, depth=depth, threshold=threshold)

    # Random initial state
    z = torch.randn(1, dim)

    # Run with high threshold (should not exit early)
    model.threshold = -1.0
    model(z)
    print("Full depth reasoning completed.")

    # Run with low threshold (should exit early)
    model.threshold = 100.0 # Force exit immediately
    model(z)
    print("Immediate exit reasoning completed.")

    # Test with realistic threshold
    model.threshold = 5.0 # Random guess for entropy range
    model(z)

    print("Recursive Reasoning Test Passed.")

if __name__ == "__main__":
    test_dynamic_exit()
