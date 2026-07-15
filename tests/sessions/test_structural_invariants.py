"""SCP structural invariants (harness SCP1–SCP4) — signature/keyword drift guards.

No SurrealDB, no network: these fire BEFORE behavioral tests when a refactor drifts
the atomic-ack pattern, the liveness mechanism, the bounded-injection caps, the
Tier-3 inert seam, or the relay's exactly-once discipline.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from cohezion.sessions import session_bus
from cohezion.sessions.session_bus import MessageKind, SessionBus

REPO = Path(__file__).resolve().parents[2]


def test_scp1_fetch_is_atomic_and_id_guarded():
    src = inspect.getsource(SessionBus.fetch)
    assert "array::add" in src, "SCP1: fetch ack must be atomic array::add, not read-modify-write"
    assert "_assert_bus_id" in src, "SCP1: fetch record-id interpolation must be guarded"


def test_scp1_claim_is_atomic_and_id_guarded():
    src = inspect.getsource(SessionBus.claim)
    assert "array::add" in src, "SCP1: claim must be atomic array::add"
    assert "_assert_bus_id" in src, "SCP1: claim record-id interpolation must be guarded"


def test_scp2_liveness_is_process_existence():
    assert "os.kill" in inspect.getsource(session_bus._pid_alive), (
        "SCP2: liveness must be os.kill(pid, 0), not last_seen recency"
    )


def test_scp2_fetch_bounds_injection():
    params = set(inspect.signature(SessionBus.fetch).parameters)
    assert {"cap_msgs", "cap_bytes"} <= params, "SCP2: fetch must bound per-turn injection"


def test_scp3_message_kinds_reserve_inert_spawn_seam():
    assert {"MSG", "REPLY", "SPAWN_REQUEST"} <= {k.name for k in MessageKind}
    # Inertness: the pending query pins kind to the caller-passed MSG/REPLY value, and no
    # public read path passes SPAWN_REQUEST.
    for reader in (SessionBus.fetch, SessionBus.read_replies):
        assert "SPAWN_REQUEST" not in inspect.getsource(reader)


def test_scp4_relay_is_single_instance_exactly_once():
    relay_src = (REPO / "scripts" / "sessions" / "reply_relay.py").read_text()
    assert "flock" in relay_src, "SCP4: relay must be single-instance (flock)"
    assert "claim(" in relay_src, "SCP4: relay must claim BEFORE send (exactly-once)"


def test_scp4_inbox_hook_untrusted_and_opt_out():
    hook = Path.home() / ".claude" / "hooks" / "session-inbox.sh"
    if not hook.exists():
        import pytest

        pytest.skip("global inbox hook not installed on this machine")
    src = hook.read_text()
    assert "UNTRUSTED" in src, "SCP4: operator messages must be framed untrusted"
    assert ".session-bus-off" in src, "SCP4: per-session opt-out must be honored"
