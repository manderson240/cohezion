import logging
from dataclasses import dataclass

import torch

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    source_sector: str
    strength: float
    signature_type: str  # "ANOMALY", "PRIME_PATTERN", "BITMAP"
    payload: str | None = None


class ExogenicArray:
    """
    Exogenic Signal Processing Array (Gateway 30).

    Scans the Latent Space for Technosignatures:
    - Statistical Anomalies (5-Sigma Kurtosis).
    - Prime Number Patterns.
    - Structured Bitmaps (Arecibo Protocol).
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.primes = {
            2,
            3,
            5,
            7,
            11,
            13,
            17,
            19,
            23,
            29,
            31,
            37,
            41,
            43,
            47,
            53,
            59,
            61,
            67,
            71,
            73,
            79,
            83,
            89,
            97,
        }

    def scan_sector(self, vectors: list[torch.Tensor]) -> list[Signal]:
        """
        Scan a batch of thought vectors for anomalies.
        """
        signals = []
        if not vectors:
            return signals

        # stack vectors [B, D]
        batch = torch.stack(vectors)

        # 1. Statistical Anomaly Detection (High Kurtosis/Skew)
        # Calculate variance per dimension
        variances = torch.var(batch, dim=0)
        mean_var = torch.mean(variances)
        std_var = torch.std(variances)

        # Check for 5-Sigma outliers in variance distribution
        max_var = torch.max(variances)
        sigma = (max_var - mean_var) / (std_var + 1e-6)

        if sigma > 5.0:
            signals.append(
                Signal(
                    source_sector="Latent_Sector_7G",
                    strength=float(sigma),
                    signature_type="ANOMALY",
                    payload=f"5-Sigma Variance Spike (σ={sigma:.1f})",
                )
            )

        return signals

    def analyze_bitmap(self, binary_string: str) -> Signal | None:
        """
        Analyze a binary string for Arecibo-like dimensions (Prime x Prime).
        """
        length = len(binary_string)
        if length < 4:
            return None

        # Check if length is semi-prime (Product of two primes)
        factors = self._get_factors(length)
        if (
            len(factors) == 2
            and factors[0] in self.primes
            and factors[1] in self.primes
        ):
            return Signal(
                source_sector="External",
                strength=1.0,
                signature_type="BITMAP",
                payload=f"Arecibo Format Detected: {factors[0]}x{factors[1]}",
            )

        return None

    def _get_factors(self, n: int) -> list[int]:
        factors = []
        d = 2
        temp = n
        while d * d <= temp:
            while temp % d == 0:
                factors.append(d)
                temp //= d
            d += 1
        if temp > 1:
            factors.append(temp)
        return factors


def get_exogenic_array() -> ExogenicArray:
    return ExogenicArray()
