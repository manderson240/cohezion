import logging
import time

import numpy as np
import psutil
import torch

logger = logging.getLogger(__name__)


class PlanetaryInterface:
    """
    Planetary Interface (Gateway 29).

    Monitors system-wide 'Vital Signs' mapped to Universal Constants.
    - As Above, So Below: System metrics -> Cosmic Analogues.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.start_time = time.time()
        self.request_timestamps: list[float] = []
        self.entropy_samples: list[float] = []

    def report_activity(self):
        """Record a unit of cognitive work."""
        self.request_timestamps.append(time.time())
        # Prune old timestamps (> 60s)
        now = time.time()
        self.request_timestamps = [t for t in self.request_timestamps if now - t <= 60]

    def report_entropy_flux(self, vector: torch.Tensor | np.ndarray):
        """Record the complexity/entropy of a thought."""
        if isinstance(vector, np.ndarray):
            vector = torch.from_numpy(vector).float()

        # Variance as proxy for entropy
        entropy = torch.var(vector).item()
        self.entropy_samples.append(entropy)
        if len(self.entropy_samples) > 100:
            self.entropy_samples.pop(0)

    def get_cosmic_constants(self) -> dict[str, float]:
        """
        Return current Universal Constants.
        """
        # 1. Cosmic Temperature (Activity Rate)
        # requests per minute
        temp = len(self.request_timestamps)

        # 2. Universal Entropy (Avg Variance)
        if self.entropy_samples:
            entropy = sum(self.entropy_samples) / len(self.entropy_samples)
        else:
            entropy = 0.08  # Default baseline

        # 3. Vacuum Energy (Free System Resources)
        # Mapped from CPU/RAM availability
        cpu_idle = 100 - psutil.cpu_percent()
        ram_avail = psutil.virtual_memory().available / (1024**3)  # GB
        vacuum_energy = (cpu_idle / 100) * min(1.0, ram_avail / 32.0)  # Normalized 0-1

        return {
            "CosmicTemperature": float(temp),
            "UniversalEntropy": float(entropy),
            "VacuumEnergy": float(vacuum_energy),
        }


def get_planetary_interface() -> PlanetaryInterface:
    return PlanetaryInterface()
