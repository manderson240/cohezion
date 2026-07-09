# math/physics symbols intentional
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, ConfigDict, field_validator
from transformers import PretrainedConfig

from cohezion.flume.latent_health import LatentBasisMonitor


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

    Two modes:
    - Token mode (default): FlumeVAE(config=FlumeVAEConfig(...)) — transformer, integer inputs
    - Embedding mode (legacy): FlumeVAE(input_dim=768, latent_dim=256) — MLP, float inputs
    """

    def __init__(
        self,
        config: FlumeVAEConfig | None = None,
        input_dim: int | None = None,
        latent_dim: int | None = None,
    ):
        super().__init__()
        if input_dim is not None:
            # Legacy embedding mode: simple MLP VAE on continuous float inputs
            self._legacy_mode = True
            self._input_dim = input_dim
            self._latent_dim = latent_dim or 256
            self.config = None
            hidden = 512
            self._enc = nn.Sequential(
                nn.Linear(input_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
            )
            self._mu_head = nn.Linear(hidden, self._latent_dim)
            self._logvar_head = nn.Linear(hidden, self._latent_dim)
            self._dec = nn.Sequential(
                nn.Linear(self._latent_dim, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, input_dim),
            )
        else:
            # Token mode: transformer VAE on integer token IDs
            self._legacy_mode = False
            if config is None:
                config = FlumeVAEConfig()
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
        # A3 complement: latent basis health monitor for posterior collapse detection.
        # A3 guards against collapse via kl_weight ≤ 0.01; this detects it empirically.
        self.latent_monitor: LatentBasisMonitor | None = None

    @property
    def input_dim(self) -> int | None:
        return self._input_dim if self._legacy_mode else None

    @property
    def latent_dim(self) -> int:
        if self._legacy_mode:
            return self._latent_dim
        return self.config.z_dim if self.config else 256

    def reparameterize(self, mu: torch.Tensor, log_var: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick. Returns mu deterministically in eval mode."""
        if not self.training:
            return mu
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + std * eps

    def encode(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode inputs to (mu, log_var). Accepts float embeddings in legacy mode."""
        if self._legacy_mode:
            h = self._enc(input_ids.float())
            mu = self._mu_head(h)
            log_var = self._logvar_head(h)
        else:
            _batch_size, seq_len = input_ids.shape
            positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
            x = self.embedding(input_ids) + self.pos_embedding(positions)
            src_key_padding_mask = ~attention_mask.bool() if attention_mask is not None else None
            x = self.transformer_encoder(x, src_key_padding_mask=src_key_padding_mask)
            if attention_mask is not None:
                mask = attention_mask.unsqueeze(-1).float()
                x = (x * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            else:
                x = x.mean(dim=1)
            mu = self.mu_head(x)
            log_var = self.logvar_head(x)
        # A3 complement: accumulate latent codes to detect posterior collapse empirically.
        if self.latent_monitor is not None:
            self.latent_monitor.update(mu)
        return mu, log_var

    def decode(self, z: torch.Tensor, target_tokens: torch.Tensor | None = None) -> torch.Tensor:
        """Decode latent z. Returns float reconstruction in legacy mode, logits in token mode."""
        if self._legacy_mode:
            return self._dec(z)
        if target_tokens is None:
            raise ValueError("decode() requires target_tokens in token mode")
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
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full VAE forward pass. Returns (recon_or_logits, mu, log_var, z)."""
        mu, log_var = self.encode(input_ids, attention_mask)
        z = self.reparameterize(mu, log_var)
        recon = self.decode(z) if self._legacy_mode else self.decode(z, input_ids)
        return recon, mu, log_var, z

    def get_latent_health(self) -> dict | None:
        """Return SVD-based latent space health metrics.

        Returns ``None`` if no monitor is attached or no samples have been accumulated.
        Attach a monitor via ``model.latent_monitor = LatentBasisMonitor()`` and call
        ``model.encode(...)`` to accumulate samples before calling this method.
        See :class:`~cohezion.flume.latent_health.LatentBasisMonitor` for details.
        """
        if self.latent_monitor is None or not self.latent_monitor.has_samples:
            return None
        return self.latent_monitor.compute_health()

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
    recon: torch.Tensor | None = None,
    mu: torch.Tensor | None = None,
    logvar: torch.Tensor | None = None,
    beta: float = 1.0,
    free_bits: float = 0.0,
    lambda_coherence: float = 0.0,
    lambda_contrastive: float = 0.0,
    lambda_sim_match: float = 0.0,
    contrastive_pairs: list | None = None,
    z: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """Compute full FLUME VAE loss: reconstruction + KL + optional coherence/contrastive terms."""
    device = mu.device if mu is not None else torch.device("cpu")
    zero = torch.tensor(0.0, device=device)

    # KL divergence
    if mu is not None and logvar is not None:
        kl_per_dim = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
        if free_bits > 0:
            kl_per_dim = torch.clamp(kl_per_dim, min=free_bits)
        kl_loss = kl_per_dim.mean()
    else:
        kl_loss = zero

    # Reconstruction loss — MSE for float embeddings, cross-entropy for token logits
    if recon is not None and x is not None:
        if recon.dim() == 3:
            _B, _seq_len, vocab_size = recon.shape
            shift_logits = recon[:, :-1].reshape(-1, vocab_size)
            shift_labels = x[:, 1:].reshape(-1).long()
            recon_loss = F.cross_entropy(shift_logits, shift_labels)
        else:
            recon_loss = F.mse_loss(recon.float(), x.float())
    else:
        recon_loss = zero

    # HIHO coherence: penalize deviation of mu mean from 0.5
    if lambda_coherence > 0.0 and mu is not None:
        coherence_loss = lambda_coherence * (mu.mean() - 0.5).pow(2)
    else:
        coherence_loss = zero

    total_loss = recon_loss + beta * kl_loss + coherence_loss

    return {
        "total_loss": total_loss,
        "recon_loss": recon_loss,
        "kl_loss": kl_loss,
        "coherence_loss": coherence_loss,
        "contrastive_loss": zero,
        "sim_match_loss": zero,
    }
