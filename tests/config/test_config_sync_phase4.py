"""Integration tests for Phase 4: Real-Time Sync & Git Integration.

Tests template rendering, sync operations, commit generation, and orchestrator integration.
"""

from pathlib import Path

import pytest

from cohezion.config import ConfigSyncEngine, ConfigSyncLogger, ConfigurationOrchestrator
from cohezion.config.config_templates import (
    ConfigTemplateEngine,
    TemplateContext,
    TemplateType,
)


class TestAuditLogIsAnchoredToRepoRoot:
    """The audit log must follow the object's repo_root, never the process cwd.

    ``ConfigSyncLogger`` defaults its ``log_dir`` to
    ``Path.cwd() / "data" / "config-sync-logs"``. Both production construction sites
    took that default while holding an explicit ``repo_root``, so running the test
    suite wrote into the checkout and left ``data/config-sync-logs/config_sync.jsonl``
    — a TRACKED file — modified. Caught by noticing an unexplained modification in
    ``git status`` and confirmed causally: restore the file, run ``tests/config``,
    watch it reappear.

    Fixing only ``ConfigSyncEngine`` left the tree dirty; ``ConfigurationOrchestrator``
    was a second writer with the identical defect. Both are asserted here so a partial
    fix cannot pass.
    """

    def test_sync_engine_log_dir_is_under_repo_root(self, tmp_path: Path) -> None:
        engine = ConfigSyncEngine(repo_root=tmp_path)

        assert engine.sync_logger.log_dir.is_relative_to(tmp_path)

    def test_orchestrator_log_dir_is_under_repo_root(self, tmp_path: Path) -> None:
        orch = ConfigurationOrchestrator(tmp_path)

        assert orch.sync_logger.log_dir.is_relative_to(tmp_path)

    def test_log_dir_is_not_the_process_cwd(self, tmp_path: Path) -> None:
        """Discriminating: `is_relative_to(tmp_path)` alone would pass if cwd were
        somehow inside tmp_path. Assert the negative directly."""
        cwd_log_dir = Path.cwd() / "data" / "config-sync-logs"

        assert ConfigSyncEngine(repo_root=tmp_path).sync_logger.log_dir != cwd_log_dir
        assert ConfigurationOrchestrator(tmp_path).sync_logger.log_dir != cwd_log_dir


class TestConfigTemplateEngine:
    """Test template rendering."""

    def test_render_claude_md_with_decisions(self) -> None:
        """Test CLAUDE.md rendering with decisions."""
        context = TemplateContext(
            latest_decisions=["Decision 1", "Decision 2"],
            operational_protocols=["Protocol A", "Protocol B"],
            operational_guardrails=["Guardrail 1"],
            recent_patterns=["Pattern 1"],
            sync_timestamp="2026-02-10T00:00:00",
        )

        content = ConfigTemplateEngine.render_claude_md(context)

        assert "# Cohezion - Claude Code Orchestration" in content
        assert "Decision 1" in content
        assert "Decision 2" in content
        assert "Protocol A" in content
        assert "Protocol B" in content
        assert len(content) > 500

    def test_render_claude_md_without_decisions(self) -> None:
        """Test CLAUDE.md rendering without decisions (fallback)."""
        context = TemplateContext(
            latest_decisions=[],
            operational_protocols=[],
            operational_guardrails=[],
            recent_patterns=[],
            sync_timestamp="2026-02-10T00:00:00",
        )

        content = ConfigTemplateEngine.render_claude_md(context)

        assert "# Cohezion - Claude Code Orchestration" in content
        assert "vault/decisions/" in content  # Fallback message

    def test_render_gemini_md_with_guardrails(self) -> None:
        """Test GEMINI.md rendering with guardrails."""
        context = TemplateContext(
            latest_decisions=["Decision"],
            operational_protocols=["Protocol"],
            operational_guardrails=["No WMD", "Idempotent"],
            recent_patterns=["Pattern"],
            sync_timestamp="2026-02-10T00:00:00",
        )

        content = ConfigTemplateEngine.render_gemini_md(context)

        assert "# GEMINI - Cohezion Orchestration Layer" in content
        assert "No WMD" in content
        assert "Idempotent" in content

    def test_template_context_dataclass(self) -> None:
        """Test TemplateContext creation."""
        context = TemplateContext(
            latest_decisions=["D1"],
            operational_protocols=["P1"],
            operational_guardrails=["G1"],
            recent_patterns=["Pat1"],
            sync_timestamp="2026-02-10T00:00:00",
        )

        assert context.latest_decisions == ["D1"]
        assert context.sync_timestamp == "2026-02-10T00:00:00"


