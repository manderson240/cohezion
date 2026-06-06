#!/usr/bin/env python3
"""Cross-session bulletin — a SurrealDB-backed blackboard for concurrent agents.

Problem: multiple Claude/Cohezion sessions run at once (we found live worktrees
under ~/.claude/projects/* and ~/.cohezion-engine/sessions/*), but they cannot
see each other. This gives them a shared, persistent channel.

Substrate: the same SurrealDB the rest of Cohezion uses
  http://localhost:8001/sql  ns=cohezion db=main  (root:root)
Bi-temporal: every row carries posted_at; presence rows carry an ttl-style
last_seen so stale sessions can be filtered. Nothing is deleted — full history
is queryable (Cohezion's "ALL artifacts persisted" principle).

Two record tables:
  session_presence  — heartbeat: who is alive, where, doing what
  session_message   — bulletin posts: topic + body, optionally @addressed

This is intentionally dependency-light (urllib only) so any session — even a
headless cron — can import and use it.

CLI:
  python session_bulletin.py announce --session A --cwd /x --task "wiring"
  python session_bulletin.py post --session A --topic coherence --body "mapped ouroboros"
  python session_bulletin.py inbox --session A          # messages to me or broadcast
  python session_bulletin.py roster                      # who's alive (last 10 min)
  python session_bulletin.py feed --limit 20             # recent global feed
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import time
import urllib.request
from typing import Any

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "main"
SURREAL_USER = "root"
SURREAL_PASS = "root"  # noqa: S105 — local dev SurrealDB, documented in CLAUDE.md

PRESENCE_FRESH_SECONDS = 600  # a session is "alive" if seen in the last 10 min


def _surql(query: str) -> list[dict[str, Any]] | None:
    """Execute SurrealQL over HTTP. Returns the parsed result list or None on failure."""
    cred = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
    req = urllib.request.Request(
        SURREAL_URL,
        data=query.encode(),
        headers={
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Authorization": f"Basic {cred}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — localhost only
            return json.loads(resp.read())
    except Exception as e:  # surface, never silently swallow
        print(f"[bulletin] SurrealDB error: {type(e).__name__}: {e}")
        return None


def _q(s: str) -> str:
    """SurrealQL single-quoted string literal with escaping."""
    return "'" + str(s).replace("'", "''") + "'"


def _now() -> float:
    # time.time() is allowed in scripts (only Date.now in workflow JS is banned)
    return time.time()


def announce(session: str, cwd: str, task: str) -> bool:
    """Upsert this session's presence heartbeat. Idempotent on session id."""
    host = socket.gethostname()
    sid = _q(session)
    # SurrealDB UPSERT keyed by session id keeps one live row per session.
    query = (
        f"UPSERT session_presence:{_sid_key(session)} SET "
        f"session = {sid}, host = {_q(host)}, cwd = {_q(cwd)}, "
        f"task = {_q(task)}, last_seen = {_now()}, pid = {os.getpid()};"
    )
    res = _surql(query)
    return res is not None


def post(session: str, topic: str, body: str, to: str | None = None) -> bool:
    """Post a bulletin message. `to` addresses a specific session; None = broadcast."""
    query = (
        f"CREATE session_message SET "
        f"from_session = {_q(session)}, "
        f"to_session = {(_q(to) if to else 'NONE')}, "
        f"topic = {_q(topic)}, body = {_q(body)}, posted_at = {_now()};"
    )
    res = _surql(query)
    return res is not None


def roster() -> list[dict[str, Any]]:
    """Return sessions seen within PRESENCE_FRESH_SECONDS, newest heartbeat first."""
    cutoff = _now() - PRESENCE_FRESH_SECONDS
    query = (
        f"SELECT session, host, cwd, task, last_seen, pid FROM session_presence "
        f"WHERE last_seen > {cutoff} ORDER BY last_seen DESC;"
    )
    return _rows(_surql(query))


