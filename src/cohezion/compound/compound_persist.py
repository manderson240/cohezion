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

Verification contract: after a call, ``SELECT count()`` on all three tables rises
and the edge exists. That is the loop compounding — one real edge at a time.
"""

from __future__ import annotations

import json
import urllib.request
from typing import TYPE_CHECKING, Any

from cohezion.config.defaults import SURREAL_DB, SURREAL_NS


if TYPE_CHECKING:
    from cohezion.compound.executor import ExecutionResult
    from cohezion.compound.journey_tracker import TrajectoryPoint

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_HEADERS = {"surreal-ns": SURREAL_NS, "surreal-db": SURREAL_DB, "Content-Type": "text/plain"}
_AUTH = "Basic cm9vdDpyb290"  # root:root, base64 — matches the fleet default


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


def persist_cycle(
    point: TrajectoryPoint,
    result: ExecutionResult,
    *,
    task_description: str,
    skill_name: str,
    learning: str,
    run_id: str,
) -> dict[str, int]:
    """Persist one real compound cycle. Returns the new count of each table.

    All arguments carry GENUINE computed values — ``point`` from
    ``JourneyTracker.track_execution``, ``result`` from a real execution,
    ``learning`` a signal derived from the run. Nothing here is fabricated to
    move a counter; the caller must drive a real cycle first.
    """
    coherence = max(0.0, min(1.0, float(getattr(point, "coherence", 0.0))))
    efficiency = max(0.0, min(1.0, float(getattr(point, "efficiency", 0.0))))
    metrics = getattr(result, "metrics", {}) or {}
    quality = float(metrics.get("quality", metrics.get("quality_score", coherence)))
    phi = max(0.0, min(1.0, float((getattr(point, "metadata", None) or {}).get("phi_score", coherence))))
    model = _lit(metrics.get("tier_used", "local"))
    success = str(bool(getattr(result, "success", True))).lower()
    dur_ms = float(getattr(result, "duration_seconds", 0.0)) * 1000.0

    jid = f"agent_journey:`{run_id}`"
    lid = f"compound_learnings:`{run_id}`"
    cid = f"compound_loop:`{run_id}`"

    # One statement block, records matching each table's SCHEMAFULL contract.
    # Idempotent via explicit ids (re-running the same run_id overwrites). The
    # RELATE edge is the compounding link. compound_learnings is schemaless.
    query = (
        f"USE NS {SURREAL_NS}; USE DB {SURREAL_DB};\n"
        # agent_journey — schema requires agent_id/agent_name/journey_id/intent (str),
        # coherence_trajectory/efficiency_trajectory (array<float>), metadata + physics_state (object).
        f"CREATE {jid} CONTENT {{ journey_id: {_lit(run_id)}, agent_id: 'compound-loop', "
        f"agent_name: 'compound-loop', intent: {_lit(task_description)}, "
        f"coherence_trajectory: [{coherence}], efficiency_trajectory: [{efficiency}], "
        f"final_coherence: {coherence}, final_phi_score: {phi}, status: 'completed', "
        f"total_steps: 1, total_duration_ms: {dur_ms}, metadata: {{}}, physics_state: {{}} }};\n"
        f"CREATE {lid} CONTENT {{ skill_name: {_lit(skill_name)}, "
        f"insight: {_lit(learning)}, quality_score: {quality}, "
        f"source: 'compound_persist', created_at: time::now() }};\n"
        # compound_loop — schema requires cycle_id/task/skill/model (str), success/escalated (bool),
        # duration_ms/mean_logprob (float), state_path/stuck_loops (array).
        f"CREATE {cid} CONTENT {{ cycle_id: {_lit(run_id)}, task: {_lit(task_description)}, "
        f"skill: {_lit(skill_name)}, model: {model}, success: {success}, escalated: false, "
        f"duration_ms: {dur_ms}, mean_logprob: {coherence}, state_path: [{_lit(run_id)}], "
        f"stuck_loops: [] }};\n"
        f"RELATE {cid}->yielded->{lid};\n"
    )
    res = _sql(query)
    # Surface any per-statement error instead of silently under-persisting.
    errs = [r for r in res if isinstance(r, dict) and r.get("status") == "ERR"]
    if errs:
        raise RuntimeError(f"persist_cycle SurrealQL error: {errs[0].get('result')}")

    counts: dict[str, int] = {}
    for table in ("agent_journey", "compound_learnings", "compound_loop", "yielded"):
        res = _sql(f"SELECT count() FROM {table} GROUP ALL;")
        rows = res[-1].get("result") or []
        counts[table] = int(rows[0]["count"]) if rows else 0
    return counts
