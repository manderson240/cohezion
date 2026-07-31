"""SCP2 liveness must survive a PID-namespace boundary.

`os.kill(pid, 0)` answers "does this PID exist in MY pid namespace", which is not the
question `list_active()` asks. Read from a sandboxed agent shell (a different pid
namespace than the session that wrote the row) it is wrong in BOTH directions:

  * false ALIVE  — a recycled sandbox PID collides with a long-dead session's pid
  * false DEAD   — a genuinely live host session's pid does not exist locally

Observed 2026-07-31: `session_registry` held a row `pid-79 / claude:l3-evolver-world-model`
whose last heartbeat was >33h old, reported alive because PID 79 was the *reader* itself.

These tests are discriminating: each fails against the namespace-blind implementation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from cohezion.sessions import session_bus
from cohezion.sessions.session_bus import SessionRegistry


def _iso(age_seconds: float) -> str:
    return (datetime.now(UTC) - timedelta(seconds=age_seconds)).isoformat()


def test_foreign_namespace_stale_row_is_not_alive():
    """The observed defect: a legacy row (no ns) whose pid collides with the reader's own
    pid, but which has not heartbeat in >33h, must NOT be reported alive.

    Namespace-blind `os.kill(os.getpid(), 0)` succeeds -> old code says ALIVE."""
    row = {"session_id": "ghost", "pid": os.getpid(), "last_seen": _iso(33 * 3600)}
    assert session_bus._liveness(row) is None


def test_foreign_namespace_recent_row_is_assumed_alive():
    """The mirror defect: a row written from another namespace, whose pid does not exist
    here, but which heartbeat seconds ago. Dropping it silently loses operator broadcasts.

    Namespace-blind `os.kill(4000000, 0)` raises ProcessLookupError -> old code says DEAD."""
    row = {
        "session_id": "remote",
        "pid": 4_000_000,  # unallocatable: above /proc/sys/kernel/pid_max
        "ns": "some-other-boot/pid:[4026500000]",
        "last_seen": _iso(30),
    }
    assert session_bus._liveness(row) == "assumed"


def test_same_namespace_keeps_process_existence_authoritative():
    """SCP2 intent preserved: when the row was written from THIS namespace, process
    existence stays authoritative and outranks last_seen recency entirely."""
    ns = session_bus._pid_namespace()
    live = {"session_id": "self", "pid": os.getpid(), "ns": ns, "last_seen": _iso(99 * 3600)}
    dead = {"session_id": "gone", "pid": 4_000_000, "ns": ns, "last_seen": _iso(1)}
    # Stale heartbeat but the process exists -> alive (last_seen must not override).
    assert session_bus._liveness(live) == "confirmed"
    # Fresh heartbeat but the process is gone -> dead.
    assert session_bus._liveness(dead) is None


def test_pid_namespace_is_stable_and_boot_qualified():
    ns = session_bus._pid_namespace()
    assert ns and ns == session_bus._pid_namespace(), "namespace token must be stable"
    assert "pid:[" in ns, "must identify the pid namespace"
    assert "/" in ns, "must be boot-qualified so namespace inodes cannot alias across reboots"


def test_register_records_the_writing_namespace(monkeypatch):
    """Without this, every row is legacy/UNKNOWN forever and the reader can never trust
    os.kill — including the row this very session writes."""
    sent: list[str] = []
    monkeypatch.setattr(session_bus, "_sql", lambda q, timeout=5.0: sent.append(q) or [])
    SessionRegistry().register("s-abc", "label", 4242)
    assert sent and "ns" in sent[0], "register() must persist the writing pid namespace"
    assert session_bus._pid_namespace() in sent[0]


def test_list_active_annotates_liveness_and_drops_ghosts(monkeypatch):
    """End-to-end through the public reader consumers actually call."""
    ns = session_bus._pid_namespace()
    rows = [
        {"session_id": "self", "pid": os.getpid(), "ns": ns, "last_seen": _iso(5)},
        {"session_id": "ghost", "pid": os.getpid(), "last_seen": _iso(33 * 3600)},
        {"session_id": "remote", "pid": 4_000_000, "ns": "other/pid:[1]", "last_seen": _iso(9)},
    ]
    monkeypatch.setattr(session_bus, "_sql", lambda q, timeout=5.0: rows)
    got = {r["session_id"]: r["liveness"] for r in SessionRegistry().list_active()}
    assert got == {"self": "confirmed", "remote": "assumed"}


@pytest.mark.parametrize("bad", [None, "", "not-a-timestamp"])
def test_unparseable_last_seen_on_foreign_row_is_not_alive(bad):
    row = {"session_id": "x", "pid": os.getpid(), "ns": "other/pid:[1]", "last_seen": bad}
    assert session_bus._liveness(row) is None
