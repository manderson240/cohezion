"""Retrospection Validator — cross-checks summary claims against execution traces.

Addresses W2 trust gap: verifies that RetrospectionEngine summaries reflect
actual journey data rather than fabricated (OLIF-vulnerable) claims.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_COHERENCE_TOLERANCE = 0.05  # Allow ±5% rounding error on coherence deltas
_MIN_SUCCESS_COHERENCE = 0.3  # Threshold for a "successful" run


@dataclass
class ValidationResult:
    valid: bool
    discrepancies: list[str]
    confidence: float  # 0-1: fraction of verifiable claims that matched


class RetrospectionValidator:
    """Cross-check retrospection summaries against actual journey data.

    Accepts the dict form produced by RetrospectionSummary.to_dict() and a
    list of journey-point dicts (keys: coherence, timestamp, metadata.success).
    Always returns a ValidationResult — never raises.
    """

    def validate_summary(
        self,
        summary: dict,
        journey_points: list[dict],
    ) -> ValidationResult:
        """Cross-check summary claims against journey data."""
        discrepancies: list[str] = []
        checks_attempted = 0
        checks_passed = 0

        if not journey_points:
            logger.warning("validate_summary: no journey points — cannot verify any claims")
            return ValidationResult(valid=True, discrepancies=[], confidence=0.0)

        first = journey_points[0]
        last = journey_points[-1]

        # --- Check 1: coherence_delta ---
        claimed_delta = summary.get("coherence_delta")
        if claimed_delta is not None:
            checks_attempted += 1
            actual_delta = last.get("coherence", 0.0) - first.get("coherence", 0.0)
            if abs(claimed_delta - actual_delta) > _COHERENCE_TOLERANCE:
                msg = (
                    f"coherence_delta mismatch: summary claims {claimed_delta:.3f}, "
                    f"journey shows {actual_delta:.3f} "
                    f"(first={first.get('coherence', 0.0):.3f}, "
                    f"last={last.get('coherence', 0.0):.3f})"
                )
                discrepancies.append(msg)
                logger.warning("RetrospectionValidator: %s", msg)
            else:
                checks_passed += 1

        # --- Check 2: step count ---
        claimed_steps = summary.get("steps_executed")
        if claimed_steps is not None:
            checks_attempted += 1
            actual_steps = len(journey_points)
            if claimed_steps != actual_steps:
                msg = (
                    f"steps_executed mismatch: summary claims {claimed_steps}, "
                    f"journey has {actual_steps} points"
                )
                discrepancies.append(msg)
                logger.warning("RetrospectionValidator: %s", msg)
            else:
                checks_passed += 1

        # --- Check 3: success vs final coherence ---
        claimed_success = summary.get("success")
        if claimed_success is not None:
            checks_attempted += 1
            final_coherence = last.get("coherence", 0.0)
            coherence_supports_success = final_coherence > _MIN_SUCCESS_COHERENCE
            if claimed_success and not coherence_supports_success:
                msg = (
                    f"success=True but final coherence {final_coherence:.3f} "
                    f"<= threshold {_MIN_SUCCESS_COHERENCE}"
                )
                discrepancies.append(msg)
                logger.warning("RetrospectionValidator: %s", msg)
            else:
                checks_passed += 1

        # --- Check 4: duration vs timestamp range ---
        claimed_duration = summary.get("duration_seconds")
        if claimed_duration is not None:
            checks_attempted += 1
            first_ts = first.get("timestamp", 0.0)
            last_ts = last.get("timestamp", 0.0)
            actual_duration = last_ts - first_ts
            if abs(claimed_duration - actual_duration) > max(1.0, actual_duration * 0.1):
                msg = (
                    f"duration_seconds mismatch: summary claims {claimed_duration:.1f}s, "
                    f"journey timestamps span {actual_duration:.1f}s"
                )
                discrepancies.append(msg)
                logger.warning("RetrospectionValidator: %s", msg)
            else:
                checks_passed += 1

        confidence = checks_passed / checks_attempted if checks_attempted > 0 else 0.0
        return ValidationResult(
            valid=len(discrepancies) == 0,
            discrepancies=discrepancies,
            confidence=confidence,
        )