def inbox(session: str, since: float = 0.0) -> list[dict[str, Any]]:
    """Messages addressed to this session OR broadcast, newest first."""
    sid = _q(session)
    query = (
        f"SELECT from_session, to_session, topic, body, posted_at FROM session_message "
        f"WHERE posted_at > {since} AND (to_session = {sid} OR to_session = NONE) "
        f"AND from_session != {sid} ORDER BY posted_at DESC LIMIT 50;"
    )
    return _rows(_surql(query))


def feed(limit: int = 20) -> list[dict[str, Any]]:
    """Recent global message feed."""
    query = (
        f"SELECT from_session, to_session, topic, body, posted_at FROM session_message "
        f"ORDER BY posted_at DESC LIMIT {int(limit)};"
    )
    return _rows(_surql(query))


def _sid_key(session: str) -> str:
    """Make a SurrealDB-safe record id key from a session name."""
    safe = "".join(c if c.isalnum() else "_" for c in session)
    return f"`{safe}`"


def _rows(res: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not res:
        return []
    # SurrealDB returns [{"result": [...], "status": "OK", ...}]
    first = res[0] if isinstance(res, list) else res
    out = first.get("result", []) if isinstance(first, dict) else []
    return out if isinstance(out, list) else []


def _fmt_age(ts: float) -> str:
    dt = _now() - ts
    if dt < 60:
        return f"{int(dt)}s ago"
    if dt < 3600:
        return f"{int(dt / 60)}m ago"
    return f"{int(dt / 3600)}h ago"


def main() -> None:
    ap = argparse.ArgumentParser(description="Cross-session bulletin over SurrealDB")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("announce")
    pa.add_argument("--session", required=True)
    pa.add_argument("--cwd", default=os.getcwd())
    pa.add_argument("--task", default="")

    pp = sub.add_parser("post")
    pp.add_argument("--session", required=True)
    pp.add_argument("--topic", required=True)
    pp.add_argument("--body", required=True)
    pp.add_argument("--to", default=None)

    pi = sub.add_parser("inbox")
    pi.add_argument("--session", required=True)
    pi.add_argument("--since", type=float, default=0.0)

    sub.add_parser("roster")

    pf = sub.add_parser("feed")
    pf.add_argument("--limit", type=int, default=20)

    args = ap.parse_args()

    if args.cmd == "announce":
        ok = announce(args.session, args.cwd, args.task)
        print(f"announced {args.session}: {'OK' if ok else 'FAILED'}")
    elif args.cmd == "post":
        ok = post(args.session, args.topic, args.body, args.to)
        tgt = f"@{args.to}" if args.to else "(broadcast)"
        print(f"posted [{args.topic}] {tgt}: {'OK' if ok else 'FAILED'}")
    elif args.cmd == "inbox":
        msgs = inbox(args.session, args.since)
        print(f"=== inbox for {args.session} ({len(msgs)} msgs) ===")
        for m in msgs:
            tgt = f"@{m['to_session']}" if m.get("to_session") else "(broadcast)"
            print(
                f"  [{_fmt_age(m['posted_at'])}] {m['from_session']} {tgt} "
                f"<{m['topic']}>: {m['body']}"
            )
    elif args.cmd == "roster":
        r = roster()
        print(f"=== live sessions ({len(r)}) ===")
        for s in r:
            print(
                f"  {s['session']:24} {_fmt_age(s['last_seen']):>10}  "
                f"pid={s.get('pid', '?')}  {s.get('task', '')[:50]}"
            )
    elif args.cmd == "feed":
        f = feed(args.limit)
        print(f"=== global feed (last {len(f)}) ===")
        for m in f:
            tgt = f"@{m['to_session']}" if m.get("to_session") else "*"
            print(
                f"  [{_fmt_age(m['posted_at'])}] {m['from_session']}->{tgt} "
                f"<{m['topic']}>: {m['body'][:70]}"
            )


if __name__ == "__main__":
    main()
