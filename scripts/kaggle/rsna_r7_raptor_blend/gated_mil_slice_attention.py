"""Gated Multiple Instance Learning (Gated MIL) Slice-Attention Module for RSNA Knee.
==================================================================================
First-Principles Mathematical Formulation (Ilse et al., ICML 2018):
In 3D MRI series (Sagittal, Coronal, Axial), pathologies (e.g., ACL tears, Meniscus tears)
are focal abnormalities localized to 1-3 slices in a 30-slice sequence.
Global average pooling dilutes the pathological signal by 1/K (~3.3%), burying
focal tears in healthy tissue noise.

Gated Slice Attention:
  a_k = exp(w^T (tanh(V h_k) * sigmoid(U h_k))) / sum_{j=1}^K exp(w^T (tanh(V h_j) * sigmoid(U h_j)))
  z = sum_{k=1}^K a_k h_k

Where:
  - V in R^{L x D}: Linear feature projection with tanh non-linearity
  - U in R^{L x D}: Information gating mechanism with sigmoid activation
  - w in R^{L}: Linear projection to attention score
  - z in R^D: Bag representation focusing on salient pathology slices

Includes:
1. PyTorch nn.Module implementation for end-to-end training.
2. Lightweight zero-overhead NumPy inference engine for Kaggle competition notebooks.
3. Slice attention interpretability maps for clinical verification.
"""

from __future__ import annotations

