# ruff: noqa: E402, N806, RUF002  # math/physics symbols intentional
"""FLUME Phase 2 TemporalEncoder — Transformer over trajectory step sequences.

Encodes variable-length sequences of compound execution steps into a 256D
latent representation, enabling interpolation between strategies, novel
trajectory sampling, and latent-space navigation for agent guidance.

Architecture:
  Input: [B, T, 29]  (batch × time × step_dim)
    → Linear(step_dim → d_model) + positional encoding
    → TransformerEncoder (n_layers=2, n_heads=4, d_model=128)
    → Attention pooling (learnable query)
    → mu(256), logvar(256)
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)

import torch
import torch.nn as nn


class TemporalEncoder(nn.Module):
    """Transformer encoder for compound execution trajectory sequences.

    Parameters
    ----------
    step_dim : int
        Dimension of each step vector (default 29: 12 traj + 12 metrics + 5 op_type).
    d_model : int
        Transformer hidden dimension (default 128).
    latent_dim : int
        VAE latent dimension — output size of mu and logvar (default 256).
    n_heads : int
        Number of attention heads (default 4).
    n_layers : int
        Number of Transformer encoder layers (default 2).
    dropout : float
        Dropout probability (default 0.1).
    max_seq_len : int
        Maximum sequence length for positional encoding (default 512).
    """

    def __init__(
        self,
        step_dim: int = 29,
        d_model: int = 128,
        latent_dim: int = 256,
        n_heads: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        max_seq_len: int = 512,
    ) -> None:
        super().__init__()
        self.step_dim = step_dim
        self.d_model = d_model
        self.latent_dim = latent_dim

        # Step projection
        self.step_proj = nn.Sequential(
            nn.Linear(step_dim, d_model),
            nn.LayerNorm(d_model),
        )

        # Sinusoidal positional encoding (fixed, not learned)
        self.register_buffer("pos_enc", self._build_pos_enc(max_seq_len, d_model), persistent=False)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,  # Pre-norm for stability
        )
        # enable_nested_tensor=False: pre-norm disables it anyway; suppress warning
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers, enable_nested_tensor=False
        )

        # Attention pooling: single learnable query collapses [B, T, d] → [B, d]
        self.attn_pool_query = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
        self.attn_pool = nn.MultiheadAttention(
            embed_dim=d_model,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )

        # Variational heads
        self.mu_head = nn.Linear(d_model, latent_dim)
        self.logvar_head = nn.Linear(d_model, latent_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    @staticmethod
    def _build_pos_enc(max_len: int, d_model: int) -> torch.Tensor:
        """Build sinusoidal positional encoding table [max_len, d_model]."""
        pos = torch.arange(max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div[: d_model // 2])
        return pe  # [max_len, d_model]

    def encode(
        self,
        x: torch.Tensor,
        padding_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode a batch of step sequences to (mu, logvar).

        Parameters
        ----------
        x : Tensor [B, T, step_dim]
            Batch of trajectory step sequences.
        padding_mask : BoolTensor [B, T], optional
            True = position is padding (ignored). False = valid step.

        Returns
        -------
        mu : Tensor [B, latent_dim]
        logvar : Tensor [B, latent_dim]
        """
        B, T, _ = x.shape

        # Project steps and add positional encoding
        h = self.step_proj(x)  # [B, T, d_model]
        h = h + self.pos_enc[:T].unsqueeze(0)  # broadcast over batch

        # Transformer encoder (padding_mask: True = ignore)
        h = self.transformer(h, src_key_padding_mask=padding_mask)  # [B, T, d_model]

        # Attention pooling: query [1,1,d] → [B,1,d] → [B,d]
        query = self.attn_pool_query.expand(B, -1, -1)  # [B, 1, d_model]
        pooled, _ = self.attn_pool(
            query,
            h,
            h,
            key_padding_mask=padding_mask,
        )
        pooled = pooled.squeeze(1)  # [B, d_model]

        mu = self.mu_head(pooled)  # [B, latent_dim]
        logvar = self.logvar_head(pooled)  # [B, latent_dim]
        return mu, logvar

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick: z = mu + eps * std."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(
        self,
        x: torch.Tensor,
        padding_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Full forward pass: x → (z, mu, logvar).

        At inference/eval time uses mu directly (no sampling noise).
        """
        mu, logvar = self.encode(x, padding_mask=padding_mask)
        z = self.reparameterize(mu, logvar) if self.training else mu
        return z, mu, logvar


class TemporalDecoder(nn.Module):
    """Transformer decoder that reconstructs trajectory step sequences from z.

    Uses teacher-forcing during training: the target sequence (shifted right by
    one position) is fed as the decoder input so the model learns to predict
    the next step given all previous steps and the latent context z.

    Parameters
    ----------
    step_dim : int
        Dimension of each step vector (default 29).
    d_model : int
        Transformer hidden dimension (default 128).
    latent_dim : int
        VAE latent dimension — size of input z (default 256).
    n_heads : int
        Number of attention heads (default 4).
    n_layers : int
        Number of Transformer decoder layers (default 2).
    dropout : float
        Dropout probability (default 0.1).
    max_seq_len : int
        Maximum sequence length for positional encoding (default 512).
    """

    def __init__(
        self,
        step_dim: int = 29,
        d_model: int = 128,
        latent_dim: int = 256,
        n_heads: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        max_seq_len: int = 512,
    ) -> None:
        super().__init__()
        self.step_dim = step_dim
        self.d_model = d_model
        self.latent_dim = latent_dim

        # Project latent z → d_model memory token [B, 1, d_model]
        self.latent_proj = nn.Linear(latent_dim, d_model)

        # Step input projection (target steps → d_model)
        self.step_proj = nn.Sequential(
            nn.Linear(step_dim, d_model),
            nn.LayerNorm(d_model),
        )

        # Sinusoidal positional encoding (shared with encoder pattern)
        self.register_buffer(
            "pos_enc", TemporalEncoder._build_pos_enc(max_seq_len, d_model), persistent=False
        )

        # Transformer decoder (causal self-attention + cross-attention to z)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerDecoder(decoder_layer, num_layers=n_layers)

        # Output projection back to step space
        self.out_proj = nn.Linear(d_model, step_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    @staticmethod
    def _causal_mask(seq_len: int, device: torch.device) -> torch.Tensor:
        """Upper-triangular mask: True = ignore (future positions)."""
        return torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1).bool()

    def decode(
        self,
        z: torch.Tensor,
        target: torch.Tensor,
    ) -> torch.Tensor:
        """Decode latent z into reconstructed step sequence.

        Uses teacher-forcing: target is the ground-truth sequence fed as
        decoder input (standard VAE training setup).

        Parameters
        ----------
        z : Tensor [B, latent_dim]
            Latent vector from encoder.
        target : Tensor [B, T, step_dim]
            Ground-truth step sequence (decoder input during training).

        Returns
        -------
        Tensor [B, T, step_dim]
            Reconstructed step sequence.
        """
        _B, T, _ = target.shape

        # Memory: expand z → [B, 1, d_model] as the encoder memory
        memory = self.latent_proj(z).unsqueeze(1)  # [B, 1, d_model]

        # Embed target steps + positional encoding
        tgt = self.step_proj(target)  # [B, T, d_model]
        tgt = tgt + self.pos_enc[:T].unsqueeze(0)

        # Causal mask prevents attending to future steps
        causal_mask = self._causal_mask(T, z.device)

        # Transformer decoder: tgt attends causally to itself + to z (memory)
        out = self.transformer(tgt, memory, tgt_mask=causal_mask)  # [B, T, d_model]

        return self.out_proj(out)  # [B, T, step_dim]

    def forward(self, z: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Alias for decode() for nn.Module convention."""
        return self.decode(z, target)


