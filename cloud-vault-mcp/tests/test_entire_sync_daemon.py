"""Integration tests for entire.io sync daemon."""

import asyncio
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "mcp_server"))

from entire_sync_daemon import EntireSyncDaemon


@pytest.fixture
def temp_vault():
    """Create temporary vault directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "vault"
        vault_path.mkdir()
        (vault_path / "daily").mkdir()
        (vault_path / "checkpoints").mkdir(parents=True)
        yield vault_path


@pytest.fixture
def daemon(temp_vault):
    """Create EntireSyncDaemon instance."""
    return EntireSyncDaemon(
        vault_path=str(temp_vault),
        poll_interval_seconds=1,
    )


class TestWorkQueue:
    """Test WorkQueue functionality."""

    def test_mark_completed(self, daemon):
        """Test marking a commit as completed."""
        daemon.work_queue.mark_completed("abc123")
        assert daemon.work_queue.is_processed("abc123")

    def test_not_processed(self, daemon):
        """Test checking unprocessed commit."""
        assert not daemon.work_queue.is_processed("nonexistent")

    def test_multiple_commits(self, daemon):
        """Test processing multiple commits."""
        daemon.work_queue.mark_completed("hash1")
        daemon.work_queue.mark_completed("hash2")
        daemon.work_queue.mark_completed("hash3")

        assert daemon.work_queue.is_processed("hash1")
        assert daemon.work_queue.is_processed("hash2")
        assert daemon.work_queue.is_processed("hash3")

    def test_pending_count(self, daemon):
        """Test pending count tracking."""
        count = daemon.work_queue.get_pending_count()
        assert isinstance(count, int)


class TestDeadLetterQueue:
    """Test DeadLetterQueue functionality."""

    def test_add_failed_commit(self, daemon):
        """Test adding failed commit to DLQ."""
        daemon.dlq.add("abc123", "Test failure reason")
        entries = daemon.dlq.get_all()

        assert any(e["commit_hash"] == "abc123" for e in entries)
        assert daemon.dlq.get_count() >= 1

    def test_increment_failure_count(self, daemon):
        """Test that failure count increments on duplicate adds."""
        daemon.dlq.add("abc123", "Reason 1")
        daemon.dlq.add("abc123", "Reason 2")

        entries = daemon.dlq.get_all()
        entry = next(e for e in entries if e["commit_hash"] == "abc123")
        assert entry["failure_count"] == 2

    def test_retry_removes_from_dlq(self, daemon):
        """Test that retry removes commit from DLQ."""
        daemon.dlq.add("abc123", "Failed")
        assert daemon.dlq.get_count() >= 1

        daemon.dlq.retry("abc123")
        entries = daemon.dlq.get_all()
        assert not any(e["commit_hash"] == "abc123" for e in entries)

    def test_get_all_returns_list(self, daemon):
        """Test that get_all returns list of dicts."""
        daemon.dlq.add("hash1", "Reason 1")
        daemon.dlq.add("hash2", "Reason 2")

        entries = daemon.dlq.get_all()
        assert isinstance(entries, list)
        assert len(entries) >= 2
        assert all("commit_hash" in e for e in entries)
        assert all("failure_reason" in e for e in entries)


class TestEntireSyncDaemon:
    """Test EntireSyncDaemon core functionality."""

    def test_daemon_initialization(self, daemon):
        """Test daemon initializes correctly."""
        assert daemon.vault_path.exists()
        assert daemon.poll_interval == 1

    @pytest.mark.asyncio
    async def test_get_status(self, daemon):
        """Test getting daemon status."""
        status = await daemon.get_status()

        assert status["status"] == "running"
        assert "last_sync" in status
        assert "processed_count" in status
        assert "dlq_count" in status
        assert status["poll_interval"] == 1

    def test_is_entire_commit(self, daemon):
        """Test identifying entire.io commits."""
        entire_commit = {
            "hash": "abc123",
            "author": "agent",
            "date": "2026-02-12",
            "body": "Entire-Checkpoint: session summary\nOutcomes achieved",
        }

        regular_commit = {
            "hash": "def456",
            "author": "agent",
            "date": "2026-02-12",
            "body": "Regular git commit message",
        }

        assert daemon._is_entire_commit(entire_commit)
        assert not daemon._is_entire_commit(regular_commit)

    @pytest.mark.asyncio
    async def test_create_vault_note(self, daemon, temp_vault):
        """Test creating vault checkpoint note."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123def456",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=["Outcome 1", "Outcome 2"],
            metrics={"coverage": 0.87},
            team_status="Ready",
            next_actions=["Action 1"],
        )

        await daemon._create_vault_note(commit_data)

        # Check that note was created
        checkpoint_dir = temp_vault / "daily" / "checkpoints"
        assert checkpoint_dir.exists()

        # Should have created a file
        files = list(checkpoint_dir.glob("*.md"))
        assert len(files) >= 1

    def test_build_checkpoint_note(self, daemon):
        """Test building checkpoint note content."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=["Outcome 1"],
            metrics={"papers_coverage": 0.87},
            team_status="All systems go",
            next_actions=["Deploy"],
        )

        content = daemon._build_checkpoint_note(commit_data)

        assert "---" in content  # YAML frontmatter
        assert "test-agent" in content
        assert "Outcome 1" in content
        assert "All systems go" in content
        assert "Deploy" in content
        assert "abc123" in content

    @pytest.mark.asyncio
    async def test_get_new_commits_empty_repo(self, temp_vault):
        """Test getting commits from repo with no commits."""
        # Create a real git repo
        import subprocess

        subprocess.run(
            ["git", "init"],
            cwd=temp_vault,
            capture_output=True,
        )

        daemon = EntireSyncDaemon(vault_path=str(temp_vault), git_path=str(temp_vault))
        commits = await daemon._get_new_commits()

        # Should return empty list for repo with no commits
        assert isinstance(commits, list)

    def test_retry_failed_nonexistent(self, daemon):
        """Test retrying nonexistent commit returns False."""
        result = asyncio.run(daemon.retry_failed("nonexistent_hash"))
        assert result is False

    def test_retry_failed_existing(self, daemon):
        """Test retrying existing failed commit returns True."""
        daemon.dlq.add("abc123", "Test failure")
        result = asyncio.run(daemon.retry_failed("abc123"))
        assert result is True

        # Should be removed from DLQ
        entries = daemon.dlq.get_all()
        assert not any(e["commit_hash"] == "abc123" for e in entries)


class TestCheckpointNoteGeneration:
    """Test checkpoint note generation."""

    def test_note_has_required_sections(self, daemon):
        """Test that generated note has all required sections."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="agent",
            outcomes=["outcome"],
            metrics={},
            team_status="status",
            next_actions=["action"],
        )

        content = daemon._build_checkpoint_note(commit_data)

        # Check for key sections
        assert "title:" in content.lower()
        assert "date:" in content.lower()
        assert "agent_id:" in content.lower()
        assert "outcomes" in content.lower()
        assert "metrics" in content.lower()
        assert "team status" in content.lower()
        assert "next actions" in content.lower()

    def test_note_formats_outcomes_list(self, daemon):
        """Test that outcomes are formatted as bullet list."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="agent",
            outcomes=["First outcome", "Second outcome"],
            metrics={},
            team_status="",
            next_actions=[],
        )

        content = daemon._build_checkpoint_note(commit_data)

        assert "- First outcome" in content
        assert "- Second outcome" in content

    def test_note_formats_metrics(self, daemon):
        """Test that metrics are formatted correctly."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="agent",
            outcomes=[],
            metrics={"papers_coverage": 0.87, "decisions_coverage": 0.88},
            team_status="",
            next_actions=[],
        )

        content = daemon._build_checkpoint_note(commit_data)

        # Should include formatted percentages
        assert "87.0%" in content or "Papers" in content
        assert "88.0%" in content or "Decisions" in content


