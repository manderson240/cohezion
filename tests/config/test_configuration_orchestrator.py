"""Unit tests for ConfigurationOrchestrator - Phase 1 Foundation.

Focus: Actual functionality, not placeholder infrastructure.
Tests that matter for Phase 1: state tracking, git integration, validation framework.
"""

import asyncio
import shutil
from pathlib import Path

import pytest

from cohezion.config import (
    ConfigurationOrchestrator,
    FileMetadata,
    GitUtils,
    ValidationReport,
    get_config_orchestrator,
    reset_config_orchestrator,
)


GIT = shutil.which("git") or "git"


class TestFileMetadata:
    """Test configuration file metadata extraction."""

    def test_metadata_from_file(self, tmp_path: Path) -> None:
        """Test that metadata is correctly extracted from file."""
        test_file = tmp_path / "test.md"
        content = "# Title\n\nSome content\n## Section\n\nMore content"
        test_file.write_text(content)

        metadata = FileMetadata.from_file(test_file)

        assert metadata.path == test_file
        assert metadata.size_bytes == len(content.encode())
        assert metadata.line_count > 0  # Should count lines
        assert metadata.content_hash  # Should be non-empty
        assert len(metadata.sections) >= 2  # Should detect headings

    def test_hash_consistency(self) -> None:
        """Test that same content produces same hash."""
        content = "# Test\n\nContent"
        hash1 = FileMetadata._compute_hash(content)
        hash2 = FileMetadata._compute_hash(content)

        assert hash1 == hash2

    def test_hash_changes_with_content(self) -> None:
        """Test that different content produces different hash."""
        hash1 = FileMetadata._compute_hash("Content 1")
        hash2 = FileMetadata._compute_hash("Content 2")

        assert hash1 != hash2

    def test_extract_sections(self) -> None:
        """Test markdown section extraction."""
        content = """# Main Title
Introduction

## Section 1
Content 1

### Subsection
Sub-content

## Section 2
Content 2"""

        sections = FileMetadata._extract_sections(content)

        assert len(sections) == 4
        assert sections[0].title == "Main Title"
        assert sections[0].level == 1
        assert sections[1].title == "Section 1"
        assert sections[1].level == 2
        assert sections[2].title == "Subsection"
        assert sections[2].level == 3


