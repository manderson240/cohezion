"""TDD tests for LoopDaemon (Task #20) — V-model MD/AD level.

The daemon wraps LoopCoordinator in a continuous sprint loop.

V-Model contracts tested here (MD = module, AD = architecture):
  MD1: daemon has stop() / is_running() lifecycle interface
  MD2: stop() causes the sprint loop to exit cleanly
  MD3: sprint_delay_seconds is respected between sprints
  MD4: sprint health is logged after each sprint
  AD1: coordinator.run() is called once per sprint
  AD2: SIGTERM triggers stop() gracefully

These MUST fail before scripts/loop_daemon.py exists.
"""

from __future__ import annotations

import signal
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ── import guard ──────────────────────────────────────────────────────────────


def _import_daemon():
    """Import LoopDaemon — fails if not yet implemented (RED guard)."""
    from cohezion.compound.loop_daemon import LoopDaemon

    return LoopDaemon


# ── structural invariants (MD level) ─────────────────────────────────────────


def test_loop_daemon_importable():
    """scripts/loop_daemon.py must exist and export LoopDaemon."""
    LoopDaemon = _import_daemon()
    assert LoopDaemon is not None


def test_loop_daemon_has_lifecycle_interface():
    """LoopDaemon must expose start(), stop(), is_running()."""
    LoopDaemon = _import_daemon()
    mock_coord = MagicMock()
    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=0.0)

    assert hasattr(daemon, "start"), "start() missing"
    assert hasattr(daemon, "stop"), "stop() missing"
    assert hasattr(daemon, "is_running"), "is_running() missing"


def test_loop_daemon_not_running_before_start():
    """is_running() must return False before start() is called."""
    LoopDaemon = _import_daemon()
    daemon = LoopDaemon(coordinator=MagicMock(), sprint_delay_seconds=0.0)
    assert not daemon.is_running()


# ── lifecycle contracts (MD level) ────────────────────────────────────────────


def test_stop_terminates_loop():
    """stop() must cause the sprint loop to exit within 2 seconds."""
    LoopDaemon = _import_daemon()

    mock_coord = MagicMock()
    mock_coord.run.return_value = SimpleNamespace(
        tasks_completed=1,
        tasks_failed=0,
        sprint_results=[],
        results=[],
    )

    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=0.01)

    t = threading.Thread(target=daemon.start, daemon=True)
    t.start()

    # Give daemon time to enter the loop
    time.sleep(0.05)
    assert daemon.is_running(), "Daemon must be running after start()"

    daemon.stop()
    t.join(timeout=2.0)

    assert not t.is_alive(), "Daemon thread must terminate within 2s of stop()"
    assert not daemon.is_running()


def test_coordinator_run_called_per_sprint():
    """coordinator.run() must be called once per sprint cycle."""
    LoopDaemon = _import_daemon()

    sprint_count = [0]
    stop_after = 3

    def fake_run(executor=None):
        sprint_count[0] += 1
        return SimpleNamespace(
            tasks_completed=1,
            tasks_failed=0,
            sprint_results=[],
            results=[],
        )

    mock_coord = MagicMock()
    mock_coord.run.side_effect = fake_run

    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=0.0)

    def run_and_stop():
        # Let 3 sprints fire then stop
        while sprint_count[0] < stop_after:
            time.sleep(0.005)
        daemon.stop()

    stopper = threading.Thread(target=run_and_stop, daemon=True)
    stopper.start()

    daemon.start()

    assert sprint_count[0] >= stop_after, (
        f"coordinator.run() must be called ≥{stop_after} times; got {sprint_count[0]}"
    )


def test_sprint_delay_is_respected():
    """sprint_delay_seconds must pause between sprints (not tight-loop)."""
    LoopDaemon = _import_daemon()

    sprint_times: list[float] = []

    def fake_run(executor=None):
        sprint_times.append(time.monotonic())
        return SimpleNamespace(
            tasks_completed=1,
            tasks_failed=0,  # non-empty → uses sprint_delay, not empty_delay
            sprint_results=[],
            results=[],
        )

    mock_coord = MagicMock()
    mock_coord.run.side_effect = fake_run

    delay = 0.05
    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=delay)

    def stop_after_two():
        while len(sprint_times) < 2:
            time.sleep(0.005)
        daemon.stop()

    threading.Thread(target=stop_after_two, daemon=True).start()
    daemon.start()

    assert len(sprint_times) >= 2
    gap = sprint_times[1] - sprint_times[0]
    assert gap >= delay * 0.8, (
        f"Gap between sprints ({gap:.3f}s) must be ≥ sprint_delay_seconds ({delay}s)"
    )


def test_sigterm_triggers_stop():
    """SIGTERM to the daemon's thread must cause is_running() to become False."""
    LoopDaemon = _import_daemon()

    mock_coord = MagicMock()
    mock_coord.run.return_value = SimpleNamespace(
        tasks_completed=0,
        tasks_failed=0,
        sprint_results=[],
        results=[],
    )

    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=0.01)

    t = threading.Thread(target=daemon.start, daemon=True)
    t.start()
    time.sleep(0.05)

    # Send SIGTERM to main process — daemon must handle it
    signal.raise_signal(signal.SIGTERM)
    t.join(timeout=2.0)

    assert not daemon.is_running(), "SIGTERM must cause daemon to stop"


def test_daemon_logs_sprint_health(capsys):
    """Daemon must emit sprint health info (tasks_done/failed/tokens) after each sprint."""
    LoopDaemon = _import_daemon()

    sprint_count = [0]

    def fake_run(executor=None):
        sprint_count[0] += 1
        return SimpleNamespace(
            tasks_completed=3,
            tasks_failed=1,
            sprint_results=[SimpleNamespace(tasks_done=3, tasks_failed=1, tokens_used=500)],
            results=[],
        )

    mock_coord = MagicMock()
    mock_coord.run.side_effect = fake_run

    daemon = LoopDaemon(coordinator=mock_coord, sprint_delay_seconds=0.0)

    def stop_after_one():
        while sprint_count[0] < 1:
            time.sleep(0.005)
        daemon.stop()

    threading.Thread(target=stop_after_one, daemon=True).start()

    with patch("cohezion.compound.loop_daemon.logger") as mock_logger:
        daemon.start()

    # At least one info log must mention sprint results
    info_calls = [str(c) for c in mock_logger.info.call_args_list]
    assert any("sprint" in c.lower() or "tasks" in c.lower() for c in info_calls), (
        f"Daemon must log sprint health; no matching log call found.\nActual calls: {info_calls}"
    )


def test_backlog_empty_triggers_delay():
    """When coordinator returns 0 tasks completed and 0 failed, daemon must pause before retry."""
    LoopDaemon = _import_daemon()

    call_times: list[float] = []

    def fake_run(executor=None):
        call_times.append(time.monotonic())
        return SimpleNamespace(
            tasks_completed=0,
            tasks_failed=0,
            sprint_results=[],
            results=[],
        )

    mock_coord = MagicMock()
    mock_coord.run.side_effect = fake_run

    empty_delay = 0.05
    daemon = LoopDaemon(
        coordinator=mock_coord,
        sprint_delay_seconds=0.0,
        empty_backlog_delay_seconds=empty_delay,
    )

    def stop_after_two():
        while len(call_times) < 2:
            time.sleep(0.005)
        daemon.stop()

    threading.Thread(target=stop_after_two, daemon=True).start()
    daemon.start()

    assert len(call_times) >= 2
    gap = call_times[1] - call_times[0]
    assert gap >= empty_delay * 0.8, f"Empty-backlog delay ({gap:.3f}s) must be ≥ {empty_delay}s"
