"""FLUME VAE Encoder for production semantic embeddings.

Wraps the trained FLUME VAE encoder to generate real semantic embeddings
for cache similarity matching. Replaces deterministic hash-based embeddings
with learned 256D latent representations.

Features:
- Load pre-trained VAE encoder from checkpoint
- Generate 256D semantic embeddings from text
- Support fallback to hash-based embeddings if VAE unavailable
- Deterministic encoding for reproducibility
- GPU support with CPU fallback
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np


try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


if TORCH_AVAILABLE:

    class _CheckpointSequentialEncoder(nn.Module):
        """Checkpoint-shaped encoder trunk.

        Mirrors cohezion.flume.training's VAETrainer.encoder —
        Linear(in→hidden), ReLU, Linear(hidden→out), ReLU — so training
        checkpoint state dicts (keys "0.weight"/"2.weight") load directly,
        with all dims derived from the artifact at load time.
        """

        def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, output_dim),
                nn.ReLU(),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.layers(x)
else:

    class _CheckpointSequentialEncoder:  # type: ignore[no-redef]
        # Inert no-torch stub; mirrors the nn.Module surface used above so
        # type checkers see one consistent protocol for both branches.
        layers: Any

        def __call__(self, x: Any) -> Any: ...

        def load_state_dict(self, state_dict: Any) -> Any: ...

        def to(self, device: Any) -> _CheckpointSequentialEncoder: ...

        def eval(self) -> _CheckpointSequentialEncoder: ...


class FlumeVAEEncoder:
    """Production VAE encoder for semantic embeddings."""

    # Anchored to the repo root (this file is src/cohezion/flume/vae_encoder.py,
    # so parents[3] is the checkout) — a CWD-relative default silently degraded
    # to the hash fallback whenever the daemon ran from another directory.
    # ep20 is the canonical full-scale artifact: encoder 256→512→512, mu→256.
    # (ep2 is a 64→128→128 toy run and ep21_distilled consumes raw 768-dim
    # nomic embeddings — neither matches the hash-256 → mu-256 contract here.)
    DEFAULT_MODEL_PATH = (
        Path(__file__).resolve().parents[3] / "data" / "flume" / "checkpoints" / "flume_vae_ep20.pt"
    )
    EMBEDDING_DIM = 256

    def __init__(
        self,
        model_path: Path | None = None,
        device: str = "cpu",
        fallback_to_hash: bool = True,
    ):
        """Initialize VAE encoder.

        Args:
            model_path: Path to VAE checkpoint (default: ep50.pt)
            device: Device to load model on ("cpu" or "cuda")
            fallback_to_hash: If True, use hash embeddings if VAE load fails
        """
        self.device = device
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.fallback_to_hash = fallback_to_hash
        self.encoder: _CheckpointSequentialEncoder | None = None
        self.mu_head: nn.Linear | None = None
        self.enabled = False

        if TORCH_AVAILABLE:
            self._load_encoder()
        elif not fallback_to_hash:
            logger.warning("PyTorch not available and fallback disabled")

    def _load_encoder(self) -> None:
        """Load encoder from checkpoint."""
        try:
            if not self.model_path.exists():
                logger.warning(f"Model path not found: {self.model_path}")
                return

            # Load checkpoint — weights_only=True prevents arbitrary code execution
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=True)

            # Extract encoder and mu_head
            encoder_state = checkpoint.get("encoder")
            mu_state = checkpoint.get("mu_head")

            if encoder_state is None or mu_state is None:
                logger.warning("Encoder or mu_head not found in checkpoint")
                return

            # Create and load encoder
            # The checkpoint stores an nn.Sequential (keys "0.weight", "2.weight", ...):
            # Linear(input→hidden), activation, Linear(hidden→hidden). Derive both
            # dims from the artifact so any checkpoint generation loads correctly.
            first_weight = encoder_state.get("0.weight")
            if first_weight is not None:
                ckpt_input_dim = first_weight.shape[1]
                ckpt_hidden_dim = first_weight.shape[0]
            else:
                ckpt_input_dim, ckpt_hidden_dim = self.EMBEDDING_DIM, 512
            middle_weight = encoder_state.get("2.weight")
            if middle_weight is not None:
                encoder_hidden = middle_weight.shape[0]
            else:
                encoder_hidden = ckpt_hidden_dim

            if ckpt_input_dim != self.EMBEDDING_DIM:
                # encode() feeds EMBEDDING_DIM-dim hash vectors; an artifact
                # expecting a different input width can never run here
                # (ep2-style toy checkpoints). Refuse to enable instead of
                # silently hashing forever with the VAE believed live.
                logger.warning(
                    "FLUME VAE checkpoint %s expects %d-dim input, not the %d-dim "
                    "hash contract; not enabling (hash fallback stays active).",
                    self.model_path,
                    ckpt_input_dim,
                    self.EMBEDDING_DIM,
                )
                return

            encoder_backend = _CheckpointSequentialEncoder(
                input_dim=ckpt_input_dim,
                hidden_dim=ckpt_hidden_dim,
                output_dim=encoder_hidden,
            )
            encoder_backend.layers.load_state_dict(encoder_state)
            encoder_backend.to(self.device)
            encoder_backend.eval()
            self.encoder = encoder_backend

            # Create and load mu_head (hidden -> latent)
            # Match mu_head to checkpoint dimensions
            mu_weight = mu_state.get("weight")
            mu_out_dim = mu_weight.shape[0] if mu_weight is not None else self.EMBEDDING_DIM
            mu_in_dim = mu_weight.shape[1] if mu_weight is not None else ckpt_hidden_dim
            self.mu_head = nn.Linear(mu_in_dim, mu_out_dim)
            self.mu_head.load_state_dict(mu_state)
            self.mu_head.to(self.device)
            self.mu_head.eval()

            # Fail-closed degeneracy gate: probe the loaded encoder with the
            # REAL hash frontend (_hash_encode) on fixed strings, i.e. exactly the
            # inputs encode() will feed it. An artifact whose latents collapse
            # (mu_head bias dominating the text-dependent signal) must not be
            # enabled: every text would embed to ~the same vector and the semantic
            # cache would match everything to everything. Measured 2026-10-22 on
            # flume_vae_ep20.pt: mean off-diagonal cosine 0.999 on these inputs
            # (the raw hash inputs themselves sit at ~0.77).
            probes = [self._hash_encode(f"vae-degeneracy-probe:{i}") for i in range(16)]
            with torch.no_grad():
                probe_tensor = torch.from_numpy(np.stack(probes)).float().to(self.device)
                latents = self.mu_head(encoder_backend(probe_tensor)).cpu().numpy()
            latents = latents / np.maximum(np.linalg.norm(latents, axis=1, keepdims=True), 1e-12)
            probe_sims = latents @ latents.T
            off_diag = probe_sims[~np.eye(len(latents), dtype=bool)]
            mean_cos = float(off_diag.mean())
            if mean_cos > 0.95:
                logger.warning(
                    "FLUME VAE checkpoint %s is degenerate (probe mean off-diag "
                    "cosine %.4f > 0.95): latents collapse to a single direction. "
                    "Refusing to enable; hash fallback stays active.",
                    self.model_path,
                    mean_cos,
                )
                self.encoder = None
                self.mu_head = None
                return

            # Store actual latent dim from checkpoint
            self._z_dim = mu_out_dim
            self.enabled = True
            logger.info(f"Loaded FLUME VAE encoder from {self.model_path}")

        except Exception as e:
            logger.warning(f"Failed to load VAE encoder: {e}")
            self.encoder = None
            self.mu_head = None

    def encode(self, text: str) -> np.ndarray:
        """Encode text to 256D semantic embedding.

        Uses VAE encoder if available, falls back to hash embedding otherwise.

        Args:
            text: Text to encode

        Returns:
            256D numpy array, normalized to unit length
        """
        if self.enabled and self.encoder is not None:
            return self._vae_encode(text)
        elif self.fallback_to_hash:
            return self._hash_encode(text)
        else:
            raise RuntimeError("VAE encoder not available and fallback disabled")

    def _vae_encode(self, text: str) -> np.ndarray:
        """Encode using trained VAE encoder.

        Args:
            text: Text to encode

        Returns:
            256D normalized embedding
        """
        try:
            if self.encoder is None or self.mu_head is None:
                return self._hash_encode(text)
            with torch.no_grad():
                # Generate initial embedding from text hash
                hash_embedding = self._hash_encode(text)
                hash_tensor = torch.from_numpy(hash_embedding).float().unsqueeze(0).to(self.device)

                # Pass through encoder and mu_head
                encoded = self.encoder(hash_tensor)
                latent = self.mu_head(encoded)

                # Convert to numpy and normalize
                embedding = latent.squeeze(0).cpu().numpy().astype(np.float32)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding /= norm

                result: np.ndarray = embedding
                return result

        except Exception as e:
            logger.debug(f"VAE encoding failed: {e}, using hash fallback")
            return self._hash_encode(text)

    @staticmethod
    def _hash_encode(text: str) -> np.ndarray:
        """Encode using deterministic hash (fallback).

        Args:
            text: Text to encode

        Returns:
            256D normalized embedding from SHA-256 hash
        """
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        embedding = np.zeros(256, dtype=np.float32)
        for i in range(256):
            byte_idx = i % len(hash_bytes)
            embedding[i] = hash_bytes[byte_idx] / 255.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding

    def is_available(self) -> bool:
        """Check if VAE encoder is available."""
        return self.enabled


# Global encoder instance
_encoder_instance: FlumeVAEEncoder | None = None


def get_encoder() -> FlumeVAEEncoder:
    """Get or create singleton VAE encoder."""
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = FlumeVAEEncoder()
    return _encoder_instance


def reset_encoder() -> None:
    """Reset encoder instance (for testing)."""
    global _encoder_instance
    _encoder_instance = None