class TestGitUtils:
    """Test git integration utilities."""

    def test_git_utils_init(self, tmp_path: Path) -> None:
        """Test that GitUtils initializes without crash."""
        git = GitUtils(tmp_path)
        assert git.repo_root == tmp_path

    def test_get_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test detection of uncommitted changes."""
        # Initialize a git repo
        import subprocess

        subprocess.run([GIT, "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "commit.gpgsign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Create and commit a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        subprocess.run([GIT, "add", "test.txt"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True
        )

        # No changes yet
        git = GitUtils(tmp_path)
        assert not git.get_uncommitted_changes(test_file)

        # Make a change
        test_file.write_text("modified")
        assert git.get_uncommitted_changes(test_file)

    def test_get_file_diff(self, tmp_path: Path) -> None:
        """Test diff extraction for file changes."""
        import subprocess

        # Setup git repo
        subprocess.run([GIT, "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "commit.gpgsign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Create and commit a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2")
        subprocess.run([GIT, "add", "test.txt"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True
        )

        # Make changes
        test_file.write_text("line1\nmodified\nline3")

        git = GitUtils(tmp_path)
        diff = git.get_file_diff(test_file)

        assert diff is not None
        assert "modified" in diff

    @pytest.mark.asyncio
    async def test_auto_commit(self, tmp_path: Path) -> None:
        """Test atomic git commit creation."""
        import subprocess

        # Setup git repo
        subprocess.run([GIT, "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [GIT, "config", "commit.gpgsign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial")
        subprocess.run([GIT, "add", "test.txt"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            [GIT, "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True
        )

        # Make changes
        test_file.write_text("modified")

        # Try auto-commit
        git = GitUtils(tmp_path)
        result = await git.auto_commit(test_file, "test: update content")

        assert result is True

        # Verify commit was created
        history = git.get_commit_history(test_file, max_count=2)
        assert len(history) >= 1  # At least one commit
        assert "test: update content" in history[0]["subject"]


class TestConfigurationOrchestrator:
    """Test the main orchestrator."""

    def test_orchestrator_init(self, tmp_path: Path) -> None:
        """Test orchestrator initialization."""
        reset_config_orchestrator()
        orch = ConfigurationOrchestrator(tmp_path)

        assert orch.repo_root == tmp_path
        assert not orch._monitoring
        assert orch.config_state is not None

    def test_orchestrator_singleton(self, tmp_path: Path) -> None:
        """Test that get_config_orchestrator returns singleton."""
        reset_config_orchestrator()
        orch1 = get_config_orchestrator(tmp_path)
        orch2 = get_config_orchestrator(tmp_path)

        assert orch1 is orch2

    def test_orchestrator_reset(self, tmp_path: Path) -> None:
        """Test singleton reset for testing."""
        orch1 = get_config_orchestrator(tmp_path)
        reset_config_orchestrator()
        orch2 = get_config_orchestrator(tmp_path)

        assert orch1 is not orch2

    def test_detect_manual_edits_no_git(self, tmp_path: Path) -> None:
        """Test manual edit detection when file not in git."""
        orch = ConfigurationOrchestrator(tmp_path)
        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        # Should return False if not in git
        result = orch.detect_manual_edits(test_file)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_consistency_with_files(self, tmp_path: Path) -> None:
        """Test validation with actual config files."""
        # Create test files
        claude_md = tmp_path / "CLAUDE.md"
        gemini_md = tmp_path / "GEMINI.md"
        claude_md.write_text("# CLAUDE\n\nContent")
        gemini_md.write_text("# GEMINI\n\nContent")

        orch = ConfigurationOrchestrator(tmp_path)
        orch.claude_md = claude_md
        orch.gemini_md = gemini_md

        report = await orch.validate_consistency()

        assert isinstance(report, ValidationReport)
        assert orch.config_state.claude_md is not None
        assert orch.config_state.gemini_md is not None
        assert orch.config_state.total_validations == 1

    @pytest.mark.asyncio
    async def test_validate_consistency_missing_files(self, tmp_path: Path) -> None:
        """Test validation when files don't exist."""
        orch = ConfigurationOrchestrator(tmp_path)

        report = await orch.validate_consistency()

        assert isinstance(report, ValidationReport)
        assert orch.config_state.total_validations == 1

    def test_get_state(self, tmp_path: Path) -> None:
        """Test state retrieval."""
        orch = ConfigurationOrchestrator(tmp_path)
        state = orch.get_state()

        assert state is not None
        assert state.total_syncs == 0

    def test_get_metrics(self, tmp_path: Path) -> None:
        """Test metrics retrieval."""
        orch = ConfigurationOrchestrator(tmp_path)
        metrics = orch.get_metrics()

        assert "total_syncs" in metrics
        assert "total_conflicts" in metrics
        assert "monitoring_active" in metrics
        assert metrics["monitoring_active"] is False

    @pytest.mark.asyncio
    async def test_regenerate_and_commit_unknown_file(self, tmp_path: Path) -> None:
        """Test regenerate with unknown filename."""
        orch = ConfigurationOrchestrator(tmp_path)

        result = await orch.regenerate_and_commit("UNKNOWN.md")

        assert result is False

    @pytest.mark.asyncio
    async def test_size_limit_checks(self, tmp_path: Path) -> None:
        """Test size limit configuration."""
        orch = ConfigurationOrchestrator(tmp_path)

        assert "CLAUDE.md" in orch.size_limits
        assert "GEMINI.md" in orch.size_limits
        assert orch.size_limits["CLAUDE.md"]["max_lines"] == 250
        assert orch.size_limits["GEMINI.md"]["max_lines"] == 200


class TestValidationReport:
    """Test validation reporting."""

    def test_validation_report_init(self) -> None:
        """Test report initialization."""
        report = ValidationReport()

        assert report.passed is True
        assert report.checksums_match is True
        assert report.schema_valid is True
        assert len(report.recommendations) == 0

    def test_validation_report_with_failures(self) -> None:
        """Test report with failures."""
        report = ValidationReport(
            passed=False,
            checksums_match=False,
            schema_valid=False,
        )

        assert report.passed is False
        assert not report.checksums_match


@pytest.mark.asyncio
async def test_monitoring_startup_stop(tmp_path: Path) -> None:
    """Test monitoring lifecycle."""
    orch = ConfigurationOrchestrator(tmp_path)

    # Start monitoring (with immediate stop to avoid hanging)
    monitor_task = asyncio.create_task(orch.start_monitoring())

    # Poll for _monitoring flag instead of fixed wait
    for _ in range(50):
        if orch._monitoring:
            break
        await asyncio.sleep(0.005)

    # Stop monitoring
    await orch.stop_monitoring()

    # Monitor should complete shortly
    try:
        await asyncio.wait_for(monitor_task, timeout=2.0)
    except TimeoutError:
        pytest.fail("Monitoring did not stop within timeout")

    assert not orch._monitoring
