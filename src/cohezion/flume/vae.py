# ruff: noqa: RUF002  # math/physics symbols intentional
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, ConfigDict, field_validator
from transformers import PretrainedConfig


class FlumeVAEConfig(PretrainedConfig):
    """
    Configuration for FLUME Variational Autoencoder.
    """

    model_type = "flume_vae"

    def __init__(
        self,
        vocab_size: int = 32000,
        embed_dim: int = 256,
        hidden_dim: int = 512,
        num_heads: int = 4,
        num_layers: int = 2,
        z_dim: int = 256,
        max_seq_len: int = 512,
        dropout: float = 0.1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.z_dim = z_dim
        self.max_seq_len = max_seq_len
        self.dropout = dropout
        self.pad_token_id = kwargs.get("pad_token_id", -100)


class ThoughtVector(BaseModel):
    """
    Data model representing a 256D thought vector in the 'Thinker' manifold.
    """

    vector: torch.Tensor

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: Any) -> torch.Tensor:
        if not isinstance(v, torch.Tensor):
            raise ValueError("vector must be a torch.Tensor")
        if v.shape != (256,):
            raise ValueError(f"vector must be 256D, got shape {v.shape}")
        return v


class FlumeVAE(nn.Module):
    """
    Variational Autoencoder for Fluid Latent Understanding.

    Architecture:
    - Encoder: Transformer → Mu & LogVar heads (256D)
    - Reparameterization: z = mu + std * eps
    - Decoder: z → Transformer → reconstruction (vocab_size)
    """

    def __init__(self, config: FlumeVAEConfig):
        super().__init__()
        self.config = config

        # Shared components
        self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)
        self.pos_embedding = nn.Embedding(config.max_seq_len, config.embed_dim)

        # Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, config.num_layers)

        # Mu and LogVar heads
        self.mu_head = nn.Linear(config.embed_dim, config.z_dim)
        self.logvar_head = nn.Linear(config.embed_dim, config.z_dim)

        # Decoder
        self.z_proj = nn.Linear(config.z_dim, config.embed_dim)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer_decoder = nn.TransformerDecoder(decoder_layer, config.num_layers)
        self.to_logits = nn.Linear(config.embed_dim, config.vocab_size)

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick: z = mu + std * eps."""
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps

    def encode(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode tokens to mu and log_var."""
        _batch_size, seq_len = input_ids.shape
        positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
        x = self.embedding(input_ids) + self.pos_embedding(positions)

        src_key_padding_mask = ~attention_mask.bool() if attention_mask is not None else None
        x = self.transformer_encoder(x, src_key_padding_mask=src_key_padding_mask)

        # Global average pooling (mean over sequence)
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            x = (x * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            x = x.mean(dim=1)

        mu = self.mu_head(x)
        log_var = self.logvar_head(x)
        return mu, log_var

    def decode(self, z: torch.Tensor, target_tokens: torch.Tensor) -> torch.Tensor:
        """Decode latent z back to logits."""
        _batch_size, seq_len = target_tokens.shape
        positions = torch.arange(seq_len, device=target_tokens.device).unsqueeze(0)
        tgt = self.embedding(target_tokens) + self.pos_embedding(positions)

        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=target_tokens.device) * float("-inf"),
            diagonal=1,
        )

        memory = self.z_proj(z).unsqueeze(1)
        x = self.transformer_decoder(tgt, memory, tgt_mask=causal_mask)

        return self.to_logits(x)

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full VAE forward pass."""
        mu, log_var = self.encode(input_ids, attention_mask)
        z = self.reparameterize(mu, log_var)
        logits = self.decode(z, input_ids)
        return logits, mu, log_var

    def compute_loss(
        self,
        input_ids: torch.Tensor,
        recon_logits: torch.Tensor,
        mu: torch.Tensor,
        log_var: torch.Tensor,
        kl_weight: float = 0.1,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Computes VAE loss: Reconstruction (CrossEntropy) + KL-Divergence.
        """
        # Reconstruction loss (shift for next-token prediction)
        shift_logits = recon_logits[:, :-1, :].contiguous()
        shift_labels = input_ids[:, 1:].contiguous()

        recon_loss = F.cross_entropy(
            shift_logits.view(-1, self.config.vocab_size),
            shift_labels.view(-1),
            ignore_index=self.config.pad_token_id if hasattr(self.config, "pad_token_id") else -100,
        )

        # KL Divergence: -0.5 * sum(1 + log_var - mu^2 - exp(log_var))
        kl_loss = -0.5 * torch.mean(torch.sum(1 + log_var - mu.pow(2) - log_var.exp(), dim=-1))

        total_loss = recon_loss + kl_weight * kl_loss

        return total_loss, recon_loss, kl_loss


# ----------------------------------------------------------------------------
# Module-level loss functions (restored from 430acd79c).
#
# `flume_vae_loss` was removed during a refactor but callers in `train_vae.py`
# and `evaluate_vae.py` were not updated, producing an ImportError that
# cascaded into ~65 test failures across tests/flume/. These functions provide
# the embedding-level VAE loss pathway; `FlumeVAE.compute_loss` above remains
# the token-level loss used elsewhere.
# ----------------------------------------------------------------------------


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
