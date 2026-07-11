"""Persist a real compound-loop cycle to SurrealDB — close the self-improvement loop.

2026-07-10: measured that the compound loop never compounded. The daemon drives
``scripts/drivers/compound_cycle.py``, which is a MagicMock smoke test (mock MCP,
canned ``high_quality_task`` output) and writes nothing — so ``compound_loop`` sat
at 0 and ``compound_learnings`` at 4 stale hand-ID'd rows. The spine itself is real
(``JourneyTracker`` computes a genuine 12-D trajectory; metrics are real), but no
code path persisted its outputs. This module is that path.

``persist_cycle`` takes the REAL outputs of a driven cycle — a ``TrajectoryPoint``
from ``JourneyTracker.track_execution`` and the run's ``ExecutionResult`` — and
writes three records + a connecting edge via the proven synchronous SurrealDB HTTP
path (stdlib urllib; no async event-loop hang, unlike the EventBus). It does NOT
fabricate data: callers pass genuine computed outputs, not hand-authored ones.

    agent_journey       ← the real trajectory point (12-D dims, coherence, action)
    compound_learnings  ← a learning derived from the run's real metrics
    compound_loop       ← the cycle record, linking journey + learning
    RELATE compound_loop -> yielded -> compound_learnings   (the compounding edge)

Only ``agent_journey`` is SCHEMAFULL; ``compound_loop`` / ``compound_learnings`` are
SCHEMALESS but still TYPE-enforce their known fields.

Idempotency + honesty (adversarial review 2026-07-10): the whole block runs in ONE
transaction; records are rewritten (DELETE+CREATE, which re-applies SCHEMAFULL
nested-field defaults) and the single ``yielded`` edge is rebuilt each run, so
re-driving the same ``run_id`` leaves counts STABLE — it never inflates the
"compounding" count the module returns as real work. ``run_id`` is validated against
a safe record-id charset (a backtick would otherwise break the id and silently write
nothing), and every value that reaches a typed field is finite-guarded.

Verification contract: after a call, ``SELECT count()`` on all three tables reflects
the UPSERT and the edge exists exactly once. That is the loop compounding — one real,
re-runnable edge at a time.
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.request
from typing import TYPE_CHECKING, Any

from cohezion.config.defaults import SURREAL_DB, SURREAL_NS


if TYPE_CHECKING:
    from cohezion.compound.executor import ExecutionResult
    from cohezion.compound.journey_tracker import TrajectoryPoint

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_HEADERS = {"surreal-ns": SURREAL_NS, "surreal-db": SURREAL_DB, "Content-Type": "text/plain"}
_AUTH = "Basic cm9vdDpyb290"  # root:root, base64 — matches the fleet default

# run_id becomes part of a backtick-quoted SurrealDB record id (agent_journey:`<run_id>`).
# A backtick or quote inside it would break the id → HTTP 400 → the error bypasses the
# per-statement guard and nothing is written. Fail fast and honestly instead (review #3).
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _sql(query: str, *, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Execute a SurrealQL statement over HTTP (sync, stdlib-only)."""
    req = urllib.request.Request(
        _SURREAL_URL,
        data=query.encode(),
        headers={**_HEADERS, "Authorization": _AUTH},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _lit(value: object) -> str:
    """SQL string literal, injection-safe via json.dumps (escapes quotes + backslashes)."""
    return json.dumps(str(value))


def _num(
    value: object,
    default: float = 0.0,
    *,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    """Coerce to a FINITE float, optionally clamped. Non-finite (inf/nan) → default.

    SurrealDB typed float fields reject inf/nan and abort the whole transaction
    (review #5); guard every value that reaches a typed field.
    """
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    if lo is not None:
        f = max(lo, f)
    if hi is not None:
        f = min(hi, f)
    return f


def persist_cycle(
    point: TrajectoryPoint,
    result: ExecutionResult,
    *,
    task_description: str,
    skill_name: str,
    learning: str,
    run_id: str,
    parent_run_id: str | None = None,
    trajectory: list | None = None,
    coherence_version: int = 1,
) -> dict[str, int]:
    """Persist one real compound cycle idempotently. Returns the new count of each table.

    All arguments carry GENUINE computed values — ``point`` from
    ``JourneyTracker.track_execution``, ``result`` from a real execution,
    ``learning`` a signal derived from the run. Nothing here is fabricated to
    move a counter; the caller must drive a real cycle first.

    Idempotent: re-running the same ``run_id`` rewrites the three records (DELETE+CREATE)
    and rebuilds the single ``yielded`` edge inside one transaction, so counts are stable
    across re-runs (never inflated). Raises ValueError on an unsafe ``run_id`` and RuntimeError
    on any SurrealQL error.

    ``coherence_version`` (optional, ADDITIVE 2026-07-11): tags which coherence formula
    produced ``final_coherence`` — ``1`` (default) = the executor Step 5.8 crude formula,
    ``2`` = the opt-in coherence-v3 multiplicative formula. When it is ``1`` NO new field is
    emitted, so the ``agent_journey`` write is BYTE-IDENTICAL to before (existing callers are
    undisturbed). Only ``coherence_version != 1`` writes an explicit ``coherence_version``
    field; the DB DEFAULT (``DEFINE FIELD coherence_version ON agent_journey TYPE int
    DEFAULT 1``) fills version-1 rows. NOTE: because ``agent_journey`` is SCHEMAFULL, that
    DEFINE FIELD migration MUST be applied before any ``coherence_version=2`` write, or the
    typed table rejects the undefined field.

    ``trajectory`` (optional, ADDITIVE 2026-07-11): a list of TrajectoryPoint-like objects
    (each with ``.coherence`` / ``.efficiency``) for a genuine multi-step cycle. When provided,
    the FULL ``coherence_trajectory`` / ``efficiency_trajectory`` arrays are written (every
    element finite-guarded + clamped 0..1), ``total_steps = len(trajectory)``, and the
    ``final_coherence`` / ``final_phi_score`` come from the LAST point. When ``None`` (or an
    empty list), behavior is EXACTLY as before — a single ``point``-derived step,
    ``total_steps: 1`` — so the vacuum-relaxation + Markov-trajectory experiments (which gate on
    ``total_steps > 1``) can finally ungate without breaking any existing caller.
    """
    if not _SAFE_RUN_ID.match(run_id or ""):
        raise ValueError(
            f"run_id must match {_SAFE_RUN_ID.pattern} (safe for a SurrealDB record id); got {run_id!r}"
        )
    if parent_run_id is not None and not _SAFE_RUN_ID.match(parent_run_id):
        raise ValueError(f"parent_run_id must match {_SAFE_RUN_ID.pattern}; got {parent_run_id!r}")

    coherence = _num(getattr(point, "coherence", 0.0), lo=0.0, hi=1.0)
    efficiency = _num(getattr(point, "efficiency", 0.0), lo=0.0, hi=1.0)
    metrics = getattr(result, "metrics", {}) or {}
    quality = _num(metrics.get("quality", metrics.get("quality_score", coherence)), lo=0.0, hi=1.0)
    phi = _num((getattr(point, "metadata", None) or {}).get("phi_score", coherence), lo=0.0, hi=1.0)
    model = _lit(metrics.get("tier_used", "local"))
    # Fail-closed: a result missing `success` is treated as NOT successful (review #8).
    success = bool(getattr(result, "success", False))
    success_sql = str(success).lower()
    status = "completed" if success else "failed"  # honest status, not hardcoded (review #7)
    dur_ms = _num(getattr(result, "duration_seconds", 0.0), lo=0.0) * 1000.0
    # mean_logprob is a real-logprob field — use one only if the run produced it; do NOT
    # alias coherence into it (review #6). Absent → neutral 0.0.
    mean_logprob = _num(metrics.get("mean_logprob", 0.0))

    # Multi-step trajectory (ADDITIVE): a truthy `trajectory` overrides the single-point
    # arrays. `if trajectory:` (not `is not None`) makes an EMPTY list fall through to the
    # byte-identical single-point path — no `total_steps: 0` and no `trajectory[-1]` IndexError.
    # Every element is finite-guarded + clamped 0..1 so one inf/nan mid-list can't abort the
    # transaction (same contract as the single-point `_num` guards above). final_phi_score is
    # read from the last point's metadata["phi_score"] (falling back to its coherence), since
    # trajectory objects only promise .coherence / .efficiency.
    if trajectory:
        coh_list = [_num(getattr(p, "coherence", 0.0), lo=0.0, hi=1.0) for p in trajectory]
        eff_list = [_num(getattr(p, "efficiency", 0.0), lo=0.0, hi=1.0) for p in trajectory]
        total_steps = len(trajectory)
        last = trajectory[-1]
        final_coherence = _num(getattr(last, "coherence", 0.0), lo=0.0, hi=1.0)
        final_phi = _num(
            (getattr(last, "metadata", None) or {}).get("phi_score", final_coherence),
            lo=0.0,
            hi=1.0,
        )
    else:
        coh_list = [coherence]
        eff_list = [efficiency]
        total_steps = 1
        final_coherence = coherence
        final_phi = phi
    coh_sql = "[" + ", ".join(str(c) for c in coh_list) + "]"
    eff_sql = "[" + ", ".join(str(e) for e in eff_list) + "]"

    # ADDITIVE era tag: emit `coherence_version` ONLY when it is not the default 1, so the
    # default write stays byte-identical (see docstring). Requires the DEFINE FIELD migration
    # to be applied before any v2 write (SCHEMAFULL table rejects undefined fields).
    version_field = (
        f"coherence_version: {int(coherence_version)}, " if coherence_version != 1 else ""
    )

    jid = f"agent_journey:`{run_id}`"
    lid = f"compound_learnings:`{run_id}`"
    cid = f"compound_loop:`{run_id}`"

    # One atomic transaction (review #4): the three record writes + the rebuilt single
    # edge commit together or roll back together, so the "all counts move together"
    # contract holds even on a mid-block failure. DELETE+CREATE (not UPSERT) makes
    # re-runs idempotent (review #1) AND re-applies the SCHEMAFULL nested-field defaults
    # (e.g. physics_state.biology TYPE float) that an UPSERT-update leaves as NONE — a
    # fresh CREATE always fills them. DELETE-before-RELATE rebuilds exactly one edge per
    # run instead of accumulating duplicates that would inflate the compounding count
    # (review #2). ns/db come from the HTTP headers, so no USE statements are needed.
    query = (
        "BEGIN TRANSACTION;\n"
        f"DELETE {jid};\n"
        f"CREATE {jid} CONTENT {{ journey_id: {_lit(run_id)}, agent_id: 'compound-loop', "
        f"agent_name: 'compound-loop', intent: {_lit(task_description)}, "
        f"coherence_trajectory: {coh_sql}, efficiency_trajectory: {eff_sql}, "
        f"final_coherence: {final_coherence}, final_phi_score: {final_phi}, status: {_lit(status)}, "
        f"{version_field}"
        f"total_steps: {total_steps}, total_duration_ms: {dur_ms}, metadata: {{}}, physics_state: {{}} }};\n"
        f"DELETE {lid};\n"
        f"CREATE {lid} CONTENT {{ skill_name: {_lit(skill_name)}, "
        f"insight: {_lit(learning)}, quality_score: {quality}, "
        f"source: 'compound_persist', created_at: time::now() }};\n"
        f"DELETE {cid};\n"
        f"CREATE {cid} CONTENT {{ cycle_id: {_lit(run_id)}, task: {_lit(task_description)}, "
        f"skill: {_lit(skill_name)}, model: {model}, success: {success_sql}, escalated: false, "
        f"duration_ms: {dur_ms}, mean_logprob: {mean_logprob}, state_path: [{_lit(run_id)}], "
        f"stuck_loops: [] }};\n"
        # Record-scoped edge delete (SurrealDB docs, verified live 2026-07-10):
        # `DELETE <record>->edge` touches only this record's outgoing edges — a
        # table-wide `DELETE ... WHERE` scan conflicted with concurrent Ring-4
        # writers under optimistic concurrency and aborted whole transactions.
        f"DELETE {cid}->yielded;\n"
        f"RELATE {cid}->yielded->{lid};\n"
    )
    # Recursive-trace lineage (markov-trace research, 2026-07-10): when this cycle
    # was spawned by another cycle (proposal -> experiment -> child cycles), rebuild
    # exactly one `spawned` parent->child edge inside the same transaction. The
    # Galton-Watson branching factor over `spawned` is the honest "is it actually
    # compounding" metric. Parent record may not exist yet (out-of-order persistence);
    # SurrealDB RELATE tolerates that — the edge binds by id.
    if parent_run_id is not None:
        pid_ = f"compound_loop:`{parent_run_id}`"
        query += f"DELETE {pid_}->spawned WHERE out = {cid};\nRELATE {pid_}->spawned->{cid};\n"
    query += "COMMIT TRANSACTION;\n"

    # Concurrency (found live 2026-07-10): the DELETE ... WHERE scans conflict with
    # concurrent Ring-4 writers (the actioner batch writes quasi-continuously) and
    # SurrealKV's optimistic concurrency aborts the whole transaction with
    # "failed transaction". Without retry, the executor's fail-open wiring silently
    # DROPS the cycle. Bounded retry with backoff; genuine errors surface unchanged.
    last_errs: list[dict] = []
    for attempt in range(6):
        res = _sql(query)
        last_errs = [r for r in res if isinstance(r, dict) and r.get("status") == "ERR"]
        if not last_errs:
            break
        msg = " ".join(str(e.get("result", "")) for e in last_errs)
        if "failed transaction" in msg.lower() and attempt < 5:
            # Conflict windows observed live span multiple seconds while the
            # actioner batch persists cycles + journey/universe side-writes;
            # widen backoff: 0.5,1,1.5,2,2.5s (~7.5s total worst case).
            time.sleep(0.5 * (attempt + 1))
            continue
        raise RuntimeError(f"persist_cycle SurrealQL error: {last_errs[0].get('result')}")
    if last_errs:
        raise RuntimeError(
            f"persist_cycle: transaction conflict persisted after 6 attempts: {last_errs[0].get('result')}"
        )

    counts: dict[str, int] = {}
    for table in ("agent_journey", "compound_learnings", "compound_loop", "yielded"):
        res = _sql(f"SELECT count() FROM {table} GROUP ALL;")
        rows = res[-1].get("result") or []
        counts[table] = int(rows[0]["count"]) if rows else 0
    return counts
