import torch
import torch.nn as nn


class ARCAxiomaticProjector(nn.Module):
    """
    Projects 256D ARC latents into the 12D Cohezion Axiomatic Manifold.

    12D Vector Components:
    - [0:3] Spatial: Object count, average size, grid density.
    - [3]   Time: Normalized step count in interaction.
    - [4:12] Brane: Color distribution (8 primary colors excluding BG/Black).
    """

    def __init__(self, latent_dim=256):
        super().__init__()
        self.projection = nn.Sequential(nn.Linear(latent_dim, 64), nn.ReLU(), nn.Linear(64, 12))

    def forward(self, z, step_normalized=0.0):
        """
        Args:
            z: 256D latent tensor
            step_normalized: current step / max steps
        Returns:
            12D axiomatic state vector
        """
        axioms = self.projection(z)
        # Force time axiom
        axioms[:, 3] = step_normalized
        return axioms


def compute_hiho_stability(axioms):
    """
    Calculates the HIHO stability score (0.0 to 1.0).
    Max stability occurs at exactly 0.5 coherence overlap.
    """
    # Simple proxy: how close is the mean of axioms to 0.5?
    coherence = torch.mean(torch.sigmoid(axioms))
    stability = 1.0 - 2.0 * torch.abs(coherence - 0.5)
    return stability.item()


if __name__ == "__main__":
    projector = ARCAxiomaticProjector()
    dummy_z = torch.randn(1, 256)
    axioms = projector(dummy_z, step_normalized=0.1)
    stability = compute_hiho_stability(axioms)
    print(f"12D Axiomatic State:\n{axioms.detach().numpy()}")
    print(f"HIHO Stability Score: {stability:.4f}")
