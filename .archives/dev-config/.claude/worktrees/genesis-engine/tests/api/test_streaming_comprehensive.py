"""Comprehensive tests for API streaming module.

Generated for P1 coverage of api/streaming.py.
Tests Pydantic models and endpoints.
"""

from __future__ import annotations

from cohezion.api.streaming import (
    SessionListResponse,
    StreamingInferenceRequest,
)


class TestStreamingInferenceRequest:
    """[P0] Tests for StreamingInferenceRequest model."""

    def test_request_creation(self):
        """[P0] Should create request with required fields."""
        request = StreamingInferenceRequest(
            skill_name="test-skill",
            input_text="Test input",
        )

        assert request.skill_name == "test-skill"
        assert request.input_text == "Test input"

    def test_request_with_defaults(self):
        """[P1] Should use default values."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
        )

        assert request.checkpoint_interval == 5
        assert request.max_duration_sec == 7200.0
        assert request.model is None

    def test_request_with_custom_model(self):
        """[P1] Should accept custom model."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
            model="custom-model-v1",
        )

        assert request.model == "custom-model-v1"

    def test_request_with_custom_checkpoints(self):
        """[P1] Should accept custom checkpoint interval."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
            checkpoint_interval=10,
        )

        assert request.checkpoint_interval == 10

    def test_request_serialization(self):
        """[P1] Should serialize to dict."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
            model="model-v1",
            checkpoint_interval=15,
            max_duration_sec=3600.0,
        )

        data = request.model_dump()

        assert data["skill_name"] == "test"
        assert data["input_text"] == "input"
        assert data["model"] == "model-v1"


class TestSessionListResponse:
    """[P0] Tests for SessionListResponse model."""

    def test_response_empty(self):
        """[P0] Should create response with empty sessions."""
        response = SessionListResponse(sessions=[])

        assert response.sessions == []

    def test_response_with_sessions(self):
        """[P0] Should create response with sessions."""
        response = SessionListResponse(sessions=["session-1", "session-2", "session-3"])

        assert len(response.sessions) == 3
        assert "session-1" in response.sessions

    def test_response_serialization(self):
        """[P1] Should serialize to dict."""
        response = SessionListResponse(sessions=["a", "b"])

        data = response.model_dump()

        assert data["sessions"] == ["a", "b"]


class TestEndpointValidation:
    """[P1] Tests for endpoint validation."""

    def test_empty_skill_name_allowed(self):
        """[P1] Should allow empty skill name (no validation)."""
        request = StreamingInferenceRequest(
            skill_name="",
            input_text="input",
        )
        assert request.skill_name == ""

    def test_empty_input_allowed(self):
        """[P1] Should allow empty input (no validation)."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="",
        )
        assert request.input_text == ""

    def test_negative_checkpoint_allowed(self):
        """[P1] Should allow negative checkpoint interval (no validation)."""
        request = StreamingInferenceRequest(
            skill_name="test",
            input_text="input",
            checkpoint_interval=-1,
        )
        assert request.checkpoint_interval == -1
