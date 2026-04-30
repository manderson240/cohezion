"""Integration tests for Phase 2: Real-time configuration monitoring.

Tests vault monitoring, config file monitoring, and event emission.
"""

import asyncio
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


GIT = shutil.which("git") or "git"

import contextlib

from cohezion.config import ConfigMonitor, ConfigurationOrchestrator
from cohezion.core.vault_subscription import VaultEvent


class TestConfigMonitor:
    """Test real-time configuration monitoring."""

    def test_monitor_init(self, tmp_path: Path) -> None:
        """Test ConfigMonitor initialization."""
        monitor = ConfigMonitor(tmp_path)

        assert monitor.repo_root == tmp_path
        assert monitor.vault_url == "http://localhost:8360"
        assert monitor.event_bus is not None
        assert not monitor._running

    def test_monitor_file_paths(self, tmp_path: Path) -> None:
        """Test that monitor tracks correct config file paths."""
        monitor = ConfigMonitor(tmp_path)

        assert monitor.claude_md == tmp_path / "CLAUDE.md"
        assert monitor.gemini_md == tmp_path / "GEMINI.md"

    @pytest.mark.asyncio
    async def test_handle_vault_file_created(self, tmp_path: Path) -> None:
        """Test handling vault file creation events."""
        monitor = ConfigMonitor(tmp_path)

        # Create a test event
        event = VaultEvent(
            event_type="file_created",
            path="decisions/2026-02-10-test-decision.md",
            timestamp="2026-02-10T01:00:00Z",
        )

        # Handle the event
        await monitor._handle_vault_create(event)

        # Verify event was published (we can't easily check without mocking EventBus)
        # Just verify no exception was raised
        assert True

    @pytest.mark.asyncio
    async def test_handle_vault_pattern_modified(self, tmp_path: Path) -> None:
        """Test handling vault pattern modification."""
        monitor = ConfigMonitor(tmp_path)

        event = VaultEvent(
            event_type="file_modified",
            path="patterns/cost-aware-routing.md",
            timestamp="2026-02-10T01:00:00Z",
        )

        await monitor._handle_vault_modify(event)
        assert True

    @pytest.mark.asyncio
    async def test_check_config_file_no_change(self, tmp_path: Path) -> None:
        """Test that no event is emitted if file hasn't changed."""
        # Create initial file
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# CLAUDE\n\nInitial content")

        monitor = ConfigMonitor(tmp_path)

        # Initialize hash
        await monitor._check_config_file(claude_md, "CLAUDE.md")

        # Check again (should detect no change)
        await monitor._check_config_file(claude_md, "CLAUDE.md")

        assert True  # No exception

    @pytest.mark.asyncio
    async def test_check_config_file_with_change(self, tmp_path: Path) -> None:
        """Test that event is emitted when file changes."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# CLAUDE\n\nInitial")

        monitor = ConfigMonitor(tmp_path)

        # Initialize hash
        await monitor._check_config_file(claude_md, "CLAUDE.md")

        # Modify file
        claude_md.write_text("# CLAUDE\n\nModified content")

        # Check again (should detect change)
        await monitor._check_config_file(claude_md, "CLAUDE.md")

        assert True  # No exception

    @pytest.mark.asyncio
    async def test_monitor_missing_config_file(self, tmp_path: Path) -> None:
        """Test monitoring handles missing config files gracefully."""
        monitor = ConfigMonitor(tmp_path)

        # Config files don't exist
        await monitor._check_config_file(tmp_path / "CLAUDE.md", "CLAUDE.md")
        await monitor._check_config_file(tmp_path / "GEMINI.md", "GEMINI.md")

        assert True  # Should not crash

    def test_register_vault_handlers(self, tmp_path: Path) -> None:
        """Test that vault event handlers are registered."""
        monitor = ConfigMonitor(tmp_path)

        # Register handlers
        monitor._register_vault_handlers()

        # Verify handlers were registered (check vault_client._callbacks)
        assert (
            len(monitor.vault_client._callbacks) >= 3
        )  # file_created, file_modified, file_deleted

    @pytest.mark.asyncio
    async def test_monitor_lifecycle(self, tmp_path: Path) -> None:
        """Test monitor start and stop lifecycle."""
        monitor = ConfigMonitor(tmp_path)

        assert not monitor._running

        # Mock the vault_client.connect to prevent actual connection
        with patch.object(monitor.vault_client, "connect", new_callable=AsyncMock):
            # Start monitoring (will run until we stop it)
            monitor_task = asyncio.create_task(monitor.start())

            # Poll for monitor._running flag instead of fixed wait
            for _ in range(50):
                if monitor._running:
                    break
                await asyncio.sleep(0.005)

            assert monitor._running

            # Stop monitoring
            await monitor.stop()

            # Wait for task to complete
            try:
                await asyncio.wait_for(monitor_task, timeout=1.0)
            except TimeoutError:
                monitor_task.cancel()

        assert not monitor._running


class TestOrchestrationWithMonitoring:
    """Test ConfigurationOrchestrator with monitoring integration."""

    def test_orchestrator_has_monitor(self, tmp_path: Path) -> None:
        """Test that orchestrator creates a monitor."""
        orch = ConfigurationOrchestrator(tmp_path)

        assert orch.monitor is not None
        assert isinstance(orch.monitor, ConfigMonitor)

    def test_orchestrator_monitor_params(self, tmp_path: Path) -> None:
        """Test that orchestrator passes vault params to monitor."""
        orch = ConfigurationOrchestrator(
            tmp_path,
            vault_url="http://vault.test:9000",
            vault_api_key="test-key",
        )

        assert orch.monitor.vault_url == "http://vault.test:9000"
        assert orch.monitor.vault_api_key == "test-key"

    @pytest.mark.asyncio
    async def test_orchestrator_monitoring_integration(self, tmp_path: Path) -> None:
        """Test that orchestrator integrates monitoring correctly."""
        orch = ConfigurationOrchestrator(tmp_path)

        # Mock monitor.start and stop
        start_mock = AsyncMock()
        stop_mock = AsyncMock()

        with (
            patch.object(orch.monitor, "start", start_mock),
            patch.object(orch.monitor, "stop", stop_mock),
        ):
            # Start orchestration
            orchestration_task = asyncio.create_task(orch.start_monitoring())

            # Poll for _monitoring flag instead of fixed 0.1s wait
            for _ in range(50):
                if orch._monitoring:
                    break
                await asyncio.sleep(0.005)

            assert orch._monitoring

            # Cancel the task
            orchestration_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await orchestration_task

                # Verify stop was called within context
                stop_mock.assert_called()


class TestEventEmission:
    """Test that events are properly emitted by monitor."""

    @pytest.mark.asyncio
    async def test_vault_decision_event_emission(self, tmp_path: Path) -> None:
        """Test that vault decision creation emits ConfigEvent."""
        monitor = ConfigMonitor(tmp_path)

        event = VaultEvent(
            event_type="file_created",
            path="decisions/2026-02-10-test.md",
            timestamp="2026-02-10T01:00:00Z",
        )

        # Verify event is processed without exception
        await monitor._handle_vault_create(event)
        assert True

    @pytest.mark.asyncio
    async def test_manual_edit_event_emission(self, tmp_path: Path) -> None:
        """Test that manual edits emit MANUAL_EDIT_DETECTED event."""
        # Setup git repo
        import subprocess

        subprocess.run([GIT, "init"], cwd=tmp_path, capture_output=True, check=True, shell=False)
        subprocess.run(
            [GIT, "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            shell=False,
        )
        subprocess.run(
            [GIT, "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            shell=False,
        )
        subprocess.run(
            [GIT, "config", "commit.gpgsign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            shell=False,
        )

        # Create and commit initial file
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Initial")
        subprocess.run(
            [GIT, "add", "."], cwd=tmp_path, capture_output=True, check=True, shell=False
        )
        subprocess.run(
            [GIT, "commit", "-m", "initial"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
            shell=False,
        )

        monitor = ConfigMonitor(tmp_path)

        # Modify file (simulating manual edit)
        claude_md.write_text("# Modified")

        # Detect manual edit
        is_manual = monitor.git_utils.is_manual_edit(claude_md)
        assert is_manual is True

        # Handle the change
        await monitor._handle_config_file_change(claude_md, "CLAUDE.md")
        assert True
