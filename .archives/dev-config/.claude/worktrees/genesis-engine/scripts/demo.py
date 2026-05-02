#!/usr/bin/env python3
"""Cohezion Demo — runs in < 30 seconds, no external dependencies.

Demonstrates:
1. Mass simulation with HIHO coherence convergence
2. Hamiltonian dynamics on FLUME latent space
3. RL environment stepping (Gymnasium FlumeNav-v0)
4. FLUME VAE encode/decode round-trip
5. Circuit breaker state machine

Usage:
    uv run python scripts/demo.py
"""

from __future__ import annotations

import time


def banner(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def demo_mass_sim() -> None:
    """Mini mass simulation with coherence tracking."""
    import numpy as np

    banner("1. Mass Simulation — HIHO Coherence Convergence")

    try:
        from cohezion_core.cohezion_core_rs import FlumePhysics

        from cohezion.mass_sim.agent_factory import AgentFactory
    except ImportError:
        print("  [SKIP] Rust extension not built. Run: cd src/cohezion_core && maturin develop --release")
        return

    z_dim = 256
    hidden = 128
    rng = np.random.default_rng(42)

    # Xavier init navigator weights
    w1 = (rng.standard_normal((hidden, z_dim)) * np.sqrt(2.0 / z_dim)).astype(np.float32)
    b1 = np.zeros(hidden, dtype=np.float32)
    w2 = (rng.standard_normal((z_dim, hidden)) * np.sqrt(2.0 / hidden)).astype(np.float32)
    b2 = np.zeros(z_dim, dtype=np.float32)
    gamma = np.ones(hidden, dtype=np.float32)
    beta = np.zeros(hidden, dtype=np.float32)

    physics = FlumePhysics(w1, b1, w2, b2, gamma, beta, 0.01, 0.1)

    n_agents, epochs, n_universes = 10, 100, 3
    print(f"  Config: {n_agents} agents x {epochs} epochs x {n_universes} universes")

    for u in range(n_universes):
        agents = AgentFactory.create_batch(n_agents, seed=u, z_dim=z_dim)
        t0 = time.perf_counter()
        final = physics.simulate_epochs_navigated(agents, epochs)
        elapsed = time.perf_counter() - t0
        stats = physics.compute_batch_stats(final)
        coh = stats["mean_coherence"]
        pct = stats["pct_within_bounds"]
        marker = "OK" if 0.3 <= coh <= 0.7 else "!!"
        print(f"  Universe {u}: coherence={coh:.3f} ({pct * 100:.0f}% in bounds) [{marker}] [{elapsed * 1000:.0f}ms]")


def demo_hamiltonian() -> None:
    """Hamiltonian dynamics on FLUME space."""
    import numpy as np

    banner("2. Hamiltonian Dynamics — Double-Well Potential")

    from cohezion.physics.hamiltonian import HamiltonianDynamics, PotentialType

    hd = HamiltonianDynamics(PotentialType.DOUBLE_WELL, dt=0.01, temperature=0.005)
    z0 = np.random.default_rng(42).normal(0.5, 0.15, (20, 256)).astype(np.float32)

    trajectory = hd.simulate_with_trajectory(z0, epochs=200, checkpoint_interval=50)

    for epoch, snap in trajectory:
        mean = float(snap.mean())
        std = float(snap.std())
        energy = float(hd.energy(snap).mean())
        print(f"  Epoch {epoch:4d}: mean={mean:.4f}  std={std:.4f}  energy={energy:.6f}")

    print("  Agents converge toward HIHO target (0.5) under potential gradient")


def demo_rl_environment() -> None:
    """RL environment stepping."""
    import gymnasium as gym

    banner("3. RL Environment — FlumeNav-v0")

    import cohezion.rl.environment  # noqa: F401

    env = gym.make("cohezion/FlumeNav-v0")
    obs, info = env.reset(seed=42)
    print(f"  Initial: shape={obs.shape}, coherence={info['coherence']:.3f}")

    total_reward = 0.0
    for step in range(20):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if step % 5 == 0:
            print(f"  Step {step + 1:3d}: reward={reward:.3f}  coherence={info['coherence']:.3f}")
        if terminated or truncated:
            break

    print(f"  Total reward over 20 steps: {total_reward:.2f}")
    env.close()


def demo_flume_vae() -> None:
    """FLUME VAE encode/decode round-trip."""
    import torch

    banner("4. FLUME VAE — Encode/Decode Round-Trip")

    from cohezion.flume.dataset import SyntheticFlumeDataset
    from cohezion.flume.training import FlumeVAETrainer, TrainConfig

    config = TrainConfig(
        epochs=5,
        batch_size=32,
        z_dim=64,
        log_interval=5,
        checkpoint_dir="/tmp/demo_flume",
    )
    trainer = FlumeVAETrainer(config)
    dataset = SyntheticFlumeDataset(n_samples=500, z_dim=64)

    print(f"  Training VAE: {len(dataset)} samples, {config.epochs} epochs, z_dim={config.z_dim}")
    metrics = trainer.train(dataset=dataset)

    first_mse = metrics[0]["mse"]
    final_mse = metrics[-1]["mse"]
    improvement = (first_mse - final_mse) / first_mse * 100
    print(f"  MSE: {first_mse:.4f} -> {final_mse:.4f} ({improvement:.1f}% improvement)")

    # Round-trip test
    sample = dataset[0].unsqueeze(0)
    recon, _mu, _logvar = trainer._forward(sample)
    recon_error = torch.nn.functional.mse_loss(recon, sample).item()
    print(f"  Single-sample reconstruction error: {recon_error:.4f}")


def demo_circuit_breaker() -> None:
    """Circuit breaker state machine."""
    banner("5. Circuit Breaker — State Machine")

    from cohezion.reliability import CircuitBreaker

    cb = CircuitBreaker(name="demo", failure_threshold=3, recovery_timeout=0.5)

    states = []
    # Normal operation
    cb.record_success()
    states.append(f"After success: {cb.state.value}")

    # Fail to threshold
    for _i in range(3):
        cb.record_failure()
    states.append(f"After 3 failures: {cb.state.value}")

    # Wait for recovery
    import time

    time.sleep(0.6)
    states.append(f"After timeout: {cb.state.value}")

    # Recovery
    cb.record_success()
    states.append(f"After recovery success: {cb.state.value}")

    for s in states:
        print(f"  {s}")


def main() -> None:
    print("Cohezion Demo")
    print("=============")
    t0 = time.perf_counter()

    demo_mass_sim()
    demo_hamiltonian()
    demo_rl_environment()
    demo_flume_vae()
    demo_circuit_breaker()

    elapsed = time.perf_counter() - t0
    banner(f"Demo Complete — {elapsed:.1f}s total")


if __name__ == "__main__":
    main()
