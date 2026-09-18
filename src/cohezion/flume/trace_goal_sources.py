"""Trace sources and measurements for the trace -> goal -> loop pipeline.

Lives in ``src/`` (not in the ops CLI) so the static gates and tests can see it:
the only place kanban met goals before was a heredoc inside a shell script, which
is invisible to every gate.

A measurement returns ``None`` for UNKNOWN. UNKNOWN is never coerced to 0.0 or
1.0 -- a fabricated reading would be persisted as a convergence verdict
(ABSENT vs UNKNOWN, ``systematic-debugging.md`` Phase 0).
"""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from cohezion.flume.loop_goal_refactor_engine import (
    GoalSpecification,
    TraceToLoopTransformer,
    content_goal_id,
    payload_looks_like_failure,
)


SURREAL_URL = "http://localhost:8001/sql"
_NAMESPACE = "cohezion"

# event_log.source values are agent/tool identifiers. Anything outside this shape
# is refused rather than interpolated into SurrealQL.
_SAFE_SOURCE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")

# How many recent rows for a source define its measured error rate.
ERROR_RATE_WINDOW = 200

# Failure clustering: one failing event is noise, a repeated one from the same
# source is an unstable component. (The engine docstring always said ">= 3"; the
# single-event catch-all fired on the first event alone.)
FAILURE_CLUSTER_THRESHOLD = 3

# A kanban card is an objective only while it is open; a terminal card is a record
# of work, and re-goaling it would re-open settled work on every run.
OPEN_KANBAN_STATUSES = frozenset({"backlog", "pending_review", "in_progress"})

# R1a: event_log spans two databases. `vault` holds session-published findings
# (via the event bridge); `main` holds the git-post-commit JOURNEY_STEP stream and
# health/agent-complete telemetry. One scan reads both, each row tagged with the
# database it came from (SurrealDB record ids do not span databases).
EVENT_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vault", ("SECURITY_VIOLATION", "SYSTEM_HEALTH", "AGENT_COMPLETE")),
    ("main", ("JOURNEY_STEP", "SYSTEM_HEALTH", "AGENT_COMPLETE")),
)
KANBAN_DB = "main"

# How many fixed_in-bearing rows to scan when deciding whether a finding is resolved.
FIXED_SCAN_LIMIT = 500