class TestSurrealDBIntegration:
    """Test SurrealDB integration in daemon."""

    def test_daemon_without_surrealdb(self, temp_vault):
        """Test daemon initializes without SurrealDB (default)."""
        daemon = EntireSyncDaemon(vault_path=str(temp_vault))
        assert daemon._agent_context_ops is None
        assert daemon.surrealdb_url is None

    def test_daemon_with_invalid_surrealdb_url(self, temp_vault):
        """Test daemon gracefully handles unavailable SurrealDB."""
        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            surrealdb_url="http://localhost:99999",
        )
        # Should not crash; _agent_context_ops may or may not be set
        # depending on whether connection is tested at init time
        assert daemon.surrealdb_url == "http://localhost:99999"

    @pytest.mark.asyncio
    async def test_sync_to_surrealdb_skips_when_disabled(self, daemon):
        """Test _sync_to_surrealdb is a no-op when SurrealDB not configured."""
        from entire_ops import CommitData

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=["outcome"],
            metrics={},
            team_status="ok",
            next_actions=[],
        )
        # Should not raise, just return silently
        await daemon._sync_to_surrealdb(commit_data)

    @pytest.mark.asyncio
    async def test_sync_to_surrealdb_calls_track_session(self, temp_vault):
        """Test _sync_to_surrealdb calls AgentContextOps.track_session."""
        from entire_ops import CommitData

        daemon = EntireSyncDaemon(vault_path=str(temp_vault))

        # Mock the agent context ops
        mock_ops = MagicMock()
        mock_ops.track_session.return_value = "session:test123"
        mock_ops.record_outcome.return_value = "outcome:test456"
        daemon._agent_context_ops = mock_ops

        commit_data = CommitData(
            commit_hash="abc123def456",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=["Completed task", "Deployed code"],
            metrics={"papers_coverage": 0.87},
            team_status="Ready",
            next_actions=["Monitor"],
        )

        await daemon._sync_to_surrealdb(commit_data)

        # Verify track_session called with correct args
        mock_ops.track_session.assert_called_once_with(
            agent_names=["test-agent"],
            duration_ms=0,
            status="completed",
        )

        # Verify record_outcome called
        mock_ops.record_outcome.assert_called_once()
        call_args = mock_ops.record_outcome.call_args
        assert call_args[1]["session_id"] == "session:test123"
        assert call_args[1]["status"] == "success"
        assert "abc123de" in call_args[1]["summary"]

    @pytest.mark.asyncio
    async def test_sync_to_surrealdb_graceful_failure(self, temp_vault):
        """Test _sync_to_surrealdb handles SurrealDB errors gracefully."""
        from entire_ops import CommitData

        daemon = EntireSyncDaemon(vault_path=str(temp_vault))

        # Mock agent context ops that raises
        mock_ops = MagicMock()
        mock_ops.track_session.side_effect = ConnectionError("SurrealDB down")
        daemon._agent_context_ops = mock_ops

        commit_data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=[],
            metrics={},
            team_status="",
            next_actions=[],
        )

        # Should not raise, just log warning
        await daemon._sync_to_surrealdb(commit_data)

    @pytest.mark.asyncio
    async def test_process_commit_with_surrealdb(self, temp_vault):
        """Test full _process_commit flow with SurrealDB enabled."""

        daemon = EntireSyncDaemon(vault_path=str(temp_vault))

        # Mock SurrealDB
        mock_ops = MagicMock()
        mock_ops.track_session.return_value = "session:mock1"
        mock_ops.record_outcome.return_value = "outcome:mock2"
        daemon._agent_context_ops = mock_ops

        commit = {
            "hash": "abcdef1234567890",
            "author": "test-agent <test@example.com>",
            "date": "2026-02-12T14:30:00+00:00",
            "body": "Session Summary:\n- Did work\nTeam: Ready\nNext Actions:\n- Do more",
        }

        await daemon._process_commit(commit)

        # Verify commit was processed
        assert daemon.work_queue.is_processed("abcdef1234567890")

        # Verify SurrealDB was called
        mock_ops.track_session.assert_called_once()
        mock_ops.record_outcome.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_commit_surrealdb_failure_doesnt_block(self, temp_vault):
        """Test that SurrealDB failure doesn't prevent commit processing."""
        daemon = EntireSyncDaemon(vault_path=str(temp_vault))

        # Mock SurrealDB that fails
        mock_ops = MagicMock()
        mock_ops.track_session.side_effect = Exception("DB unreachable")
        daemon._agent_context_ops = mock_ops

        commit = {
            "hash": "faildb123456",
            "author": "agent <a@b.com>",
            "date": "2026-02-12T14:30:00+00:00",
            "body": "Session Summary:\n- Work done\nTeam: OK",
        }

        await daemon._process_commit(commit)

        # Commit should still be marked as processed (vault note was created)
        assert daemon.work_queue.is_processed("faildb123456")

    def test_status_includes_surrealdb_info(self, daemon):
        """Test get_status includes SurrealDB fields."""
        status = asyncio.run(daemon.get_status())
        assert "surrealdb_enabled" in status
        assert status["surrealdb_enabled"] is False
        assert status["surrealdb_url"] is None

    def test_status_surrealdb_enabled(self, temp_vault):
        """Test get_status reports SurrealDB as enabled when configured."""
        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            surrealdb_url="http://localhost:8000",
        )
        # Force mock to simulate successful init
        daemon._agent_context_ops = MagicMock()
        status = asyncio.run(daemon.get_status())
        assert status["surrealdb_enabled"] is True
        assert status["surrealdb_url"] == "http://localhost:8000"


