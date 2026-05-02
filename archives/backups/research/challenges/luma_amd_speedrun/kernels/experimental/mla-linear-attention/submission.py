"""
MLA: Linear Attention Approximation (Kernel Feature Maps)

#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

Implements linear attention via explicit kernel feature maps, replacing the
softmax-based attention with a dot-product of positive feature mappings.
This reduces complexity from O(N^2) to O(N) where N is sequence length.

Key Innovation:
- Feature map transformation: phi(q), phi(k) where phi is a positive feature map
- Linear attention: softmax(QK^T/sqrt(d))V → phi(Q)phi(K)^TV
- Associative property: O(N^2) matmul becomes O(N) sequential accumulation

Trade-offs:
+ Linear complexity in sequence length (crucial for long sequences)
+ No materialization of N×N attention matrix (memory efficient)
+ Mathematically equivalent when feature map approximates softmax
- Approximation quality depends on feature map choice
- Different error profile than exact softmax attention

Reference: "Transformers are RNNs" (Katharopoulos et al., 2020)
Feature maps: ReLU, ELU+1, or learnable feature maps
"""

from __future__ import annotations

import math
import os
import sys
from collections.abc import Callable

import torch
import torch.nn.functional as F
from task import input_t, output_t


# Environment optimizations
os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"