import math
from typing import Any, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:

    class GatedAttentionPooling(nn.Module):
        """Gated Attention Pooling module (Ilse et al., 2018).

        Parameters
        ----------
        in_dim : int
            Dimension of input slice feature vectors (D).
        latent_dim : int, default 128
            Latent projection dimension (L).
        dropout : float, default 0.1
            Dropout rate applied to latent features.
        """

        def __init__(self, in_dim: int, latent_dim: int = 128, dropout: float = 0.1) -> None:
            super().__init__()
            self.in_dim = in_dim
            self.latent_dim = latent_dim

            self.attention_V = nn.Sequential(
                nn.Linear(in_dim, latent_dim),
                nn.Tanh(),
            )
            self.attention_U = nn.Sequential(
                nn.Linear(in_dim, latent_dim),
                nn.Sigmoid(),
            )
            self.attention_w = nn.Linear(latent_dim, 1, bias=False)
            self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        def forward(self, h: torch.Tensor, mask: torch.Tensor | None = None) -> Tuple[torch.Tensor, torch.Tensor]:
            """Forward pass through Gated Attention Pooling.

            Parameters
            ----------
            h : torch.Tensor
                Slice feature representations of shape (B, K, D) where:
                B = batch size (number of MRI series),
                K = number of slices per series,
                D = feature embedding dimension.
            mask : torch.Tensor | None
                Optional binary mask of shape (B, K) where 1 indicates valid slice, 0 indicates padding.

            Returns
            -------
            Tuple[torch.Tensor, torch.Tensor]
                z : Pooled feature vectors of shape (B, D).
                a : Attention weights across slices of shape (B, K).
            """
            # (B, K, L)
            v = self.attention_V(h)
            u = self.attention_U(h)

            # Element-wise gating: (B, K, L)
            gated = self.dropout(v * u)

            # Raw attention logits: (B, K, 1) -> (B, K)
            a_logits = self.attention_w(gated).squeeze(-1)

            if mask is not None:
                a_logits = a_logits.masked_fill(~mask.bool(), -1e9)

            # Softmax over slices: (B, K)
            a = F.softmax(a_logits, dim=-1)

            # Weighted sum over slice dimension: (B, D)
            z = torch.bmm(a.unsqueeze(1), h).squeeze(1)

            return z, a

    class RSNAGatedMILNet(nn.Module):
        """Multi-Label Gated Multiple Instance Learning Network for Knee Pathology.

        Predicts multi-label probabilities for:
        1. ACL tear
        2. Meniscal tear
        3. General joint abnormality
        """

        def __init__(
            self,
            in_dim: int = 512,
            latent_dim: int = 128,
            num_classes: int = 3,
            dropout: float = 0.2,
        ) -> None:
            super().__init__()
            self.in_dim = in_dim
            self.num_classes = num_classes

            self.pooling = GatedAttentionPooling(in_dim, latent_dim=latent_dim, dropout=dropout)
            self.classifier = nn.Sequential(
                nn.Linear(in_dim, latent_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
                nn.Linear(latent_dim, num_classes),
            )

        def forward(self, h: torch.Tensor, mask: torch.Tensor | None = None) -> Tuple[torch.Tensor, torch.Tensor]:
            """Compute multi-label pathology probabilities and slice attention weights.

            Parameters
            ----------
            h : torch.Tensor
                Feature matrix of shape (B, K, D).
            mask : torch.Tensor | None
                Slice mask of shape (B, K).

            Returns
            -------
            Tuple[torch.Tensor, torch.Tensor]
                probs : Sigmoid multi-label probabilities of shape (B, num_classes).
                attn : Attention weights of shape (B, K).
            """
            z, attn = self.pooling(h, mask=mask)
            logits = self.classifier(z)
            probs = torch.sigmoid(logits)
            return probs, attn


class NumpyGatedMILInference:
    """Zero-overhead pure NumPy inference engine for Gated MIL Slice Attention.

    Enables deployment inside resource-constrained Kaggle submission kernels
    without requiring heavy PyTorch graph overhead.
    """

    def __init__(
        self,
        v_weight: np.ndarray,
        v_bias: np.ndarray,
        u_weight: np.ndarray,
        u_bias: np.ndarray,
        w_weight: np.ndarray,
        clf_w1: np.ndarray,
        clf_b1: np.ndarray,
        clf_w2: np.ndarray,
        clf_b2: np.ndarray,
    ) -> None:
        self.v_weight = v_weight.astype(np.float32)  # (L, D)
        self.v_bias = v_bias.astype(np.float32)      # (L,)
        self.u_weight = u_weight.astype(np.float32)  # (L, D)
        self.u_bias = u_bias.astype(np.float32)      # (L,)
        self.w_weight = w_weight.astype(np.float32)  # (1, L)
        self.clf_w1 = clf_w1.astype(np.float32)      # (L, D)
        self.clf_b1 = clf_b1.astype(np.float32)      # (L,)
        self.clf_w2 = clf_w2.astype(np.float32)      # (C, L)
        self.clf_b2 = clf_b2.astype(np.float32)      # (C,)

    @classmethod
    def from_torch_model(cls, model: Any) -> "NumpyGatedMILInference":
        """Export parameters from a PyTorch RSNAGatedMILNet instance to NumPy."""
        v_w = model.pooling.attention_V[0].weight.detach().cpu().numpy()
        v_b = model.pooling.attention_V[0].bias.detach().cpu().numpy()
        u_w = model.pooling.attention_U[0].weight.detach().cpu().numpy()
        u_b = model.pooling.attention_U[0].bias.detach().cpu().numpy()
        w_w = model.pooling.attention_w.weight.detach().cpu().numpy()

        c1_w = model.classifier[0].weight.detach().cpu().numpy()
        c1_b = model.classifier[0].bias.detach().cpu().numpy()
        c2_w = model.classifier[3].weight.detach().cpu().numpy()
        c2_b = model.classifier[3].bias.detach().cpu().numpy()

        return cls(v_w, v_b, u_w, u_b, w_w, c1_w, c1_b, c2_w, c2_b)

    def predict(self, slice_embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute multi-label predictions and attention weights on slice embeddings.

        Parameters
        ----------
        slice_embeddings : np.ndarray
            Slice feature array of shape (K, D) for a single MRI series.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            probs : Multi-label pathology probabilities of shape (num_classes,).
            attn : Attention weight distribution of shape (K,).
        """
        # Linear projections: (K, L)
        v = np.tanh(slice_embeddings @ self.v_weight.T + self.v_bias)
        # Sigmoid gate: 1 / (1 + exp(-x))
        u = 1.0 / (1.0 + np.exp(-np.clip(slice_embeddings @ self.u_weight.T + self.u_bias, -30.0, 30.0)))

        # Gated representation: (K, L)
        gated = v * u

        # Attention logits: (K,)
        a_logits = (gated @ self.w_weight.T).squeeze(-1)

        # Numerical stable softmax: (K,)
        max_logit = np.max(a_logits)
        exp_logits = np.exp(a_logits - max_logit)
        attn = exp_logits / (np.sum(exp_logits) + 1e-12)

        # Pooled feature vector: (D,)
        z = attn @ slice_embeddings

        # Multi-label classifier forward pass:
        h1 = np.maximum(0.0, z @ self.clf_w1.T + self.clf_b1)  # ReLU
        logits = h1 @ self.clf_w2.T + self.clf_b2
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))

        return probs, attn


def synthesize_toy_mri_features(
    batch_size: int = 4,
    num_slices: int = 30,
    feature_dim: int = 512,
    focal_slice_idx: int = 15,
) -> np.ndarray:
    """Generate synthetic MRI slice features with an injected focal tear signal."""
    # Background healthy tissue noise
    features = np.random.randn(batch_size, num_slices, feature_dim).astype(np.float32) * 0.1

    # Inject distinctive focal pathology signal into specific slice
    pathology_pattern = np.ones(feature_dim, dtype=np.float32) * 2.5
    features[:, focal_slice_idx, :] += pathology_pattern

    return features


if __name__ == "__main__":
    print("=== RSNA Knee Gated MIL Slice Attention Module ===")
    if TORCH_AVAILABLE:
        model = RSNAGatedMILNet(in_dim=128, latent_dim=64, num_classes=3)
        sample = torch.randn(2, 30, 128)
        probs, attn = model(sample)
        print(f"PyTorch Forward Output Shape: probs={probs.shape}, attn={attn.shape}")
        print(f"Sample Attention Sum: {attn.sum(dim=-1).tolist()} (Should be ~1.0)")

        # Test NumPy conversion
        np_engine = NumpyGatedMILInference.from_torch_model(model)
        single_sample = sample[0].numpy()
        np_probs, np_attn = np_engine.predict(single_sample)
        print(f"NumPy Engine Output Shape: probs={np_probs.shape}, attn={np_attn.shape}")
        print(f"NumPy Attention Sum: {np.sum(np_attn):.4f}")
    else:
        print("PyTorch not installed in environment; skipping torch test.")
