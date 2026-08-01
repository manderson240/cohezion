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


@pytest.mark.parametrize("ahead_s", [3600, 10 * 365 * 24 * 3600])
def test_d3_future_last_seen_is_not_permanently_alive(ahead_s):
    """D3 (orchestrator probe + kimi #4/#9 + gpt-oss #8) — a negative age never exceeds
    stale_after_s, so a row written under clock skew stayed 'assumed' alive FOREVER (verified
    with a timestamp 10 years ahead). A clock ahead of the reader must not confer immortality."""
    ts = (datetime.now(UTC) + timedelta(seconds=ahead_s)).isoformat()
    row = {"session_id": "skewed", "pid": 4_000_000, "ns": "other/pid:[1]", "last_seen": ts}
    assert session_bus._liveness(row) is None


def test_d4_legacy_row_with_no_timestamp_is_kept_by_the_weak_pid_signal():
    """D4 (kimi-k2.7 #5/#8) — a legacy row (no `ns`) with NO usable timestamp had os.kill
    ignored entirely and was dropped even when the process was genuinely alive here.

    os.kill is a WEAK signal without a namespace, so the row is KEPT as 'assumed' and never
    promoted to 'confirmed' — a colliding PID must not manufacture certainty."""
    for bad in (None, "", "not-a-timestamp"):
        row = {"session_id": "legacy", "pid": os.getpid(), "last_seen": bad}
        assert session_bus._liveness(row) == "assumed", f"last_seen={bad!r}"


def test_d4_weak_signal_must_not_override_a_definite_stale_timestamp():
    """The gate that keeps D4 from resurrecting the original ghost.

    A dead session whose pid collides with the reader, and a live session that has not
    heartbeat in 33h, are THE SAME INPUT SHAPE — indistinguishable. Letting the weak pid
    signal win would re-admit `pid-79 / claude:l3-evolver-world-model` (33h stale, colliding
    pid), the exact row this module was fixed to drop. Evidence beats a tiebreaker.

    Safe because session-inbox.sh heartbeats on every UserPromptSubmit, so a genuinely live
    session has a FRESH last_seen and is kept by the TTL branch; only a session idle past the
    TTL is dropped, and it re-registers on its next turn."""
    ghost = {"session_id": "ghost", "pid": os.getpid(), "last_seen": _iso(33 * 3600)}
    assert session_bus._liveness(ghost) is None


def test_d4_legacy_row_with_dead_pid_still_falls_back_to_ttl():
    """The weak signal must not become authoritative in the other direction either: a legacy
    row whose PID is absent HERE may still be a live session in another namespace, so a fresh
    heartbeat keeps it, and only a stale one drops it."""
    fresh = {"session_id": "legacy-fresh", "pid": 4_000_000, "last_seen": _iso(30)}
    stale = {"session_id": "legacy-stale", "pid": 4_000_000, "last_seen": _iso(33 * 3600)}
    assert session_bus._liveness(fresh) == "assumed"
    assert session_bus._liveness(stale) is None


def test_d5_unreadable_boot_id_yields_a_non_matching_namespace(monkeypatch):
    """D5 (kimi-k2.7 #6) — falling back to the literal 'unknown-boot' made the token COLLIDABLE:
    two different hosts that both cannot read boot_id produce an equal string, the same-namespace
    guard passes, and a foreign PID is trusted as 'confirmed'. An unknown boot id must produce a
    falsy token so the honest TTL path is taken instead."""
    monkeypatch.setattr(session_bus, "_BOOT_ID_PATH", "/nonexistent/boot_id")
    ns = session_bus._pid_namespace()
    assert not ns, "unreadable boot_id must not yield a matchable namespace token"
    # The property that matters is that certainty is unreachable, not that the row is
    # dropped: a falsy token can still be KEPT via the D4 weak signal, but must never be
    # promoted to "confirmed" on the strength of a colliding namespace string.
    row = {"session_id": "x", "pid": os.getpid(), "ns": ns, "last_seen": _iso(33 * 3600)}
    assert session_bus._liveness(row) != "confirmed"
    # And a row whose PID is absent here gets no rescue at all once its heartbeat is stale.
    dead = {"session_id": "y", "pid": 4_000_000, "ns": ns, "last_seen": _iso(33 * 3600)}
    assert session_bus._liveness(dead) is None
