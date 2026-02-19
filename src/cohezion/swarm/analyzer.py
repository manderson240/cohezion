"""Journey Analyzer for the Quadrature Nexus.

Detects high-impact moments, anomalies, and successful convergences
in agentic journeys.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.swarm.perception import PerceptionEvent

logger = logging.getLogger(__name__)


class JourneyAnalyzer:
    """
    Analyzes perceived journeys to extract insights.
    
    Identifies 'High-Impact Moments' (HIMs) where novelty or 
    performance delta is significant.
    """

    def __init__(self, high_impact_threshold: float = 0.9):
        self.threshold = high_impact_threshold

    def extract_high_impact_moments(self, events: list[PerceptionEvent]) -> list[PerceptionEvent]:
        """
        Filter events to find ones that meet the high-impact threshold.
        """
        hims = [e for e in events if e.impact_score >= self.threshold]
        logger.info(f"[ANALYZER] Extracted {len(hims)} High-Impact Moments from {len(events)} events.")
        return hims

    def analyze_convergence(self, events: list[PerceptionEvent]) -> dict[str, Any]:
        """
        Analyze the trajectory for stability and convergence.
        """
        if not events:
            return {"status": "void", "convergence": 0.0}
            
        scores = [e.impact_score for e in events]
        mean_score = sum(scores) / len(scores)
        
        # Stability: Low variance in the last 3 events
        recent_scores = scores[-3:]
        stability = 1.0 - (max(recent_scores) - min(recent_scores)) if len(recent_scores) > 1 else 1.0
        
        return {
            "status": "stable" if stability > 0.8 else "transient",
            "mean_impact": float(mean_score),
            "stability": float(stability),
            "event_count": len(events)
        }
