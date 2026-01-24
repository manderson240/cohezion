import torch
import torch.nn.functional as F
import logging
import random
import numpy as np

logger = logging.getLogger(__name__)

class RealityStabilizer:
    """
    HIHO Reality Stability Protocol (Gateway 27).

    Ensures that agent thought vectors maintain "Half-In-Half-Out" coherence (0.5).
    - Too Static (> 0.6): Reality becomes rigid/stagnant.
    - Too Chaotic (< 0.4): Reality dissolves into noise.

    The Stabilizer injects Order or Chaos to restore equilibrium.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RealityStabilizer, cls).__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.target_coherence = 0.5
        self.tolerance = 0.1

    def calculate_stability(self, vector: torch.Tensor | np.ndarray) -> float:
        """
        Calculate the stability/coherence of a thought vector.
        We approximate this by the variance/entropy of the vector elements.
        - High variance/entropy = Chaos (Low Coherence)
        - Low variance/entropy = Order (High Coherence)

        Normalized to 0.0 (Chaos) to 1.0 (Static).
        """
        if isinstance(vector, np.ndarray):
            vector = torch.from_numpy(vector).float()

        # Normalize to 0-1 range for entropy calc
        v_min = vector.min()
        v_max = vector.max()
        if v_max - v_min == 0:
            return 1.0 # Static

        v_norm = (vector - v_min) / (v_max - v_min)

        # Simple variance-based coherence metric
        # High variance -> diversity -> 0.5 is ideal balance
        var = torch.var(v_norm).item()

        # Map variance to 0-1 scale intuitively
        # Variance of uniform dist [0,1] is 1/12 (~0.083).
        # We define Max Chaos as var ~ 0.25 (binary 0/1 mix).
        # We inverse map so 1.0 is static (var=0)

        coherence = max(0.0, 1.0 - (var * 4.0))
        return coherence

    def stabilize(self, vector: torch.Tensor | np.ndarray) -> torch.Tensor:
        """
        Adjust vector to nudge coherence toward 0.5.
        """
        if isinstance(vector, np.ndarray):
            vector = torch.from_numpy(vector).float()

        coherence = self.calculate_stability(vector)

        if abs(coherence - self.target_coherence) <= self.tolerance:
            return vector # Stable

        logger.info(f"⚖️ Reality Instability Detected (Coherence: {coherence:.2f}). Stabilizing...")

        if coherence > 0.6:
            # Too Static -> Inject Chaos (Noise)
            noise = torch.randn_like(vector) * 0.2
            return vector + noise

        elif coherence < 0.4:
            # Too Chaotic -> Inject Order (Smoothing)
            return F.avg_pool1d(vector.unsqueeze(0).unsqueeze(0), kernel_size=3, stride=1, padding=1).squeeze()

        return vector

def get_reality_stabilizer() -> RealityStabilizer:
    return RealityStabilizer()
