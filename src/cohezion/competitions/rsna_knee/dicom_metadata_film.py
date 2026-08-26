"""RSNA Knee DICOM Header Feature Extractor & FiLM Conditioning Module (Hardened)."""
from __future__ import annotations
from typing import Dict, Any
import numpy as np

class DICOMMetadataFilmExtractor:
    """Extracts and normalizes DICOM metadata with strictly bounded FiLM affine modulations."""

    def __init__(self, feature_dim: int = 128):
        self.feature_dim = feature_dim
        # Bounded projection weights with tanh scaling to prevent Jacobian gradient explosion
        self.film_gamma_weights = np.ones((4, feature_dim), dtype=np.float32) * 0.05
        self.film_beta_weights = np.zeros((4, feature_dim), dtype=np.float32)

    def extract_tabular_vector(self, metadata: Dict[str, Any]) -> np.ndarray:
        """Extracts tabular vector with safe dictionary key fallbacks."""
        if not metadata:
            return np.zeros(4, dtype=np.float32)

        desc = str(metadata.get("SeriesDescription", "")).upper()
        is_t2 = 1.0 if ("T2" in desc or "PD" in desc) else 0.0
        
        try:
            thickness = float(metadata.get("SliceThickness", 3.0))
        except (ValueError, TypeError):
            thickness = 3.0
        thickness_norm = np.clip((thickness - 3.0) / 2.0, -1.0, 1.0)
        
        try:
            spacing = float(metadata.get("PixelSpacing", 0.5))
        except (ValueError, TypeError):
            spacing = 0.5
        spacing_norm = np.clip((spacing - 0.5) / 0.5, -1.0, 1.0)
        
        try:
            b0 = float(metadata.get("MagneticFieldStrength", 3.0))
        except (ValueError, TypeError):
            b0 = 3.0
        is_3t = 1.0 if b0 >= 2.5 else 0.0

        return np.array([is_t2, thickness_norm, spacing_norm, is_3t], dtype=np.float32)

    def apply_film(self, slice_representation: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """Applies bounded FiLM affine modulation: gamma in [0.5, 1.5], beta in [-0.5, 0.5]."""
        if len(slice_representation) == 0:
            return np.zeros(self.feature_dim, dtype=np.float32)

        tab_vec = self.extract_tabular_vector(metadata)
        # Apply tanh to strictly bound affine scale & shift
        gamma_raw = np.dot(tab_vec, self.film_gamma_weights)
        gamma = 1.0 + 0.5 * np.tanh(gamma_raw)
        beta = 0.5 * np.tanh(np.dot(tab_vec, self.film_beta_weights))
        
        return slice_representation * gamma + beta
