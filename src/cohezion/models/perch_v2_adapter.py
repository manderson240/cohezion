"""
Google Perch v2 Adapter for 1536-D Audio Embeddings.
Based on Perch 2.0 (Google Research).
"""

import os
import logging
from typing import Any, List, Dict, Optional

import numpy as np
import tensorflow as tf
try:
    import tensorflow_hub as hub
except ImportError:
    hub = None

logger = logging.getLogger(__name__)

# Model URL for Perch v2 (Hoplite/Global)
PERCH_V2_URL = "https://www.kaggle.com/models/google/bird-vocalization-classifier/tensorFlow2/bird-vocalization-classifier/4"

class PerchV2Adapter:
    """Adapter for Google Perch v2 model."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_url = model_path or PERCH_V2_URL
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Load the TFLite or TFHub model."""
        try:
            if hub:
                logger.info(f"Loading Perch v2 from: {self.model_url}")
                self.model = hub.load(self.model_url)
                logger.info("Perch v2 loaded successfully.")
            else:
                logger.warning("tensorflow_hub not installed. Model loading deferred.")
        except Exception as e:
            logger.error(f"Failed to load Perch v2: {e}")

    def extract_embeddings(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extract 1536-D embeddings from 32kHz audio data.
        audio_data: float32 array of shape (N,)
        """
        if self.model is None:
            raise RuntimeError("Perch v2 model not loaded.")
            
        # Perch expects [batch, samples]
        if len(audio_data.shape) == 1:
            audio_data = audio_data[np.newaxis, :]
            
        # Model returns (logits, embeddings)
        _, embeddings = self.model(audio_data)
        return embeddings.numpy()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = PerchV2Adapter()
    print("Perch v2 Adapter Initialized.")
