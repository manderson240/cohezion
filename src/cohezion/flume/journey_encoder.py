"""JourneyToFlumeEncoder — compress an AgentTrajectory into the FLUME latent.

A Journey through the 12D manifold is a variable-length sequence of per-step
physics observations. We project each step's features (12D state + coherence +
spin + tempic + reward = 16 dims) into the FLUME embedding space, run a small
Transformer encoder to aggregate temporal context, then project to
(mu, log_var) in the 256D latent.

This is a parallel encoder to FlumeVAE's token encoder — they share the 256D
thought space. A token-encoded thought and a journey-encoded thought are
comparable in that space (enabling retrieval, clustering, and generation
seeded by journey embeddings in later phases).

The Journey latent can be:
  - Used as the `z` seed for FlumeVAE.decode to generate token artifacts that
    describe the journey (Phase 4 will use this for training data generation).
  - Compared across journeys via cosine similarity — the Mycelium registry
    clusters journeys in Phase 5.
  - Serialized as a 256D thought vector for vault/SurrealDB persistence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
from torch import Tensor

from cohezion.universe.llm_training_bridge import AgentTrajectory


logger = logging.getLogger(__name__)


# Per-step feature count: 12D state + coherence + spin_coherence + tempic_field + reward.
STEP_FEATURE_DIM = 16


def _trajectory_to_tensor(
    trajectory: AgentTrajectory,
    max_seq_len: int,
    pad_value: float = 0.5,
) -> tuple[Tensor, Tensor]:
    """Convert an AgentTrajectory to a padded (T, STEP_FEATURE_DIM) tensor + mask.

    pad_value defaults to 0.5 (HIHO baseline) so padding is a "neutral" state
    and doesn't bias the encoder toward zero.
    """
    steps = trajectory.steps[:max_seq_len]
    features = torch.full((max_seq_len, STEP_FEATURE_DIM), pad_value, dtype=torch.float32)
    mask = torch.zeros(max_seq_len, dtype=torch.bool)
    for i, step in enumerate(steps):
        state_12d = torch.tensor(step.state_12d, dtype=torch.float32)
        features[i, :12] = state_12d
        features[i, 12] = step.coherence
        features[i, 13] = step.spin_coherence
        features[i, 14] = step.tempic_field
        features[i, 15] = step.reward
        mask[i] = True
    return features, mask


@dataclass
class JourneyEncoderConfig:
    """Configuration for the JourneyToFlumeEncoder."""

    embed_dim: int = 256  # matches FlumeVAE.config.embed_dim
    z_dim: int = 256  # matches FlumeVAE.config.z_dim
    num_heads: int = 4
    num_layers: int = 2
    ff_dim: int = 512
    dropout: float = 0.1
    max_seq_len: int = 512


class JourneyToFlumeEncoder(nn.Module):
    """Maps an AgentTrajectory → (mu, log_var) in the 256D FLUME latent space.

    Architecture mirrors FlumeVAE's encoder but accepts continuous step features
    instead of token ids:

        per-step features (16D) → Linear → embed_dim
        + learned positional embedding
        → TransformerEncoder (mean-pooled over valid steps)
        → (mu_head, logvar_head) → z_dim
    """

    def __init__(self, config: JourneyEncoderConfig | None = None) -> None:
        super().__init__()
        self.config = config or JourneyEncoderConfig()

        self.input_proj = nn.Linear(STEP_FEATURE_DIM, self.config.embed_dim)
        self.pos_embedding = nn.Embedding(self.config.max_seq_len, self.config.embed_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.config.embed_dim,
            nhead=self.config.num_heads,
            dim_feedforward=self.config.ff_dim,
            dropout=self.config.dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, self.config.num_layers)

        self.mu_head = nn.Linear(self.config.embed_dim, self.config.z_dim)
        self.logvar_head = nn.Linear(self.config.embed_dim, self.config.z_dim)

        # Reconstruct back to step-feature space, for VAE training.
        self.decoder_proj = nn.Linear(self.config.z_dim, self.config.embed_dim)
        decoder_layer = nn.TransformerEncoderLayer(
            d_model=self.config.embed_dim,
            nhead=self.config.num_heads,
            dim_feedforward=self.config.ff_dim,
            dropout=self.config.dropout,
            batch_first=True,
        )
        self.decoder_transformer = nn.TransformerEncoder(decoder_layer, self.config.num_layers)
        self.output_proj = nn.Linear(self.config.embed_dim, STEP_FEATURE_DIM)

    def encode_batch(self, features: Tensor, mask: Tensor) -> tuple[Tensor, Tensor]:
        """Run the encoder on a batch of padded sequences.

        Parameters
        ----------
        features : Tensor of shape (B, T, STEP_FEATURE_DIM)
        mask : Tensor of shape (B, T) bool — True where valid.

        Returns
        -------
        (mu, log_var) each of shape (B, z_dim)
        """
        B, T, _ = features.shape
        positions = torch.arange(T, device=features.device).unsqueeze(0).expand(B, T)
        x = self.input_proj(features) + self.pos_embedding(positions)

        # src_key_padding_mask expects True at padded positions.
        pad_mask = ~mask
        x = self.transformer(x, src_key_padding_mask=pad_mask)

        # Masked mean pool over valid steps.
        mask_f = mask.unsqueeze(-1).float()
        pooled = (x * mask_f).sum(dim=1) / mask_f.sum(dim=1).clamp(min=1)

        mu = self.mu_head(pooled)
        log_var = self.logvar_head(pooled)
        return mu, log_var

    def reparameterize(self, mu: Tensor, log_var: Tensor) -> Tensor:
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps

    def decode(self, z: Tensor, seq_len: int) -> Tensor:
        """Decode z back into a (B, seq_len, STEP_FEATURE_DIM) sequence."""
        B = z.size(0)
        memory = self.decoder_proj(z).unsqueeze(1).expand(B, seq_len, -1).contiguous()
        positions = torch.arange(seq_len, device=z.device).unsqueeze(0).expand(B, seq_len)
        pos_emb = self.pos_embedding(positions)
        x = self.decoder_transformer(memory + pos_emb)
        return self.output_proj(x)

    def forward(
        self,
        features: Tensor,
        mask: Tensor,
    ) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        """Encode, sample z, decode back. Returns (recon, mu, log_var, z)."""
        mu, log_var = self.encode_batch(features, mask)
        z = self.reparameterize(mu, log_var)
        recon = self.decode(z, features.size(1))
        return recon, mu, log_var, z

    def encode_trajectory(self, trajectory: AgentTrajectory) -> tuple[Tensor, Tensor]:
        """Convenience: encode a single trajectory to (mu, log_var)."""
        features, mask = _trajectory_to_tensor(trajectory, self.config.max_seq_len)
        features = features.unsqueeze(0)
        mask = mask.unsqueeze(0)
        with torch.no_grad():
            mu, log_var = self.encode_batch(features, mask)
        return mu.squeeze(0), log_var.squeeze(0)


def compute_journey_vae_loss(
    recon: Tensor,
    target: Tensor,
    mask: Tensor,
    mu: Tensor,
    log_var: Tensor,
    kl_weight: float = 0.01,
) -> tuple[Tensor, Tensor, Tensor]:
    """Compute MSE reconstruction + KL divergence losses.

    Reconstruction is only scored on valid (unpadded) positions.
    """
    mask_f = mask.unsqueeze(-1).float()
    squared_error = ((recon - target) ** 2) * mask_f
    valid = mask_f.sum().clamp(min=1.0)
    recon_loss = squared_error.sum() / (valid * recon.size(-1))
    kl_loss = -0.5 * torch.mean(torch.sum(1 + log_var - mu.pow(2) - log_var.exp(), dim=-1))
    total = recon_loss + kl_weight * kl_loss
    return total, recon_loss, kl_loss


def save_checkpoint(
    encoder: JourneyToFlumeEncoder,
    path: Path | str,
    metadata: dict | None = None,
) -> Path:
    """Save encoder weights + config to disk."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state_dict": encoder.state_dict(),
        "config": encoder.config.__dict__,
        "metadata": metadata or {},
    }
    torch.save(payload, target)
    return target


def load_checkpoint(path: Path | str) -> JourneyToFlumeEncoder:
    """Load a JourneyToFlumeEncoder from a checkpoint file."""
    payload = torch.load(path, map_location="cpu", weights_only=False)
    config = JourneyEncoderConfig(**payload["config"])
    encoder = JourneyToFlumeEncoder(config)
    encoder.load_state_dict(payload["state_dict"])
    return encoder


__all__ = [
    "STEP_FEATURE_DIM",
    "JourneyEncoderConfig",
    "JourneyToFlumeEncoder",
    "compute_journey_vae_loss",
    "load_checkpoint",
    "save_checkpoint",
]