class TemporalVAELoader:
    """Production loader for a trained TemporalVAE checkpoint.

    Loads encoder weights from a checkpoint produced by scripts/train_temporal_vae.py
    and provides a simple encode_sequence() interface for JourneyTracker integration.

    Parameters
    ----------
    model_path : Path, optional
        Path to checkpoint file. Defaults to DEFAULT_MODEL_PATH.
    device : str
        Torch device string (default "cpu").
    """

    DEFAULT_MODEL_PATH = Path("data/flume/checkpoints_v2/temporal_vae_best.pt")

    def __init__(
        self,
        model_path: Path | None = None,
        device: str = "cpu",
    ) -> None:
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.device = device
        self._encoder: TemporalEncoder | None = None
        self.enabled = False

        self._load()

    def _load(self) -> None:
        """Load encoder from checkpoint. Silently disables on any failure."""
        try:
            if not self.model_path.exists():
                logger.debug("TemporalVAE checkpoint not found: %s", self.model_path)
                return

            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=True)
            config = checkpoint.get("config", {})
            enc = TemporalEncoder(
                step_dim=config.get("step_dim", 29),
                d_model=config.get("d_model", 128),
                latent_dim=config.get("latent_dim", 256),
                n_heads=config.get("n_heads", 4),
                n_layers=config.get("n_layers", 2),
                max_seq_len=config.get("max_seq_len", 512),
            )
            # Filter out pos_enc — it's non-persistent (deterministic sinusoidal, not learned)
            state_dict = {
                k: v for k, v in checkpoint["encoder_state_dict"].items() if k != "pos_enc"
            }
            enc.load_state_dict(state_dict, strict=False)
            enc.to(self.device)
            enc.eval()
            self._encoder = enc
            self.enabled = True
            metrics = checkpoint.get("metrics", {})
            logger.info(
                "Loaded TemporalVAE encoder (epoch=%d, recon=%.4f, kl=%.4f)",
                checkpoint.get("epoch", 0),
                metrics.get("recon", 0),
                metrics.get("kl", 0),
            )
        except Exception as e:
            logger.warning("Failed to load TemporalVAE checkpoint: %s", e)
            self._encoder = None
            self.enabled = False

    def encode_sequence(self, steps: torch.Tensor) -> np.ndarray:
        """Encode a step sequence tensor to a normalized 256D vector.

        Parameters
        ----------
        steps : Tensor [T, step_dim]
            Sequence of step vectors.

        Returns
        -------
        np.ndarray [256]
            Unit-normalized latent vector, or zeros if disabled.
        """
        if not self.enabled or self._encoder is None:
            return np.zeros(256, dtype=np.float32)

        try:
            with torch.no_grad():
                x = steps.float().unsqueeze(0).to(self.device)  # [1, T, step_dim]
                mu, _ = self._encoder.encode(x)
                vec = mu.squeeze(0).cpu().numpy().astype(np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec /= norm
                return vec
        except Exception as e:
            logger.debug("TemporalVAELoader encode failed: %s", e)
            return np.zeros(256, dtype=np.float32)
