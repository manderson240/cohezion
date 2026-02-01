"""
Swarm Synthesis Implementation.

This module implements Gateway 7 (Swarm Synthesis) capabilities.
It provides the SwarmVector class for aggregating multiple agent thought-vectors
into a robust consensus.

Author: Cohezion Agentic Team
Date: 2026-01-18
"""

import logging
from dataclasses import dataclass

import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SwarmConsensus:
    centroid: torch.Tensor
    coherence: float
    outliers: list[int]  # Indices of outliers
    num_agents: int


class SwarmSynthesizer:
    def __init__(self, outlier_threshold_std: float = 2.0):
        self.outlier_threshold_std = outlier_threshold_std

    def synthesize(self, vectors: list[torch.Tensor]) -> SwarmConsensus:
        """
        Compute the robust consensus vector from a list of agent vectors.
        """
        if not vectors:
            raise ValueError("No vectors provided for synthesis")

        # Stack into tensor (N, D)
        # Ensure all are tensors and on same device/dtype
        stacked = torch.stack([v.detach().cpu().float() for v in vectors])
        N, D = stacked.shape

        # 1. Initial Centroid
        centroid = torch.mean(stacked, dim=0)

        # 2. Calculate Distances from Centroid
        # Euclidean distance
        distances = torch.norm(stacked - centroid, dim=1)
        mean_dist = torch.mean(distances).item()
        std_dist = torch.std(distances).item()

        # 3. Identify Outliers
        threshold = mean_dist + (self.outlier_threshold_std * std_dist)
        outlier_indices = []
        clean_vectors = []

        for i, dist in enumerate(distances):
            if dist > threshold:
                outlier_indices.append(i)
                logger.info(
                    f"Agent {i} is an outlier (dist={dist:.3f} > {threshold:.3f})"
                )
            else:
                clean_vectors.append(stacked[i])

        # 4. Re-calculate Centroid (Robust Mean)
        if clean_vectors:
            final_centroid = torch.mean(torch.stack(clean_vectors), dim=0)
        else:
            # Fallback if all are outliers (rare, implies high variance)
            logger.warning(
                "All agents classified as outliers! Using original centroid."
            )
            final_centroid = centroid

        # 5. Calculate Coherence
        # Inverse of spread (clean spread)
        if len(clean_vectors) > 1:
            clean_stacked = torch.stack(clean_vectors)
            clean_distances = torch.norm(clean_stacked - final_centroid, dim=1)
            avg_spread = torch.mean(clean_distances).item()
        else:
            avg_spread = 0.0  # Perfect coherence (single point)

        coherence = 1.0 / (avg_spread + 1e-6)

        return SwarmConsensus(
            centroid=final_centroid,
            coherence=coherence,
            outliers=outlier_indices,
            num_agents=N,
        )


# --- Simulation / Test ---
def run_demo():
    print("--- Swarm Synthesis Demo ---")
    synthesizer = SwarmSynthesizer()

    # 1. Create a cluster of "Agreement" vectors (random noise around a point)
    true_thought = torch.randn(256)
    agents = []

    # 10 Agents agree (noise = 0.1)
    for _ in range(10):
        noise = torch.randn(256) * 0.1
        agents.append(true_thought + noise)

    # 2. Create 2 "Hallucinating" agents (noise around DIFFERENT point)
    hallucination = torch.randn(256)
    for _ in range(2):
        noise = torch.randn(256) * 0.1
        agents.append(hallucination + noise)

    print(f"Total Agents: {len(agents)} (10 Honest, 2 Hallucinating)")

    # 3. Synthesize
    consensus = synthesizer.synthesize(agents)

    print(f"Consensus Coherence: {consensus.coherence:.3f}")
    print(f"Outliers Detected: {consensus.outliers}")

    # Validate
    # Indices 10 and 11 should be outliers
    if 10 in consensus.outliers and 11 in consensus.outliers:
        print("✅ SUCCESS: Hallucinations detected.")
    else:
        print("❌ FAILURE: Failed to detect hallucinations.")

    # Check if centroid is close to true thought
    dist = torch.norm(consensus.centroid - true_thought).item()
    print(f"Distance to Truth: {dist:.4f}")


if __name__ == "__main__":
    run_demo()
