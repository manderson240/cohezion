"""A stalled daemon must be DETECTABLE from the bus.

Written against a measured incident (2026-08-11): research_daemon logged 865 scoring
timeouts against 9 successes (99.0% failure) while compound_daemon reported "No pending
tasks" for 17 consecutive rounds. `work-queue.json` went untouched for 7.5 hours. Both
processes were alive and writing their own logs the entire time.

Nothing detected it. Bus activity over 24h showed 8 distinct sources and ZERO from either
daemon. The only reason anyone found out is that a human asked and a session read the logs.

This is the same defect class as DataMeshEventBridge before its loss counters: the failure
is real, the system looks healthy, and nothing can tell the difference.

The tests below are written so that a health reporter which merely EXISTS fails them. Each
one asserts a condition that would have caught the real incident.
"""

from __future__ import annotations

import pytest

from cohezion.data_mesh.daemon_health import DaemonHealth


class TestFailureRateIsCountable:
    """The 99% scorer failure had to be countable, not just loggable."""

    def test_counts_are_zero_at_start(self) -> None:
        h = DaemonHealth("research_daemon", publish_fn=lambda _: True)
        assert h.counters() == {"attempts": 0, "failures": 0, "successes": 0, "stalls": 0}

    def test_failure_rate_reproduces_the_real_incident(self) -> None:
        """865 failures / 9 successes = 98.97%. A reporter that tracks only a boolean
        'healthy' flag cannot express this, which is why the incident was invisible."""
        h = DaemonHealth("research_daemon", publish_fn=lambda _: True)
        for _ in range(865):
            h.record_failure("timed out")
        for _ in range(9):
            h.record_success()
        assert h.counters()["failures"] == 865
        assert h.failure_rate == pytest.approx(865 / 874, abs=1e-6)
        assert h.is_degraded, "99% failure must register as degraded"

    def test_healthy_daemon_is_not_degraded(self) -> None:
        """DISCRIMINATING: a reporter that always says 'degraded' would pass the test above
        and fail this one."""
        h = DaemonHealth("d", publish_fn=lambda _: True)
        for _ in range(100):
            h.record_success()
        assert h.failure_rate == 0.0
        assert not h.is_degraded

    def test_degradation_threshold_is_crossable_in_both_directions(self) -> None:
        h = DaemonHealth("d", publish_fn=lambda _: True, failure_rate_threshold=0.5)
        for _ in range(10):
            h.record_failure("x")
        assert h.is_degraded
        for _ in range(30):
            h.record_success()
        assert not h.is_degraded, "recovery must be visible, not latched"

    def test_failure_rate_with_no_attempts_is_zero_not_undefined(self) -> None:
        assert DaemonHealth("d", publish_fn=lambda _: True).failure_rate == 0.0


class TestStallDetection:
    """compound_daemon: 'No pending tasks' x17 rounds, ~7 hours."""

    def test_consecutive_idle_rounds_become_a_stall(self) -> None:
        h = DaemonHealth("compound_daemon", publish_fn=lambda _: True, stall_after_idle=5)
        for _ in range(4):
            h.record_idle()
        assert not h.is_stalled
        h.record_idle()
        assert h.is_stalled, "5 consecutive idle rounds must register as a stall"

    def test_the_real_incident_registers(self) -> None:
        h = DaemonHealth("compound_daemon", publish_fn=lambda _: True, stall_after_idle=5)
        for _ in range(17):
            h.record_idle()
        assert h.is_stalled
        assert h.counters()["stalls"] == 17 - 5 + 1

    def test_work_resets_the_idle_streak(self) -> None:
        """DISCRIMINATING: a counter that never resets reports a permanent stall after the
        first quiet period, which is noise, not signal."""
        h = DaemonHealth("d", publish_fn=lambda _: True, stall_after_idle=3)
        for _ in range(3):
            h.record_idle()
        assert h.is_stalled
        h.record_success()
        assert not h.is_stalled, "a stall must clear when the daemon does work again"

    def test_idle_is_not_failure(self) -> None:
        """An idle daemon is not a failing one — conflating them makes both unactionable.
        compound_daemon was idle BECAUSE research_daemon was failing; they are different
        conditions with different fixes."""
        h = DaemonHealth("d", publish_fn=lambda _: True)
        for _ in range(10):
            h.record_idle()
        assert h.counters()["failures"] == 0
        assert h.failure_rate == 0.0


