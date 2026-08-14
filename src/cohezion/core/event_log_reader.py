"""Unified event_log reader — one view over the split-brained event bus.

The bus fragmented across two SurrealDB databases with drifted schemas
(live-verified 2026-08-14):

- ns ``cohezion`` / db ``main``:  434 rows, fields ``session`` + ISO-string
  ``timestamp`` (shell hooks, deepdive) — frozen since 2026-08-03.
- ns ``cohezion`` / db ``vault``: 1,949 rows, fields ``session_id`` + epoch-float
  ``timestamp`` + ``priority`` (SurrealClient-based writers, live daemons).

Until writers converge (vault decision 2026-08-13: reliability first, unify the
store before the format), nobody reading a single database sees the whole bus.
This module is the NORMALIZING READER from that decision: it queries both
databases, coerces both schemas (and known edge shapes: ``event_type`` field
variant, numeric-string timestamps, JSON-string payloads) into one
``NormalizedEvent``, and merge-sorts by time.

Consumers: the ``python -m cohezion.core.event_log_reader`` CLI (humans tailing
the bus; agents via ``--json``). Fail-open per database: one store being down
must not hide the other.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx


SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = "Basic cm9vdDpyb290"  # root:root — fleet default (matches daemon_state.py)
_EVENT_DBS: tuple[str, ...] = ("main", "vault")


@dataclass(frozen=True)
class NormalizedEvent:
    """One event in canonical shape, regardless of which writer produced it."""

    id: str
    type: str
    source: str
    session: str
    epoch: float
    iso: str
    payload: dict[str, Any]
    priority: int | None
    origin_db: str

    def render_line(self) -> str:
        payload_head = json.dumps(self.payload, default=str)
        if len(payload_head) > 80:
            payload_head = payload_head[:77] + "..."
        return (
            f"{self.iso}  [{self.origin_db}] {self.type:<16} "
            f"session={self.session or '-'} source={self.source or '-'} {payload_head}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "session": self.session,
            "epoch": self.epoch,
            "iso": self.iso,
            "payload": self.payload,
            "priority": self.priority,
            "origin_db": self.origin_db,
        }


def _coerce_epoch(raw: Any) -> float:
    """Accept epoch float/int, numeric string, or ISO-8601 string. 0.0 when absent."""
    if raw is None:
        return 0.0
    if isinstance(raw, int | float):
        return float(raw)
    text = str(raw).strip()
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _coerce_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
        return parsed if isinstance(parsed, dict) else {"raw": raw}
    return {"raw": str(raw)}


def normalize_row(row: dict[str, Any], *, origin_db: str) -> NormalizedEvent:
    """Coerce any known event_log row shape into a NormalizedEvent."""
    epoch = _coerce_epoch(row.get("timestamp"))
    iso = datetime.fromtimestamp(epoch, tz=UTC).isoformat(timespec="seconds") if epoch > 0 else ""
    priority_raw = row.get("priority")
    try:
        priority = int(priority_raw) if priority_raw is not None else None
    except (TypeError, ValueError):
        priority = None
    return NormalizedEvent(
        id=str(row.get("id", "")),
        type=str(row.get("type") or row.get("event_type") or "UNKNOWN"),
        source=str(row.get("source") or ""),
        session=str(row.get("session") or row.get("session_id") or ""),
        epoch=epoch,
        iso=iso,
        payload=_coerce_payload(row.get("payload")),
        priority=priority,
        origin_db=origin_db,
    )


_IDENT_SAFE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:")


def _safe_literal(value: str) -> str:
    """Reject values that could break out of a SurrealQL string literal (M5 pattern)."""
    if not set(value) <= _IDENT_SAFE:
        raise ValueError(f"unsafe filter value: {value!r}")
    return value


def _sql(db: str, query: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Run one SurrealQL statement against ns=cohezion/db=<db>; return result rows."""
    resp = httpx.post(
        SURREAL_URL,
        content=query,
        headers={
            "surreal-ns": "cohezion",
            "surreal-db": db,
            "Content-Type": "text/plain",
            "Authorization": _SURREAL_AUTH,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body or body[0].get("status") != "OK":
        raise RuntimeError(f"SurrealDB statement error in db={db}: {str(body)[:200]}")
    result = body[0].get("result")
    return result if isinstance(result, list) else []


def fetch_events(
    *,
    limit: int = 50,
    dbs: tuple[str, ...] = _EVENT_DBS,
    session: str | None = None,
    event_type: str | None = None,
    since_epoch: float | None = None,
    per_db_fetch: int | None = None,
) -> list[NormalizedEvent]:
    """Fetch, normalize, and merge-sort events from every database on the bus.

    ``session`` and ``event_type`` are pushed into the SurrealQL ``WHERE`` clause
    against BOTH raw field names (``session``/``session_id``, ``type``/``event_type``)
    so a match beyond the fetch window is still found — a client-side-only filter over
    a shallow window silently misses (live-caught: this session's own day-1 AGENT_START
    had already been pushed out of the newest-200 window by daemon traffic).
    ``since_epoch`` stays CLIENT-side on the normalized epoch: event_log carries MIXED
    timestamp types (ISO strings and floats in the same table), so a server-side time
    predicate — like server-side ORDER BY — silently lies. Fail-open per database: an
    unreachable store is skipped (visible in ``origin_db`` coverage, not fatal).
    """
    fetch_n = per_db_fetch or max(limit * 4, 200)
    where_parts: list[str] = []
    if session is not None:
        lit = _safe_literal(session)
        where_parts.append(f"(session = '{lit}' OR session_id = '{lit}')")
    if event_type is not None:
        lit = _safe_literal(event_type)
        where_parts.append(f"(type = '{lit}' OR event_type = '{lit}')")
    where = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    events: list[NormalizedEvent] = []
    for db in dbs:
        try:
            rows = _sql(
                db,
                f"SELECT * FROM event_log{where} ORDER BY timestamp DESC LIMIT {fetch_n};",
            )
        except Exception as exc:  # one db down must not hide the other
            print(f"[event_log_reader] db={db} unreachable: {exc}", file=sys.stderr)
            continue
        events.extend(normalize_row(r, origin_db=db) for r in rows)

    # Re-apply on the normalized shape too — server-side WHERE is an optimization,
    # normalization stays the source of truth for what matches.
    if session is not None:
        events = [e for e in events if e.session == session]
    if event_type is not None:
        events = [e for e in events if e.type == event_type]
    if since_epoch is not None:
        events = [e for e in events if e.epoch > since_epoch]

    events.sort(key=lambda e: e.epoch, reverse=True)
    return events[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cohezion.core.event_log_reader",
        description="Unified view of the event bus across db=main and db=vault.",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--session", default=None, help="filter by normalized session id")
    parser.add_argument("--type", dest="event_type", default=None, help="filter by event type")
    parser.add_argument("--json", action="store_true", help="machine-readable output (agents)")
    parser.add_argument(
        "--follow",
        action="store_true",
        help="poll for new events every --interval seconds (no LIVE queries by design)",
    )
    parser.add_argument("--interval", type=float, default=15.0)
    args = parser.parse_args(argv)

    def emit(batch: list[NormalizedEvent]) -> None:
        for ev in reversed(batch):  # oldest first, like tail -f
            print(json.dumps(ev.to_dict(), default=str) if args.json else ev.render_line())

    events = fetch_events(limit=args.limit, session=args.session, event_type=args.event_type)
    emit(events)
    if not args.follow:
        return 0

    high_water = max((e.epoch for e in events), default=0.0)
    try:
        while True:
            time.sleep(args.interval)
            fresh = fetch_events(
                limit=args.limit,
                session=args.session,
                event_type=args.event_type,
                since_epoch=high_water,
            )
            if fresh:
                high_water = max(e.epoch for e in fresh)
                emit(fresh)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
