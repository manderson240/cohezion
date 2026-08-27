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
from datetime import UTC, datetime
from enum import Enum


SURREAL_URL = "http://localhost:8001/sql"
_NS, _DB = "cohezion", "main"
_AUTH = "root:root"

_BUS_ID_RE = re.compile(r"^session_bus:[A-Za-z0-9]+$")
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Liveness across a pid-namespace boundary (SCP2). See _liveness().
_PID_NS_LINK = "/proc/self/ns/pid"
_BOOT_ID_PATH = "/proc/sys/kernel/random/boot_id"
# last_seen IS a real freshness signal: ~/.claude/hooks/session-inbox.sh runs
# `python -m cohezion.sessions heartbeat <sid>` on every UserPromptSubmit. But it fires on
# USER INPUT, not wall-clock, so a live-but-idle session (operator asleep) still ages — and
# a session that opted out via .session-bus-off, or runs outside the cohezion checkout,
# never heartbeats at all. 12h therefore tolerates an overnight idle gap while still
# excluding the 33h ghost row that motivated this. Widen before narrowing (see _liveness).
_STALE_AFTER_S = 12 * 3600


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


def _pid_namespace() -> str:
    """Identity of the pid namespace in which this process can resolve PIDs.

    Boot-qualified because namespace inodes are reused across reboots, which would
    otherwise let a post-reboot reader trust a pre-reboot writer's PIDs.
    """
    try:
        ns = os.readlink(_PID_NS_LINK)
    except OSError:
        return ""
    try:
        with open(_BOOT_ID_PATH) as fh:
            boot = fh.read().strip()
    except OSError:
        # NOT a placeholder string (D5): a literal like "unknown-boot" is COLLIDABLE — two
        # different hosts that both cannot read boot_id would produce an equal token, the
        # same-namespace guard would pass, and a foreign PID would be trusted as "confirmed".
        # An empty token is falsy, which routes to the honest last_seen path instead.
        return ""
    return f"{boot}/{ns}"


def _age_seconds(last_seen: object) -> float | None:
    """Seconds since an ISO-8601 last_seen, or None when it is absent/unparseable."""
    if not isinstance(last_seen, str) or not last_seen:
        return None
    try:
        ts = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return (datetime.now(UTC) - ts).total_seconds()


def _liveness(row: dict, *, stale_after_s: float = _STALE_AFTER_S) -> str | None:
    """Liveness of one registry row: 'confirmed', 'assumed', or None (dead).

    `os.kill(pid, 0)` answers "does this PID exist in MY pid namespace" — only the same
    question `list_active()` asks when the row was WRITTEN from that same namespace. Read
    across a boundary (an agent shell in a bwrap sandbox vs a host session) it is wrong in
    BOTH directions: a recycled sandbox PID reads alive, a live host session reads dead.

    Same namespace  -> process-existence is authoritative and outranks last_seen (SCP2).
    Otherwise       -> UNKNOWN, bounded by last_seen staleness and biased to INCLUDE:
                       dropping a live session silently loses operator broadcasts, while
                       retaining a dead one costs only an unacked row.
    """
    ns = row.get("ns")
    if ns and ns == _pid_namespace():
        return "confirmed" if _pid_alive(int(row.get("pid") or 0)) else None
    age = _age_seconds(row.get("last_seen"))
    # `age < 0` is a FUTURE last_seen (clock skew at the writer). Without this it can never
    # exceed stale_after_s, so the row stays "assumed" alive forever — verified with a
    # timestamp 10 years ahead (D3). A clock ahead of the reader must not confer immortality.
    if age is not None and 0 <= age <= stale_after_s:
        return "assumed"
    if age is None and not ns and _pid_alive(int(row.get("pid") or 0)):
        # Legacy row (no ns) with NO usable timestamp: os.kill is the only signal left, so
        # use it to KEEP the row — but never promote to "confirmed", since the pid may belong
        # to an unrelated process in this namespace (D4/kimi #8).
        #
        # Deliberately gated on `age is None`. The weak signal breaks a tie in the ABSENCE of
        # evidence; it must not override evidence. A legacy row with a definite 33h-old
        # heartbeat and a colliding pid is exactly the ghost this module was fixed to drop
        # (`pid-79 / claude:l3-evolver-world-model`), and those two cases are the same input
        # shape — indistinguishable. Resolving the tie toward "stale timestamp wins" is safe
        # because the heartbeat hook fires every UserPromptSubmit, so a genuinely live session
        # already has a FRESH last_seen and is kept by the branch above; only a session idle
        # past the TTL is dropped, and it re-registers on its very next turn.
        return "assumed"
    return None


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
    except Exception:
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
            # ns pins WHICH pid namespace this row's pid is resolvable in — without it a
            # reader in another namespace cannot know its os.kill answer is meaningless.
            f"ns = {json.dumps(_pid_namespace())}, last_seen = time::now();"
        )

    def heartbeat(self, session_id: str) -> None:
        sid = _assert_sid(session_id)
        _sql(f"UPDATE session_registry:⟨{sid}⟩ SET last_seen = time::now();")

    def list_active(self, *, stale_after_s: float = _STALE_AFTER_S) -> list[dict]:
        """Live sessions, each annotated with a `liveness` of 'confirmed' or 'assumed'.

        Callers that must not act on a guess (e.g. anything destructive) should require
        `row["liveness"] == "confirmed"`; broadcasters should accept both.
        """
        out: list[dict] = []
        for row in _sql("SELECT * FROM session_registry;"):
            state = _liveness(row, stale_after_s=stale_after_s)
            if state:
                out.append({**row, "liveness": state})
        return out


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