def sql(statement: str, database: str) -> list[Any]:
    """Run SurrealQL; raise on embedded ERR (the HTTP-200-with-ERR trap)."""
    headers = {
        "Accept": "application/json",
        "surreal-ns": _NAMESPACE,
        "surreal-db": database,
        "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
        "Content-Type": "text/plain",
    }
    req = urllib.request.Request(
        SURREAL_URL, data=statement.encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 -- fixed literal localhost url
        body = json.loads(r.read())
    rows: list[Any] = []
    for stmt in body:
        if stmt.get("status") == "ERR":
            raise RuntimeError(f"SurrealDB error: {stmt.get('result')}")
        result = stmt.get("result")
        if isinstance(result, dict):  # INFO FOR ... returns one object, not a row list
            rows.append(result)
        else:
            rows.extend(result or [])
    return rows


def measure_error_rate(source: str, database: str) -> float | None:
    """Fraction of a source's most recent events that look like failures.

    Scored with the ENGINE's catch-all predicate, not a local copy: the
    measurement must drive down the same quantity that opened the goal. Returns
    None (UNKNOWN) when the source is unmeasurable: bad shape, or no rows.
    """
    if not _SAFE_SOURCE_RE.match(source):
        return None
    # ORDER BY is what makes the window "recent"; SurrealQL requires the ordering
    # field to appear in the projection.
    rows = sql(
        f"SELECT payload, timestamp FROM event_log WHERE source = '{source}' "
        f"ORDER BY timestamp DESC LIMIT {ERROR_RATE_WINDOW};",
        database,
    )
    if not rows:
        return None
    return sum(1 for r in rows if payload_looks_like_failure(r.get("payload"))) / len(rows)


def measure_finding_open(finding: str, database: str) -> float | None:
    """1.0 while a finding is open, 0.0 once some event reports it fixed.

    Rows are compared in Python, not matched in SurrealQL: finding text is
    free-form (quotes, colons) and interpolating it would be an injection seam.
    A saturated page is UNKNOWN, never "open": event_log grows without bound, so
    once fixed_in-bearing rows exceed the page a resolved finding's fix record can
    fall outside it, and reporting 1.0 would pin a CLOSED goal open forever.
    """
    if not finding:
        return None
    rows = sql(
        f"SELECT payload FROM event_log WHERE payload.fixed_in != NONE LIMIT {FIXED_SCAN_LIMIT};",
        database,
    )
    for row in rows:
        payload = row.get("payload") or {}
        if str(payload.get("finding") or "") == finding:
            return 0.0
    if len(rows) >= FIXED_SCAN_LIMIT:
        return None
    return 1.0


def finding_of(trace: dict[str, Any]) -> str:
    payload = trace.get("payload") or {}
    return str(payload.get("finding") or payload.get("title") or "")


# metric name -> callable(trace, database) -> measured value or None. A metric
# absent here has no measurement source, so its goals are synthesized but NOT
# executed -- the runner never invents a reading.
MEASUREMENTS = {
    "error_rate": lambda trace, db: measure_error_rate(str(trace.get("source") or ""), db),
    "finding_open": lambda trace, db: measure_finding_open(finding_of(trace), db),
}


# ---------------------------------------------------------------------------
# Trace intake: two databases + kanban, every row tagged with its origin
# ---------------------------------------------------------------------------


def fetch_event_traces(limit: int, database: str, types: tuple[str, ...]) -> list[dict[str, Any]]:
    """Newest event_log rows of ``types`` from ``database``, tagged with their origin."""
    type_list = ", ".join(f"'{t}'" for t in types)
    rows = sql(
        "SELECT id, type, source, session_id, payload, timestamp FROM event_log "
        f"WHERE type IN [{type_list}] ORDER BY timestamp DESC LIMIT {int(limit)};",
        database,
    )
    return [{**r, "_source_db": database, "_source_table": "event_log"} for r in rows]


def fetch_kanban_traces(limit: int, database: str = KANBAN_DB) -> list[dict[str, Any]]:
    """Open, non-reading-list kanban cards, tagged with their origin."""
    statuses = ", ".join(f"'{s}'" for s in sorted(OPEN_KANBAN_STATUSES))
    rows = sql(
        "SELECT id, title, status, priority, url, created_at FROM kanban_item "
        f"WHERE status IN [{statuses}] AND (url = NONE OR url = '') "
        f"ORDER BY created_at DESC LIMIT {int(limit)};",
        database,
    )
    return [{**r, "_source_db": database, "_source_table": "kanban_item"} for r in rows]


def scan_traces(limit: int, database: str | None = None) -> list[dict[str, Any]]:
    """One scan, all sources (R1a). ``database`` restricts to one event_log db.

    A source that fails to read raises: an unreadable source must not read as
    "no findings" (ABSENT vs UNKNOWN).
    """
    rows: list[dict[str, Any]] = []
    for db, types in EVENT_SOURCES:
        if database is None or database == db:
            rows.extend(fetch_event_traces(limit, db, types))
    if database is None:
        rows.extend(fetch_kanban_traces(limit))
    return rows


# ---------------------------------------------------------------------------
# Synthesis: kanban items, failure clusters, and provenance-carrying drafts
# ---------------------------------------------------------------------------


def synthesize_goal_from_kanban_item(row: dict[str, Any]) -> GoalSpecification | None:
    """Goal from an OPEN kanban card (test_pass_rate >= 1.0; no measurement source yet).

    Terminal cards are records of work, not objectives. A card carrying an external
    ``url`` is reading material (the research daemon's arXiv queue: 606 of 2,131
    open cards when measured 2026-09-05), not something to converge on.
    """
    status = str(row.get("status") or "").strip().lower()
    if status not in OPEN_KANBAN_STATUSES:
        return None
    if str(row.get("url") or "").strip():
        return None
    title = str(row.get("title") or "").strip()
    if not title:
        return None
    return GoalSpecification(
        goal_id=content_goal_id(title, "test_pass_rate"),
        title=title[:200],
        target_metric="test_pass_rate",
        target_threshold=1.0,
        max_iterations=5,
        timeout_seconds=300.0,
    )


def failure_cluster(events: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]] | None:
    """Largest same-source cluster of failure events, or None below the threshold.

    Uses the shared ``payload_looks_like_failure``: the cluster must count the
    same quantity the loop later measures. Three failures from one subsystem clear
    the bar; three one-offs across three subsystems stay below it.
    """
    by_source: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        if payload_looks_like_failure(ev.get("payload")):
            by_source.setdefault(str(ev.get("source") or "unknown-source"), []).append(ev)
    if not by_source:
        return None
    src, evs = max(by_source.items(), key=lambda kv: (len(kv[1]), kv[0]))
    return (src, evs) if len(evs) >= FAILURE_CLUSTER_THRESHOLD else None