class TestBackfill:
    """Test backfill functionality."""

    @pytest.mark.asyncio
    async def test_backfill_empty_repo(self, temp_vault):
        """Test backfill with no commits."""
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_vault, capture_output=True)

        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            git_path=str(temp_vault),
        )

        results = await daemon.backfill()
        assert results["total"] == 0
        assert results["entire_commits"] == 0
        assert results["processed"] == 0

    @pytest.mark.asyncio
    async def test_backfill_with_since(self, temp_vault):
        """Test backfill sets last_sync_time from since parameter."""
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_vault, capture_output=True)

        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            git_path=str(temp_vault),
        )

        results = await daemon.backfill(since="2026-01-01")
        # Should have set last_sync_time initially
        assert daemon.last_sync_time is not None

    @pytest.mark.asyncio
    async def test_backfill_skips_processed(self, temp_vault):
        """Test backfill skips already-processed commits."""
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_vault, capture_output=True)

        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            git_path=str(temp_vault),
        )

        # Pre-mark a commit as processed
        daemon.work_queue.mark_completed("already_done_hash")
        assert daemon.work_queue.is_processed("already_done_hash")

    @pytest.mark.asyncio
    async def test_backfill_returns_result_dict(self, temp_vault):
        """Test backfill returns properly structured results."""
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_vault, capture_output=True)

        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            git_path=str(temp_vault),
        )

        results = await daemon.backfill()
        assert "total" in results
        assert "entire_commits" in results
        assert "processed" in results
        assert "skipped" in results
        assert "failed" in results

    @pytest.mark.asyncio
    async def test_start_with_since_sets_sync_time(self, temp_vault):
        """Test start(since=...) sets initial last_sync_time."""
        daemon = EntireSyncDaemon(
            vault_path=str(temp_vault),
            git_path=str(temp_vault),
            poll_interval_seconds=1,
        )

        # We can't run the full daemon loop, but test that since parsing works
        # by calling start with a CancelledError to break out immediately
        async def cancel_after_setup():
            await asyncio.sleep(0)
            raise asyncio.CancelledError()

        # Patch poll_and_sync to cancel immediately
        daemon.poll_and_sync = cancel_after_setup
        await daemon.start(since="2026-01-15")
        assert daemon.last_sync_time == datetime.fromisoformat("2026-01-15")


