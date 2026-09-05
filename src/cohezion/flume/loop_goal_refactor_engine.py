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
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")


@dataclass(frozen=True, slots=True)
class GoalSpecification:
    """Formal Goal contract with convergence criteria and invariant bounds."""

    goal_id: str
    title: str
    target_metric: str  # e.g., 'coherence', 'snr_db', 'test_pass_rate'
    target_threshold: float  # e.g., 0.50, 20.0, 1.00
    max_iterations: int = 10
    timeout_seconds: float = 30.0


@dataclass
class LoopIterationResult(Generic[S]):
    iteration: int
    state: S
    metric_value: float
    is_goal_met: bool
    duration_ms: float
    action_taken: str


@dataclass
class AutonomousGoalLoopResult(Generic[S]):
    goal: GoalSpecification
    converged: bool
    iterations_run: int
    final_metric: float
    total_time_ms: float
    history: list[LoopIterationResult[S]] = field(default_factory=list)


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
    ) -> GoalSpecification | None:
        """Synthesize an actionable goal from real event_log/kanban trace rows.

        Extraction rules (deterministic, zero-inference):
        - SECURITY_VIOLATION / SYSTEM_HEALTH payloads with severity=high ->
          goal "Resolve <finding>" with test_pass_rate >= 1.0
        - AGENT_COMPLETE results with 'fixed' lists -> goal "Verify <fixes>" with
          test_pass_rate >= 1.0
        - any single event whose payload contains 'fail'/'error' (checked last,
          across any event type) -> goal "Stabilize <source>" with
          error_rate <= 0.05. NOTE (corrected 2026-09-05): this was previously
          documented as requiring ">= 3 occurrences of the same source" but that
          was never implemented -- the loop below returns on the FIRST matching
          event in trace_events, and the one existing regression test
          (test_failure_trace_synthesizes_stabilize_goal) asserts exactly that
          single-occurrence behavior. Corrected the claim rather than the code,
          since the test already locks in single-occurrence as the intended
          contract. A true repeated-occurrence check would need the CALLER to
          group events by source before calling this (it currently doesn't).
        Returns None when the trace carries no actionable signal.

        goal_id is content-derived (title+metric hash): stable across re-runs
        (idempotent REFETCH) and collision-free across distinct findings —
        a time-based id made distinct traces in the same second collide
        (2026-08-30: three goals got one id, 2/3 writes failed).
        """
        if not trace_events:
            return None

        def _goal_id(title: str, metric: str) -> str:
            digest = hashlib.sha256(f"{title}|{metric}".encode()).hexdigest()[:10]
            return f"goal_{metric}_{digest}"

        for ev in trace_events:
            etype = str(ev.get("type") or (ev.get("payload") or {}).get("type") or "")
            payload = ev.get("payload") or {}
            text = json.dumps(payload, default=str)

            if etype == "SECURITY_VIOLATION" or "SECURITY_VIOLATION" in etype:
                finding = payload.get("finding") or payload.get("title") or "security finding"
                title = f"Resolve: {str(finding)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "test_pass_rate"),
                    title=title,
                    target_metric="test_pass_rate",
                    target_threshold=1.0,
                    max_iterations=5,
                    timeout_seconds=300.0,
                )
            if etype == "SYSTEM_HEALTH" and (
                payload.get("severity") == "high" or payload.get("finding")
            ):
                finding = payload.get("finding") or payload.get("title") or "health finding"
                title = f"Resolve: {str(finding)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "test_pass_rate"),
                    title=title,
                    target_metric="test_pass_rate",
                    target_threshold=1.0,
                    max_iterations=5,
                    timeout_seconds=300.0,
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
            if "fail" in text.lower() or "error" in text.lower():
                src = ev.get("source") or "unknown-source"
                title = f"Stabilize: {str(src)[:120]}"
                return GoalSpecification(
                    goal_id=_goal_id(title, "error_rate"),
                    title=title,
                    target_metric="error_rate",
                    target_threshold=0.05,
                    max_iterations=10,
                    timeout_seconds=300.0,
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
        self._headers = {
            "Accept": "application/json",
            "surreal-ns": namespace,
            "surreal-db": database,
            "Authorization": "Basic " + base64.b64encode(auth.encode()).decode(),
            "Content-Type": "text/plain",
        }
        self._timeout = timeout

    def _sql(self, statement: str) -> list:
        """Execute one statement; raise on embedded ERR status (never swallow)."""
        req = urllib.request.Request(  # noqa: S310 — fixed literal localhost url
            self._url, data=statement.encode(), headers=self._headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as r:  # noqa: S310 — fixed literal localhost url
            body = json.loads(r.read())
        rows = []
        for stmt_result in body:
            if stmt_result.get("status") == "ERR":
                raise RuntimeError(f"SurrealDB statement error: {stmt_result.get('result')}")
            rows.extend(stmt_result.get("result") or [])
        return rows

    def persist_goal(
        self, goal: GoalSpecification, origin_trace_ids: list[str] | None = None
    ) -> str:
        record_id = goal.goal_id
        payload = {
            "title": goal.title,
            "target_metric": goal.target_metric,
            "target_threshold": goal.target_threshold,
            "max_iterations": goal.max_iterations,
            "status": "active",
            "origin_trace_ids": origin_trace_ids or [],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # Parameter-free literal via json.dumps — the unbound-$param trap is
        # structurally impossible here (2026-08-30: kanban writes silently
        # ERR'd because of an unbound $TS piped to /dev/null).
        # Idempotent: re-running the pipeline re-synthesizes the same
        # content-derived goal_id; UPSERT MERGE (not CONTENT) preserves any
        # status transitions an executor made between runs.
        self._sql(f"UPSERT goal:`{record_id}` MERGE {json.dumps(payload)};")
        return f"goal:`{record_id}`"

    def persist_loop_result(self, result: AutonomousGoalLoopResult[Any]) -> str:
        record_id = f"{result.goal.goal_id}_result_{int(time.time())}"
        payload = {
            "goal_id": result.goal.goal_id,
            "title": result.goal.title,
            "converged": result.converged,
            "iterations_run": result.iterations_run,
            "final_metric": result.final_metric,
            "target_metric": result.goal.target_metric,
            "target_threshold": result.goal.target_threshold,
            "total_time_ms": result.total_time_ms,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._sql(f"CREATE loop_trace:`{record_id}` CONTENT {json.dumps(payload)};")
        return f"loop_trace:`{record_id}`"

    def fetch_open_goals(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._sql(f"SELECT * FROM goal WHERE status = 'active' LIMIT {int(limit)};")
        return rows


class AutonomousGoalExecutor:
    """Executes goal-seeking loops with convergence verification."""

    def __init__(self, goal: GoalSpecification) -> None:
        self.goal = goal

    async def execute_loop(
        self,
        initial_state: S,
        step_fn: Callable[[int, S], tuple[S, float, str]],
        verifier_fn: Callable[[float], bool] | None = None,
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
                verifier_fn(metric_val)
                if verifier_fn
                else (metric_val >= self.goal.target_threshold)
            )
            history.append(
                LoopIterationResult(
                    iteration=it,
                    state=next_state,
                    metric_value=metric_val,
                    is_goal_met=is_met,
                    duration_ms=dt_step,
                    action_taken=action,
                )
            )

            current_state = next_state
            final_metric = metric_val

            if is_met:
                converged = True
                break

        total_dt = round((time.perf_counter() - t0) * 1000, 3)
        return AutonomousGoalLoopResult(
            goal=self.goal,
            converged=converged,
            iterations_run=len(history),
            final_metric=final_metric,
            total_time_ms=total_dt,
            history=history,
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
    ) -> tuple[GoalSpecification | None, AutonomousGoalLoopResult[Any] | None]:
        """Synthesize + execute + persist a goal from a raw trace.

        ``step_fn`` maps (iteration, state) -> (state, metric, action). If the
        caller provides no verifier the goal threshold comparison is used.
        Returns (goal, result); goal is None when the trace is not actionable.
        """
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace_events)
        if goal is None:
            return None, None

        if step_fn is None:
            raise ValueError(
                f"an actionable trace needs a step_fn to execute the loop (goal: {goal.title})"
            )

        executor = AutonomousGoalExecutor(goal)
        result = asyncio.run(executor.execute_loop(initial_state={}, step_fn=step_fn))
        self._persistence.persist_goal(goal, origin_trace_ids=trace_ids)
        self._persistence.persist_loop_result(result)
        return goal, result
