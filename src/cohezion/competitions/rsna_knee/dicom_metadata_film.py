"""RSNA Knee DICOM Header Feature Extractor & FiLM Conditioning Module.

Extracts series description, slice thickness, pixel spacing, and magnetic field
strength to condition multi-view MIL sequence representations.
"""

from __future__ import annotations
from typing import Dict, Any, List
import numpy as np

class DICOMMetadataFilmExtractor:
    """Extracts and normalizes DICOM metadata for Feature-wise Linear Modulation (FiLM)."""

    def __init__(self, feature_dim: int = 128):
        self.feature_dim = feature_dim
        # Linear projection weights: 4 tabular metadata features -> gamma (scale) & beta (shift)
        self.film_gamma_weights = np.ones((4, feature_dim), dtype=np.float32) * 0.1
        self.film_beta_weights = np.zeros((4, feature_dim), dtype=np.float32)

    def extract_tabular_vector(self, metadata: Dict[str, Any]) -> np.ndarray:
        """Extracts normalized tabular vector [is_t1_t2, slice_thickness_norm, spacing_norm, is_3t]."""
        desc = str(metadata.get("SeriesDescription", "")).upper()
        is_t2 = 1.0 if "T2" in desc or "PD" in desc else 0.0
        
        thickness = float(metadata.get("SliceThickness", 3.0))
        thickness_norm = np.clip((thickness - 3.0) / 2.0, -1.0, 1.0)
        
        spacing = float(metadata.get("PixelSpacing", 0.5))
        spacing_norm = np.clip((spacing - 0.5) / 0.5, -1.0, 1.0)
        
        b0 = float(metadata.get("MagneticFieldStrength", 3.0))
        is_3t = 1.0 if b0 >= 2.5 else 0.0

        return np.array([is_t2, thickness_norm, spacing_norm, is_3t], dtype=np.float32)

    def apply_film(self, slice_representation: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """Applies FiLM affine modulation: h_modulated = gamma(x_meta) * h + beta(x_meta)."""
        tab_vec = self.extract_tabular_vector(metadata)
        gamma = 1.0 + np.dot(tab_vec, self.film_gamma_weights)
        beta = np.dot(tab_vec, self.film_beta_weights)
        return slice_representation * gamma + beta
