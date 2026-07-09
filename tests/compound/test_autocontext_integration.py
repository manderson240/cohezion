"""Tests for autocontext integration in CompoundExecutor.

Follows TDD: tests verify that compound sessions automatically initialize
autocontext on warm-start and archive on clean-shutdown.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.context_integration import (
    CompoundContextMixin,
)
from cohezion.compound.executor import CompoundExecutor
from cohezion.core.mcp_client import MCPClient


class TestAutocontextInit:
    """[P0] Tests for init_autocontext()."""

    def test_creates_manifest_when_missing(self, tmp_path: Path):
        """Should create manifest.json if .context/traceability/ doesn't exist."""
        ctx = tmp_path / ".context"
        trace = ctx / "traceability"
        manifest = trace / "manifest.json"

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        result = obj.init_autocontext()

        assert result == manifest
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["version"] == "1.0.0"
        assert "created_at" in data
        assert data["core_files"] == []
        assert data["skills"] == {}

    def test_returns_existing_manifest_without_overwrite(self, tmp_path: Path):
        """Should not overwrite an existing manifest."""
        ctx = tmp_path / ".context"
        trace = ctx / "traceability"
        trace.mkdir(parents=True)
        manifest = trace / "manifest.json"
        custom = {"version": "2.0.0", "custom": True}
        manifest.write_text(json.dumps(custom))

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        result = obj.init_autocontext()

        assert result == manifest
        data = json.loads(manifest.read_text())
        assert data["version"] == "2.0.0"
        assert data["custom"] is True

    def test_creates_policy_directory(self, tmp_path: Path):
        """Should also create the policy/ directory alongside traceability/."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        obj.init_autocontext()

        assert (tmp_path / ".context" / "policy").is_dir()

    def test_idempotent_multiple_calls(self, tmp_path: Path):
        """Multiple calls should be safe and not corrupt existing files."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        r1 = obj.init_autocontext()
        r2 = obj.init_autocontext()

        assert r1 == r2
        assert (tmp_path / ".context" / "traceability" / "manifest.json").exists()

    def test_returns_none_on_failure(self, tmp_path: Path):
        """Should return None if writing fails (e.g. permission error)."""
        ctx = tmp_path / ".context"
        trace = ctx / "traceability"
        trace.mkdir(parents=True)
        # Make directory read-only so creating manifest.json fails
        import os

        os.chmod(str(trace), 0o555)
        try:

            class DummyMixin(CompoundContextMixin):
                def __init__(self):
                    self.__init_context__(project_root=tmp_path)

            obj = DummyMixin()
            result = obj.init_autocontext()
            if os.getuid() == 0:
                pytest.skip("Running as root — permission test ineffective")
            assert result is None
        finally:
            os.chmod(str(trace), 0o755)


class TestArchiveSession:
    """[P0] Tests for archive_session()."""

    def test_creates_learned_budgets(self, tmp_path: Path):
        """Should write a YAML-frontmatter entry to policy/learned-budgets.md."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        budget_path = obj.archive_session(outcome={"coherence": 0.7, "tasks": 3})

        assert budget_path == (tmp_path / ".context" / "policy" / "learned-budgets.md")
        assert budget_path.exists()
        content = budget_path.read_text()
        assert "archived_at:" in content
        assert "coherence: 0.7" in content
        assert "tasks: 3" in content
        assert "Session Archive" in content

    def test_appends_entries(self, tmp_path: Path):
        """Multiple archives should append, not overwrite."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        obj.archive_session(outcome={"a": 1})
        obj.archive_session(outcome={"b": 2})

        content = (tmp_path / ".context" / "policy" / "learned-budgets.md").read_text()
        assert content.count("---") == 4  # 2 frontmatter blocks
        assert "a: 1" in content
        assert "b: 2" in content

    def test_handles_no_outcome(self, tmp_path: Path):
        """Should still write a minimal entry when outcome is None."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        budget_path = obj.archive_session(outcome=None)

        assert budget_path is not None
        content = budget_path.read_text()
        assert "outcome: no_data" in content

    def test_returns_none_on_failure(self, tmp_path: Path):
        """Should return None if writing fails."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        policy_dir = tmp_path / ".context" / "policy"
        policy_dir.mkdir(parents=True)
        import os

        os.chmod(str(policy_dir), 0o555)
        try:
            result = obj.archive_session(outcome={"x": 1})
            if os.getuid() == 0:
                pytest.skip("Running as root — permission test ineffective")
            assert result is None
        finally:
            os.chmod(str(policy_dir), 0o755)


