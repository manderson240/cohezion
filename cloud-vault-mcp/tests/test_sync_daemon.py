"""Tests for sync daemon orchestrator."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from src.mcp_server.sync_daemon import (
    SyncDaemon,
    SyncConfig,
    SyncStats,
    get_sync_daemon,
    reset_sync_daemon
)
from src.mcp_server.entire_ops import Checkpoint


class TestSyncDaemon:
    """Test SyncDaemon orchestration."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_sync_daemon()
        yield
        reset_sync_daemon()

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return SyncConfig(
            repo_path=tmp_path,
            branch="main",
            poll_interval_seconds=1,  # Fast polling for tests
            sync_direction="bidirectional"
        )

    @pytest.mark.asyncio
    async def test_daemon_initialization(self, config):
        """Test daemon initializes with config."""
        daemon = SyncDaemon(config)

        assert daemon.config == config
        assert not daemon.is_running()
        assert daemon.stats.commits_synced == 0

    @pytest.mark.asyncio
    async def test_daemon_start_and_stop(self, config):
        """Test daemon can start and stop gracefully."""
        daemon = SyncDaemon(config)

        # Mock sync methods to avoid actual git/API calls
        daemon._sync_git_to_entire = AsyncMock()
        daemon._sync_entire_to_git = AsyncMock()

        # Start daemon in background
        task = asyncio.create_task(daemon.start())

        # Wait for daemon to start
        await asyncio.sleep(0.1)
        assert daemon.is_running()

        # Stop daemon
        await daemon.stop()
        await asyncio.wait_for(task, timeout=2.0)

        assert not daemon.is_running()

    @pytest.mark.asyncio
    async def test_sync_git_to_entire_no_commits(self, config):
        """Test git→entire sync with no new commits."""
        daemon = SyncDaemon(config)
        daemon._get_new_commits = AsyncMock(return_value=[])

        await daemon._sync_git_to_entire()

        assert daemon.stats.commits_synced == 0
        assert daemon.stats.checkpoints_created == 0

    @pytest.mark.asyncio
    async def test_sync_git_to_entire_with_commits(self, config):
        """Test git→entire sync creates checkpoints."""
        daemon = SyncDaemon(config)

        # Mock git commits
        mock_commits = [
            {
                "hash": "abc123",
                "message": "Test commit",
                "author": "test_author",
                "files_changed": 5,
                "lines_added": 100,
                "lines_deleted": 50
            }
        ]
        daemon._get_new_commits = AsyncMock(return_value=mock_commits)

        # Mock checkpoint creation
        mock_checkpoint = Checkpoint(
            id="cp_123",
            commit_hash="abc123",
            message="Test commit",
            timestamp="2026-02-13T00:00:00Z",
            author="test_author",
            files_changed=5,
            lines_added=100,
            lines_deleted=50
        )
        daemon.entire_client.create_checkpoint = AsyncMock(return_value=mock_checkpoint)
        daemon.entire_client.tag_checkpoint = AsyncMock(return_value=mock_checkpoint)

        await daemon._sync_git_to_entire()

        assert daemon.stats.commits_synced == 1
        assert daemon.stats.checkpoints_created == 1
        assert daemon._last_synced_commit == "abc123"

    @pytest.mark.asyncio
    async def test_sync_git_to_entire_batch_limit(self, config):
        """Test git→entire sync respects batch size limit."""
        config.max_batch_size = 2
        daemon = SyncDaemon(config)

        # Mock more commits than batch size
        mock_commits = [
            {"hash": f"commit{i}", "message": f"Msg {i}", "author": "author",
             "files_changed": 1, "lines_added": 10, "lines_deleted": 5}
            for i in range(5)
        ]
        daemon._get_new_commits = AsyncMock(return_value=mock_commits)

        mock_checkpoint = Checkpoint(
            id="cp_test",
            commit_hash="test",
            message="test",
            timestamp="2026-02-13T00:00:00Z",
            author="author",
            files_changed=1,
            lines_added=10,
            lines_deleted=5
        )
        daemon.entire_client.create_checkpoint = AsyncMock(return_value=mock_checkpoint)
        daemon.config.auto_tag = False  # Disable tagging for this test

        await daemon._sync_git_to_entire()

        # Should only sync first 2 commits
        assert daemon.stats.commits_synced == 2
        assert daemon.entire_client.create_checkpoint.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_entire_to_git_no_checkpoints(self, config):
        """Test entire→git sync with no new checkpoints."""
        daemon = SyncDaemon(config)
        daemon.entire_client.list_checkpoints = AsyncMock(return_value=[])

        await daemon._sync_entire_to_git()

        assert daemon.stats.checkpoints_downloaded == 0

    @pytest.mark.asyncio
    async def test_sync_entire_to_git_with_checkpoints(self, config):
        """Test entire→git sync annotates commits."""
        daemon = SyncDaemon(config)

        mock_checkpoints = [
            Checkpoint(
                id="cp_remote",
                commit_hash="def456",
                message="Remote checkpoint",
                timestamp="2026-02-13T00:00:00Z",
                author="remote_author",
                files_changed=3,
                lines_added=30,
                lines_deleted=15
            )
        ]
        daemon.entire_client.list_checkpoints = AsyncMock(return_value=mock_checkpoints)
        daemon._annotate_commit = AsyncMock()

        await daemon._sync_entire_to_git()

        assert daemon.stats.checkpoints_downloaded == 1
        assert daemon._last_synced_checkpoint == "cp_remote"
        daemon._annotate_commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_new_commits_parsing(self, config, tmp_path):
        """Test git log parsing extracts commit data."""
        daemon = SyncDaemon(config)

        # Mock subprocess to return fake git log output
        mock_output = """abc123|John Doe|Test commit message
10\t5\tfile1.py
20\t10\tfile2.py
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=mock_output,
                stderr="",
                returncode=0
            )

            commits = await daemon._get_new_commits()

            assert len(commits) == 1
            assert commits[0]["hash"] == "abc123"
            assert commits[0]["author"] == "John Doe"
            assert commits[0]["message"] == "Test commit message"
            assert commits[0]["files_changed"] == 2
            assert commits[0]["lines_added"] == 30
            assert commits[0]["lines_deleted"] == 15

    @pytest.mark.asyncio
    async def test_get_new_commits_with_range_filter(self, config):
        """Test git log uses commit range when last_synced_commit set."""
        daemon = SyncDaemon(config)
        daemon._last_synced_commit = "previous123"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

            await daemon._get_new_commits()

            # Verify git log was called with range
            call_args = mock_run.call_args[0][0]
            assert "previous123..main" in call_args

    @pytest.mark.asyncio
    async def test_extract_tags_from_message(self, config):
        """Test tag extraction from commit messages."""
        daemon = SyncDaemon(config)

        message = "Fix bug in sync daemon #bugfix #important"
        tags = daemon._extract_tags_from_message(message)

        assert "bugfix" in tags
        assert "important" in tags
        assert len(tags) == 2

    @pytest.mark.asyncio
    async def test_extract_tags_no_hashtags(self, config):
        """Test tag extraction returns empty list for no hashtags."""
        daemon = SyncDaemon(config)

        message = "Regular commit message without tags"
        tags = daemon._extract_tags_from_message(message)

        assert len(tags) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, config):
        """Test retrieving daemon statistics."""
        daemon = SyncDaemon(config)
        daemon.stats.commits_synced = 10
        daemon.stats.checkpoints_created = 10
        daemon.stats.errors = 2

        stats = daemon.get_stats()

        assert stats.commits_synced == 10
        assert stats.checkpoints_created == 10
        assert stats.errors == 2

    @pytest.mark.asyncio
    async def test_sync_direction_git_only(self, config):
        """Test daemon respects git_to_entire sync direction."""
        config.sync_direction = "git_to_entire"
        daemon = SyncDaemon(config)

        daemon._sync_git_to_entire = AsyncMock()
        daemon._sync_entire_to_git = AsyncMock()

        # Run one sync cycle manually
        await daemon._sync_git_to_entire()

        daemon._sync_git_to_entire.assert_awaited_once()
        daemon._sync_entire_to_git.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sync_direction_entire_only(self, config):
        """Test daemon respects entire_to_git sync direction."""
        config.sync_direction = "entire_to_git"
        daemon = SyncDaemon(config)

        daemon._sync_git_to_entire = AsyncMock()
        daemon._sync_entire_to_git = AsyncMock()

        # Run one sync cycle manually
        await daemon._sync_entire_to_git()

        daemon._sync_entire_to_git.assert_awaited_once()
        daemon._sync_git_to_entire.assert_not_awaited()

    def test_singleton_pattern(self, config):
        """Test get_sync_daemon returns singleton instance."""
        daemon1 = get_sync_daemon(config)
        daemon2 = get_sync_daemon()  # Should return same instance

        assert daemon1 is daemon2

    def test_singleton_requires_config_first_call(self):
        """Test get_sync_daemon raises error if config not provided first."""
        with pytest.raises(ValueError, match="Config required"):
            get_sync_daemon()

    def test_reset_singleton(self, config):
        """Test reset_sync_daemon clears singleton."""
        daemon1 = get_sync_daemon(config)
        reset_sync_daemon()
        daemon2 = get_sync_daemon(config)

        assert daemon1 is not daemon2