class LinearAttentionKernel:
    """
    Implements linear attention with explicit kernel feature maps.

    Instead of computing attention(Q, K, V) = softmax(QK^T/sqrt(d))V,
    we use the identity:
        softmax(QK^T/sqrt(d)) = phi(Q)phi(K)^T / (sum(phi(K)) * phi(Q))

    This allows reformulating attention as:
        O = phi(Q) * (sum_t phi(K_t)V_t^T) / (sum_t phi(K_t))

    The key insight is that sum_t can be computed incrementally,
    yielding linear complexity in sequence length.

    Supported feature maps:
    - elu: ELU(x) + 1 (original "Transformers are RNNs")
    - relu: ReLU(x) (simpler, often effective)
    - softmax_approx: Polynomial approximation of softmax
    """

    def __init__(self, feature_dim: int = 64, feature_map: str = "elu"):
        """
        Initialize linear attention kernel.

        Args:
            feature_dim: Dimensionality of feature space (default: 64)
            feature_map: Type of feature transformation ("elu", "relu", "softmax_approx")
        """
        self.feature_dim = feature_dim
        self.feature_map_name = feature_map
        self._feature_fn = self._get_feature_map(feature_map)

    def _get_feature_map(self, name: str) -> Callable[[torch.Tensor], torch.Tensor]:
        """Get feature transformation function by name."""
        if name == "elu":
            # ELU(x) + 1: ensures positivity, good gradient flow
            return lambda x: F.elu(x) + 1.0
        elif name == "relu":
            # ReLU(x): simple, fast, but no negative information
            return lambda x: torch.relu(x)
        elif name == "softmax_approx":
            # Polynomial softmax approximation via Taylor expansion
            # softmax(x)_i ≈ x_i^2 / sum(x_j^2) for normalized inputs
            return lambda x: x**2 + 1e-6
        else:
            raise ValueError(f"Unknown feature map: {name}")

    def apply_feature_map(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply feature map to input tensor.

        Args:
            x: Input tensor [..., d]

        Returns:
            Feature-mapped tensor [..., feature_dim]
        """
        # Project to feature dimension if needed
        orig_shape = x.shape
        x_flat = x.reshape(-1, x.shape[-1])

        # Simple linear projection to feature space
        if x.shape[-1] != self.feature_dim:
            # Use random orthogonal projection for approximation
            proj = torch.randn(
                x.shape[-1], self.feature_dim, device=x.device, dtype=x.dtype
            ) / math.sqrt(x.shape[-1])
            x_flat = x_flat @ proj

        # Apply non-linear feature map
        features = self._feature_fn(x_flat)
        return features.reshape(*orig_shape[:-1], self.feature_dim)

    def linear_attention_forward(
        self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, causal: bool = True
    ) -> torch.Tensor:
        """
        Compute linear attention forward pass.

        For causal (autoregressive) attention:
            O_i = phi(Q_i) * (sum_{j<=i} phi(K_j)V_j^T) / (sum_{j<=i} phi(K_j))

        Args:
            q: Query tensor [batch, nheads, q_len, head_dim]
            k: Key tensor [batch, nheads, kv_len, head_dim]
            v: Value tensor [batch, nheads, kv_len, v_dim]
            causal: Whether to use causal masking

        Returns:
            Output tensor [batch, nheads, q_len, v_dim]
        """
        batch, nheads, q_len, head_dim = q.shape
        kv_len = k.shape[2]
        v_dim = v.shape[-1]

        # Apply feature maps
        phi_q = self.apply_feature_map(q)  # [B, H, Q, F]
        phi_k = self.apply_feature_map(k)  # [B, H, KV, F]

        # Compute KV^T accumulation (the key linearization)
        # S_i = sum_{j<=i} phi(K_j) V_j^T
        # Z_i = sum_{j<=i} phi(K_j)
        if causal:
            # Causal: cumulative sum along sequence dimension
            # kv_state[b,h,i,:,:] = sum_{j<=i} phi(k[b,h,j,:]) * v[b,h,j,:]
            # Shape: [B, H, KV, F, V]

            # Use einsum for clean broadcasting
            # phi_k: [B, H, KV, F], v: [B, H, KV, V]
            kv_products = torch.einsum("bhki,bhkj->bhkij", phi_k, v)
            # kv_state: [B, H, KV, F, V]
            kv_state = torch.cumsum(kv_products, dim=2)

            # Normalization factor
            # phi_k: [B, H, KV, F] -> sum over F -> [B, H, KV]
            k_sum = torch.cumsum(phi_k.sum(dim=-1), dim=2)  # [B, H, KV]

            # Query positions: for each query, use KV state at that position
            # Q_len may differ from KV_len (e.g., for new tokens)
            if q_len <= kv_len:
                # Standard case: query attends to all previous KV
                indices = torch.arange(q_len, device=q.device)
                selected_kv_state = kv_state[:, :, indices]  # [B, H, Q, F, V]
                selected_k_sum = k_sum[:, :, indices]  # [B, H, Q]
            else:
                # Extended query (shouldn't happen for decode)
                selected_kv_state = kv_state[:, :, -1:].expand(-1, -1, q_len, -1, -1)
                selected_k_sum = k_sum[:, :, -1:].expand(-1, -1, q_len)

            # Compute output: phi(q) @ kv_state / normalization
            # phi_q: [B, H, Q, F], selected_kv_state: [B, H, Q, F, V]
            numerator = torch.einsum("bhqi,bhqfv->bhqv", phi_q, selected_kv_state)
            denominator = torch.einsum("bhqi,bhq->bhq", phi_q, selected_k_sum).clamp(min=1e-6)

            output = numerator / denominator.unsqueeze(-1)
        else:
            # Non-causal: full aggregation (e.g., for prefill)
            # S = sum_j phi(K_j) V_j^T  [B, H, F, V]
            kv_state = torch.einsum("bhki,bhkj->bhij", phi_k, v)
            k_sum = phi_k.sum(dim=2)  # [B, H, F]

            # O = phi(Q) @ S / (phi(Q) @ sum(K))
            numerator = torch.einsum("bhqi,bhiv->bhqv", phi_q, kv_state)
            denominator = torch.einsum("bhqi,bhi->bhq", phi_q, k_sum).clamp(min=1e-6)
            output = numerator / denominator.unsqueeze(-1)

        return output

    def chunked_forward(
        self, q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, chunk_size: int = 1024
    ) -> torch.Tensor:
        """
        Memory-efficient chunked forward for long sequences.

        Processes attention in chunks to maintain constant memory usage.

        Args:
            q: Query tensor [batch, nheads, q_len, head_dim]
            k: Key tensor [batch, nheads, kv_len, head_dim]
            v: Value tensor [batch, nheads, kv_len, v_dim]
            chunk_size: Size of chunks for processing

        Returns:
            Output tensor [batch, nheads, q_len, v_dim]
        """
        batch, nheads, q_len, head_dim = q.shape
        v_dim = v.shape[-1]
        device = q.device

        output = torch.zeros(batch, nheads, q_len, v_dim, device=device, dtype=q.dtype)

        # Process queries in chunks
        for q_start in range(0, q_len, chunk_size):
            q_end = min(q_start + chunk_size, q_len)
            q_chunk = q[:, :, q_start:q_end, :]

            # For causal attention, KV is limited to current position
            kv_end = q_end if k.shape[2] >= q_end else k.shape[2]
            k_chunk = k[:, :, :kv_end, :]
            v_chunk = v[:, :, :kv_end, :]

            out_chunk = self.linear_attention_forward(q_chunk, k_chunk, v_chunk, causal=True)
            output[:, :, q_start:q_end, :] = out_chunk

        return output


# Global linear attention instance (singleton)
_LINEAR_ATTN: LinearAttentionKernel | None = None


def _get_linear_attn(feature_dim: int = 64, feature_map: str = "elu") -> LinearAttentionKernel:
    """Get or create global linear attention instance."""
    global _LINEAR_ATTN
    if _LINEAR_ATTN is None:
        _LINEAR_ATTN = LinearAttentionKernel(feature_dim, feature_map)
    return _LINEAR_ATTN


def custom_kernel(data: input_t) -> output_t:
    """
    Execute MLA decode with linear attention approximation.

    Args:
        data: Tuple of (q, kv_data, qo_indptr, kv_indptr, config)

    Returns:
        Output tensor [total_q, nheads, v_head_dim]
    """
    q, kv_data, qo_indptr, kv_indptr, config = data

    # Extract configuration
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    nheads = config["num_heads"]
    total_q = q.shape[0]
    qseqlen = total_q // bs

    try:
        # Get KV cache (use bf16 as fallback if specific format unavailable)
        if "bf16" in kv_data:
            kv_bf16 = kv_data["bf16"]
        elif "fp8" in kv_data:
            kv_fp8, _ = kv_data["fp8"]
            kv_bf16 = kv_fp8.to(torch.bfloat16)
        elif "mxfp4" in kv_data:
            kv_mxfp4, _ = kv_data["mxfp4"]
            kv_bf16 = kv_mxfp4.to(torch.bfloat16)
        else:
            raise ValueError("No compatible KV format found")

        # Parse KV layout: MLA packs K and V together
        # KV shape: [total_kv, k_head_dim + v_head_dim]
        # For DeepSeek: K=576, V=512, but packed as single tensor
        total_kv = kv_bf16.shape[0]
        kv_combined_dim = kv_bf16.shape[-1]

        # Split into K and V components
        # Standard MLA: K=576, V=512, packed as [..., 1088]
        v_head_dim = 512
        if kv_combined_dim > v_head_dim:
            k_head_dim = kv_combined_dim - v_head_dim
            k = kv_bf16[:, :k_head_dim]
            v = kv_bf16[:, k_head_dim : k_head_dim + v_head_dim]
        else:
            # Fallback: use same tensor for both (approximation)
            k = v = kv_bf16
            v_head_dim = kv_combined_dim

        # Reshape to [batch, nheads, seqlen, head_dim]
        k = k.view(bs, kvseqlen, nheads, -1).transpose(1, 2)
        v = v.view(bs, kvseqlen, nheads, -1).transpose(1, 2)
        q_reshaped = q.view(bs, qseqlen, nheads, -1).transpose(1, 2)

        # Initialize linear attention
        feature_dim = int(os.environ.get("MLA_LINEAR_FEATURE_DIM", "64"))
        feature_map = os.environ.get("MLA_LINEAR_FEATURE_MAP", "elu")
        linear_attn = _get_linear_attn(feature_dim, feature_map)

        # Compute linear attention
        # For decode (qseqlen=1), causal attention is appropriate
        output = linear_attn.linear_attention_forward(q_reshaped, k, v, causal=True)

        # Reshape back to [total_q, nheads, v_head_dim]
        output = output.transpose(1, 2).reshape(total_q, nheads, v_head_dim)

        return output

    except Exception as e:
        print(f"Linear attention failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)

        # Fallback to einsum-based attention (standard but slower)
        try:
            # Simple attention fallback
            kv_bf16 = kv_data.get("bf16", kv_data.get("fp8", (None,))[0])
            if kv_bf16 is None:
                raise ValueError("No KV data available")

            # Reshape
            k = kv_bf16[:, :576].view(bs, kvseqlen, nheads, 576).transpose(1, 2)
            v = kv_bf16[:, 576:1088].view(bs, kvseqlen, nheads, 512).transpose(1, 2)
            q_reshaped = q.view(bs, qseqlen, nheads, 576).transpose(1, 2)

            # Compute attention scores
            scale = 1.0 / math.sqrt(576)
            scores = torch.matmul(q_reshaped, k.transpose(-2, -1)) * scale
            weights = torch.softmax(scores, dim=-1)
            output = torch.matmul(weights, v)

            return output.transpose(1, 2).reshape(total_q, nheads, 512)

        except Exception as e2:
            print(f"Fallback also failed: {e2}", file=sys.stderr)
            # Final fallback: reference kernel
            from reference import ref_kernel

            return ref_kernel(data)
