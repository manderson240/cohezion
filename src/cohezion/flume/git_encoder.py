"""
Git FLUME Encoder - Semantic history analysis using latent space trajectories.

Wraps FlumeEncoder to analyze git commit message sequences as continuous
semantic trajectories. Detects "health drift" by calculating the direction
of semantic change over time.
"""

import logging

import torch
import torch.nn.functional as F

from cohezion.flume.autoencoder import FlumeEncoder
from cohezion.swarm.git_health import GitCommit


logger = logging.getLogger(__name__)


class GitEncoder:
    """
    Analyzes git history through the lens of FLUME manifold encoding.
    """

    def __init__(self, encoder: FlumeEncoder | None = None):
        if encoder is None:
            from cohezion.flume.autoencoder import FlumeConfig

            self.encoder = FlumeEncoder(FlumeConfig(z_dim=256))
        else:
            self.encoder = encoder

    def encode_history(self, commits: list[GitCommit]) -> torch.Tensor:
        """
        Encode a sequence of commit messages into a trajectory of z-vectors.

        Args:
            commits: List of GitCommit objects, ordered by time.

        Returns:
            trajectory: (len(commits), 256) tensor of thought vectors.
        """
        if not commits:
            return torch.zeros((0, 256))

        # Reverse to get chronological order if they were newest-first
        chronological = sorted(commits, key=lambda c: c.date)
        messages = [c.message for c in chronological]

        # Batch encode if possible (FlumeEncoder.encode handles list[str])
        z_sequence = self.encoder.encode(messages)
        return z_sequence

    def get_health_direction(self, trajectory: torch.Tensor) -> tuple[torch.Tensor, float]:
        """
        Calculates the semantic vector indicating the "drift" in health.

        Args:
            trajectory: (N, 256) tensor of commit vectors.

        Returns:
            direction: The mean velocity vector in latent space.
            momentum: Scalar indicating how focused the drift is.
        """
        if trajectory.shape[0] < 2:
            return torch.zeros(256), 0.0

        # Calculate velocities (deltas between consecutive thoughts)
        velocities = trajectory[1:] - trajectory[:-1]
        mean_velocity = velocities.mean(dim=0)

        # Calculate momentum (cosine similarity between consecutive velocities)
        if velocities.shape[0] < 2:
            momentum = 1.0  # Only one delta, perfect consistency
        else:
            v_norm = F.normalize(velocities, dim=-1)
            momentum = (v_norm[1:] * v_norm[:-1]).sum(dim=-1).mean().item()

        return mean_velocity, momentum

    def evaluate_drift(self, commits: list[GitCommit], pivot_index: int = -5) -> float:
        """
        Compares the recent history to the older history to detect semantic shift.

        Returns a similarity score [0, 1]. Lower means higher drift (divergence).
        """
        trajectory = self.encode_history(commits)
        if trajectory.shape[0] < abs(pivot_index) * 2:
            return 1.0  # Not enough history to judge drift

        old_mean = trajectory[:pivot_index].mean(dim=0)
        recent_mean = trajectory[pivot_index:].mean(dim=0)

        # Cosine similarity
        sim = F.cosine_similarity(old_mean.unsqueeze(0), recent_mean.unsqueeze(0)).item()
        return sim


if __name__ == "__main__":
    # Smoke test
    ge = GitEncoder()
    mock_commits = [
        GitCommit("1", "A", None, "Initial commit"),
        GitCommit("2", "A", None, "Add core logic"),
        GitCommit("3", "A", None, "Fix minor bug"),
        GitCommit("4", "A", None, "Refactor for clarity"),
    ]
    traj = ge.encode_history(mock_commits)
    print(f"Trajectory shape: {traj.shape}")
    drift = ge.evaluate_drift(mock_commits, pivot_index=-2)
    print(f"Semantic drift similarity: {drift:.4f}")
