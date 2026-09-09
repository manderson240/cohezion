"""Tests for the trace->goal->loop refactor pipeline (flume.loop_goal_refactor_engine).

Covers:
- Goal synthesis from real event_log trace shapes (SECURITY_VIOLATION,
  AGENT_COMPLETE-with-fixes, failure traces, non-actionable traces)
- DurableSurrealGoalPersistence ERR-inside-HTTP-200 checking (regression for
  the 2026-08-30 silent kanban-loss incident: unbound $TS params piped to
  /dev/null vanished writes without any signal)
- Pipeline refactor roundtrip with a converging step function
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cohezion.flume.loop_goal_refactor_engine import (
    AutonomousGoalExecutor,
    DurableSurrealGoalPersistence,
    GoalSpecification,
    TraceGoalRefactorPipeline,
    TraceToLoopTransformer,
)


# ---------------------------------------------------------------------------
# Goal synthesis from real trace shapes
# ---------------------------------------------------------------------------


def test_security_violation_trace_synthesizes_resolve_goal() -> None:
    trace = [
        {"type": "JOURNEY_STEP", "source": "s", "payload": {"event": "commit"}},
        {
            "type": "SECURITY_VIOLATION",
            "source": "audit",
            "payload": {"finding": "verify_code dotted-call bypass", "severity": "high"},
        },
    ]
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace)
    assert goal is not None
    assert goal.title.startswith("Resolve: verify_code dotted-call bypass")
    assert goal.target_metric == "test_pass_rate"
    assert goal.target_threshold == 1.0


def test_agent_complete_with_fixes_synthesizes_verify_goal() -> None:
    trace = [
        {
            "type": "AGENT_COMPLETE",
            "source": "campaign",
            "payload": {"result": {"fixed": ["b1", "b2", "b3"], "tests": "1882 passed"}},
        }
    ]
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace)
    assert goal is not None
    assert goal.title == "Verify 3 fixes stay green"
    assert goal.target_metric == "test_pass_rate"


def test_failure_trace_synthesizes_stabilize_goal() -> None:
    trace = [
        {"type": "JOURNEY_STEP", "source": "robinhood-bridge", "payload": {"error": "timeout x3"}},
    ]
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace)
    assert goal is not None
    assert goal.title.startswith("Stabilize: robinhood-bridge")
    assert goal.target_metric == "error_rate"


def test_high_severity_health_finding_synthesizes_resolve_goal() -> None:
    trace = [
        {"type": "SYSTEM_HEALTH", "source": "guardian", "payload": {"finding": "kde-open SIGABRT loop", "severity": "high"}},
    ]
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace)
    assert goal is not None
    assert goal.title.startswith("Resolve: kde-open")


def test_non_actionable_trace_returns_none() -> None:
    trace = [
        {"type": "JOURNEY_STEP", "source": "git-post-commit", "payload": {"event": "commit", "ok": True}},
        {"type": "CACHE_HIT", "source": "s", "payload": {}},
    ]
    assert TraceToLoopTransformer.synthesize_goal_from_real_trace(trace) is None


def test_empty_trace_returns_none() -> None:
    assert TraceToLoopTransformer.synthesize_goal_from_real_trace([]) is None


def test_goal_ids_are_content_derived_and_distinct() -> None:
    """Two different findings synthesized in the same second must not collide.

    Regression for 2026-08-30: time-based ids made three distinct goals share
    one id, 2/3 persistence writes failed with 'record already exists'.
    """
    t_a = [{"type": "SECURITY_VIOLATION", "payload": {"finding": "os.system bypass", "severity": "high"}}]
    t_b = [{"type": "SECURITY_VIOLATION", "payload": {"finding": "kde-open SIGABRT loop", "severity": "high"}}]
    goal_a = TraceToLoopTransformer.synthesize_goal_from_real_trace(t_a)
    goal_b = TraceToLoopTransformer.synthesize_goal_from_real_trace(t_b)
    assert goal_a is not None and goal_b is not None
    assert goal_a.goal_id != goal_b.goal_id
    # Same finding re-synthesized -> same id (idempotent re-runs)
    goal_a2 = TraceToLoopTransformer.synthesize_goal_from_real_trace(t_a)
    assert goal_a2 is not None and goal_a2.goal_id == goal_a.goal_id


def test_persist_goal_is_idempotent_on_rerun(fake_surreal) -> None:
    """UPSERT MERGE: the second persist of the same goal must not raise."""
    persistence = DurableSurrealGoalPersistence(
        url=fake_surreal, namespace="cohezion", database="main", auth="root:root"
    )
    goal = GoalSpecification(
        goal_id="goal_test_pass_rate_abc123", title="Resolve: x",
        target_metric="test_pass_rate", target_threshold=1.0,
    )
    first = persistence.persist_goal(goal)
    second = persistence.persist_goal(goal)  # re-run: must not raise
    assert first == second


def test_legacy_synthesize_from_trace_still_works() -> None:
    """The demo path (explicit title) keeps its old contract."""
    goal = TraceToLoopTransformer.synthesize_goal_from_trace(
        [{"step": 1}], goal_title="Attain and Lock HIHO 0.50"
    )
    assert goal.target_metric == "coherence"
    assert goal.target_threshold == 0.50


# ---------------------------------------------------------------------------
# Executor convergence
# ---------------------------------------------------------------------------


def test_executor_converges_and_stops_early() -> None:
    goal = GoalSpecification(
        goal_id="goal_test_conv", title="converge",
        target_metric="test_pass_rate", target_threshold=1.0, max_iterations=10,
    )

    def step_fn(it: int, state: dict):
        metric = min(1.0, it / 3.0)  # reaches 1.0 at iteration 3
        return {"it": it}, metric, f"iter {it}"

    result = asyncio.run(
        AutonomousGoalExecutor(goal).execute_loop(initial_state={}, step_fn=step_fn)
    )
    assert result.converged
    assert result.iterations_run == 3  # stopped at convergence, not max_iterations
    assert result.final_metric == 1.0


# ---------------------------------------------------------------------------
# DurableSurrealGoalPersistence — ERR-inside-HTTP-200 regression
# ---------------------------------------------------------------------------


class _FakeSurrealHandler(BaseHTTPRequestHandler):
    """Minimal SurrealDB /sql emulator: returns HTTP 200 + embedded ERR for
    statements it rejects (the trap that silently ate the 2026-08-30 kanban
    writes)."""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        if "$" not in body and "FAIL" not in body:
            # Parameter-free statement — accepted
            payload = [
                {"result": [{"id": "goal:x", "title": "ok"}], "status": "OK", "time": "1ms"}
            ]
        else:
            # SurrealDB's actual failure mode: HTTP 200 with status ERR inside
            payload = [
                {
                    "result": "Found unbound param $TS but this is a CONTENT clause",
                    "status": "ERR",
                    "time": "1ms",
                }
            ]
        blob = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, format, *args):  # noqa: A002 — stdlib signature
        pass


@pytest.fixture()
def fake_surreal():
    server = HTTPServer(("127.0.0.1", 0), _FakeSurrealHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/sql"
    server.shutdown()


def test_persistence_raises_on_embedded_err(fake_surreal) -> None:
    """HTTP 200 + status ERR body must raise, never silently vanish."""
    persistence = DurableSurrealGoalPersistence(
        url=fake_surreal, namespace="cohezion", database="main", auth="root:root"
    )
    with pytest.raises(RuntimeError, match="unbound param"):
        persistence._sql("CREATE kanban_item:x CONTENT {created_at: $TS};")


def test_persistence_ok_statement_roundtrips(fake_surreal) -> None:
    persistence = DurableSurrealGoalPersistence(
        url=fake_surreal, namespace="cohezion", database="main", auth="root:root"
    )
    rows = persistence._sql("SELECT * FROM goal WHERE title = 'ok';")
    assert rows == [{"id": "goal:x", "title": "ok"}]


def test_persist_goal_writes_parameter_free_literals(fake_surreal) -> None:
    persistence = DurableSurrealGoalPersistence(
        url=fake_surreal, namespace="cohezion", database="main", auth="root:root"
    )
    goal = GoalSpecification(
        goal_id="goal_persist_test", title="Resolve: 'quoted' \"title\" with chars",
        target_metric="test_pass_rate", target_threshold=1.0,
    )
    # The OK path: json.dumps literal — no $params. The fake server returns OK
    # only when the statement carries no unbound params (heuristic: OK_STATEMENT
    # token injected via the record id).
    record = persistence.persist_goal(goal)
    assert record == "goal:`goal_persist_test`"


# ---------------------------------------------------------------------------
# Pipeline refactor roundtrip
# ---------------------------------------------------------------------------


def test_pipeline_refactors_security_trace_into_executed_loop(fake_surreal) -> None:
    persistence = DurableSurrealGoalPersistence(
        url=fake_surreal, namespace="cohezion", database="main", auth="root:root"
    )
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    trace = [
        {"type": "SECURITY_VIOLATION", "payload": {"finding": "os.system verified-safe", "severity": "high"}},
    ]

    def step_fn(it: int, state: dict):
        metric = min(1.0, it / 2.0)
        return state, metric, "run regression suite"

    goal, result = pipeline.refactor(trace, trace_ids=["event_log:evt1"], step_fn=step_fn)
    assert goal is not None
    assert goal.title.startswith("Resolve: os.system")
    assert result is not None
    assert result.converged  # reaches 1.0 by iteration 2


def test_pipeline_returns_none_for_non_actionable_trace() -> None:
    pipeline = TraceGoalRefactorPipeline()
    goal, result = pipeline.refactor(
        [{"type": "JOURNEY_STEP", "payload": {"event": "commit", "ok": True}}],
        step_fn=lambda it, s: (s, 1.0, "noop"),
    )
    assert goal is None
    assert result is None


def test_pipeline_requires_step_fn_for_actionable_trace() -> None:
    pipeline = TraceGoalRefactorPipeline()
    trace = [{"type": "SECURITY_VIOLATION", "payload": {"finding": "x", "severity": "high"}}]
    with pytest.raises(ValueError, match="step_fn"):
        pipeline.refactor(trace)
