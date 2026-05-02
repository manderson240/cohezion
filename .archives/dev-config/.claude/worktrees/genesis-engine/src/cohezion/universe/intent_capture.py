"""Metacognitive Intent Capture middleware (Story 3.3, FR6).

Every agent must log a JSON payload explaining its intent before executing
a 12D physical state change. This creates an auditable trail of agent
reasoning and blocks "silent" state mutations.

Violations are captured as training data for the Ouroboros fine-tuning loop,
enabling the system to learn from its own intent-action misalignments.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)

# Axiomatic manifold dimension
MANIFOLD_DIM = 12


@dataclass
class IntentPayload:
    """JSON payload an agent must provide before a state change."""

    agent_id: str
    intent: str  # Human-readable reasoning
    latent_vector: list[float]  # 12D axiomatic vector

    def is_valid(self) -> bool:
        """Check structural validity of the intent payload."""
        if not self.agent_id or not self.agent_id.strip():
            return False
        if not self.intent or not self.intent.strip():
            return False
        if len(self.latent_vector) != MANIFOLD_DIM:
            return False
        return True

    def to_dict(self) -> dict:
        """Serialize for audit logging."""
        return {
            "agent_id": self.agent_id,
            "intent": self.intent,
            "latent_vector": self.latent_vector,
        }


@dataclass
class IntentViolation:
    """A blocked state change due to missing or invalid intent."""

    violation_type: str  # "missing_intent" | "invalid_intent"
    agent_id: str | None
    timestamp: float = field(default_factory=time.time)
    details: str = ""


@dataclass
class StateChangeRequest:
    """A proposed 12D state change with optional intent payload."""

    intent: IntentPayload | None
    proposed_state: np.ndarray


@dataclass
class CheckResult:
    """Result of intent capture check."""

    approved: bool
    violation: IntentViolation | None = None


class IntentCapture:
    """Middleware that validates intent before allowing state changes.

    Blocks state changes that lack valid intent payloads and accumulates
    violations as training data for the Ouroboros fine-tuning loop.
    """

    def __init__(self) -> None:
        self._violations: list[IntentViolation] = []

    @property
    def violations(self) -> list[IntentViolation]:
        return list(self._violations)

    def check(self, request: StateChangeRequest) -> CheckResult:
        """Validate a state change request against intent requirements."""
        if request.intent is None:
            violation = IntentViolation(
                violation_type="missing_intent",
                agent_id=None,
                details="State change proposed without intent payload",
            )
            self._violations.append(violation)
            logger.warning("Silent Intent Violation: %s", violation.details)
            return CheckResult(approved=False, violation=violation)

        if not request.intent.is_valid():
            violation = IntentViolation(
                violation_type="invalid_intent",
                agent_id=request.intent.agent_id or None,
                details="Malformed intent payload (missing fields or wrong vector dimension)",
            )
            self._violations.append(violation)
            logger.warning(
                "Invalid Intent Violation from %s: %s",
                request.intent.agent_id,
                violation.details,
            )
            return CheckResult(approved=False, violation=violation)

        logger.debug(
            "Intent approved for %s: %s",
            request.intent.agent_id,
            request.intent.intent[:80],
        )
        return CheckResult(approved=True)

    def get_training_data(self) -> list[dict]:
        """Export violations as training data for Ouroboros."""
        return [
            {
                "violation_type": v.violation_type,
                "agent_id": v.agent_id,
                "timestamp": v.timestamp,
                "details": v.details,
            }
            for v in self._violations
        ]

    def clear(self) -> None:
        """Clear violation history after Ouroboros consumption."""
        self._violations.clear()