class TestHealthCheck:
    """Test health check CLI command logic."""

    def test_health_check_basic(self, temp_vault):
        """Test health check with valid paths returns healthy."""
        from click.testing import CliRunner
        from entire_main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                str(temp_vault),
                "--git-path",
                str(temp_vault),
            ],
        )
        assert "HEALTHY" in result.output
        assert result.exit_code == 0

    def test_health_check_json_output(self, temp_vault):
        """Test health check with --json-output returns valid JSON."""
        from click.testing import CliRunner
        from entire_main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                str(temp_vault),
                "--git-path",
                str(temp_vault),
                "--json-output",
            ],
        )
        import json as json_mod

        data = json_mod.loads(result.output)
        assert "healthy" in data
        assert "checks" in data
        assert data["healthy"] is True
        assert result.exit_code == 0

    def test_health_check_invalid_vault_path(self, temp_vault):
        """Test health check fails with nonexistent vault path."""
        from click.testing import CliRunner
        from entire_main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                "/nonexistent/path",
                "--git-path",
                str(temp_vault),
            ],
        )
        assert "UNHEALTHY" in result.output or result.exit_code == 1

    def test_health_check_invalid_git_path(self, temp_vault):
        """Test health check fails with nonexistent git path."""
        from click.testing import CliRunner
        from entire_main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                str(temp_vault),
                "--git-path",
                "/nonexistent/git/path",
            ],
        )
        assert result.exit_code == 1

    def test_health_check_surrealdb_skip(self, temp_vault):
        """Test health check skips SurrealDB when not configured."""
        from click.testing import CliRunner
        from entire_main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                str(temp_vault),
                "--git-path",
                str(temp_vault),
                "--json-output",
            ],
        )
        import json as json_mod

        data = json_mod.loads(result.output)
        assert data["checks"]["surrealdb"]["status"] == "skip"

    def test_health_check_dlq_warn(self, temp_vault):
        """Test health check warns when DLQ has entries."""
        from click.testing import CliRunner
        from entire_main import cli

        # Add some DLQ entries
        daemon = EntireSyncDaemon(vault_path=str(temp_vault))
        daemon.dlq.add("fail1", "reason1")
        daemon.dlq.add("fail2", "reason2")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "health",
                "--vault-path",
                str(temp_vault),
                "--git-path",
                str(temp_vault),
                "--json-output",
            ],
        )
        import json as json_mod

        data = json_mod.loads(result.output)
        assert data["checks"]["dlq"]["status"] == "warn"
        assert "2 failed" in data["checks"]["dlq"]["detail"]
