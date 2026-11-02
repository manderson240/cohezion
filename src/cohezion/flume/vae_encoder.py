"""Compatibility facade: ``get_encoder()`` returns the canonical text latent.

This module used to load a VAE checkpoint and silently fell back to SHA-256 vectors, so every
consumer compared hashes (hash cos(similar) 0.77 vs cos(unrelated) 0.76: AUC 0.51). There is no
hash path any more. ``encode`` returns a 256-d unit vector from
``cohezion.flume.canonical_latent`` or raises ``TextLatentUnavailable``.
"""

from __future__ import annotations

from cohezion.flume.canonical_latent import (
    LATENT_DIM,
    CanonicalTextLatent,
    TextLatentUnavailable,
)


__all__ = [
    "FlumeVAEEncoder",
    "TextLatentUnavailable",
    "get_encoder",
    "reset_encoder",
]


class FlumeVAEEncoder(CanonicalTextLatent):
    """Name kept for the ~25 importers; behaviour is the canonical latent."""

    EMBEDDING_DIM = LATENT_DIM


_encoder_instance: FlumeVAEEncoder | None = None


def get_encoder() -> FlumeVAEEncoder:
    """Get or create the singleton canonical encoder."""
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = FlumeVAEEncoder()
    return _encoder_instance


def reset_encoder() -> None:
    """Reset encoder instance (for testing)."""
    global _encoder_instance
    _encoder_instance = None