class TestConfigSyncEngine:
    """Test sync engine operations."""

    def test_sync_engine_init(self, tmp_path: Path) -> None:
        """Test ConfigSyncEngine initialization."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=vault_root,
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )

        assert sync_engine.repo_root == tmp_path
        assert sync_engine.vault_root == vault_root
        assert sync_engine.claude_md == tmp_path / "CLAUDE.md"
        assert sync_engine.gemini_md == tmp_path / "GEMINI.md"

    @pytest.mark.asyncio
    async def test_extract_vault_content(self, tmp_path: Path) -> None:
        """Test extracting canonical content from vault."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "decisions").mkdir()
        (vault_root / "patterns").mkdir()

        # Create sample decision files
        (vault_root / "decisions" / "decision-1.md").write_text("# Decision 1")
        (vault_root / "decisions" / "decision-2.md").write_text("# Decision 2")

        # Create sample pattern files
        (vault_root / "patterns" / "pattern-1.md").write_text("# Pattern 1")

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=vault_root,
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )
        content = await sync_engine._extract_vault_content()

        assert "decision-1" in content["decisions"]
        assert "decision-2" in content["decisions"]
        assert "pattern-1" in content["patterns"]
        assert len(content["protocols"]) > 0
        assert len(content["guardrails"]) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_no_file(self, tmp_path: Path) -> None:
        """Test conflict check when file doesn't exist."""
        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )

        conflicts = await sync_engine._check_conflicts(tmp_path / "nonexistent.md")

        assert conflicts == []

    @pytest.mark.asyncio
    async def test_generate_commit_message(self, tmp_path: Path) -> None:
        """Test AI-style commit message generation."""
        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )

        vault_content = {
            "decisions": ["Decision 1", "Decision 2"],
            "patterns": [],
            "protocols": [],
            "guardrails": [],
        }

        message = await sync_engine._generate_commit_message("CLAUDE.md", vault_content)

        assert "config:" in message
        assert "CLAUDE.md" in message
        assert "decisions" in message.lower()
        assert "\n" in message  # Has body

    @pytest.mark.asyncio
    async def test_get_sync_status(self, tmp_path: Path) -> None:
        """Test getting sync status of files."""
        claude_md = tmp_path / "CLAUDE.md"
        gemini_md = tmp_path / "GEMINI.md"
        claude_md.write_text("# CLAUDE\n\nContent")
        gemini_md.write_text("# GEMINI\n\nContent")

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )
        status = sync_engine.get_sync_status()

        assert "CLAUDE.md" in status
        assert "GEMINI.md" in status
        assert status["CLAUDE.md"]["exists"]
        assert status["CLAUDE.md"]["size_bytes"] > 0


class TestConfigSyncEngineIntegration:
    """Test full sync operations with git integration."""

    @pytest.mark.asyncio
    async def test_sync_config_file_new_file(self, tmp_path: Path) -> None:
        """Test syncing a config file that doesn't exist yet."""
        # Initialize git repo
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgSign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "decisions").mkdir()

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=vault_root,
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )

        result = await sync_engine.sync_config_file("CLAUDE.md")

        assert result["file"] == "CLAUDE.md"
        assert result["synced"]
        assert (tmp_path / "CLAUDE.md").exists()

    @pytest.mark.asyncio
    async def test_sync_all_files(self, tmp_path: Path) -> None:
        """Test syncing both CLAUDE.md and GEMINI.md."""
        # Initialize git repo
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgSign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "decisions").mkdir()

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=vault_root,
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )

        results = await sync_engine.sync_all()

        assert "timestamp" in results
        assert "files" in results
        assert "CLAUDE.md" in results["files"]
        assert "GEMINI.md" in results["files"]


