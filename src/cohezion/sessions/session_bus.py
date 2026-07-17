"""Session Control Plane — SurrealDB-backed session registry + message bus (SCP1–SCP4).

Rebuilt 2026-07-15 from the SCP1–SCP4 contracts in .claude/rules/harness.md after the
original module (built 2026-06-03 in a /tmp-based worktree) was lost uncommitted.
Consumers: ~/.claude/hooks/session-register.sh, ~/.claude/hooks/session-inbox.sh,
cohezion.compound.telegram_hub.broadcast_to_sessions, scripts/sessions/reply_relay.py.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from enum import Enum


SURREAL_URL = "http://localhost:8001/sql"
_NS, _DB = "cohezion", "main"
_AUTH = "root:root"

_BUS_ID_RE = re.compile(r"^session_bus:[A-Za-z0-9]+$")
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class MessageKind(Enum):
    """Bus message kinds. SPAWN_REQUEST is the reserved Tier-3 seam and stays INERT:
    it is never returned by fetch()/read_replies() (SCP3)."""

    MSG = "MSG"
    REPLY = "REPLY"
    SPAWN_REQUEST = "SPAWN_REQUEST"


def _assert_bus_id(record_id: str) -> str:
    """Guard raw record-id interpolation seams (SCP1)."""
    if not _BUS_ID_RE.match(record_id):
        raise ValueError(f"invalid session_bus record id: {record_id!r}")
    return record_id


def _assert_sid(session_id: str) -> str:
    if not _SID_RE.match(session_id):
        raise ValueError(f"invalid session id: {session_id!r}")
    return session_id


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        # os.kill(0,0) signals our own process group and ALWAYS succeeds —
        # corrupted/null pids must read as dead, not immortal (ultrareview bug_015).
        return False
    """Liveness is process-existence, not last_seen recency (SCP2)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (TypeError, ValueError):
        return False
    return True


