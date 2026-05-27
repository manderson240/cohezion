# math/physics: T, F, B, P, S, G, R, A — single-letter conventions
"""
Glass Box Debate Simulation.

This simulation demonstrates Gateway 5 (Observable Intelligence) capabilities
by visualizing the semantic trajectory of a debate between two agents.
It produces a 'thought-space' plot showing how positions evolve.

Author: Cohezion Agentic Team (Gemini 3 Pro)
Date: 2026-01-18
"""

import asyncio
import logging

import matplotlib.pyplot as plt
import numpy as np
import torch

from cohezion.flume.autoencoder import FlumeEncoder


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_simulation():
    logger.info("Initializing Glass Box Debate...")
    from cohezion.flume.autoencoder import FlumeConfig

    encoder = FlumeEncoder(FlumeConfig(z_dim=256))

    # 1. Define Debate Topic & Initial Positions
    topic = "AI Regulation"
    agent_a_initial = "AI innovation should be unrestricted to maximize progress."
    agent_b_initial = "AI development must be strictly controlled to ensure safety."

    logger.info(f"Topic: {topic}")
    logger.info(f"Agent A: {agent_a_initial}")
    logger.info(f"Agent B: {agent_b_initial}")

    # 2. Simulate Debate Turns (Thought Vectors)
    # In a real system, agents would generate text. Here we interpolate/simulate evolution.

    z_a = encoder.encode(agent_a_initial)
    z_b = encoder.encode(agent_b_initial)

    trajectory_a = [z_a]
    trajectory_b = [z_b]

    turns = 5
    for i in range(turns):
        # Simulate convergence/divergence
        # Agent A moves slightly towards B (compromise) but maintains core
        # Agent B holds firm

        # Calculate direction B -> A (Agent A sees B's point)
        direction_ba = encoder.semantic_direction(z_b, z_a)

        # Agent A updates: moves 10% towards B
        z_a = encoder.semantic_add(z_a, direction_ba, scale=-0.1)

        # Agent B updates: moves 5% towards A
        direction_ab = encoder.semantic_direction(z_a, z_b)
        z_b = encoder.semantic_add(z_b, direction_ab, scale=-0.05)

        trajectory_a.append(z_a)
        trajectory_b.append(z_b)

        logger.info(f"Turn {i + 1}: Positions updated.")

    # 3. Visualize
    logger.info("Generating Thought-Space Visualization...")
    output_path = "debate_trajectory.png"
    visualize_debate(trajectory_a, trajectory_b, output_path)
    logger.info(f"Visualization saved to {output_path}")


def visualize_debate(traj_a: list[torch.Tensor], traj_b: list[torch.Tensor], filepath: str):
    """Plot trajectories projected to 2D using PCA (simulated via SVD for now)."""

    # Combine data for projection info
    data_a = torch.stack(traj_a).detach().cpu().squeeze().numpy()
    data_b = torch.stack(traj_b).detach().cpu().squeeze().numpy()
    combined = np.concatenate([data_a, data_b], axis=0)

    # Simple PCA via SVD
    # Center data
    mean = np.mean(combined, axis=0)
    centered = combined - mean
    _U, _S, Vt = np.linalg.svd(centered)

    # Project to top 2 components
    pcs = Vt[:2, :]
    proj_a = (data_a - mean) @ pcs.T
    proj_b = (data_b - mean) @ pcs.T

    # Plot
    plt.figure(figsize=(10, 8))
    plt.plot(proj_a[:, 0], proj_a[:, 1], "bo-", label="Agent A (Innovation)", alpha=0.7)
    plt.plot(proj_b[:, 0], proj_b[:, 1], "ro-", label="Agent B (Safety)", alpha=0.7)

    # Mark start/end
    plt.scatter(proj_a[0, 0], proj_a[0, 1], c="blue", s=200, marker="^", label="Start A")
    plt.scatter(proj_b[0, 0], proj_b[0, 1], c="red", s=200, marker="^", label="Start B")
    plt.scatter(proj_a[-1, 0], proj_a[-1, 1], c="blue", s=200, marker="x", label="End A")
    plt.scatter(proj_b[-1, 0], proj_b[-1, 1], c="red", s=200, marker="x", label="End B")

    plt.title("Semantic Trajectory of AI Safety Debate (Projected)")
    plt.xlabel("PC1 (Principal Semantic Dimension 1)")
    plt.ylabel("PC2 (Principal Semantic Dimension 2)")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()

    plt.savefig(filepath)
    plt.close()


if __name__ == "__main__":
    asyncio.run(run_simulation())