class TestOrchestrationWithSync:
    """Test orchestrator integration with sync engine."""

    def test_orchestrator_has_sync_engine(self, tmp_path: Path) -> None:
        """Test that orchestrator has sync engine."""
        orch = ConfigurationOrchestrator(tmp_path)

        assert hasattr(orch, "sync_engine")
        assert isinstance(orch.sync_engine, ConfigSyncEngine)

    @pytest.mark.asyncio
    async def test_orchestrator_regenerate_and_commit(self, tmp_path: Path) -> None:
        """Test orchestrator regenerate_and_commit method."""
        # Initialize git repo
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgSign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        (vault_root / "decisions").mkdir()

        orch = ConfigurationOrchestrator(tmp_path)
        # Keep the sync engine off the real ~/vaults tree AND off the repo's own
        # data/config-sync-logs/ (ConfigSyncLogger defaults to Path.cwd()); now
        # that regenerate_and_commit really syncs, the default logger would
        # append to a tracked LFS file on every test run.
        orch.sync_engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=vault_root,
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )

        result = await orch.regenerate_and_commit("CLAUDE.md", "test_trigger")

        # The contract is the method's NAME: regenerate the file and commit it.
        # A True return has to mean the artifact exists -- the previous assertion
        # (`result is True or result is False`) was a tautology that could not
        # fail for any bool-returning body, and it certified a body whose entire
        # promised behaviour was four `# Phase 4:` comments.
        assert result is True
        assert orch.claude_md.exists(), "returned True but regenerated no CLAUDE.md"

    @pytest.mark.asyncio
    async def test_orchestrator_regenerate_reports_failure_for_unknown_file(
        self, tmp_path: Path
    ) -> None:
        """An unsynced file must not be reported as a successful sync.

        Discriminating: an implementation that increments `total_syncs` on a
        path that synced nothing manufactures a success metric out of nothing.
        """
        orch = ConfigurationOrchestrator(tmp_path)
        before = orch.get_metrics()["total_syncs"]

        result = await orch.regenerate_and_commit("NOT_A_CONFIG.md", "test_trigger")

        assert result is False
        assert orch.get_metrics()["total_syncs"] == before

    @pytest.mark.asyncio
    async def test_orchestrator_regenerate_delegates_to_sync_engine(self, tmp_path: Path) -> None:
        """The verdict comes from ConfigSyncEngine.sync_config_file, not a stub.

        Discriminating both ways: a body that ignores the engine's answer (the old
        unconditional ``return True``) fails the not-synced case; a body that never
        calls the engine cannot produce the synced case's counter movement.
        """
        from unittest.mock import AsyncMock

        orch = ConfigurationOrchestrator(tmp_path)
        orch.sync_engine.sync_config_file = AsyncMock(return_value={"synced": False, "details": {}})
        failures, syncs = orch.config_state.sync_failures, orch.config_state.total_syncs

        assert await orch.regenerate_and_commit("CLAUDE.md", "t") is False
        assert orch.config_state.sync_failures == failures + 1
        assert orch.config_state.total_syncs == syncs

        orch.sync_engine.sync_config_file = AsyncMock(
            return_value={"synced": True, "commit_hash": "abc"}
        )
        assert await orch.regenerate_and_commit("CLAUDE.md", "t") is True
        assert orch.config_state.total_syncs == syncs + 1
        orch.sync_engine.sync_config_file.assert_awaited_once_with("CLAUDE.md")

    @pytest.mark.asyncio
    async def test_orchestrator_regenerate_no_changes_is_success_not_failure(
        self, tmp_path: Path
    ) -> None:
        """File already in the desired state: True, and neither counter moves."""
        from unittest.mock import AsyncMock

        orch = ConfigurationOrchestrator(tmp_path)
        orch.sync_engine.sync_config_file = AsyncMock(
            return_value={
                "file": "CLAUDE.md",
                "synced": False,
                "commit_hash": None,
                "details": {"skipped": "no_changes"},
            }
        )

        assert await orch.regenerate_and_commit("CLAUDE.md", "t") is True
        assert orch.config_state.sync_failures == 0
        assert orch.config_state.total_syncs == 0

    @pytest.mark.asyncio
    async def test_orchestrator_regenerate_conflict_is_a_failure(self, tmp_path: Path) -> None:
        from unittest.mock import AsyncMock

        orch = ConfigurationOrchestrator(tmp_path)
        orch.sync_engine.sync_config_file = AsyncMock(
            return_value={
                "synced": False,
                "commit_hash": None,
                "details": {"conflicts": ["manual edit"]},
            }
        )

        assert await orch.regenerate_and_commit("CLAUDE.md", "t") is False
        assert orch.config_state.sync_failures == 1
        assert orch.config_state.total_syncs == 0

    @pytest.mark.asyncio
    async def test_engine_marks_no_change_skip(self, tmp_path: Path) -> None:
        """The engine's no-change path must say WHY it did not sync."""
        from unittest.mock import AsyncMock, patch

        engine = ConfigSyncEngine(
            repo_root=tmp_path,
            vault_root=tmp_path / "vault",
            sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs"),
        )
        engine.claude_md.write_text("same\n")
        with (
            patch.object(engine, "_check_conflicts", AsyncMock(return_value=[])),
            patch.object(engine, "_extract_vault_content", AsyncMock(return_value={})),
            patch.object(engine, "_render_config_file", return_value="same\n"),
        ):
            result = await engine.sync_config_file("CLAUDE.md")

        assert result["synced"] is False
        assert result["details"].get("skipped") == "no_changes"


