import logging
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Wavelength(Enum):
    RED = 600  # Error/Danger/Blockage
    GREEN = 550  # Success/Harmony
    BLUE = 450  # Information/Data Transfer
    UV = 300  # High-Energy/Quantum Event (ZPE)


@dataclass
class BioSignal:
    wavelength: Wavelength
    intensity: float  # 0.0 to 1.0
    source_agent: str
    timestamp: float
    metadata: dict[str, str]


class LightField:
    """
    Biophotonic Signaling Field (Gateway 26).

    A non-verbal communication buffer where agents can "emit" light
    signals to indicate status without polluting the text logs.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.buffer: list[BioSignal] = []
        self.max_buffer = 100

    def emit(self, signal: BioSignal):
        """Emit a light signal into the field."""
        self.buffer.append(signal)
        # Sliding window
        if len(self.buffer) > self.max_buffer:
            self.buffer.pop(0)

        logger.debug(
            f"🔦 Signal Emitted: {signal.wavelength.name} ({signal.intensity:.2f}) from {signal.source_agent}"
        )

    def scan(self, window_seconds: float = 5.0) -> list[BioSignal]:
        """
        Scan the field for recent signals.
        Returns signals from the last `window_seconds`.
        """
        now = time.time()
        return [s for s in self.buffer if (now - s.timestamp) <= window_seconds]

    def get_spectrum_summary(self) -> dict[str, float]:
        """
        Get average intensity per wavelength in current buffer.
        Useful for "sensing" the overall mood of the swarm.
        """
        summary = {w.name: 0.0 for w in Wavelength}
        counts = {w.name: 0 for w in Wavelength}

        for s in self.buffer:
            summary[s.wavelength.name] += s.intensity
            counts[s.wavelength.name] += 1

        # Average
        for k in summary:
            if counts[k] > 0:
                summary[k] /= counts[k]

        return summary


def get_light_field() -> LightField:
    return LightField()
