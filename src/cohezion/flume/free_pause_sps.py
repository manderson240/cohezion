"""Almost Free State Prediction Separation (SPS) Engine for Cohezion.

arXiv:2609.03807v2 (Langford et al., Sep 2026):
- State Stream (a): causal self-attention generating persistent KV cache.
- Prediction Stream (p): weight-shared cross-attention initialized from a single
  learned 'predict_embedding' tensor (0 added context, 0 KV cache bloat).
- Evaluates shared gated FFN once per position.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class FreePauseStatePredictionModule(nn.Module):
    """Iso-parameter Module with Free Pause State-Prediction Separation (SPS).

    Equips any language model or agentic state vector with a parallel prediction
    stream over a weight-shared backbone using exactly ONE additional parameter tensor.
    """

    def __init__(
        self,
        d_model: int = 256,
        n_heads: int = 8,
        d_ff: int = 1024,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads

        # Exactly ONE additional parameter tensor: the shared learned predict_embedding
        self.predict_embedding = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)

        # Weight-shared attention projections
        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(d_model, d_model, bias=False)
        self.v_proj = nn.Linear(d_model, d_model, bias=False)
        self.out_proj = nn.Linear(d_model, d_model, bias=False)

        # Shared gated FFN (SwiGLU)
        self.ffn_gate = nn.Linear(d_model, d_ff, bias=False)
        self.ffn_up = nn.Linear(d_model, d_ff, bias=False)
        self.ffn_down = nn.Linear(d_ff, d_model, bias=False)

        self.norm1 = nn.RMSNorm(d_model)
        self.norm2 = nn.RMSNorm(d_model)

    def forward_two_pass(
        self, state_embeddings: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Execute FlashAttention-friendly two-pass State-Prediction Separation.

        Parameters
        ----------
        state_embeddings : torch.Tensor
            Hidden state tensor of shape (batch_size, seq_len, d_model).

        Returns
        -------
        tuple[torch.Tensor, torch.Tensor]
            (prediction_output, state_output)
            Both tensors of shape (batch_size, seq_len, d_model).
        """
        B, T, D = state_embeddings.shape

        # Pass 1: State Stream 'a' causal self-attention -> populates KV cache
        h_a = self.norm1(state_embeddings)
        q_a = self.q_proj(h_a).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k_a = self.k_proj(h_a).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v_a = self.v_proj(h_a).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        attn_a = F.scaled_dot_product_attention(q_a, k_a, v_a, is_causal=True)
        attn_a = attn_a.transpose(1, 2).contiguous().view(B, T, D)
        h_a = state_embeddings + self.out_proj(attn_a)

        # Pass 2: Prediction Stream 'p' (Free Pause)
        # Initialized from the single shared learned vector across all sequence positions
        h_p = self.predict_embedding.expand(B, T, D)
        q_p = self.q_proj(h_p).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        # Cross-attention: Query_p attends over Key_a, Value_a
        attn_p = F.scaled_dot_product_attention(q_p, k_a, v_a, is_causal=True)
        attn_p = attn_p.transpose(1, 2).contiguous().view(B, T, D)
        h_p = h_p + self.out_proj(attn_p)

        # Shared Gated FFN evaluated once per stream
        h_a_norm = self.norm2(h_a)
        ffn_a = self.ffn_down(F.silu(self.ffn_gate(h_a_norm)) * self.ffn_up(h_a_norm))
        state_output = h_a + ffn_a

        h_p_norm = self.norm2(h_p)
        ffn_p = self.ffn_down(F.silu(self.ffn_gate(h_p_norm)) * self.ffn_up(h_p_norm))
        prediction_output = h_p + ffn_p

        return prediction_output, state_output
