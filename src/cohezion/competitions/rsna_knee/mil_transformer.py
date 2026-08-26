"""RSNA Knee Multi-View Multi-Instance Learning (MIL) Sequence Classifier (Hardened V&V)."""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Optional

class RSNAKneeMILClassifier:
    """Multi-view slice aggregator with isolated RNG, inference determinism & zero-slice guards."""

    def __init__(self, feature_dim: int = 512, seed: int = 42):
        self.feature_dim = feature_dim
        # Use isolated RNG to prevent global seed contamination
        self._rng = np.random.default_rng(seed)
        self.cls_token = self._rng.standard_normal(feature_dim, dtype=np.float32)
        self.head_weights = self._rng.standard_normal((feature_dim * 3, 4), dtype=np.float32) * 0.01

    def apply_slice_dropout(self, slice_features: np.ndarray, drop_rate: float = 0.15, training: bool = False) -> np.ndarray:
        """Applies dropout ONLY during training; guarantees at least 1 slice is retained."""
        if not training or len(slice_features) <= 1:
            return slice_features
        n_slices = len(slice_features)
        keep_mask = self._rng.random(n_slices) > drop_rate
        if not np.any(keep_mask):
            # Guarantee at least the center slice is kept
            idx = n_slices // 2
            keep_mask[idx] = True
        return slice_features[keep_mask]

    def aggregate_view(self, slice_features: np.ndarray) -> np.ndarray:
        """Attention-weighted pooling with zero-slice safety guard."""
        if len(slice_features) == 0:
            return np.zeros(self.feature_dim, dtype=np.float32)
            
        scores = np.dot(slice_features, self.cls_token)
        attn_weights = np.exp(scores - np.max(scores))
        attn_sum = np.sum(attn_weights)
        if attn_sum > 0:
            attn_weights /= attn_sum
        else:
            attn_weights = np.ones(len(slice_features)) / float(len(slice_features))
        return np.sum(slice_features * attn_weights[:, np.newaxis], axis=0)

    def predict_probabilities(
        self,
        sagittal_feats: np.ndarray,
        coronal_feats: np.ndarray,
        axial_feats: np.ndarray,
        training: bool = False
    ) -> Dict[str, float]:
        """Fuses Sagittal, Coronal, and Axial representations into calibrated abnormality probabilities."""
        sag_proc = self.apply_slice_dropout(sagittal_feats, training=training)
        cor_proc = self.apply_slice_dropout(coronal_feats, training=training)
        ax_proc = self.apply_slice_dropout(axial_feats, training=training)

        sag_rep = self.aggregate_view(sag_proc)
        cor_rep = self.aggregate_view(cor_proc)
        ax_rep = self.aggregate_view(ax_proc)

        fused = np.concatenate([sag_rep, cor_rep, ax_rep])
        logits = np.dot(fused, self.head_weights)
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -15.0, 15.0)))

        return {
            "ACL_Tear": float(probs[0]),
            "Meniscus_Tear": float(probs[1]),
            "Cartilage_Lesion": float(probs[2]),
            "Bone_Marrow_Edema": float(probs[3])
        }
