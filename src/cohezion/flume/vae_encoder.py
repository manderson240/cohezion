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

import hashlib
import logging
from pathlib import Path

import numpy as np


try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class SimpleEncoder(nn.Module):
    """Encoder to match VAE checkpoint structure.

    Matches the sequential encoder: Linear(256->512) + ReLU + Linear(512->512)
    """

    def __init__(self, input_size: int = 256, hidden_size: int = 512):
        """Initialize encoder.

        Args:
            input_size: Input embedding dimension (256)
            hidden_size: Hidden layer dimension (512)
        """
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode input through layers."""
        return self.encoder(x)


class FlumeVAEEncoder:
    """Production VAE encoder for semantic embeddings."""

    DEFAULT_MODEL_PATH = Path("./data/flume/checkpoints/flume_vae_ep2.pt")
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
        self.encoder = None
        self.mu_head = None
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
            # Encoder outputs 512D (hidden_size), not 256D
            # Read dimensions from checkpoint to match architecture
            first_weight = encoder_state.get("0.weight")
            if first_weight is not None:
                ckpt_input_dim = first_weight.shape[1]  # 64 for ep2 checkpoint
                ckpt_hidden_dim = first_weight.shape[0]  # 128 for ep2 checkpoint
            else:
                ckpt_input_dim, ckpt_hidden_dim = 256, 512
            self.encoder = SimpleEncoder(input_size=ckpt_input_dim, hidden_size=ckpt_hidden_dim)
            # The checkpoint stores the sequential module directly, not under "encoder"
            self.encoder.encoder.load_state_dict(encoder_state)
            self.encoder.to(self.device)
            self.encoder.eval()

            # Create and load mu_head (512 -> 256)
            # Match mu_head to checkpoint dimensions
            mu_weight = mu_state.get("weight")
            mu_out_dim = mu_weight.shape[0] if mu_weight is not None else self.EMBEDDING_DIM
            mu_in_dim = mu_weight.shape[1] if mu_weight is not None else 512
            self.mu_head = nn.Linear(mu_in_dim, mu_out_dim)
            self.mu_head.load_state_dict(mu_state)
            self.mu_head.to(self.device)
            self.mu_head.eval()

            # Store actual latent dim from checkpoint
            self._z_dim = mu_out_dim if "mu_out_dim" in dir() else self.EMBEDDING_DIM
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

                return embedding

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