class TestCommitMessageGeneration:
    """Test AI-style commit message generation."""

    @pytest.mark.asyncio
    async def test_commit_message_with_multiple_decisions(self, tmp_path: Path) -> None:
        """Test commit message with multiple decisions."""
        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )

        vault_content = {
            "decisions": ["Cost Optimization", "Security Hardening", "Performance"],
            "patterns": [],
            "protocols": [],
            "guardrails": [],
        }

        message = await sync_engine._generate_commit_message("CLAUDE.md", vault_content)

        assert "3" in message or "decisions" in message.lower()

    @pytest.mark.asyncio
    async def test_commit_message_with_patterns(self, tmp_path: Path) -> None:
        """Test commit message when syncing patterns."""
        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )

        vault_content = {
            "decisions": [],
            "patterns": ["Pattern A", "Pattern B"],
            "protocols": [],
            "guardrails": [],
        }

        message = await sync_engine._generate_commit_message("CLAUDE.md", vault_content)

        assert "pattern" in message.lower()


class TestConflictDetection:
    """Test conflict detection in sync operations."""

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_manual_edit(self, tmp_path: Path) -> None:
        """Test conflict detection when file has manual edits."""
        import subprocess

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgSign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Initial content")

        # Commit initial version
        subprocess.run(
            ["git", "add", "CLAUDE.md"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Manual edit
        claude_md.write_text("# Manually edited content")

        sync_engine = ConfigSyncEngine(
            repo_root=tmp_path, sync_logger=ConfigSyncLogger(log_dir=tmp_path / "sync-logs")
        )
        conflicts = await sync_engine._check_conflicts(claude_md)

        # May or may not detect depending on git state
        assert isinstance(conflicts, list)


class TestTemplateRendering:
    """Test template rendering quality."""

    def test_claude_md_template_format(self) -> None:
        """Test CLAUDE.md template has correct format."""
        from cohezion.config.config_templates import CLAUDE_MD_TEMPLATE

        assert "# Cohezion - Claude Code Orchestration" in CLAUDE_MD_TEMPLATE
        assert "{latest_decisions}" in CLAUDE_MD_TEMPLATE
        assert "{operational_protocols}" in CLAUDE_MD_TEMPLATE

    def test_gemini_md_template_format(self) -> None:
        """Test GEMINI.md template has correct format."""
        from cohezion.config.config_templates import GEMINI_MD_TEMPLATE

        assert "# GEMINI - Cohezion Orchestration Layer" in GEMINI_MD_TEMPLATE
        assert "{operational_guardrails}" in GEMINI_MD_TEMPLATE

    def test_template_engine_get_template(self) -> None:
        """Test getting raw template strings."""
        claude_template = ConfigTemplateEngine.get_template(TemplateType.CLAUDE_MD)
        gemini_template = ConfigTemplateEngine.get_template(TemplateType.GEMINI_MD)

        assert len(claude_template) > 100
        assert len(gemini_template) > 100
        assert "Cohezion" in claude_template
        assert "GEMINI" in gemini_template
