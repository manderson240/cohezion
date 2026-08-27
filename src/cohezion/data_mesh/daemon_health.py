r"""Make a stalled daemon DETECTABLE from the datamesh bus.

WHY THIS EXISTS — a measured incident, 2026-08-11
--------------------------------------------------
``research_daemon`` logged **865 scoring timeouts against 9 successes (99.0% failure)**
while ``compound_daemon`` reported *"No pending tasks"* for **17 consecutive rounds**.
``work-queue.json`` went untouched for **7.5 hours**. Both processes were alive and writing
their own logs throughout.

Nothing detected it. Bus activity over the same 24h showed 8 distinct sources and **zero**
from either daemon. The only reason anyone found out is that a human asked a question and a
session read the logs.

It was also ONE failure, not two: research_daemon feeds the queue, it could not score, so
nothing entered the queue, so compound_daemon idled. The idle daemon was a SYMPTOM. A health
signal that cannot distinguish *failing* from *idle* would have pointed at the wrong daemon.

This is the same defect class as ``DataMeshEventBridge`` before its loss counters, and as the
~8 uncounted fail-open paths found in the codebase sweep the same day: **the failure is real,
the system looks healthy, and nothing can tell the difference.**

DESIGN COMMITMENTS
------------------
* **Liveness is not health.** A heartbeat proving only "I am running" would NOT have caught
  this — both daemons were provably alive the whole time. Every heartbeat carries the
  failure rate, the idle streak and artifact staleness.
* **Fail-open, never silent.** This must never take down the daemon it watches, so publish
  errors are swallowed — and *counted* in ``publish_failures``. A health reporter whose own
  publishing fails silently is precisely the defect it exists to detect.
* **Idle is not failure.** They have different causes and different fixes; conflating them
  makes both unactionable.
* **Stalls clear.** A counter that never resets reports a permanent stall after the first
  quiet period, which is noise rather than signal.

INTEGRATION (deliberately one import and two calls, for out-of-repo daemons)::

    from cohezion.data_mesh.daemon_health import DaemonHealth, make_bus_publisher

    health = DaemonHealth("research_daemon",
                          publish_fn=make_bus_publisher(),
                          watch_artifact=Path.home() / ".cohezion/work-queue.json")
    ...
    health.record_failure("scoring timed out")   # or record_success() / record_idle()
    health.heartbeat()                            # once per cycle
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_SURREAL_URL = "http://localhost:8001"
_TABLE = "data_product_event"
# The persisted event_type. Named so a consumer can select heartbeats specifically;
# see make_bus_publisher for why this is not "CUSTOM".
_EVENT_TYPE = "daemon_heartbeat"

# 30% of attempts failing is already an outage worth surfacing. The real incident sat at
# 99%, so this is not a tight threshold -- it is a floor beneath an obvious catastrophe.
_DEFAULT_FAILURE_THRESHOLD = 0.30
# compound_daemon sleeps 30m per round, so 5 idle rounds is ~2.5h of no work. The observed
# incident ran to 17.
_DEFAULT_STALL_AFTER_IDLE = 5
_DEFAULT_STALE_AFTER_S = 3600.0

_PRIORITY_HEALTHY = 1
_PRIORITY_DEGRADED = 5


class DaemonHealth:
    """Counters plus a bus heartbeat for a long-running daemon.

    Parameters
    ----------
    name : str
        Daemon identifier, used as the bus source suffix.
    publish_fn : callable
        Takes the payload dict, returns True on success. Injected so the class is testable
        without a live SurrealDB; use :func:`make_bus_publisher` in production.
    failure_rate_threshold : float
        Fraction of attempts failing at which ``is_degraded`` becomes True.
    stall_after_idle : int
        Consecutive idle cycles that constitute a stall.
    watch_artifact : Path | None
        A file the daemon is expected to update. Staleness here is what would have caught
        `work-queue.json` sitting untouched for 7.5h while the daemons looked busy.
    stale_after_s : float
        Age at which ``watch_artifact`` counts as stale.
    """

    def __init__(
        self,
        name: str,
        *,
        publish_fn: Callable[[dict[str, Any]], bool],
        failure_rate_threshold: float = _DEFAULT_FAILURE_THRESHOLD,
        stall_after_idle: int = _DEFAULT_STALL_AFTER_IDLE,
        watch_artifact: Path | None = None,
        stale_after_s: float = _DEFAULT_STALE_AFTER_S,
    ) -> None:
        self.name = name
        self._publish = publish_fn
        self._failure_threshold = failure_rate_threshold
        self._stall_after_idle = max(1, int(stall_after_idle))
        self._watch_artifact = watch_artifact
        self._stale_after_s = stale_after_s

        self.attempts = 0
        self.failures = 0
        self.successes = 0
        self.stalls = 0
        self.publish_failures = 0
        self._idle_streak = 0
        self._last_failure_reason = ""
        self._started = time.time()

    # ---------------------------------------------------------------- recording

    def record_success(self) -> None:
        """A unit of real work completed. Clears any stall."""
        self.attempts += 1
        self.successes += 1
        self._idle_streak = 0

    def record_failure(self, reason: str = "") -> None:
        """An attempt that failed. Counted separately from idle, deliberately."""
        self.attempts += 1
        self.failures += 1
        self._idle_streak = 0
        if reason:
            self._last_failure_reason = reason[:200]

    def record_idle(self) -> None:
        """A cycle with nothing to do. NOT an attempt and NOT a failure.

        compound_daemon was idle because research_daemon was failing. Counting idle as
        failure would have pointed the investigation at the wrong daemon.
        """
        self._idle_streak += 1
        if self._idle_streak >= self._stall_after_idle:
            self.stalls += 1

    # ---------------------------------------------------------------- state

    @property
    def failure_rate(self) -> float:
        """Fraction of attempts that failed. Zero when nothing has been attempted --
        undefined would force every caller to special-case it."""
        return self.failures / self.attempts if self.attempts else 0.0

    @property
    def is_degraded(self) -> bool:
        return self.attempts > 0 and self.failure_rate >= self._failure_threshold

    @property
    def is_stalled(self) -> bool:
        return self._idle_streak >= self._stall_after_idle

    @property
    def artifact_stale_seconds(self) -> float | None:
        """Age of ``watch_artifact``; None when unconfigured OR missing.

        Callers must use ``is_artifact_missing`` to tell those apart -- returning "fresh"
        for a file that does not exist would be the fail-open-and-silent shape again.
        """
        if self._watch_artifact is None:
            return None
        try:
            return time.time() - self._watch_artifact.stat().st_mtime
        except OSError:
            return None

    @property
    def is_artifact_missing(self) -> bool:
        """True only when an artifact was CONFIGURED and cannot be stat'd."""
        if self._watch_artifact is None:
            return False
        try:
            self._watch_artifact.stat()
        except OSError:
            return True
        return False

    @property
    def is_artifact_stale(self) -> bool:
        age = self.artifact_stale_seconds
        return age is not None and age > self._stale_after_s

    def counters(self) -> dict[str, int]:
        """Everything countable in one call, so a consumer can assert health without
        knowing the field names -- the same reasoning as DataMeshEventBridge.loss_counters."""
        return {
            "attempts": self.attempts,
            "failures": self.failures,
            "successes": self.successes,
            "stalls": self.stalls,
        }

    # ---------------------------------------------------------------- publishing

    def heartbeat(self) -> bool:
        """Publish current health. Returns True if it landed.

        Carries the counters, not merely liveness: both daemons in the real incident were
        alive and would have passed any liveness-only check.
        """
        payload: dict[str, Any] = {
            "kind": "daemon_heartbeat",
            "daemon": self.name,
            "uptime_s": round(time.time() - self._started, 1),
            "counters": self.counters(),
            "failure_rate": round(self.failure_rate, 4),
            "degraded": self.is_degraded,
            "stalled": self.is_stalled,
            "idle_streak": self._idle_streak,
            "publish_failures": self.publish_failures,
            "priority": _PRIORITY_DEGRADED
            if (self.is_degraded or self.is_stalled or self.is_artifact_stale)
            else _PRIORITY_HEALTHY,
        }
        if self._last_failure_reason:
            payload["last_failure"] = self._last_failure_reason
        age = self.artifact_stale_seconds
        if age is not None:
            payload["artifact_age_s"] = round(age, 1)
            payload["artifact_stale"] = self.is_artifact_stale
        if self.is_artifact_missing:
            payload["artifact_missing"] = True

        try:
            ok = bool(self._publish(payload))
        except Exception as exc:
            self.publish_failures += 1
            logger.debug("daemon_health(%s): publish raised: %s", self.name, exc)
            return False
        if not ok:
            self.publish_failures += 1
            logger.debug("daemon_health(%s): publish returned falsey", self.name)
        return ok


