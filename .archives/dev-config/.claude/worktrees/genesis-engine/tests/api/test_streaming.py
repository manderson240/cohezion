"""Tests for api/streaming.py.

Covers streaming inference endpoints and session management.
"""

from __future__ import annotations

from cohezion.api.streaming import (
    SessionListResponse,
    StreamingInferenceRequest,
)


class TestStreamingInferenceRequest:
    """[P0] Unit tests for StreamingInferenceRequest dataclass."""

    def test_request_creation(self):
        """[P0] Should create streaming inference request."""
        request = StreamingInferenceRequest(
            skill_name="test-skill",
            input_text="Test input",
            model="test-model",
        )

        assert request.skill_name == "test-skill"
        assert request.input_text == "Test input"
        assert request.model == "test-model"

    def test_request_with_optional_params(self):
        """[P1] Should accept optional parameters."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
            checkpoint_interval=10,
            max_duration_sec=3600.0,
        )

        assert request.checkpoint_interval == 10
        assert request.max_duration_sec == 3600.0


class TestSessionListResponse:
    """[P0] Unit tests for SessionListResponse dataclass."""

    def test_response_creation(self):
        """[P0] Should create session list response."""
        response = SessionListResponse(sessions=[])

        assert response.sessions == []

    def test_response_with_sessions(self):
        """[P1] Should accept list of sessions."""
        sessions = [
            "session-1",
            "session-2",
        ]

        response = SessionListResponse(sessions=sessions)

        assert len(response.sessions) == 2
        assert response.sessions == ["session-1", "session-2"]
