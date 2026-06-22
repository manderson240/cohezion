"""LoopDaemon — continuous sprint execution wrapping LoopCoordinator.

Runs LoopCoordinator.run() in an infinite sprint loop with:
- Graceful SIGTERM/SIGINT shutdown (stop() sets a flag, loop exits cleanly)
- Sprint health logging after each cycle (tasks_done/failed/tokens)
- Configurable inter-sprint delay (sprint_delay_seconds)
- Empty-backlog back-off (empty_backlog_delay_seconds) when no work was done

Entry point: scripts/run_loop_daemon.py
"""

from __future__ import annotations

import logging
import signal
import threading
from typing import Any

logger = logging.getLogger(__name__)


class LoopDaemon:
    """Wraps LoopCoordinator in a continuous sprint loop.

    Usage::

        daemon = LoopDaemon(coordinator=coord, sprint_delay_seconds=300)
        daemon.start()          # blocks until stop() is called
        # or run in a thread:
        t = threading.Thread(target=daemon.start)
        t.start()
        daemon.stop()
    """

    def __init__(
        self,
        coordinator: Any,
        sprint_delay_seconds: float = 300.0,
        empty_backlog_delay_seconds: float = 60.0,
    ) -> None:
        self._coordinator = coordinator
        self._sprint_delay = sprint_delay_seconds
        self._empty_delay = empty_backlog_delay_seconds
        self._stop_event = threading.Event()
        self._running = False

        # Install SIGTERM / SIGINT handler on construction so tests can fire signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    # ── lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Run the sprint loop (blocking). Returns when stop() is called."""
        self._stop_event.clear()
        self._running = True
        logger.info("LoopDaemon starting (sprint_delay=%.1fs)", self._sprint_delay)

        try:
            self._loop()
        finally:
            self._running = False
            logger.info("LoopDaemon stopped")

    def stop(self) -> None:
        """Signal the sprint loop to exit after the current sprint completes."""
        logger.info("LoopDaemon stop requested")
        self._stop_event.set()

    def is_running(self) -> bool:
        """True while the sprint loop is active."""
        return self._running

    # ── internal ──────────────────────────────────────────────────────────

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info("LoopDaemon received signal %d — stopping", signum)
        self.stop()

    def _loop(self) -> None:
        sprint_num = 0
        while not self._stop_event.is_set():
            sprint_num += 1
            logger.info("LoopDaemon sprint #%d starting", sprint_num)

            try:
                report = self._coordinator.run()
                self._log_sprint_health(sprint_num, report)
                is_empty = (
                    getattr(report, "tasks_completed", 0) == 0
                    and getattr(report, "tasks_failed", 0) == 0
                )
            except Exception as exc:
                logger.warning("LoopDaemon sprint #%d failed: %s", sprint_num, exc)
                is_empty = True

            if self._stop_event.is_set():
                break

            delay = self._empty_delay if is_empty else self._sprint_delay
            if delay > 0:
                self._stop_event.wait(timeout=delay)

    def _log_sprint_health(self, sprint_num: int, report: Any) -> None:
        completed = getattr(report, "tasks_completed", 0)
        failed = getattr(report, "tasks_failed", 0)
        sprints = getattr(report, "sprint_results", [])
        total_tokens = sum(getattr(s, "tokens_used", 0) for s in sprints)
        logger.info(
            "Sprint #%d done: tasks=%d/%d tokens=%d",
            sprint_num,
            completed,
            completed + failed,
            total_tokens,
        )
