"""FLUME VAE Encoder for production semantic embeddings.

Supports two checkpoint formats:
  v1: SimpleEncoder (256→512→mu) with SHA-256 hash input (legacy)
  v2: FlumeVAE (768→...→256) with Ollama nomic-embed-text input (new)

Falls back to deterministic hash encoding if no model or Ollama available.
"""

import hashlib
import logging
from pathlib import Path

import numpy as np

from cohezion.flume.embedding_provider import OllamaEmbeddingProvider


try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class SimpleEncoder(nn.Module):
    """Legacy v1 encoder: Linear(256->512) + ReLU + Linear(512->512)."""

    def __init__(self, input_size: int = 256, hidden_size: int = 512):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class FlumeVAEEncoder:
    """Production VAE encoder for semantic embeddings."""

    DEFAULT_MODEL_PATH = Path("./data/flume/checkpoints_v2/flume_vae_v2_best.pt")
    EMBEDDING_DIM = 256

    def __init__(
        self,
        model_path: Path | None = None,
        device: str = "cpu",
        fallback_to_hash: bool = True,
    ):
        self.device = device
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.fallback_to_hash = fallback_to_hash
        self.encoder = None
        self.mu_head = None
        self._vae_v2 = None
        self._ollama_provider = None
        self.enabled = False
        self._version = 0

        if TORCH_AVAILABLE:
            self._load_encoder()
        elif not fallback_to_hash:
            logger.warning("PyTorch not available and fallback disabled")

    def _load_encoder(self) -> None:
        """Load encoder from checkpoint (v1 or v2 format)."""
        try:
            if not self.model_path.exists():
                logger.warning("Model path not found: %s", self.model_path)
                return

            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=True)

            # Detect v2 checkpoint (has model_state_dict and version or config with input_dim)
            if "model_state_dict" in checkpoint:
                self._load_v2(checkpoint)
            elif "encoder" in checkpoint and "mu_head" in checkpoint:
                self._load_v1(checkpoint)
            else:
                logger.warning("Unknown checkpoint format")

        except Exception as e:
            logger.warning("Failed to load VAE encoder: %s", e)
            self.encoder = None
            self.mu_head = None
            self._vae_v2 = None

    def _load_v2(self, checkpoint: dict) -> None:
        """Load v2 FlumeVAE model."""
        from cohezion.flume.vae import FlumeVAE

        config = checkpoint.get("config", {})
        input_dim = config.get("input_dim", 768)
        latent_dim = config.get("latent_dim", 256)

        model = FlumeVAE(input_dim=input_dim, latent_dim=latent_dim)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(self.device)
        model.eval()
        self._vae_v2 = model
        self._version = 2

        # Set up Ollama provider (no eager probe — fails gracefully at encode time)
        try:
            self._ollama_provider = OllamaEmbeddingProvider()
            logger.info("Loaded FLUME VAE v2 (Ollama provider configured)")
        except Exception:
            self._ollama_provider = None
            logger.info("Loaded FLUME VAE v2 (Ollama unavailable, hash fallback)")

        self.enabled = True

    def _load_v1(self, checkpoint: dict) -> None:
        """Load legacy v1 encoder."""
        self.encoder = SimpleEncoder(input_size=256, hidden_size=512)
        self.encoder.encoder.load_state_dict(checkpoint["encoder"])
        self.encoder.to(self.device)
        self.encoder.eval()

        self.mu_head = nn.Linear(512, self.EMBEDDING_DIM)
        self.mu_head.load_state_dict(checkpoint["mu_head"])
        self.mu_head.to(self.device)
        self.mu_head.eval()

        self._version = 1
        self.enabled = True
        logger.info("Loaded FLUME VAE v1 from checkpoint")

    def encode(self, text: str) -> np.ndarray:
        """Encode text to 256D semantic embedding."""
        if self.enabled:
            if self._version == 2 and self._vae_v2 is not None:
                return self._vae_v2_encode(text)
            if self._version == 1 and self.encoder is not None:
                return self._vae_v1_encode(text)
        if self.fallback_to_hash:
            return self._hash_encode(text)
        raise RuntimeError("VAE encoder not available and fallback disabled")

    def _vae_v2_encode(self, text: str) -> np.ndarray:
        """Encode using v2 model: text → Ollama 768D → VAE → 256D."""
        try:
            with torch.no_grad():
                if self._ollama_provider is not None:
                    input_vec = self._ollama_provider.embed(text)
                else:
                    # Fallback: hash to 768D (poor quality but functional)
                    input_vec = self._hash_encode_nd(text, 768)

                tensor = torch.from_numpy(input_vec).float().unsqueeze(0).to(self.device)
                mu, _ = self._vae_v2.encode(tensor)
                embedding = mu.squeeze(0).cpu().numpy().astype(np.float32)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding /= norm
                return embedding
        except Exception as e:
            logger.debug("VAE v2 encoding failed: %s, using hash fallback", e)
            return self._hash_encode(text)

    def _vae_v1_encode(self, text: str) -> np.ndarray:
        """Encode using legacy v1 model: text → hash 256D → encoder → mu → 256D."""
        try:
            with torch.no_grad():
                hash_embedding = self._hash_encode(text)
                hash_tensor = torch.from_numpy(hash_embedding).float().unsqueeze(0).to(self.device)
                encoded = self.encoder(hash_tensor)
                latent = self.mu_head(encoded)
                embedding = latent.squeeze(0).cpu().numpy().astype(np.float32)
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding /= norm
                return embedding
        except Exception as e:
            logger.debug("VAE v1 encoding failed: %s, using hash fallback", e)
            return self._hash_encode(text)

    @staticmethod
    def _hash_encode(text: str) -> np.ndarray:
        """256D normalized embedding from SHA-256 hash."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = np.zeros(256, dtype=np.float32)
        for i in range(256):
            embedding[i] = hash_bytes[i % len(hash_bytes)] / 255.0
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        return embedding

    @staticmethod
    def _hash_encode_nd(text: str, dim: int) -> np.ndarray:
        """N-dimensional normalized embedding from SHA-256 hash."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = np.zeros(dim, dtype=np.float32)
        for i in range(dim):
            embedding[i] = hash_bytes[i % len(hash_bytes)] / 255.0
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        return embedding

    def is_available(self) -> bool:
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
