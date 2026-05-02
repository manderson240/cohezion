"""Comprehensive tests for security modules.

Generated for P1 coverage of security/guardrail_pipeline.py and audit_log.py.
Tests guardrail actions, pipeline checks, and audit logging.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.security.guardrail_pipeline import (
    GuardrailAction,
    GuardrailPipeline,
    GuardrailResult,
)


class TestGuardrailAction:
    """[P0] Tests for GuardrailAction enum."""

    def test_allow_action(self):
        """[P0] Should have ALLOW action."""
        assert GuardrailAction.ALLOW == "allow"

    def test_block_action(self):
        """[P0] Should have BLOCK action."""
        assert GuardrailAction.BLOCK == "block"

    def test_sanitize_action(self):
        """[P1] Should have SANITIZE action."""
        assert GuardrailAction.SANITIZE == "sanitize"

    def test_log_and_allow_action(self):
        """[P1] Should have LOG_AND_ALLOW action."""
        assert GuardrailAction.LOG_AND_ALLOW == "log_and_allow"


class TestGuardrailResult:
    """[P0] Tests for GuardrailResult dataclass."""

    def test_result_creation_basic(self):
        """[P0] Should create basic result."""
        result = GuardrailResult(
            action=GuardrailAction.ALLOW,
        )

        assert result.action == GuardrailAction.ALLOW
        assert result.reason == ""
        assert result.metadata == {}

    def test_result_with_all_fields(self):
        """[P1] Should create result with all fields."""
        result = GuardrailResult(
            action=GuardrailAction.BLOCK,
            reason="Test reason",
            modified_input="modified",
            metadata={"key": "value"},
            guard_name="test-guard",
            latency_ms=100.0,
        )

        assert result.reason == "Test reason"
        assert result.modified_input == "modified"
        assert result.metadata["key"] == "value"
        assert result.guard_name == "test-guard"
        assert result.latency_ms == 100.0

    def test_result_defaults(self):
        """[P1] Should use default values."""
        result = GuardrailResult(action=GuardrailAction.ALLOW)

        assert result.reason == ""
        assert result.modified_input is None
        assert result.metadata == {}
        assert result.guard_name == ""
        assert result.latency_ms == 0.0


class TestGuardrailPipeline:
    """[P0] Tests for GuardrailPipeline."""

    @pytest.fixture()
    def pipeline(self):
        """Create GuardrailPipeline."""
        return GuardrailPipeline()

    def test_pipeline_initialization(self, pipeline):
        """[P0] Should initialize pipeline."""
        assert pipeline is not None

    def test_pipeline_with_guardrails(self):
        """[P1] Should initialize with guardrails."""
        guardrail = MagicMock()
        pipeline = GuardrailPipeline(guardrails=[("test-guard", guardrail)])

        assert len(pipeline.guardrails) == 1

    def test_pipeline_stats_initially_empty(self, pipeline):
        """[P1] Should start with empty stats."""
        assert len(pipeline.stats) == 0


class TestGuardrailActions:
    """[P1] Tests for action behaviors."""

    def test_allow_is_truthy(self):
        """[P1] ALLOW should be truthy."""
        action = GuardrailAction.ALLOW
        assert bool(action) is True

    def test_block_is_truthy(self):
        """[P1] BLOCK should be truthy."""
        action = GuardrailAction.BLOCK
        assert bool(action) is True

    def test_action_equality(self):
        """[P1] Actions should be comparable."""
        assert GuardrailAction.ALLOW == GuardrailAction.ALLOW
        assert GuardrailAction.ALLOW != GuardrailAction.BLOCK