def _sql(query: str, timeout: float = 5.0) -> list:
    """Run SurrealQL over HTTP; a statement error (HTTP-200 + status ERR with a string
    result) is treated as no-rows, never iterated as data (GAIA FAILURE #2 lesson)."""
    import base64

    req = urllib.request.Request(
        SURREAL_URL,
        data=query.encode(),
        headers={
            "surreal-ns": _NS,
            "surreal-db": _DB,
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(_AUTH.encode()).decode(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            batches = json.loads(r.read())
    except Exception:  # noqa: BLE001 — bus reads degrade to empty, never crash a session
        return []
    rows: list = []
    for batch in batches if isinstance(batches, list) else []:
        result = batch.get("result")
        if batch.get("status") != "OK" or not isinstance(result, list):
            continue  # ERR carries a string result — no-rows, not fixtures
        rows.extend(result)
    return rows


class SessionRegistry:
    """session_registry table: one row per live agent session."""

    def register(self, session_id: str, label: str, pid: int, mode: str = "turn") -> None:
        sid = _assert_sid(session_id)
        # ⟨⟩ record-id quoting: real sids ('s-'+hex) contain a hyphen, which SurrealQL
        # would otherwise parse as an expression, erroring the whole statement silently.
        _sql(
            f"UPSERT session_registry:⟨{sid}⟩ SET session_id = {json.dumps(sid)}, "
            f"label = {json.dumps(label)}, pid = {int(pid)}, mode = {json.dumps(mode)}, "
            f"last_seen = time::now();"
        )

    def heartbeat(self, session_id: str) -> None:
        sid = _assert_sid(session_id)
        _sql(f"UPDATE session_registry:⟨{sid}⟩ SET last_seen = time::now();")

    def list_active(self) -> list[dict]:
        rows = _sql("SELECT * FROM session_registry;")
        return [r for r in rows if _pid_alive(int(r.get("pid") or 0))]


class SessionBus:
    """session_bus table: operator/agent messages with idempotent set-insert acking."""

    def post(
        self,
        to_session: str,
        body: str,
        kind: MessageKind = MessageKind.MSG,
        from_session: str = "",
    ) -> None:
        _sql(
            f"CREATE session_bus SET to_session = {json.dumps(to_session)}, "
            f"from_session = {json.dumps(from_session)}, kind = {json.dumps(kind.value)}, "
            f"body = {json.dumps(body)}, acked_by = [], claimed_by = [], "
            f"created_at = time::now();"
        )

    def _pending(self, session_id: str, kind: MessageKind) -> list[dict]:
        sid = _assert_sid(session_id)
        # SPAWN_REQUEST is deliberately unreachable here: callers pass MSG or REPLY only,
        # and the WHERE clause pins the kind — the Tier-3 seam stays inert (SCP3).
        return _sql(
            f"SELECT * FROM session_bus WHERE kind = {json.dumps(kind.value)} "
            f"AND (to_session = {json.dumps(sid)} OR to_session = 'all') "
            f"AND {json.dumps(sid)} NOT IN acked_by ORDER BY created_at ASC LIMIT 50;"
        )

    def fetch(self, session_id: str, *, cap_msgs: int = 20, cap_bytes: int = 8000) -> list[dict]:
        """Fetch + ack pending MSG entries. Ack is an atomic idempotent set-insert via
        array::add — NEVER a SELECT-then-write read-modify-write (SCP1). Per-turn
        injection is bounded by cap_msgs/cap_bytes (SCP2)."""
        sid = _assert_sid(session_id)
        out: list[dict] = []
        budget = cap_bytes
        for row in self._pending(sid, MessageKind.MSG)[: max(0, cap_msgs)]:
            body = str(row.get("body") or "")
            if budget - len(body) < 0 and out:
                break
            budget -= len(body)
            rid = _assert_bus_id(str(row.get("id")))
            # Conditional atomic ack: only the drain that WINS the array::add emits the
            # message, so two concurrent hooks of the same session can't double-inject.
            acked = _sql(
                f"UPDATE {rid} SET acked_by = array::add(acked_by, {json.dumps(sid)}) "
                f"WHERE {json.dumps(sid)} NOT IN acked_by RETURN AFTER;"
            )
            if acked:
                out.append(row)
        return out

    def claim(self, session_id: str, record_id: str) -> bool:
        """Exactly-once claim for relays (SCP4 consumer): atomic array::add gated on an
        empty claimed_by, so two relays can never both win (SCP1 pattern)."""
        sid = _assert_sid(session_id)
        rid = _assert_bus_id(record_id)
        rows = _sql(
            f"UPDATE {rid} SET claimed_by = array::add(claimed_by, {json.dumps(sid)}) "
            f"WHERE claimed_by = NONE OR array::len(claimed_by) = 0 RETURN AFTER;"
        )
        return bool(rows) and (rows[0].get("claimed_by") or [None])[0] == sid

    def read_replies(
        self, session_id: str, *, cap_msgs: int = 20, cap_bytes: int = 8000
    ) -> list[dict]:
        """Pending REPLY entries for a session (unacked), same caps as fetch. The Tier-3
        spawn seam kind is filtered out by the pinned-kind query (SCP3 inert)."""
        sid = _assert_sid(session_id)
        out: list[dict] = []
        budget = cap_bytes
        for row in self._pending(sid, MessageKind.REPLY)[: max(0, cap_msgs)]:
            body = str(row.get("body") or "")
            if budget - len(body) < 0 and out:
                break
            budget -= len(body)
            out.append(row)
        return out

    async def broadcast(self, body: str) -> None:
        """Operator broadcast to every session (to_session='all' — the pattern
        _pending already reads). async because the declared consumer
        (telegram_hub.broadcast_to_sessions) awaits it; the AttributeError it
        used to swallow was ultrareview bug_013."""
        self.post("all", body, from_session="operator")
