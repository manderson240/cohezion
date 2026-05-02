"""Tests for Metacognitive Intent Capture middleware (Story 3.3, FR6).

Every agent must log a JSON payload explaining its 512D intent before
executing a 12D physical state change. State changes without valid intent
are blocked and logged as Silent Intent Violations.
"""

from __future__ import annotations

import json

import numpy as np

from cohezion.universe.intent_capture import (
    IntentCapture,
    IntentPayload,
    StateChangeRequest,
)


# ── IntentPayload Validation ──────────────────────────────────────


class TestIntentPayload:
    def test_valid_payload(self):
        """A payload with agent_id, intent text, and 12D vector is valid."""
        payload = IntentPayload(
            agent_id="researcher-1",
            intent="Exploring high-coherence region for pattern discovery",
            latent_vector=np.random.default_rng(0).standard_normal(12).tolist(),
        )
        assert payload.is_valid()

    def test_missing_intent_text_is_invalid(self):
        """Empty intent string should be rejected."""
        payload = IntentPayload(
            agent_id="researcher-1",
            intent="",
            latent_vector=[0.0] * 12,
        )
        assert not payload.is_valid()

    def test_missing_agent_id_is_invalid(self):
        payload = IntentPayload(
            agent_id="",
            intent="Some intent",
            latent_vector=[0.0] * 12,
        )
        assert not payload.is_valid()

    def test_wrong_vector_dimension_is_invalid(self):
        """Vector must be 12D (axiomatic manifold dimension)."""
        payload = IntentPayload(
            agent_id="researcher-1",
            intent="Testing",
            latent_vector=[0.0] * 5,  # Wrong dimension
        )
        assert not payload.is_valid()

    def test_payload_serializes_to_json(self):
        """IntentPayload must be JSON-serializable for audit logging."""
        payload = IntentPayload(
            agent_id="researcher-1",
            intent="Exploring manifold",
            latent_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
        )
        data = payload.to_dict()
        roundtrip = json.loads(json.dumps(data))
        assert roundtrip["agent_id"] == "researcher-1"
        assert len(roundtrip["latent_vector"]) == 12


# ── IntentCapture Middleware ──────────────────────────────────────


class TestIntentCaptureMiddleware:
    def test_valid_request_is_allowed(self):
        """A state change with valid intent should be approved."""
        capture = IntentCapture()
        request = StateChangeRequest(
            intent=IntentPayload(
                agent_id="engineer-1",
                intent="Adjusting coherence toward HIHO target",
                latent_vector=np.random.default_rng(1).standard_normal(12).tolist(),
            ),
            proposed_state=np.random.default_rng(2).standard_normal(12),
        )

        result = capture.check(request)
        assert result.approved is True
        assert result.violation is None

    def test_missing_intent_is_blocked(self):
        """A state change without intent payload is blocked."""
        capture = IntentCapture()
        request = StateChangeRequest(
            intent=None,
            proposed_state=np.random.default_rng(0).standard_normal(12),
        )

        result = capture.check(request)
        assert result.approved is False
        assert result.violation is not None
        assert result.violation.violation_type == "missing_intent"

    def test_invalid_intent_is_blocked(self):
        """A state change with malformed intent is blocked."""
        capture = IntentCapture()
        request = StateChangeRequest(
            intent=IntentPayload(
                agent_id="",
                intent="",
                latent_vector=[],
            ),
            proposed_state=np.random.default_rng(0).standard_normal(12),
        )

        result = capture.check(request)
        assert result.approved is False
        assert result.violation.violation_type == "invalid_intent"

    def test_violations_are_logged(self):
        """Violations should be accumulated for Ouroboros training."""
        capture = IntentCapture()

        # Two violations
        for _ in range(2):
            capture.check(
                StateChangeRequest(
                    intent=None,
                    proposed_state=np.zeros(12),
                )
            )

        assert len(capture.violations) == 2

    def test_approved_requests_are_not_violations(self):
        """Approved requests should not appear in violation log."""
        capture = IntentCapture()
        request = StateChangeRequest(
            intent=IntentPayload(
                agent_id="agent-1",
                intent="Valid action",
                latent_vector=[0.5] * 12,
            ),
            proposed_state=np.zeros(12),
        )

        capture.check(request)
        assert len(capture.violations) == 0

    def test_get_training_data_returns_violations(self):
        """get_training_data() returns violations for Ouroboros fine-tuning."""
        capture = IntentCapture()

        # One violation
        capture.check(StateChangeRequest(intent=None, proposed_state=np.zeros(12)))

        data = capture.get_training_data()
        assert len(data) == 1
        assert "violation_type" in data[0]
        assert "timestamp" in data[0]
