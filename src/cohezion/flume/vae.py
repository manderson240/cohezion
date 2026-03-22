"""FLUME VAE v2 — Semantic latent space from pre-trained embeddings.

Architecture:
  Encoder: 768 → 512 → 512 → 384 → mu(256), logvar(256)
  Decoder: 256 → 384 → 512 → 512 → 768

Loss: L_recon + β·L_KL (with free-bits) + λ_align·L_contrastive + λ_coh·L_coherence
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812


class FlumeVAE(nn.Module):
    """Variational autoencoder for semantic embedding compression.

    Takes pre-trained 768D embeddings (e.g., nomic-embed-text) and learns a
    structured 256D latent space where distances are semantically meaningful.
    """

    def __init__(
        self,
        input_dim: int = 768,
        latent_dim: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Encoder: input_dim → 512 → 512 → 384
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 384),
            nn.LayerNorm(384),
            nn.GELU(),
        )

        # Latent heads
        self.mu_head = nn.Linear(384, latent_dim)
        self.logvar_head = nn.Linear(384, latent_dim)

        # Decoder: latent_dim → 384 → 512 → 512 → input_dim
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 384),
            nn.LayerNorm(384),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(384, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Linear(512, input_dim),
        )

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode input to (mu, logvar)."""
        h = self.encoder(x)
        return self.mu_head(h), self.logvar_head(h)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent vector to reconstruction."""
        return self.decoder(z)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Sample z using reparameterization trick. In eval mode, return mu."""
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full forward pass: encode → reparameterize → decode.

        Returns (reconstruction, mu, logvar, z).
        """
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z)
        return recon, mu, logvar, z


def info_nce_loss(
    z: torch.Tensor,
    pairs: list[tuple[int, int]] | None = None,
    temperature: float = 0.07,
) -> torch.Tensor:
    """InfoNCE contrastive loss over known paraphrase pairs.

    For each anchor, the paired sample is the positive and all others are negatives.
    """
    if not pairs:
        return torch.tensor(0.0, device=z.device, requires_grad=True)

    # Normalize embeddings
    z_norm = F.normalize(z, dim=1)
    losses = []

    for anchor_idx, positive_idx in pairs:
        if anchor_idx >= z.shape[0] or positive_idx >= z.shape[0]:
            continue
        anchor = z_norm[anchor_idx]
        positive = z_norm[positive_idx]

        # Similarity of anchor with all others
        sims = z_norm @ anchor / temperature
        # Positive similarity
        pos_sim = (anchor @ positive) / temperature

        # InfoNCE: -log(exp(pos) / sum(exp(all)))
        log_sum_exp = torch.logsumexp(sims, dim=0)
        losses.append(log_sum_exp - pos_sim)

    if not losses:
        return torch.tensor(0.0, device=z.device, requires_grad=True)

    return torch.stack(losses).mean()


def batch_similarity_matching_loss(
    x: torch.Tensor,
    mu: torch.Tensor,
) -> torch.Tensor:
    """Similarity matching loss: penalize differences in batch pairwise cosine similarity.

    Directly optimizes Spearman ρ between input and latent pairwise similarities.
    Computed over normalized vectors in both spaces.
    """
    x_norm = F.normalize(x, dim=1)
    mu_norm = F.normalize(mu, dim=1)

    # Batch pairwise cosine similarities
    input_sims = x_norm @ x_norm.T  # (B, B)
    latent_sims = mu_norm @ mu_norm.T  # (B, B)

    # Upper triangle (exclude diagonal) — soft MSE between sim matrices
    n = x.shape[0]
    triu_mask = torch.triu(torch.ones(n, n, device=x.device), diagonal=1).bool()
    input_flat = input_sims[triu_mask]
    latent_flat = latent_sims[triu_mask]

    return F.mse_loss(latent_flat, input_flat)


def flume_vae_loss(
    x: torch.Tensor,
    recon: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    *,
    beta: float = 0.1,
    free_bits: float = 0.125,
    lambda_coherence: float = 0.01,
    lambda_contrastive: float = 0.0,
    lambda_sim_match: float = 0.0,
    contrastive_pairs: list[tuple[int, int]] | None = None,
    z: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """Compute FLUME VAE loss with KL annealing, free-bits, and contrastive loss.

    Returns dict with individual loss components and total.
    """
    # Reconstruction: cosine similarity loss (better for normalized embeddings)
    # MSE on normalized vectors can be weak; cosine similarity directly optimizes
    # what we measure at evaluation time
    x_norm = F.normalize(x, dim=1)
    recon_norm = F.normalize(recon, dim=1)
    cos_sim = (x_norm * recon_norm).sum(dim=1).mean()
    recon_loss = 1.0 - cos_sim  # 0 when perfect, 1 when orthogonal

    # KL divergence per dimension with free-bits
    kl_per_dim = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
    # Free-bits: dimensions below threshold contribute 0 to loss (no gradient)
    if free_bits > 0:
        kl_per_dim = torch.where(kl_per_dim > free_bits, kl_per_dim, torch.zeros_like(kl_per_dim))
    kl_loss = kl_per_dim.mean()

    # HIHO coherence: per-sample mean(mu) should be near 0.5
    sample_means = mu.mean(dim=1)  # (batch,)
    coherence_loss = ((sample_means - 0.5) ** 2).mean()

    # Contrastive loss (InfoNCE)
    contrastive_loss = torch.tensor(0.0, device=x.device)
    if lambda_contrastive > 0 and contrastive_pairs and z is not None:
        contrastive_loss = info_nce_loss(z, contrastive_pairs)

    # Batch similarity matching: latent pairwise sims → input pairwise sims
    sim_match_loss = torch.tensor(0.0, device=x.device)
    if lambda_sim_match > 0:
        sim_match_loss = batch_similarity_matching_loss(x, mu)

    total = (
        recon_loss
        + beta * kl_loss
        + lambda_coherence * coherence_loss
        + lambda_contrastive * contrastive_loss
        + lambda_sim_match * sim_match_loss
    )

    return {
        "total_loss": total,
        "recon_loss": recon_loss,
        "kl_loss": kl_loss,
        "coherence_loss": coherence_loss,
        "contrastive_loss": contrastive_loss,
        "sim_match_loss": sim_match_loss,
    }
