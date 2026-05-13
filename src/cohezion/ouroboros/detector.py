import logging
from typing import Any


logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Logic for identifying coherence degradation and trajectory anomalies.
    """

    def __init__(self, coherence_threshold: float = 0.1, target_coherence: float = 0.5):
        """
        Initializes the detector.

        Args:
            coherence_threshold: Maximum allowable deviation from target.
            target_coherence: The HIHO stability point (0.5).
        """
        self.coherence_threshold = coherence_threshold
        self.target_coherence = target_coherence

    def is_anomaly(self, coherence: float) -> bool:
        """
        Checks if a single coherence score is anomalous.
        """
        deviation = abs(coherence - self.target_coherence)
        return deviation > self.coherence_threshold

    def analyze_batch(self, trajectories: list[dict[Any, Any]]) -> dict[str, Any]:
        """
        Analyzes a batch of trajectories for sustained degradation.

        Returns:
            Dict containing analysis results.
        """
        if not trajectories:
            return {"is_degraded": False, "anomaly_count": 0}

        anomalies = [t for t in trajectories if self.is_anomaly(t.get("coherence", 0.5))]
        anomaly_count = len(anomalies)

        # Consider system degraded if > 50% of recent trajectories are anomalous
        is_degraded = anomaly_count > (len(trajectories) / 2)

        if is_degraded:
            logger.warning(f"System degradation detected! {anomaly_count}/{len(trajectories)} anomalous.")

        return {
            "is_degraded": is_degraded,
            "anomaly_count": anomaly_count,
            "total_count": len(trajectories),
        }