def make_bus_publisher(
    surreal_url: str = _SURREAL_URL, ns: str = "cohezion", db: str = "main"
) -> Callable[[dict[str, Any]], bool]:
    """Publisher writing to ``data_product_event`` in the shape consumers already replay.

    ``timestamp`` MUST be a float -- consumers compare it numerically, and an ISO string
    produces an HTTP 200 that no consumer will ever match.

    ``event_type`` is ``daemon_heartbeat``, NOT ``CUSTOM``. It was CUSTOM until 2026-08-12,
    which was discovered by reading the bus rather than by any test: ~170 heartbeats from a
    real run were sitting there indistinguishable from every other CUSTOM event, so the one
    query a responder would actually write --
    ``WHERE event_type = 'daemon_heartbeat'`` -- returned nothing. A health signal that
    cannot be selected is not a health signal.

    ``event_type`` is ``TYPE string`` in the schema (event_bridge.py), not an enum column,
    so a distinct value is storable; ``read_since`` selects by timestamp, so replay is
    unaffected. ``EventType.CUSTOM`` remains correct for the in-process EventBus enum --
    this is the persisted string, which is a different namespace.
    """

    def _publish(payload: dict[str, Any]) -> bool:
        body = json.dumps(
            {
                "event_type": _EVENT_TYPE,
                "source": f"daemon:{payload.get('daemon', 'unknown')}",
                "timestamp": time.time(),
                "payload": json.dumps(payload),
                "priority": int(payload.get("priority", _PRIORITY_HEALTHY)),
            }
        ).encode()
        req = urllib.request.Request(
            f"{surreal_url}/key/{_TABLE}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "surreal-ns": ns,
                "surreal-db": db,
            },
        )
        import base64

        req.add_header("Authorization", "Basic " + base64.b64encode(b"root:root").decode())
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300

    return _publish


__all__ = ["DaemonHealth", "make_bus_publisher"]
