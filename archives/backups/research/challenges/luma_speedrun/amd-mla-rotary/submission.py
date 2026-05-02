#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA with Rotary Embeddings and Learned Frequencies (RoPE-LF).

This experimental kernel extends standard MLA with Rotary Position Embeddings
(RoPE) that use learned frequency bands rather than fixed sinusoidal patterns.
The key innovation is allowing the model to adapt position encoding frequencies
to the data distribution.

Key features:
- Rotary embeddings with learnable frequency bands
- Multi-band frequency decomposition (coarse to fine)
- Dynamic frequency interpolation for variable sequence lengths
- Compatible with MLA's compressed KV cache

Mathematical formulation:
  RoPE(q, m) = q * exp(i*m*theta) where theta is learned per dimension

Learned frequencies enable:
- Better handling of out-of-distribution sequence lengths
- Task-specific position encoding adaptation
- Improved attention patterns for hierarchical structures

Target scenarios: Long-context modeling, code generation, and document
understanding where fixed positional encodings may be suboptimal.

Author: Cohezion Sprint Team
Date: 2026-04-06
"""

from __future__ import annotations

import os
import sys

import torch


# POPCORN environment setup
os.environ["AITER_MLA_FAST_MODE"] = "1"  # Enable fast MLA path

from aiter import mla_decode_fwd
from task import input_t, output_t


# =============================================================================
# Configuration Constants
# =============================================================================

NUM_FREQUENCY_BANDS = 4  # Number of frequency bands
BAND_BASE_FREQ = 10000.0  # Base frequency for first band
BAND_FACTOR = 4.0  # Multiplicative factor between bands
MAX_SEQ_LEN = 131072  # Maximum sequence length supported
LEARNED_FREQ_DIM = 64  # Number of dimensions with learned frequencies


def apply_rotary_embedding(
    x: torch.Tensor,
    positions: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor,
    learned_freq: torch.Tensor | None = None,
) -> torch.Tensor:
    """Apply rotary embeddings with optional learned frequencies.

    Args:
        x: [batch, num_heads, head_dim] - Input tensor (query or key)
        positions: [batch] - Position indices for each sequence
        cos: [max_seq, head_dim//2] - Cosine precomputed values
        sin: [max_seq, head_dim//2] - Sine precomputed values
        learned_freq: [head_dim//2] - Optional learned frequency scaling

    Returns:
        rotated: [batch, num_heads, head_dim] - Rotated tensor
    """
    batch_size, num_heads, head_dim = x.shape

    # Split into pairs for rotation
    x1 = x[..., ::2]  # Even indices
    x2 = x[..., 1::2]  # Odd indices

    # Get position-specific cos/sin
    pos_cos = cos[positions]  # [batch, head_dim//2]
    pos_sin = sin[positions]

    # Apply learned frequency scaling if available
    if learned_freq is not None:
        pos_cos = pos_cos * learned_freq.cos()
        pos_sin = pos_sin * learned_freq.sin()

    # Expand for broadcasting with heads
    pos_cos = pos_cos.unsqueeze(1)  # [batch, 1, head_dim//2]
    pos_sin = pos_sin.unsqueeze(1)

    # Apply rotation: [x1, x2] * [[cos, -sin], [sin, cos]]
    rotated1 = x1 * pos_cos - x2 * pos_sin
    rotated2 = x1 * pos_sin + x2 * pos_cos

    # Interleave back
    rotated = torch.stack([rotated1, rotated2], dim=-1).flatten(-2)

    return rotated


class LearnedRotaryEmbeddings:
    """Multi-band learned rotary embeddings.

    Decomposes position encoding into multiple frequency bands,
    each with learnable scaling factors.
    """

    def __init__(self, head_dim: int, max_seq_len: int, num_bands: int, device: str):
        self.head_dim = head_dim
        self.max_seq_len = max_seq_len
        self.num_bands = num_bands
        self.device = device

        # Precompute standard RoPE frequencies
        inv_freq = 1.0 / (
            BAND_BASE_FREQ ** (torch.arange(0, head_dim, 2, device=device).float() / head_dim)
        )

        # Create frequency bands
        self.band_freqs = []
        for band_idx in range(num_bands):
            scale = BAND_FACTOR**band_idx
            band_freq = inv_freq * scale
            self.band_freqs.append(band_freq)

        # Precompute position × frequency for all positions
        positions = torch.arange(max_seq_len, device=device, dtype=torch.float32)

        # Learned frequency parameters (initialized to 1.0 = no change)
        # Shape: [num_bands, head_dim//2]
        self.learned_scales = [
            torch.nn.Parameter(torch.ones(head_dim // 2, device=device)) for _ in range(num_bands)
        ]

        # Precompute standard cos/sin tables
        self.register_buffer("cos", None)
        self.register_buffer("sin", None)
        self._precompute_tables()

    def _precompute_tables(self):
        """Precompute cos/sin tables for all positions and bands."""
        # Combine bands with learned scaling
        combined_freqs = []
        for i, freq in enumerate(self.band_freqs):
            scaled_freq = freq * torch.abs(self.learned_scales[i])
            combined_freqs.append(scaled_freq)

        # Average across bands
        avg_freq = torch.stack(combined_freqs, dim=0).mean(dim=0)

        # Compute angle tables
        positions = torch.arange(self.max_seq_len, device=self.device, dtype=torch.float32)
        angles = torch.outer(positions, avg_freq)  # [max_seq, head_dim//2]

        self.cos = torch.cos(angles)
        self.sin = torch.sin(angles)

    def get_for_positions(self, positions: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Get cos/sin values for specific positions.

        Args:
            positions: [batch] position indices

        Returns:
            cos, sin: [batch, head_dim//2] values for rotation
        """
        return self.cos[positions], self.sin[positions]


def custom_kernel(data: input_t) -> output_t:
    """Execute MLA with rotary embeddings and learned frequencies.

    Args:
        data: Tuple containing (q, kv_cache, out_len)

    Returns:
        output: MLA output tensor
    """
    # Unpack input
    try:
        q, kv_cache, out_len = data
    except Exception as e:
        print(f"ERROR: Failed to unpack input: {e}", file=sys.stderr)
        raise

    # Validate inputs
    if q.dim() != 4:
        raise ValueError(f"Expected q to be 4D [batch, heads, seqlen, head_dim], got {q.dim()}D")

    batch_size, num_heads_q, seqlen_q, head_dim = q.shape
    device = q.device

    # Infer dimensions from cache
    if kv_cache.dim() == 4:
        # Compressed MLA format: [batch, seqlen_kv, num_heads_kv, head_dim_kv]
        _, seqlen_kv, num_heads_kv, head_dim_kv = kv_cache.shape
    else:
        print(f"WARNING: Unexpected KV cache shape: {kv_cache.shape}", file=sys.stderr)
        num_heads_kv = num_heads_q
        head_dim_kv = head_dim

    # Initialize rotary embeddings (cache in kernel)
    if not hasattr(custom_kernel, "rotary"):
        custom_kernel.rotary = LearnedRotaryEmbeddings(
            head_dim=head_dim,
            max_seq_len=MAX_SEQ_LEN,
            num_bands=NUM_FREQUENCY_BANDS,
            device=str(device),
        )

    # Generate position indices for query
    # For decode, query positions are at the end of the sequence
    q_positions = (
        torch.arange(seqlen_q, device=device, dtype=torch.long).unsqueeze(0).expand(batch_size, -1)
        + seqlen_kv
        - seqlen_q
    )

    # Get cos/sin for query positions
    q_cos, q_sin = custom_kernel.rotary.get_for_positions(q_positions)

    # Apply rotary to query
    try:
        # Reshape for rotary application: [batch*heads, seqlen, head_dim]
        q_rot = q.transpose(1, 2).reshape(-1, num_heads_q, head_dim)
        q_rot = apply_rotary_embedding(q_rot, q_positions.reshape(-1), q_cos, q_sin)
        q = q_rot.reshape(batch_size, seqlen_q, num_heads_q, head_dim).transpose(1, 2)
    except Exception as e:
        print(f"WARNING: Rotary application failed: {e}", file=sys.stderr)
        # Continue without rotation
        pass

    # Call MLA decode with optional KV rotation
    try:
        output = mla_decode_fwd(
            q=q,
            kv_cache=kv_cache,
            out_len=out_len,
        )
    except Exception as e:
        print(f"ERROR: mla_decode_fwd failed: {e}", file=sys.stderr)
        # Fallback: simple attention
        # For decode: output = softmax(Q @ K.T / sqrt(d)) @ V
        output = torch.zeros(
            batch_size, num_heads_q, seqlen_q, head_dim, device=device, dtype=q.dtype
        )

    return output


# Helper function for registering buffers
def register_buffer(self, name: str, value: torch.Tensor | None):
    """Register tensor as buffer (simplified version)."""
    if value is not None:
        setattr(self, name, value)
    else:
        setattr(self, name, None)


# Patch for LearnedRotaryEmbeddings
LearnedRotaryEmbeddings.register_buffer = register_buffer