class TestCompoundExecutorSessionLifecycle:
    """[P0] Integration tests for start_session / end_session hooks."""

    @pytest.fixture()
    def mock_mcp(self):
        return MagicMock(spec=MCPClient)

    def test_start_session_initializes_autocontext(self, tmp_path: Path, mock_mcp):
        """start_session should create manifest and warm cache."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            executor = CompoundExecutor(mcp_client=mock_mcp)
            summary = executor.start_session(max_cache_entries=128)

        assert summary["autocontext_initialized"] is True
        manifest = tmp_path / ".context" / "traceability" / "manifest.json"
        assert manifest.exists()
        assert summary["manifest_path"] == str(manifest)

    def test_end_session_archives_outcome(self, tmp_path: Path, mock_mcp):
        """end_session should write policy/learned-budgets.md."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            executor = CompoundExecutor(mcp_client=mock_mcp)
            executor.start_session()
            summary = executor.end_session()

        assert summary["session_archived"] is True
        archive = tmp_path / ".context" / "policy" / "learned-budgets.md"
        assert archive.exists()
        assert summary["archive_path"] == str(archive)

    def test_end_session_includes_context_state(self, tmp_path: Path, mock_mcp):
        """The archive should include current context state if available."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            executor = CompoundExecutor(mcp_client=mock_mcp)
            executor.start_session()
            executor.end_session()

        archive = tmp_path / ".context" / "policy" / "learned-budgets.md"
        content = archive.read_text()
        # Context state contains at minimum token_usage, coherence_state, etc.
        assert "token_usage" in content

    def test_start_and_end_idempotent(self, tmp_path: Path, mock_mcp):
        """Calling start/end multiple times should be safe."""
        with patch.object(Path, "cwd", return_value=tmp_path):
            executor = CompoundExecutor(mcp_client=mock_mcp)
            s1 = executor.start_session()
            s2 = executor.start_session()
            e1 = executor.end_session()
            e2 = executor.end_session()

        assert s1["autocontext_initialized"] is True
        assert s2["autocontext_initialized"] is True
        assert e1["session_archived"] is True
        assert e2["session_archived"] is True

        archive = tmp_path / ".context" / "policy" / "learned-budgets.md"
        content = archive.read_text()
        # Should have two archive entries
        assert content.count("Session Archive") == 2


class TestAutocontextWithRealContextStructure:
    """[P1] Ensure autocontext plays nicely with an existing .context tree."""

    def test_init_does_not_clobber_existing_core_files(self, tmp_path: Path):
        """init_autocontext must leave existing core files alone."""
        ctx = tmp_path / ".context"
        core = ctx / "core"
        trace = ctx / "traceability"
        core.mkdir(parents=True)
        trace.mkdir(parents=True)
        (core / "syntax-rules.md").write_text("# Syntax\n")
        manifest = trace / "manifest.json"
        manifest.write_text(
            json.dumps({"version": "2.0.0", "core_files": [{"path": "core/syntax-rules.md"}]})
        )

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        obj.init_autocontext()

        data = json.loads(manifest.read_text())
        assert data["version"] == "2.0.0"
        assert len(data["core_files"]) == 1

    def test_load_execution_context_after_init(self, tmp_path: Path):
        """After init_autocontext, load_execution_context should succeed."""

        class DummyMixin(CompoundContextMixin):
            def __init__(self):
                self.__init_context__(project_root=tmp_path)

        obj = DummyMixin()
        obj.init_autocontext()
        # Create a core file referenced by the fresh manifest
        core = tmp_path / ".context" / "core"
        core.mkdir(parents=True)
        (core / "rules.md").write_text("# Rules\n")
        manifest = tmp_path / ".context" / "traceability" / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "core_files": [
                        {"path": "core/rules.md", "token_budget": 50, "coherence_threshold": 0.5}
                    ],
                    "skills": {},
                }
            )
        )

        obj.load_execution_context()
        assert obj._context_loaded is True
        assert obj._context_manager.token_usage == 50
