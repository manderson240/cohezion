"""Unit tests for multi-framework tier modules: sandbox, headless claude, gemini."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.sandbox import (
    SandboxedSubprocess,
    apply_resource_limits,
    sandbox_tempdir,
    sanitized_env,
)


class TestSandboxedEnv:
    def test_strips_telegram_token(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
        env = sanitized_env()
        assert "TELEGRAM_BOT_TOKEN" not in env

    def test_strips_anthropic_key_by_default(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
        env = sanitized_env()
        assert "ANTHROPIC_API_KEY" not in env

    def test_preserves_anthropic_when_allowed(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
        env = sanitized_env(allow_anthropic=True)
        assert "ANTHROPIC_API_KEY" in env
        assert env["ANTHROPIC_API_KEY"] == "sk-secret"

    def test_preserves_gemini_when_allowed(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
        env = sanitized_env(allow_gemini=True)
        assert "GEMINI_API_KEY" in env

    def test_preserves_path(self, monkeypatch):
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        env = sanitized_env()
        assert "PATH" in env

    def test_strips_aws_keys(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        env = sanitized_env()
        assert "AWS_ACCESS_KEY_ID" not in env
        assert "AWS_SECRET_ACCESS_KEY" not in env

    def test_strips_sudo_password(self, monkeypatch):
        monkeypatch.setenv("SUDO_PASSWORD", "admin123")
        env = sanitized_env()
        assert "SUDO_PASSWORD" not in env


class TestSandboxTempdir:
    def test_creates_directory(self):
        tmpdir = sandbox_tempdir()
        try:
            assert tmpdir.exists()
            assert tmpdir.is_dir()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_has_sandbox_prefix(self):
        tmpdir = sandbox_tempdir()
        try:
            assert "cohezion_sandbox" in tmpdir.name
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSandboxedSubprocess:
    def test_creates_and_cleans_tmpdir(self):
        with SandboxedSubprocess() as sb:
            tmpdir = Path(sb.cwd)
            assert tmpdir.exists()
        assert not tmpdir.exists()

    def test_env_is_sanitized(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "leaked-token")
        with SandboxedSubprocess() as sb:
            assert "TELEGRAM_BOT_TOKEN" not in sb.env

    def test_cwd_is_inside_tmp(self):
        with SandboxedSubprocess() as sb:
            assert sb.cwd.startswith("/tmp") or "tmp" in sb.cwd

    def test_cleanup_on_exception(self):
        with pytest.raises(ValueError), SandboxedSubprocess() as sb:
            tmpdir = Path(sb.cwd)
            raise ValueError("test exception")
        assert not tmpdir.exists()


class TestApplyResourceLimits:
    def test_is_callable(self):
        """Verify apply_resource_limits is callable without triggering it in test process.

        We do NOT call apply_resource_limits() directly in tests — it sets RLIMIT_AS
        on the current process, which would cap pytest's memory and cause MemoryError
        in pytest's assertion rewriting module.
        """
        import inspect

        assert callable(apply_resource_limits)
        sig = inspect.signature(apply_resource_limits)
        assert len(sig.parameters) == 0  # no required args


class TestHeadlessClaudeTier:
    def test_imports_cleanly(self):
        from cohezion.inference.headless_claude_tier import build_claude_tier

        tier = build_claude_tier()
        assert tier.label == "headless-claude"

    def test_returns_error_when_claude_not_found(self):
        import asyncio

        from cohezion.inference.headless_claude_tier import HeadlessClaudeTier

        tier = HeadlessClaudeTier()
        with patch("subprocess.run", side_effect=FileNotFoundError("claude not found")):
            with patch("cohezion.inference.sandbox.SandboxedSubprocess") as mock_sb:
                mock_sb.return_value.__enter__ = MagicMock(
                    return_value=MagicMock(env={}, cwd="/tmp")
                )
                mock_sb.return_value.__exit__ = MagicMock(return_value=False)
                result = asyncio.run(tier.run("test prompt"))
        assert result.error is not None or result.text == ""

    def test_label_is_headless_claude(self):
        from cohezion.inference.headless_claude_tier import HeadlessClaudeTier

        t = HeadlessClaudeTier(label="my-claude")
        assert t.label == "my-claude"


class TestGeminiCliTier:
    def test_imports_cleanly(self):
        from cohezion.inference.gemini_cli_tier import GeminiCliTier

        tier = GeminiCliTier()
        assert tier.label == "gemini-cli"

    def test_returns_error_when_gemini_not_found(self):
        import asyncio

        from cohezion.inference.gemini_cli_tier import GeminiCliTier

        tier = GeminiCliTier(persist=False)
        with patch("subprocess.run", side_effect=FileNotFoundError("gemini not found")):
            result = asyncio.run(tier.run("test prompt"))
        assert result.error is not None

    def test_default_model_is_flash(self):
        from cohezion.inference.gemini_cli_tier import GeminiCliTier

        tier = GeminiCliTier()
        assert "flash" in tier.model.lower()


class TestGeminiADKTier:
    def test_imports_cleanly(self):
        from cohezion.inference.gemini_cli_tier import GeminiADKTier

        tier = GeminiADKTier()
        assert tier.label == "gemini-adk"

    def test_returns_error_when_adk_not_installed(self):
        import asyncio

        from cohezion.inference.gemini_cli_tier import GeminiADKTier

        tier = GeminiADKTier(persist=False)
        with patch.dict("sys.modules", {"google.adk.agents": None}):
            result = asyncio.run(tier.run("test prompt"))
        assert result.error is not None or result.text == ""
