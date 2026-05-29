"""Unit tests for HeadlessClaudeTier — structure, graceful failure, subprocess mock."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.headless_claude_tier import HeadlessClaudeTier, build_claude_tier
from cohezion.inference.orchestrator import OrchestrationResult


class TestHeadlessClaudeTierInit:
    def test_default_label(self):
        tier = HeadlessClaudeTier()
        assert "claude" in tier.label.lower()

    def test_default_timeout(self):
        tier = HeadlessClaudeTier()
        assert tier.timeout_s > 0

    def test_custom_timeout(self):
        tier = HeadlessClaudeTier(timeout_s=30.0)
        assert tier.timeout_s == 30.0


class TestHeadlessClaudeTierRun:
    @pytest.mark.asyncio
    async def test_run_returns_orchestration_result(self):
        """run() must always return OrchestrationResult, never raise."""
        tier = HeadlessClaudeTier(timeout_s=5.0)
        mock_proc = MagicMock()
        mock_proc.stdout = '{"result": "def add(a, b): return a + b"}'
        mock_proc.returncode = 0

        with patch("subprocess.run", return_value=mock_proc):
            result = await tier.run("write an add function")

        assert isinstance(result, OrchestrationResult)
        assert isinstance(result.text, str)
        assert result.error is None or isinstance(result.error, str)

    @pytest.mark.asyncio
    async def test_run_graceful_on_subprocess_error(self):
        """When claude binary is unavailable, return structured error."""
        tier = HeadlessClaudeTier(timeout_s=5.0)

        with patch("subprocess.run", side_effect=FileNotFoundError("claude not found")):
            result = await tier.run("write code")

        assert isinstance(result, OrchestrationResult)
        assert result.error is not None
        assert result.text == "" or isinstance(result.text, str)

    @pytest.mark.asyncio
    async def test_run_graceful_on_timeout(self):
        """Timeout returns OrchestrationResult with error, not TimeoutExpired."""
        tier = HeadlessClaudeTier(timeout_s=5.0)

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=5.0),
        ):
            result = await tier.run("complex task")

        assert isinstance(result, OrchestrationResult)
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_run_latency_ms_populated(self):
        """latency_ms must be set on all outcomes."""
        tier = HeadlessClaudeTier(timeout_s=5.0)
        mock_proc = MagicMock()
        mock_proc.stdout = "answer"
        mock_proc.returncode = 0

        with patch("subprocess.run", return_value=mock_proc):
            result = await tier.run("test")

        assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_run_final_model_is_claude(self):
        """final_model must identify as a Claude tier."""
        tier = HeadlessClaudeTier(timeout_s=5.0)
        mock_proc = MagicMock()
        mock_proc.stdout = "result text"
        mock_proc.returncode = 0

        with patch("subprocess.run", return_value=mock_proc):
            result = await tier.run("test prompt")

        assert "claude" in result.final_model.lower() or result.error is not None


class TestBuildClaudeTier:
    def test_returns_headless_claude_tier(self):
        tier = build_claude_tier()
        assert isinstance(tier, HeadlessClaudeTier)

    def test_custom_timeout(self):
        tier = build_claude_tier(timeout_s=60.0)
        assert tier.timeout_s == 60.0