@dataclass
class GoalDraft:
    """A synthesized goal plus the trace rows that raised it (provenance).

    ``derived_from`` is what P3 writes as ``derived_from`` edges: it carries
    ``source_db`` because SurrealDB record ids do not span databases.
    """

    goal: GoalSpecification
    trace: dict[str, Any]  # the primary trace row (the measurement needs its source)
    derived_from: list[dict[str, str]] = field(default_factory=list)

    def merge(self, other: GoalDraft) -> None:
        for ref in other.derived_from:
            if ref not in self.derived_from:
                self.derived_from.append(ref)


def _ref(row: dict[str, Any]) -> dict[str, str]:
    return {
        "source_db": str(row.get("_source_db") or "main"),
        "source_table": str(row.get("_source_table") or "event_log"),
        "source_id": str(row.get("id") or ""),
    }


_MAX_REFS_PER_CLUSTER = 10


def synthesize_scan(rows: list[dict[str, Any]]) -> list[GoalDraft]:
    """All goals a tagged scan yields, deduplicated by content-derived goal_id.

    Per-event findings (security / health / fixes-verified) come from the engine
    with its single-event catch-all DISABLED; failure clustering, per source
    database, replaces it. Kanban rows use the kanban classifier.
    """
    drafts: dict[str, GoalDraft] = {}

    def add(goal: GoalSpecification, trace: dict[str, Any], refs: list[dict[str, str]]) -> None:
        draft = GoalDraft(goal=goal, trace=trace, derived_from=list(refs))
        if goal.goal_id in drafts:
            drafts[goal.goal_id].merge(draft)
        else:
            drafts[goal.goal_id] = draft

    by_db: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("_source_table") == "kanban_item":
            goal = synthesize_goal_from_kanban_item(row)
            if goal is not None:
                add(goal, row, [_ref(row)])
            continue
        by_db.setdefault(str(row.get("_source_db") or "main"), []).append(row)
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace([row], catch_all=False)
        if goal is not None:
            add(goal, row, [_ref(row)])

    for events in by_db.values():
        cluster = failure_cluster(events)
        if cluster is None:
            continue
        src, evs = cluster
        title = f"Stabilize: {src[:120]}"
        goal = GoalSpecification(
            goal_id=content_goal_id(title, "error_rate"),
            title=title,
            target_metric="error_rate",
            target_threshold=0.05,
            max_iterations=10,
            timeout_seconds=300.0,
            direction="at_most",
        )
        add(goal, evs[0], [_ref(e) for e in evs[:_MAX_REFS_PER_CLUSTER]])
    return list(drafts.values())
