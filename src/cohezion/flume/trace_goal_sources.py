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
from typing import Any

from cohezion.flume.loop_goal_refactor_engine import payload_looks_like_failure


SURREAL_URL = "http://localhost:8001/sql"
_NAMESPACE = "cohezion"

# event_log.source values are agent/tool identifiers. Anything outside this shape
# is refused rather than interpolated into SurrealQL.
_SAFE_SOURCE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")

# How many recent rows for a source define its measured error rate.
ERROR_RATE_WINDOW = 200

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
        rows.extend(stmt.get("result") or [])
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
