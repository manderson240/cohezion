import sys
import time
from pathlib import Path

import numpy as np
import torch


# Add src to sys.path
sys.path.insert(0, str(Path.cwd() / "src"))

import cohezion_core


print(f"DEBUG: cohezion_core loaded from: {cohezion_core.__file__}")
from cohezion_core import FlumePhysics  # noqa: E402


print(f"DEBUG: FlumePhysics dir: {dir(FlumePhysics)}")

import cohezion.flume.predictor  # noqa: E402


print(f"DEBUG: predictor loaded from: {cohezion.flume.predictor.__file__}")
from cohezion.flume.predictor import TrajectoryPredictor  # noqa: E402


def benchmark_swarm():
    z_dim = 256
    hidden_dim = 512
    steps = 100
    swarm_size = 1000  # Simulating 1000 parallel thoughts

    print(f"Benchmarking SWARM Evolution (size={swarm_size}, steps={steps})...")

    predictor = TrajectoryPredictor(z_dim=z_dim, hidden_dim=hidden_dim)
    # Create swarm of vectors
    swarm_z = torch.randn(swarm_size, z_dim)

    # 1. Warmup Python (Serial Loop)
    # Note: Python implementation processes one by one in a loop or batches if optimized.
    # Our current optimize_with_physics is single-trajectory. We'll wrap it in a loop.
    print("Warming up Python...")
    # Just do 10 to warm up
    for i in range(10):
        _ = predictor.predict_with_physics(swarm_z[i], steps=steps)

    print("Running Python Benchmark (Serial implementation)...")
    start = time.perf_counter()
    # Simulate swarm: Loop through all agents
    # Realistically, Python would try to batch this. Let's assume naive loop first.
    # If we batch the tensor, Torch is fast. But our logic has "if" conditions and state updates.
    # predictor.predict_with_physics handles single tensor.
    # Let's see how fast 1000 independent calls are.
    results_py = []
    for i in range(swarm_size):
        results_py.append(predictor.predict_with_physics(swarm_z[i], steps=steps))
    python_time = time.perf_counter() - start
    print(f"Python Serial Time: {python_time * 1000:.4f}ms")

    # Sync weights
    predictor._sync_to_rust()
    rust_physics = predictor.rust_physics
    print(f"Rust Physics Object: {rust_physics}")
    print(f"Attributes: {dir(rust_physics)}")
    sys.stdout.flush()

    # Prepare inputs (list of numpy arrays)
    # This might be slow for 1000 items, but fine for benchmark setup
    swarm_z_np = [z.numpy() for z in swarm_z]

    print("Running Rust Benchmark (Parallel implementation)...")
    sys.stdout.flush()

    # Call parallel evolution
    start = time.perf_counter()

    # simulate_epochs_batch expects (latent_batch, epochs)
    # Convert list of numpy arrays to a single 2D array for the batch call
    swarm_z_batch = np.stack(swarm_z_np).astype(np.float32)

    _results_rs = rust_physics.simulate_epochs_batch(swarm_z_batch, steps)

    rust_time = time.perf_counter() - start
    print(f"Rust Parallel Time: {rust_time * 1000:.4f}ms")

    speedup = python_time / rust_time
    print(f"Speedup: {speedup:.2f}x")


if __name__ == "__main__":
    benchmark_swarm()
