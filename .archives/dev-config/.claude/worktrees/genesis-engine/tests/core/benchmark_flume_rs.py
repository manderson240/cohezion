import sys
import time
from pathlib import Path

import torch


# Add src to sys.path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.flume.predictor import TrajectoryPredictor


def benchmark():
    z_dim = 256
    hidden_dim = 512
    steps = 500

    predictor = TrajectoryPredictor(z_dim=z_dim, hidden_dim=hidden_dim)
    z = torch.randn(z_dim)

    print(f"Benchmarking Trajectory Physics (steps={steps}, dim={z_dim})...")

    # 1. Warmup Python
    for _ in range(10):
        _ = predictor.predict_with_physics(z, steps=steps)

    start = time.perf_counter()
    for _ in range(100):
        _ = predictor.predict_with_physics(z, steps=steps)
    python_time = (time.perf_counter() - start) / 100
    print(f"Python Average Time: {python_time * 1000:.4f}ms")

    # 2. Rust
    # First sync (ensure cohezion_core is available)
    try:
        import cohezion_core  # noqa: F401
        from cohezion_core import FlumePhysics  # noqa: F401

        print("Rust accelerator active.")
    except ImportError:
        print("Rust accelerator NOT found.")
        return

    # Trigger Rust path
    # (The first call will sync weights)
    start = time.perf_counter()
    for _ in range(100):
        _ = predictor.predict_with_physics(z, steps=steps)
    rust_time = (time.perf_counter() - start) / 100
    print(f"Rust Average Time:   {rust_time * 1000:.4f}ms")

    improvement = python_time / rust_time
    print(f"Speedup: {improvement:.2f}x")


if __name__ == "__main__":
    benchmark()
