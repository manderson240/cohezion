"""Integration tests for Phase 2: Real-time configuration monitoring.

Tests vault monitoring, config file monitoring, and event emission.
"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.config import ConfigMonitor, ConfigurationOrchestrator
from cohezion.core.event_bus import Event, EventType
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
        received = await _collect_config_events(
            monitor, lambda: monitor._handle_vault_create(event)
        )

        assert [e.payload["config_event"] for e in received] == ["VAULT_DECISION_ADDED"]

    @pytest.mark.asyncio
    async def test_handle_vault_pattern_modified(self, tmp_path: Path) -> None:
        """Test handling vault pattern modification."""
        monitor = ConfigMonitor(tmp_path)

        event = VaultEvent(
            event_type="file_modified",
            path="patterns/cost-aware-routing.md",
            timestamp="2026-02-10T01:00:00Z",
        )

        received = await _collect_config_events(
            monitor, lambda: monitor._handle_vault_modify(event)
        )

        assert [e.payload["config_event"] for e in received] == ["VAULT_PATTERN_UPDATED"]

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
        received = await _collect_config_events(
            monitor, lambda: monitor._check_config_file(claude_md, "CLAUDE.md")
        )

        # The negative half of the pair with test_check_config_file_with_change.
        # Asserting emptiness only means something because that sibling proves
        # this same collector DOES see an event when the file really changed --
        # otherwise a permanently-broken publish path would satisfy it.
        assert received == []

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
        received = await _collect_config_events(
            monitor, lambda: monitor._check_config_file(claude_md, "CLAUDE.md")
        )

        assert [e.payload["config_event"] for e in received] == ["CONFIG_FILE_MODIFIED"]
        assert received[0].payload["file"] == "CLAUDE.md"

    @pytest.mark.asyncio
    async def test_monitor_missing_config_file(self, tmp_path: Path) -> None:
        """Test monitoring handles missing config files gracefully."""
        monitor = ConfigMonitor(tmp_path)

        # Config files don't exist
        received = await _collect_config_events(
            monitor,
            lambda: monitor._check_config_file(tmp_path / "CLAUDE.md", "CLAUDE.md"),
        )

        # Absent is not "changed": a missing file must not raise AND must not
        # announce a modification.
        assert received == []

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

    @pytest.mark.asyncio
    async def test_start_starts_the_event_bus_and_stop_stops_it(self, tmp_path: Path) -> None:
        """`start()` must bring the bus up, or every publish is refused.

        The delivery tests in TestEventEmission start the bus themselves to
        isolate the publish contract, so without this test nothing would fail
        if `start()` stopped starting the bus -- and every config event would
        silently go back to being dropped (event_bus D7).

        Polls the bus's own flag rather than `monitor._running`: the monitor
        sets its flag first and only then awaits `event_bus.start()`, so
        `monitor._running` is true for a moment while the bus is still down.
        """
        monitor = ConfigMonitor(tmp_path)

        assert not monitor.event_bus._running

        with patch.object(monitor.vault_client, "connect", new_callable=AsyncMock):
            monitor_task = asyncio.create_task(monitor.start())

            for _ in range(100):
                if monitor.event_bus._running:
                    break
                await asyncio.sleep(0.005)

            assert monitor.event_bus._running, "start() did not start the event bus"

            await monitor.stop()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(monitor_task, timeout=1.0)
            monitor_task.cancel()

        assert not monitor.event_bus._running

    @pytest.mark.asyncio
    async def test_bus_is_stopped_exactly_once_per_lifecycle(self, tmp_path: Path) -> None:
        """Both `stop()` and `start()`'s finally reach the bus -- only one may act.

        `EventBus.stop()` is not cheaply idempotent when its drain times out:
        it counts abandoned events without calling `task_done()`, so a second
        call blocks for the whole `drain_timeout` again (measured 0.501s for a
        0.5s timeout => ~60s at the 30s default) and double-counts them into
        `dropped`. Adversarial review of the bus-lifecycle change caught this;
        the probe reproducing it is quoted in `_stop_bus_once`.
        """
        monitor = ConfigMonitor(tmp_path)

        calls = 0
        real_stop = monitor.event_bus.stop

        async def counting_stop(*args, **kwargs):
            nonlocal calls
            calls += 1
            return await real_stop(*args, **kwargs)

        monitor.event_bus.stop = counting_stop  # type: ignore[method-assign]

        with patch.object(monitor.vault_client, "connect", new_callable=AsyncMock):
            monitor_task = asyncio.create_task(monitor.start())

            for _ in range(100):
                if monitor.event_bus._running:
                    break
                await asyncio.sleep(0.005)
            assert monitor.event_bus._running

            await monitor.stop()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(monitor_task, timeout=1.0)
            monitor_task.cancel()

        assert calls == 1, f"EventBus.stop() called {calls}x; the second re-runs the drain"

    @pytest.mark.asyncio
    async def test_stopping_an_unstarted_monitor_never_touches_the_bus(
        self, tmp_path: Path
    ) -> None:
        """Discriminating: a guard of `if True` would call stop() here anyway."""
        monitor = ConfigMonitor(tmp_path)

        calls = 0

        async def counting_stop(*args, **kwargs):
            nonlocal calls
            calls += 1

        monitor.event_bus.stop = counting_stop  # type: ignore[method-assign]

        with patch.object(monitor.vault_client, "disconnect", new_callable=AsyncMock):
            await monitor.stop()

        assert calls == 0


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

        with patch.object(orch.monitor, "start", start_mock):
            with patch.object(orch.monitor, "stop", stop_mock):
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


async def _collect_config_events(monitor: ConfigMonitor, emit) -> list:
    """Run `emit()` against a started bus and return what a subscriber received.

    Delivery, not invocation, is the assertion that discriminates here. Every
    config event used to be dropped twice over: `publish()` was called without
    `await` (the coroutine was discarded before reaching the queue), and the
    monitor's private EventBus was never started, so `publish()` would have
    returned False anyway (event_bus D7). A test asserting "publish was called"
    goes green the moment `await` is added, while delivery is still zero.

    `stop()` performs a bounded drain, so it is both the synchronisation point
    and coverage of the lifecycle wiring.
    """
    received: list = []

    async def _collector(event) -> None:
        received.append(event)

    monitor.event_bus.register_handler(_collector)
    await monitor.event_bus.start()
    try:
        await emit()
    finally:
        await monitor.event_bus.stop()
    return received


class TestEventEmission:
    """Test that events are properly emitted by monitor."""

    @pytest.mark.asyncio
    async def test_publish_is_refused_while_the_bus_is_not_started(self, tmp_path: Path) -> None:
        """The precondition this suite relies on must be able to fail.

        If `publish()` returned True on an unstarted bus, the delivery tests
        below could not distinguish a working bus from a dropped event.
        """
        monitor = ConfigMonitor(tmp_path)
        from cohezion.core.event_bus import Event, EventType

        accepted = await monitor.event_bus.publish(
            Event(type=EventType.CUSTOM, source="test", payload={})
        )

        assert accepted is False

    @pytest.mark.asyncio
    async def test_vault_decision_event_reaches_a_subscriber(self, tmp_path: Path) -> None:
        """A vault decision must actually deliver VAULT_DECISION_ADDED."""
        monitor = ConfigMonitor(tmp_path)

        event = VaultEvent(
            event_type="file_created",
            path="decisions/2026-02-10-test.md",
            timestamp="2026-02-10T01:00:00Z",
        )

        received = await _collect_config_events(
            monitor, lambda: monitor._handle_vault_create(event)
        )

        assert [e.payload["config_event"] for e in received] == ["VAULT_DECISION_ADDED"]

    @pytest.mark.asyncio
    async def test_manual_edit_event_emission(self, tmp_path: Path) -> None:
        """Test that manual edits emit MANUAL_EDIT_DETECTED event."""
        # Setup git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
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
            ["git", "config", "commit.gpgsign", "false"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Create and commit initial file
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Initial")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True
        )

        monitor = ConfigMonitor(tmp_path)

        # Modify file (simulating manual edit)
        claude_md.write_text("# Modified")

        # Detect manual edit
        is_manual = monitor.git_utils.is_manual_edit(claude_md)
        assert is_manual is True

        # Handle the change
        received = await _collect_config_events(
            monitor, lambda: monitor._handle_config_file_change(claude_md, "CLAUDE.md")
        )

        assert [e.payload["config_event"] for e in received] == ["MANUAL_EDIT_DETECTED"]
        assert received[0].payload["file"] == "CLAUDE.md"


class TestConfigEventDelivery:
    """A config event must REACH a subscriber, not merely be awaited.

    Regression guard for the 2026-09-10 false-contract audit (F1). Seven call sites
    invoked the ``async`` ``EventBus.publish`` without ``await``: the coroutine was
    constructed and dropped, so the event was never even offered to the bus. mypy
    reported every one as ``[unused-coroutine]`` and nothing gated on it.

    The tests below cover the softer defect the fix could itself have introduced
    (delivery itself is pinned by TestEventEmission).

    * ``test_refused_event_is_counted_not_silently_discarded`` fails if the returned
      bool is awaited and then ignored: ``publish`` returns False when the bus is not
      running (EB1c/D7) precisely so a caller can tell enqueued from dropped.

    Asserting delivery rather than invocation is deliberate: a passing consumption
    invariant proves wiring, never throughput.
    """

    @pytest.mark.asyncio
    async def test_refused_event_is_counted_not_silently_discarded(self, tmp_path: Path) -> None:
        """A bus that never started refuses the event, and the caller records it."""
        monitor = ConfigMonitor(tmp_path)
        assert not monitor.event_bus._running, "precondition: bus must not be running"

        await monitor._handle_vault_create(
            VaultEvent(event_type="file_created", path="decisions/x.md", timestamp="t0")
        )

        assert monitor.dropped_events == 1

    @pytest.mark.asyncio
    async def test_non_matching_path_emits_nothing(self, tmp_path: Path) -> None:
        """Negative control: the counter tracks real drops, not every call.

        Without this, ``dropped_events == 1`` above could be satisfied by an
        implementation that increments unconditionally.
        """
        monitor = ConfigMonitor(tmp_path)

        await monitor._handle_vault_create(
            VaultEvent(event_type="file_created", path="unrelated/x.md", timestamp="t0")
        )

        assert monitor.dropped_events == 0
