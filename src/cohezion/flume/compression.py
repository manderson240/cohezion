"""FLUME 2048D -> 256D -> 12D dimensionality compression pipeline."""

from __future__ import annotations

import logging

import numpy as np
import numpy.typing as npt


logger = logging.getLogger(__name__)


class FlumeCompressionPipeline:
    """Handles the sequential down-projection of semantic vectors."""

    proj_2048_to_256: npt.NDArray[np.float64]
    proj_256_to_12: npt.NDArray[np.float64]

    def __init__(self) -> None:
        # In a real system, these would be loaded projection matrices or autoencoder weights.
        # We simulate them as random orthogonal matrices for the engine.
        self.proj_2048_to_256 = np.random.randn(2048, 256) / np.sqrt(2048)
        self.proj_256_to_12 = np.random.randn(256, 12) / np.sqrt(256)

    def compress(self, embedding_2048d: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """Compress a raw 2048D LLM embedding down to a 12D Toroidal manifold state."""
        if embedding_2048d.shape[-1] != 2048:
            raise ValueError(f"Expected 2048D input, got {embedding_2048d.shape}")

        logger.debug("FLUME: Projecting 2048D -> 256D")
        latent_256d: npt.NDArray[np.float64] = np.dot(embedding_2048d, self.proj_2048_to_256)

        # Non-linear activation simulating VAE latent space
        latent_256d_act: npt.NDArray[np.float64] = np.tanh(latent_256d)

        logger.debug("FLUME: Projecting 256D -> 12D (HIHO Topology)")
        manifold_12d: npt.NDArray[np.float64] = np.dot(latent_256d_act, self.proj_256_to_12)

        # Normalize to the target manifold
        norm = np.linalg.norm(manifold_12d, axis=-1, keepdims=True)
        manifold_12d_norm: npt.NDArray[np.float64] = manifold_12d / (norm + 1e-8)

        return manifold_12d_norm


class PolarQuantEncoder:
    """TurboQuant PolarQuant for FLUME 256D vectors (Google, March 2026).

    Converts Cartesian FLUME vectors to polar coordinates, then quantizes
    angles to a fixed circular grid. Preserves geometric structure of manifold
    vectors better than naive scalar quantization.

    Key insight: manifold vectors have angular structure (SU(2) spinors,
    Bloch sphere coordinates). PolarQuant exploits this by quantizing in
    the coordinate system that matches the data geometry.

    References:
        - TurboQuant (Google, March 2026): PolarQuant + QJL
        - IsoQuant (arXiv:2603.28430): SO(4) isoclinic rotations
        - Learning 223: TurboQuant integration path for FLUME + SemanticCache
    """

    def __init__(self, n_bits: int = 4, dim: int = 256) -> None:
        self.n_bits = n_bits
        self.n_levels = 2**n_bits
        self.dim = dim

    def encode(self, vectors: npt.NDArray[np.float64]) -> dict:
        """Encode FLUME vectors to polar quantized representation.

        Args:
            vectors: Array of shape (batch, dim) or (dim,)

        Returns:
            Dict with 'magnitudes' (float16) and 'angles' (uint8 quantized)
        """
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        # Convert pairs of dimensions to polar (magnitude, angle)
        n_pairs = vectors.shape[1] // 2
        magnitudes = np.zeros((vectors.shape[0], n_pairs), dtype=np.float16)
        angles = np.zeros((vectors.shape[0], n_pairs), dtype=np.uint8)

        for i in range(n_pairs):
            x = vectors[:, 2 * i]
            y = vectors[:, 2 * i + 1]
            magnitudes[:, i] = np.sqrt(x**2 + y**2).astype(np.float16)
            # Quantize angle to n_levels bins
            theta = np.arctan2(y, x)  # [-pi, pi]
            theta_normalized = (theta + np.pi) / (2 * np.pi)  # [0, 1]
            angles[:, i] = (theta_normalized * (self.n_levels - 1)).astype(np.uint8)

        return {"magnitudes": magnitudes, "angles": angles}

    def decode(self, encoded: dict) -> npt.NDArray[np.float64]:
        """Decode polar quantized representation back to Cartesian vectors.

        Args:
            encoded: Dict with 'magnitudes' and 'angles'

        Returns:
            Reconstructed vectors of shape (batch, dim)
        """
        magnitudes = encoded["magnitudes"].astype(np.float64)
        angles_q = encoded["angles"].astype(np.float64)

        # Dequantize angles
        theta = (angles_q / (self.n_levels - 1)) * 2 * np.pi - np.pi

        n_pairs = magnitudes.shape[1]
        vectors = np.zeros((magnitudes.shape[0], n_pairs * 2), dtype=np.float64)

        for i in range(n_pairs):
            vectors[:, 2 * i] = magnitudes[:, i] * np.cos(theta[:, i])
            vectors[:, 2 * i + 1] = magnitudes[:, i] * np.sin(theta[:, i])

        return vectors

    def compression_ratio(self) -> float:
        """Compute compression ratio vs float32 storage.

        Returns:
            Compression ratio (e.g., 4.0 means 4x smaller)
        """
        # Original: dim * 32 bits (float32)
        # Compressed: (dim/2) * 16 bits (float16 magnitude) + (dim/2) * 8 bits (uint8 angle)
        original_bits = self.dim * 32
        compressed_bits = (self.dim // 2) * 16 + (self.dim // 2) * 8
        return original_bits / compressed_bits


class QJLProjector:
    """TurboQuant QJL 1-bit projection for SemanticCache L2 cosine similarity.

    Johnson-Lindenstrauss sign-only encoding: project high-dimensional vectors
    to random hyperplanes, keep only the sign bit. Cosine similarity is
    approximated by Hamming distance between sign vectors.

    32x storage reduction (float32 → 1-bit per dimension).

    References:
        - QJL (Google TurboQuant, March 2026)
        - Learning 223: QJL's sign-only quantization IS HIHO (half positive, half negative)
    """

    def __init__(self, input_dim: int = 256, n_projections: int = 256) -> None:
        self.input_dim = input_dim
        self.n_projections = n_projections
        # Random projection matrix (Gaussian)
        rng = np.random.RandomState(42)  # Deterministic for reproducibility
        self.projection = rng.randn(input_dim, n_projections) / np.sqrt(n_projections)

    def encode(self, vectors: npt.NDArray[np.float64]) -> npt.NDArray[np.uint8]:
        """Encode vectors to 1-bit sign projections.

        Args:
            vectors: Array of shape (batch, input_dim) or (input_dim,)

        Returns:
            Packed bit array of shape (batch, n_projections // 8)
        """
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        projected = vectors @ self.projection
        signs = (projected > 0).astype(np.uint8)

        # Pack bits into bytes
        n_bytes = (self.n_projections + 7) // 8
        packed = np.zeros((vectors.shape[0], n_bytes), dtype=np.uint8)
        for i in range(self.n_projections):
            packed[:, i // 8] |= signs[:, i] << (i % 8)

        return packed

    def cosine_similarity(
        self, packed_a: npt.NDArray[np.uint8], packed_b: npt.NDArray[np.uint8]
    ) -> float:
        """Approximate cosine similarity from packed bit representations.

        Uses Hamming distance: sim ≈ 1 - 2 * hamming_distance / n_projections

        Args:
            packed_a: Packed bits for vector A
            packed_b: Packed bits for vector B

        Returns:
            Approximate cosine similarity [-1, 1]
        """
        # XOR to find differing bits
        xor = np.bitwise_xor(packed_a, packed_b)
        # Count differing bits
        hamming = sum(bin(byte).count("1") for byte in xor.flatten())
        # Convert to similarity
        return 1.0 - 2.0 * hamming / self.n_projections
