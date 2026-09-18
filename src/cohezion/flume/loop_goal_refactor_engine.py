"""Goal-Oriented Autonomous Loop & Trace Refactoring Engine.

Refactors raw linear traces into goal-directed, closed-loop state machines:
1. `GoalSpecification`: Target invariants, acceptance criteria, convergence metrics (coherence >= 0.50).
2. `AutonomousExecutionLoop`: Iterate -> Sample -> Evaluate -> AutoHarness Verify -> Adapt.
3. `TraceToLoopTransformer`: Refactors linear event traces into recurrent execution loops with backtracking.
4. `DurableSurrealGoalPersistence`: Persists goals and convergence proofs to SurrealDB `goal` & `loop_trace`.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Generic, TypeVar


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def payload_looks_like_failure(payload: dict[str, Any] | None) -> bool:
    """The catch-all predicate: does this payload read as a failure?

    Exported so a MEASUREMENT can score the same quantity that opened the goal.
    A private copy in an ops CLI would drift from this one silently, and the
    loop would then drive down a different number than the one it was opened
    for -- with nothing failing to say so.
    """
    text = json.dumps(payload or {}, default=str).lower()
    return "fail" in text or "error" in text


def content_goal_id(title: str, metric: str) -> str:
    """Content-derived goal id: stable across re-runs, distinct across findings."""
    digest = hashlib.sha256(f"{title}|{metric}".encode()).hexdigest()[:10]
    return f"goal_{metric}_{digest}"


@dataclass(frozen=True, slots=True)
class GoalSpecification:
    """Formal Goal contract with convergence criteria and invariant bounds."""

    goal_id: str
    title: str
    target_metric: str  # e.g., 'coherence', 'snr_db', 'test_pass_rate'
    target_threshold: float  # e.g., 0.50, 20.0, 1.00
    max_iterations: int = 10
    timeout_seconds: float = 30.0
    # Polarity of the acceptance test: "at_least" = higher-is-better
    # (test_pass_rate >= 1.0), "at_most" = lower-is-better (error_rate <= 0.05).
    # Defaults to "at_least" so existing goals keep their meaning.
    direction: str = "at_least"

    def is_satisfied_by(self, value: float) -> bool:
        """Single definition of "goal met", used by the executor and by readers.

        Without it a lower-is-better goal named anything but ``error_rate`` is
        scored with ``>=``: a finding_open of 1.0 against a 0.0 ceiling reads as
        CONVERGED and that verdict is written to durable storage. The polarity
        travels with the goal (and into both persisted payloads) so a stored
        ``converged`` flag stays interpretable after the fact.
        """
        if self.direction == "at_most":
            return value <= self.target_threshold
        return value >= self.target_threshold


@dataclass(frozen=True, slots=True)
class LoopSpec:
    """Canonical loop spec -- the fields of the loop-spec template
    (``references/loop-spec-canonical-template.md``) plus maturation data.

    ``rung`` is the maturation ladder: 0 = never run, 1 = one manual run reliable,
    2 = a skill/module, 3 = wrapped in a bounded loop, 4 = unattended on a schedule.
    ``depth`` is a measured loopception depth (None = never measured).
    """

    name: str
    goal: str
    each_iteration: str | None = None
    verify: str | None = None
    stop_when: str | None = None
    bound: int | None = None
    on_stop: str | None = None
    rung: int = 0
    cadence: str | None = None
    domain: str | None = None
    session: str | None = None
    impl: str | None = None
    lane: str | None = None
    note: str | None = None
    depth: int | None = None


# One typed edge table for the whole goal/loop graph (the memory graph's `relates_to`
# shape: nodes + ONE edge table + `domain` as data, not as a table-name prefix).
GRAPH_EDGE_KINDS = ("pursues", "derived_from", "supersedes", "mirrors")
GRAPH_SCHEMA_DDL = (
    "DEFINE TABLE IF NOT EXISTS goal_graph TYPE RELATION SCHEMALESS; "
    "DEFINE FIELD IF NOT EXISTS kind ON goal_graph TYPE string "
    f"ASSERT $value IN {json.dumps(list(GRAPH_EDGE_KINDS))}; "
    "DEFINE FIELD IF NOT EXISTS domain ON goal_graph TYPE option<string>; "
    "DEFINE FIELD IF NOT EXISTS session ON goal_graph TYPE option<string>; "
    "DEFINE INDEX IF NOT EXISTS goal_graph_in ON goal_graph FIELDS in; "
    "DEFINE INDEX IF NOT EXISTS goal_graph_out ON goal_graph FIELDS out; "
    + "".join(
        f"DEFINE FIELD IF NOT EXISTS {f} ON {t} TYPE option<{ty}>; "
        for t in ("goal", "loop")
        for f, ty in (("domain", "string"), ("session", "string"), ("source_table", "string"))
    )
    + "DEFINE FIELD IF NOT EXISTS source_id ON goal TYPE option<string>; "
    "DEFINE FIELD IF NOT EXISTS source_id ON loop TYPE option<string>; "
    "DEFINE FIELD IF NOT EXISTS rung ON loop TYPE option<int>; "
    "DEFINE FIELD IF NOT EXISTS depth ON loop TYPE option<int>;"
)


def record_ref(table: str, key: str) -> str:
    """Backtick-quoted SurrealQL record id; refuses keys that could break out."""
    if not key or any(c in key for c in "`\n\r\\"):
        raise ValueError(f"unsafe record key for {table}: {key!r}")
    return f"{table}:`{key}`"


@dataclass(frozen=True, slots=True)
class PlanSegment:
    """A verified memory segment grounded in plans (arXiv:2609.11561).

    Represents an atomic sub-goal segment (l_k, G_k) with its progress scalar,
    verification proof certificate, and episodic commitment status.
    """

    segment_id: str
    goal_id: str
    subgoal_plan: str
    contract_guidance: dict[str, Any] = field(default_factory=dict)
    progress: float = 1.0
    verification_proof: str | None = None
    committed: bool = True
    created_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )


class MemoryAsPlans:
    """Episodic memory retaining completed segment contracts (arXiv:2609.11561).

    Instead of accumulating frame-by-frame or step-by-step raw history O_{1:t}
    which leads to linear/quadratic token bloat, attention degradation, and OOMs,
    MemoryAsPlans preserves only verified plan-contract segments {(l_i, G_i)}.

    Guarantees O(1) context length for the active loop executor, delivering
    constant inference latency and zero context drift across arbitrarily
    long horizons.
    """

    def __init__(self, segments: list[PlanSegment] | None = None) -> None:
        self._segments: list[PlanSegment] = list(segments) if segments else []

    @property
    def segments(self) -> tuple[PlanSegment, ...]:
        return tuple(self._segments)

    def commit(self, segment: PlanSegment) -> None:
        """Commit a completed, verified segment into episodic memory."""
        self._segments.append(segment)

    def get_active_context(self, current_goal: GoalSpecification) -> dict[str, Any]:
        """Produce constant-size bounded context for the active executor.

        Decouples execution latency from total episode length.
        """
        summary = (
            hashlib.sha256("".join(s.segment_id for s in self._segments).encode()).hexdigest()[:12]
            if self._segments
            else "root"
        )
        return {
            "current_goal_id": current_goal.goal_id,
            "target_metric": current_goal.target_metric,
            "target_threshold": current_goal.target_threshold,
            "completed_segments_count": len(self._segments),
            "last_verified_segment": self._segments[-1].segment_id if self._segments else None,
            "summary_digest": summary,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_count": len(self._segments),
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "goal_id": s.goal_id,
                    "subgoal_plan": s.subgoal_plan,
                    "progress": s.progress,
                    "verification_proof": s.verification_proof,
                    "committed": s.committed,
                    "created_at": s.created_at,
                }
                for s in self._segments
            ],
        }


@dataclass
class LoopIterationResult(Generic[S]):
    iteration: int
    state: S
    metric_value: float
    is_goal_met: bool
    duration_ms: float
    action_taken: str
    progress: float = 0.0
    alignment_verified: bool = False


@dataclass
class AutonomousGoalLoopResult(Generic[S]):
    goal: GoalSpecification
    converged: bool
    iterations_run: int
    final_metric: float
    total_time_ms: float
    history: list[LoopIterationResult[S]] = field(default_factory=list)
    memory_as_plans: MemoryAsPlans | None = None


class TraceToLoopTransformer:
    """Transforms raw sequence traces into iterative goal loops."""

    @staticmethod
    def synthesize_goal_from_trace(
        trace_events: list[dict[str, Any]], goal_title: str
    ) -> GoalSpecification:
        goal_id = f"goal_{int(time.time())}_{len(trace_events)}"
        return GoalSpecification(
            goal_id=goal_id,
            title=goal_title,
            target_metric="coherence",
            target_threshold=0.50,
            max_iterations=len(trace_events) * 2,
        )

    @staticmethod
    def synthesize_goal_from_real_trace(
        trace_events: list[dict[str, Any]],
        catch_all: bool = True,
    ) -> GoalSpecification | None:
        """Synthesize an actionable goal from real event_log/kanban trace rows.

        Extraction rules (deterministic, zero-inference):
        - SECURITY_VIOLATION / SYSTEM_HEALTH payloads with severity=high ->
          goal "Resolve <finding>" with finding_open <= 0.0 (1.0 open, 0.0 resolved --
          test_pass_rate named a quantity nothing measures)
        - AGENT_COMPLETE results with 'fixed' lists -> goal "Verify <fixes>" with
          test_pass_rate >= 1.0
        - repeated JOURNEY_STEP failures (same source, >= 3 occurrences of
          'fail'/'error' in payload) -> goal "Stabilize <source>" with
          error_rate <= 0.05
        - a payload carrying ``fixed_in`` is CLOSED and yields no goal.
        ``catch_all=False`` disables the single-event "Stabilize" rule: a group
        caller (``trace_goal_sources.synthesize_scan``) replaces it with
        same-source failure CLUSTERING, because one failing event is noise.
        Returns None when the trace carries no actionable signal.

        goal_id is content-derived (title+metric hash): stable across re-runs
        (idempotent REFETCH) and collision-free across distinct findings —
        a time-based id made distinct traces in the same second collide
        (2026-08-30: three goals got one id, 2/3 writes failed).
        """
        if not trace_events:
            return None

        _goal_id = content_goal_id

        for ev in trace_events:
            etype = str(ev.get("type") or (ev.get("payload") or {}).get("type") or "")
            payload = ev.get("payload") or {}

            # A finding that records the commit that fixed it is CLOSED. Re-opening it
            # manufactures permanent work (the loop can never converge on something
            # resolved). Must be a `continue`, not an extra clause on the
            # SECURITY_VIOLATION test: falling through would let the catch-all below
            # re-catch the same event and emit a mislabelled "Stabilize:" goal.
            if payload.get("fixed_in"):
                continue

            if etype == "SECURITY_VIOLATION" or "SECURITY_VIOLATION" in etype:
                finding = payload.get("finding") or payload.get("title") or "security finding"
                title = f"Resolve: {str(finding)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "finding_open"),
                    title=title,
                    target_metric="finding_open",
                    target_threshold=0.0,
                    max_iterations=5,
                    timeout_seconds=300.0,
                    direction="at_most",
                )
            if etype == "SYSTEM_HEALTH" and (
                payload.get("severity") == "high" or payload.get("finding")
            ):
                finding = payload.get("finding") or payload.get("title") or "health finding"
                title = f"Resolve: {str(finding)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "finding_open"),
                    title=title,
                    target_metric="finding_open",
                    target_threshold=0.0,
                    max_iterations=5,
                    timeout_seconds=300.0,
                    direction="at_most",
                )
            if (
                etype == "AGENT_COMPLETE"
                and isinstance(payload.get("result"), dict)
                and payload["result"].get("fixed")
            ):
                n_fixed = len(payload["result"]["fixed"])
                title = f"Verify {n_fixed} fixes stay green"
                return GoalSpecification(
                    goal_id=_goal_id(title, "test_pass_rate"),
                    title=title,
                    target_metric="test_pass_rate",
                    target_threshold=1.0,
                    max_iterations=3,
                    timeout_seconds=300.0,
                )
            if catch_all and payload_looks_like_failure(payload):
                src = ev.get("source") or "unknown-source"
                title = f"Stabilize: {str(src)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "error_rate"),
                    title=title,
                    target_metric="error_rate",
                    target_threshold=0.05,
                    max_iterations=10,
                    timeout_seconds=300.0,
                    direction="at_most",
                )
        return None


class DurableSurrealGoalPersistence:
    """Persists goals + loop results to SurrealDB with ERR-inside-HTTP-200 checking.

    SurrealDB returns HTTP 200 with status ERR inside the JSON body for
    statement failures (unbound params, missing tables). Every write here is
    checked; failures raise instead of silently vanishing.
    """

    def __init__(
        self,
        url: str = "http://localhost:8001/sql",
        namespace: str = "cohezion",
        database: str = "main",
        auth: str = "root:root",
        timeout: float = 5.0,
    ) -> None:
        self._url = url
        self._database = database
        self._headers = {
            "Accept": "application/json",
            "surreal-ns": namespace,
            "surreal-db": database,
            "Authorization": "Basic " + base64.b64encode(auth.encode()).decode(),
            "Content-Type": "text/plain",
        }
        self._timeout = timeout
        self._graph_ready = False

    def _sql(self, statement: str) -> list[Any]:
        """Execute one statement; raise on embedded ERR status (never swallow)."""
        req = urllib.request.Request(  # noqa: S310 — fixed literal localhost url
            self._url, data=statement.encode(), headers=self._headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as r:  # noqa: S310 — fixed literal localhost url
            body = json.loads(r.read())
        rows: list[Any] = []
        for stmt_result in body:
            if stmt_result.get("status") == "ERR":
                raise RuntimeError(f"SurrealDB statement error: {stmt_result.get('result')}")
            rows.extend(stmt_result.get("result") or [])
        return rows

    def persist_goal(
        self,
        goal: GoalSpecification,
        origin_trace_ids: list[str] | None = None,
        *,
        domain: str | None = None,
        session: str | None = None,
        derived_from: list[dict[str, str]] | None = None,
    ) -> str:
        record_id = goal.goal_id
        payload = {
            "title": goal.title,
            "target_metric": goal.target_metric,
            "target_threshold": goal.target_threshold,
            "direction": goal.direction,
            "max_iterations": goal.max_iterations,
        }
        # `status`/`created_at`/`origin_trace_ids` are deliberately NOT in the MERGE
        # unless there is something to write: MERGE preserves fields it OMITS, not
        # fields it names. Naming status='active' here re-opened every converged
        # goal on every re-run (fetch_open_goals grew monotonically).
        if origin_trace_ids:
            payload["origin_trace_ids"] = origin_trace_ids
        if domain:
            payload["domain"] = domain
        if session:
            payload["session"] = session
        # Parameter-free literal via json.dumps — the unbound-$param trap is
        # structurally impossible here (2026-08-30: kanban writes silently
        # ERR'd because of an unbound $TS piped to /dev/null).
        # Idempotent: re-running the pipeline re-synthesizes the same content-derived
        # goal_id. The MERGE omits status; the second statement seeds 'active' ONLY
        # when the record has no status yet, so a converged goal stays converged.
        self._sql(
            f"UPSERT goal:`{record_id}` MERGE {json.dumps(payload)};"
            f" UPDATE goal:`{record_id}` SET created_at = created_at ?? "
            f"'{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}'; "
            f"UPDATE goal:`{record_id}` SET status = 'active' WHERE status = NONE;"
        )
        for ref in derived_from or []:
            self.relate(
                "derived_from",
                record_ref("goal", record_id),
                self._trace_rid(ref),
                domain=domain,
                session=session,
                source_db=ref["source_db"],
                source_table=ref["source_table"],
                source_id=ref["source_id"],
            )
        return f"goal:`{record_id}`"

    # -- the graph layer: the ONLY write path for goal / loop / goal_graph ------

    def ensure_graph_schema(self) -> None:
        """Idempotent DDL for goal_graph and the extended goal/loop node fields."""
        self._sql(GRAPH_SCHEMA_DDL)
        self._graph_ready = True

    def upsert_node(self, table: str, key: str, fields: dict[str, Any]) -> str:
        """UPSERT MERGE a node by deterministic id (idempotent; None values dropped)."""
        rid = record_ref(table, key)
        clean = {k: v for k, v in fields.items() if v is not None}
        self._sql(f"UPSERT {rid} MERGE {json.dumps(clean, default=str)};")
        return rid

    def relate(self, kind: str, in_rid: str, out_rid: str, **fields: Any) -> str:
        """Idempotent typed edge in ``goal_graph`` (deterministic id per kind|in|out)."""
        if kind not in GRAPH_EDGE_KINDS:
            raise ValueError(f"unknown goal_graph kind {kind!r}")
        if not self._graph_ready:  # INSERT into an undefined table would mint a non-RELATION one
            self.ensure_graph_schema()
        edge_id = hashlib.sha256(f"{kind}|{in_rid}|{out_rid}".encode()).hexdigest()[:20]
        body = {k: v for k, v in fields.items() if v is not None}
        body["kind"] = kind
        assigns = ", ".join(f"{k} = {json.dumps(v, default=str)}" for k, v in body.items())
        self._sql(
            f"INSERT RELATION INTO goal_graph {{id: goal_graph:`{edge_id}`, in: {in_rid}, "
            f"out: {out_rid}, {', '.join(f'{k}: {json.dumps(v, default=str)}' for k, v in body.items())}}}"
            f" ON DUPLICATE KEY UPDATE {assigns};"
        )
        return f"goal_graph:`{edge_id}`"

    def _trace_rid(self, ref: dict[str, str]) -> str:
        """A derived_from target. SurrealDB ids do not span databases: a trace row in
        THIS database is a real record id; one from another database is a `trace_ref`
        placeholder whose identity lives in the edge's source_db/source_id fields."""
        table, _, key = ref["source_id"].partition(":")
        key = key.strip("\u27e8\u27e9`")
        if ref["source_db"] == self._database and key:
            return record_ref(table, key)
        return record_ref("trace_ref", f"{ref['source_db']}|{ref['source_id']}")

    def persist_loop(
        self, spec: LoopSpec, goal_id: str | None = None, key: str | None = None
    ) -> str:
        """Write a ``loop`` node (+ a ``pursues`` edge to its goal when known)."""
        if not self._graph_ready:
            self.ensure_graph_schema()
        rid = self.upsert_node("loop", key or spec.name, {**asdict(spec), "updated_at": _utc_now()})
        self._sql(f"UPDATE {rid} SET created_at = created_at ?? '{_utc_now()}';")
        if goal_id:
            self.relate(
                "pursues",
                rid,
                record_ref("goal", goal_id),
                domain=spec.domain,
                session=spec.session,
            )
        return rid

    def persist_loop_result(self, result: AutonomousGoalLoopResult[Any]) -> str:
        record_id = f"{result.goal.goal_id}_result_{int(time.time())}"
        payload: dict[str, Any] = {
            "goal_id": result.goal.goal_id,
            "title": result.goal.title,
            "converged": result.converged,
            "iterations_run": result.iterations_run,
            "final_metric": result.final_metric,
            "target_metric": result.goal.target_metric,
            "target_threshold": result.goal.target_threshold,
            # Without polarity a stored `converged` flag cannot be re-derived.
            "direction": result.goal.direction,
            "total_time_ms": result.total_time_ms,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if result.memory_as_plans is not None:
            payload["memory_as_plans"] = result.memory_as_plans.to_dict()
        self._sql(f"CREATE loop_trace:`{record_id}` CONTENT {json.dumps(payload)};")
        return f"loop_trace:`{record_id}`"

    def mark_goal_converged(self, goal: GoalSpecification, final_metric: float) -> str:
        """Flip a goal out of the open set once its loop has converged.

        This terminates the cross-run loop. ``persist_goal`` no longer names
        ``status`` in its MERGE, so a later re-synthesis of the same content-derived
        goal_id cannot reset this back to 'active'.
        """
        record_id = goal.goal_id
        payload = {
            "status": "converged",
            "final_metric": final_metric,
            "converged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._sql(f"UPSERT goal:`{record_id}` MERGE {json.dumps(payload)};")
        return f"goal:`{record_id}`"

    def fetch_open_goals(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._sql(f"SELECT * FROM goal WHERE status = 'active' LIMIT {int(limit)};")
        return rows


class AutonomousGoalExecutor:
    """Executes goal-seeking loops with convergence verification and MaP-WAM memory."""

    def __init__(
        self,
        goal: GoalSpecification,
        memory: MemoryAsPlans | None = None,
    ) -> None:
        self.goal = goal
        self.memory = memory or MemoryAsPlans()

    async def execute_loop(
        self,
        initial_state: S,
        step_fn: Callable[[int, S], tuple[S, float, str]],
        verifier_fn: Callable[[float], bool] | None = None,
        progress_fn: Callable[[S, float], float] | None = None,
        contract_guidance: dict[str, Any] | None = None,
        transition_threshold: float = 1.0,
    ) -> AutonomousGoalLoopResult[S]:
        t0 = time.perf_counter()
        current_state = initial_state
        history: list[LoopIterationResult[S]] = []
        converged = False
        final_metric = 0.0

        for it in range(1, self.goal.max_iterations + 1):
            t_step = time.perf_counter()
            next_state, metric_val, action = step_fn(it, current_state)
            dt_step = round((time.perf_counter() - t_step) * 1000, 3)

            is_met = (
                verifier_fn(metric_val) if verifier_fn else self.goal.is_satisfied_by(metric_val)
            )

            # Compute progress p_t in [0.0, 1.0] (MaP-WAM progress modeling)
            if progress_fn:
                p_t = max(0.0, min(1.0, float(progress_fn(next_state, metric_val))))
            elif self.goal.direction == "at_most":
                if metric_val <= self.goal.target_threshold:
                    p_t = 1.0
                else:
                    denominator = max(0.01, 1.0 - self.goal.target_threshold)
                    p_t = max(0.0, 1.0 - (metric_val - self.goal.target_threshold) / denominator)
            else:
                denom = max(1e-6, self.goal.target_threshold)
                p_t = min(1.0, max(0.0, metric_val / denom))

            alignment_verified = bool(is_met and p_t >= transition_threshold)

            history.append(
                LoopIterationResult(
                    iteration=it,
                    state=next_state,
                    metric_value=metric_val,
                    is_goal_met=is_met,
                    duration_ms=dt_step,
                    action_taken=action,
                    progress=round(p_t, 4),
                    alignment_verified=alignment_verified,
                )
            )

            current_state = next_state
            final_metric = metric_val

            if is_met:
                converged = True
                # Commit segment to MemoryAsPlans (arXiv:2609.11561)
                proof_digest = hashlib.sha256(
                    f"{self.goal.goal_id}:{it}:{metric_val}".encode()
                ).hexdigest()[:12]
                seg = PlanSegment(
                    segment_id=f"seg_{self.goal.goal_id}_{it}",
                    goal_id=self.goal.goal_id,
                    subgoal_plan=self.goal.title,
                    contract_guidance=contract_guidance
                    or {
                        "target_metric": self.goal.target_metric,
                        "target_threshold": self.goal.target_threshold,
                    },
                    progress=round(p_t, 4),
                    verification_proof=f"autoharness_proof_{proof_digest}",
                    committed=True,
                )
                self.memory.commit(seg)
                break

        total_dt = round((time.perf_counter() - t0) * 1000, 3)
        return AutonomousGoalLoopResult(
            goal=self.goal,
            converged=converged,
            iterations_run=len(history),
            final_metric=final_metric,
            total_time_ms=total_dt,
            history=history,
            memory_as_plans=self.memory,
        )


class TraceGoalRefactorPipeline:
    """End-to-end: event_log traces -> GoalSpecification -> executed loop -> persisted result.

    The linear-trace antipattern this replaces: agents publish events, humans
    read them, nothing closes the loop. This pipeline refactors a trace into a
    goal-directed loop and durably persists both ends.
    """

    def __init__(self, persistence: DurableSurrealGoalPersistence | None = None) -> None:
        self._persistence = persistence or DurableSurrealGoalPersistence()

    def refactor(
        self,
        trace_events: list[dict[str, Any]],
        trace_ids: list[str] | None = None,
        step_fn: Callable[[int, Any], tuple[Any, float, str]] | None = None,
        verifier_fn: Callable[[float], bool] | None = None,
        max_iterations: int | None = None,
        goal: GoalSpecification | None = None,
        derived_from: list[dict[str, str]] | None = None,
        domain: str | None = None,
        session: str | None = None,
    ) -> tuple[GoalSpecification | None, AutonomousGoalLoopResult[Any] | None]:
        """Synthesize + execute + persist a goal from a raw trace.

        ``step_fn`` maps (iteration, state) -> (state, metric, action). If the
        caller provides no ``verifier_fn`` the goal's polarity-aware
        ``is_satisfied_by`` is used. Returns (goal, result); goal is None when the
        trace is not actionable.

        ``goal`` bypasses synthesis when the caller already holds the GoalSpecification.

        ``max_iterations`` overrides the synthesized budget for THIS run. A real
        caller passes 1: re-measuring an unchanged system N times in one process
        yields N identical readings. The loop closes across invocations and is
        terminated by the convergence status flip.
        """
        # A caller that already synthesized the goal (a failure cluster or a kanban
        # card -- shapes the single-event synthesizer cannot reproduce) passes it in.
        if goal is None:
            goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace_events)
        if goal is None:
            return None, None

        if step_fn is None:
            raise ValueError(
                f"an actionable trace needs a step_fn to execute the loop (goal: {goal.title})"
            )

        if max_iterations is not None:
            goal = replace(goal, max_iterations=max_iterations)

        executor = AutonomousGoalExecutor(goal)
        result: AutonomousGoalLoopResult[Any] = asyncio.run(
            executor.execute_loop(initial_state={}, step_fn=step_fn, verifier_fn=verifier_fn)
        )
        self._persistence.persist_goal(
            goal,
            origin_trace_ids=trace_ids,
            domain=domain,
            session=session,
            derived_from=derived_from,
        )
        self._persistence.persist_loop_result(result)
        # Every executed loop is a row (rung 1: run by hand, observed) in the ONE
        # loop table, linked to its goal -- not a per-session table.
        op = "<=" if goal.direction == "at_most" else ">="
        self._persistence.persist_loop(
            LoopSpec(
                name=f"trace-loop:{goal.goal_id}",
                goal=goal.title,
                verify=f"{goal.target_metric} {op} {goal.target_threshold}",
                stop_when="verify passes OR the per-run iteration bound",
                bound=goal.max_iterations,
                rung=1,
                cadence="per ops run (one iteration per invocation)",
                domain=domain,
                session=session,
                impl="scripts/ops/refactor_traces_to_goals.py",
            ),
            goal_id=goal.goal_id,
            key=f"trace_{goal.goal_id}",
        )
        if result.converged:
            self._persistence.mark_goal_converged(goal, result.final_metric)
        return goal, result