class TestPublishing:
    """A health report nobody can see is the defect, not the fix."""

    def test_heartbeat_publishes(self) -> None:
        sent: list[dict] = []
        h = DaemonHealth("d", publish_fn=lambda p: sent.append(p) or True)
        h.heartbeat()
        assert len(sent) == 1
        assert sent[0]["kind"] == "daemon_heartbeat"
        assert sent[0]["daemon"] == "d"

    def test_heartbeat_carries_the_counters(self) -> None:
        """DISCRIMINATING: a heartbeat that proves only liveness would NOT have caught this
        incident — both daemons were demonstrably alive the whole time. It must carry the
        failure rate."""
        sent: list[dict] = []
        h = DaemonHealth("d", publish_fn=lambda p: sent.append(p) or True)
        for _ in range(9):
            h.record_failure("boom")
        h.record_success()
        h.heartbeat()
        p = sent[0]
        assert p["counters"]["failures"] == 9
        assert p["failure_rate"] == pytest.approx(0.9)
        assert p["degraded"] is True

    def test_publish_failure_is_COUNTED_not_swallowed(self) -> None:
        """The recursion the whole exercise is about: a health reporter whose OWN publish
        fails silently is exactly the defect it exists to detect."""
        h = DaemonHealth("d", publish_fn=lambda _: False)  # publish always fails
        h.heartbeat()
        h.heartbeat()
        assert h.publish_failures == 2

    def test_publish_exception_does_not_crash_the_daemon(self) -> None:
        """Fail-open is required — a health reporter must never take down the daemon it
        watches — but it must still COUNT."""

        def boom(_):
            raise RuntimeError("bus down")

        h = DaemonHealth("d", publish_fn=boom)
        h.heartbeat()  # must not raise
        assert h.publish_failures == 1

    def test_degraded_state_escalates_priority(self) -> None:
        sent: list[dict] = []
        h = DaemonHealth("d", publish_fn=lambda p: sent.append(p) or True)
        h.heartbeat()
        healthy_priority = sent[-1]["priority"]
        for _ in range(20):
            h.record_failure("x")
        h.heartbeat()
        assert sent[-1]["priority"] > healthy_priority, (
            "a degraded heartbeat must be distinguishable from a healthy one by priority"
        )


class TestStaleness:
    """work-queue.json untouched for 7.5h while both daemons wrote logs."""

    def test_stale_artifact_is_reported(self, tmp_path) -> None:
        import os
        import time

        p = tmp_path / "work-queue.json"
        p.write_text("{}")
        os.utime(p, (time.time() - 8 * 3600, time.time() - 8 * 3600))
        h = DaemonHealth("d", publish_fn=lambda _: True, watch_artifact=p, stale_after_s=3600)
        assert h.artifact_stale_seconds is not None
        assert h.artifact_stale_seconds > 7 * 3600
        assert h.is_artifact_stale

    def test_fresh_artifact_is_not_stale(self, tmp_path) -> None:
        p = tmp_path / "q.json"
        p.write_text("{}")
        h = DaemonHealth("d", publish_fn=lambda _: True, watch_artifact=p, stale_after_s=3600)
        assert not h.is_artifact_stale

    def test_missing_artifact_is_not_silently_fresh(self, tmp_path) -> None:
        """DISCRIMINATING: returning 'not stale' for a file that does not exist is the
        fail-open-and-silent shape all over again."""
        h = DaemonHealth(
            "d",
            publish_fn=lambda _: True,
            watch_artifact=tmp_path / "nope.json",
            stale_after_s=60,
        )
        assert h.artifact_stale_seconds is None
        assert h.is_artifact_missing

    def test_no_watch_artifact_configured_is_distinguishable_from_fresh(self) -> None:
        h = DaemonHealth("d", publish_fn=lambda _: True)
        assert h.artifact_stale_seconds is None
        assert not h.is_artifact_missing, "not configured is not the same as missing"
