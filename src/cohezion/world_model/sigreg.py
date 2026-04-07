"""SIGReg: Sketched-Isotropic-Gaussian Regularizer.

Based on LeWorldModel (Maes et al., 2026, arxiv:2603.19312).
Provably forces high-dimensional latent distributions to match an 
Isotropic Gaussian by testing random 1D projections via Epps-Pulley.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SIGReg(nn.Module):
    """Anti-collapse loss using random unit-norm projections."""

    def __init__(self, embed_dim: int, num_projections: int = 1024):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_projections = num_projections
        
        # Random projections (M x D) - fixed unit vectors
        projections = torch.randn(num_projections, embed_dim)
        projections = F.normalize(projections, p=2, dim=1)
        self.register_buffer("projections", projections)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Compute the SIGReg loss for a batch of embeddings.
        
        Args:
            z: Embeddings of shape (batch_size, embed_dim)
            
        Returns:
            Scalar loss value
        """
        # Batch size
        n = z.size(0)
        if n < 2:
            return torch.tensor(0.0, device=z.device)

        # 1. Project embeddings onto random unit-norm directions (N x M)
        # We want the resulting distribution to be N(0, 1) in every direction
        projected = F.linear(z, self.projections)  # Shape: (batch_size, num_projections)
        
        # 2. Epps-Pulley test statistic (univariate)
        # Efficient implementation using pairwise differences within each projection
        # L = (1/n) sum_{i,j} exp(-0.5 * (x_i - x_j)^2) - sqrt(2) sum_i exp(-0.25 * x_i^2) + 1
        
        # projected: (N, M)
        # Pairwise squared differences for each projection: (N, N, M)
        # We do this projection-wise to save memory
        
        # Vectorized Epps-Pulley across all M projections
        # Term 1: exp(-0.5 * (x_i - x_j)^2)
        dist_sq = (projected.unsqueeze(0) - projected.unsqueeze(1)).pow(2)  # (N, N, M)
        term1 = torch.exp(-0.5 * dist_sq).sum(dim=(0, 1)) / (n * n)  # (M,)
        
        # Term 2: -sqrt(2) * exp(-0.25 * x_i^2)
        term2 = -torch.sqrt(torch.tensor(2.0)) * torch.exp(-0.25 * projected.pow(2)).sum(dim=0) / n  # (M,)
        
        # Sum of test statistics across all projections
        per_projection_loss = term1 + term2 + 1.0
        
        return per_projection_loss.mean()
