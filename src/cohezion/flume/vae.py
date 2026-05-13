from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812
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

    Two construction modes:
    1. ``FlumeVAE(config)`` — transformer-based, operates on token IDs.
       ``encode(input_ids)`` → ``(mu, log_var)``
       ``forward(input_ids)`` → ``(logits, mu, log_var)``

    2. ``FlumeVAE(input_dim=D, latent_dim=L)`` — MLP-based, operates on float vectors.
       ``encode(x)`` → ``(mu, logvar)``
       ``decode(z)`` → reconstruction
       ``forward(x)`` → ``(recon, mu, logvar, z)``
    """

    def __init__(
        self,
        config: FlumeVAEConfig | None = None,
        *,
        input_dim: int | None = None,
        latent_dim: int | None = None,
        hidden_dim: int = 1024,
    ):
        super().__init__()

        if config is not None:
            self._mode = "transformer"
            self.config = config

            self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)
            self.pos_embedding = nn.Embedding(config.max_seq_len, config.embed_dim)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=config.embed_dim,
                nhead=config.num_heads,
                dim_feedforward=config.hidden_dim,
                dropout=config.dropout,
                batch_first=True,
            )
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, config.num_layers)
            self.mu_head = nn.Linear(config.embed_dim, config.z_dim)
            self.logvar_head = nn.Linear(config.embed_dim, config.z_dim)
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

        elif input_dim is not None and latent_dim is not None:
            self._mode = "mlp"
            self._input_dim = input_dim
            self._latent_dim = latent_dim
            self.enc_hidden = nn.Linear(input_dim, hidden_dim)
            self.enc_mu = nn.Linear(hidden_dim, latent_dim)
            self.enc_logvar = nn.Linear(hidden_dim, latent_dim)
            self.dec_hidden = nn.Linear(latent_dim, hidden_dim)
            self.dec_out = nn.Linear(hidden_dim, input_dim)

        else:
            raise ValueError("Provide either config or (input_dim, latent_dim)")

    @property
    def input_dim(self) -> int:
        if self._mode == "mlp":
            return self._input_dim
        return self.config.embed_dim

    @property
    def latent_dim(self) -> int:
        if self._mode == "mlp":
            return self._latent_dim
        return self.config.z_dim

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick: z = mu + std*eps (train) or mu (eval)."""
        if not self.training:
            return mu
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps

    def encode(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode input to (mu, log_var).

        MLP mode: x is float (batch, input_dim).
        Transformer mode: x is integer token IDs (batch, seq_len).
        """
        if self._mode == "mlp":
            h = torch.relu(self.enc_hidden(x))
            return self.enc_mu(h), self.enc_logvar(h)

        # Transformer mode
        input_ids = x
        _batch_size, seq_len = input_ids.shape
        positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
        h = self.embedding(input_ids) + self.pos_embedding(positions)
        src_key_padding_mask = ~attention_mask.bool() if attention_mask is not None else None
        h = self.transformer_encoder(h, src_key_padding_mask=src_key_padding_mask)
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            h = (h * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            h = h.mean(dim=1)
        return self.mu_head(h), self.logvar_head(h)

    def decode(self, z: torch.Tensor, target_tokens: torch.Tensor | None = None) -> torch.Tensor:
        """Decode latent z.

        MLP mode: returns (batch, input_dim) reconstruction.
        Transformer mode: returns (batch, seq_len, vocab_size) logits; target_tokens required.
        """
        if self._mode == "mlp":
            h = torch.relu(self.dec_hidden(z))
            return self.dec_out(h)

        if target_tokens is None:
            raise ValueError("target_tokens required in transformer mode")
        _batch_size, seq_len = target_tokens.shape
        positions = torch.arange(seq_len, device=target_tokens.device).unsqueeze(0)
        tgt = self.embedding(target_tokens) + self.pos_embedding(positions)
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=target_tokens.device) * float("-inf"),
            diagonal=1,
        )
        memory = self.z_proj(z).unsqueeze(1)
        out = self.transformer_decoder(tgt, memory, tgt_mask=causal_mask)
        return self.to_logits(out)

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> tuple:
        """Full VAE forward pass.

        MLP mode returns (recon, mu, logvar, z).
        Transformer mode returns (logits, mu, log_var).
        """
        if self._mode == "mlp":
            mu, logvar = self.encode(x)
            z = self.reparameterize(mu, logvar)
            recon = self.decode(z)
            return recon, mu, logvar, z

        mu, log_var = self.encode(x, attention_mask)
        z = self.reparameterize(mu, log_var)
        logits = self.decode(z, x)
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


def flume_vae_loss(
    x: torch.Tensor,
    recon: torch.Tensor,
    mu: torch.Tensor,
    logvar: torch.Tensor,
    beta: float = 0.1,
    free_bits: float = 0.0,
    lambda_coherence: float = 0.0,
    lambda_contrastive: float = 0.0,
    lambda_sim_match: float = 0.0,
    contrastive_pairs: list | None = None,
    z: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """MLP VAE loss: MSE reconstruction + KL divergence + optional HIHO coherence.

    Args:
        x: Original input (batch, input_dim).
        recon: Reconstructed input (batch, input_dim).
        mu: Encoder mean (batch, latent_dim).
        logvar: Encoder log-variance (batch, latent_dim).
        beta: KL weight (beta-VAE).
        free_bits: Minimum KL per dimension (nats) — clamps away posterior collapse.
        lambda_coherence: Weight for HIHO coherence loss (penalises mean(mu) ≠ 0.5).

    Returns:
        Dict with ``recon_loss``, ``kl_loss``, ``coherence_loss``, ``total_loss``.
    """
    recon_loss = F.mse_loss(recon, x, reduction="mean")

    kl_per_dim = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
    if free_bits > 0.0:
        kl_per_dim = kl_per_dim.clamp(min=free_bits)
    kl_loss = kl_per_dim.sum(dim=-1).mean()

    coherence_loss = torch.tensor(0.0, device=x.device)
    if lambda_coherence > 0.0:
        coherence_loss = (mu.mean(dim=-1) - 0.5).pow(2).mean()

    total_loss = recon_loss + beta * kl_loss + lambda_coherence * coherence_loss

    return {
        "recon_loss": recon_loss,
        "kl_loss": kl_loss,
        "coherence_loss": coherence_loss,
        "contrastive_loss": torch.tensor(0.0, device=x.device),
        "sim_match_loss": torch.tensor(0.0, device=x.device),
        "total_loss": total_loss,
    }
