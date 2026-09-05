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
from pathlib import Path

import pytest

from cohezion.flume.loop_goal_refactor_engine import (
    AutonomousGoalExecutor,
    DurableSurrealGoalPersistence,
    GoalSpecification,
    TraceGoalRefactorPipeline,
    TraceToLoopTransformer,
    payload_looks_like_failure,
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
    # finding_open, not test_pass_rate: a code-health finding is resolved when
    # the event_log records a fixed_in for it, and `test_pass_rate >= 1.0` was
    # unreachable in principle against the only plausible scope (tests/unit,
    # measured at 0.9728) — an unreachable goal never leaves fetch_open_goals.
    assert goal.target_metric == "finding_open"
    assert goal.target_threshold == 0.0
    assert goal.direction == "at_most"


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
        {
            "type": "SYSTEM_HEALTH",
            "source": "guardian",
            "payload": {"finding": "kde-open SIGABRT loop", "severity": "high"},
        },
    ]
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(trace)
    assert goal is not None
    assert goal.title.startswith("Resolve: kde-open")


def test_non_actionable_trace_returns_none() -> None:
    trace = [
        {
            "type": "JOURNEY_STEP",
            "source": "git-post-commit",
            "payload": {"event": "commit", "ok": True},
        },
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
    t_a = [
        {
            "type": "SECURITY_VIOLATION",
            "payload": {"finding": "os.system bypass", "severity": "high"},
        }
    ]
    t_b = [
        {
            "type": "SECURITY_VIOLATION",
            "payload": {"finding": "kde-open SIGABRT loop", "severity": "high"},
        }
    ]
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
        goal_id="goal_test_pass_rate_abc123",
        title="Resolve: x",
        target_metric="test_pass_rate",
        target_threshold=1.0,
    )
    first = persistence.persist_goal(goal)
    second = persistence.persist_goal(goal)  # re-run: must not raise
    assert first == second


# ---------------------------------------------------------------------------
# Executor convergence
# ---------------------------------------------------------------------------


def test_executor_converges_and_stops_early() -> None:
    goal = GoalSpecification(
        goal_id="goal_test_conv",
        title="converge",
        target_metric="test_pass_rate",
        target_threshold=1.0,
        max_iterations=10,
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
            payload = [{"result": [{"id": "goal:x", "title": "ok"}], "status": "OK", "time": "1ms"}]
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
        goal_id="goal_persist_test",
        title="Resolve: 'quoted' \"title\" with chars",
        target_metric="test_pass_rate",
        target_threshold=1.0,
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
        {
            "type": "SECURITY_VIOLATION",
            "payload": {"finding": "os.system verified-safe", "severity": "high"},
        },
    ]

    def step_fn(it: int, state: dict):
        # finding_open: 1.0 while open, 0.0 once the event_log records a fix.
        metric = 1.0 if it < 2 else 0.0
        return state, metric, "check event_log for a fixed_in"

    goal, result = pipeline.refactor(trace, trace_ids=["event_log:evt1"], step_fn=step_fn)
    assert goal is not None
    assert goal.title.startswith("Resolve: os.system")
    assert result is not None
    assert result.converged  # reaches 0.0 (resolved) at iteration 2
    assert result.iterations_run == 2


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


# ---------------------------------------------------------------------------
# Goal polarity — lower-is-better metrics must not read as converged
# ---------------------------------------------------------------------------


def test_at_most_goal_is_not_satisfied_by_a_value_above_threshold() -> None:
    """DISCRIMINATING: the pre-fix executor scored every goal with `>=`.

    An error_rate of 0.9 against a 0.05 ceiling then read as CONVERGED, and
    that verdict was written to durable storage. An implementation that
    ignores `direction` returns True here.
    """
    goal = GoalSpecification(
        goal_id="g_at_most",
        title="Stabilize: noisy-source",
        target_metric="error_rate",
        target_threshold=0.05,
        direction="at_most",
    )
    assert not goal.is_satisfied_by(0.9)
    assert goal.is_satisfied_by(0.01)
    assert goal.is_satisfied_by(0.05)  # boundary is inclusive


def test_default_direction_preserves_at_least_semantics() -> None:
    goal = GoalSpecification(
        goal_id="g_default",
        title="Verify fixes",
        target_metric="test_pass_rate",
        target_threshold=1.0,
    )
    assert goal.direction == "at_least"
    assert goal.is_satisfied_by(1.0)
    assert not goal.is_satisfied_by(0.97)


def test_executor_does_not_converge_on_high_error_rate() -> None:
    """DISCRIMINATING at the executor level, not just on the dataclass."""
    goal = GoalSpecification(
        goal_id="g_exec_at_most",
        title="Stabilize: noisy",
        target_metric="error_rate",
        target_threshold=0.05,
        max_iterations=3,
        direction="at_most",
    )
    result = asyncio.run(
        AutonomousGoalExecutor(goal).execute_loop(
            initial_state={}, step_fn=lambda it, s: (s, 0.9, "measured")
        )
    )
    assert not result.converged
    assert result.iterations_run == 3  # ran the full budget without meeting the goal


def test_stabilize_goal_is_synthesized_with_at_most_direction() -> None:
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [{"type": "JOURNEY_STEP", "source": "flaky-agent", "payload": {"msg": "error occurred"}}]
    )
    assert goal is not None
    assert goal.target_metric == "error_rate"
    assert goal.direction == "at_most"


# ---------------------------------------------------------------------------
# Already-fixed findings must not be re-opened as goals
# ---------------------------------------------------------------------------


def test_finding_with_fixed_in_yields_no_goal() -> None:
    """A finding recording the commit that fixed it is CLOSED.

    Re-opening it manufactures a goal that can never converge, which would sit
    in fetch_open_goals forever.
    """
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [
            {
                "type": "SECURITY_VIOLATION",
                "source": "health-campaign",
                "payload": {
                    "finding": "verify_code dotted-call bypass",
                    "fixed_in": "55e625ee2",
                    "severity": "high",
                },
            }
        ]
    )
    assert goal is None


def test_fixed_in_skip_does_not_fall_through_to_the_catch_all() -> None:
    """DISCRIMINATING: guards `continue` against an extra clause on the branch.

    Implemented instead as `and not payload.get("fixed_in")` on the
    SECURITY_VIOLATION test, control falls through to the catch-all IN THE SAME
    ITERATION. This payload says "failure", so the catch-all re-catches it and
    emits a mislabelled Stabilize goal instead of no goal at all.
    """
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [
            {
                "type": "SECURITY_VIOLATION",
                "source": "health-campaign",
                "payload": {
                    "finding": "verify_code bypass caused a test failure",
                    "fixed_in": "55e625ee2",
                    "severity": "high",
                },
            }
        ]
    )
    assert goal is None, "already-fixed finding must not become a Stabilize goal"


# ---------------------------------------------------------------------------
# Cross-run loop: one iteration per invocation, status flip terminates
# ---------------------------------------------------------------------------


class _RecordingPersistence(DurableSurrealGoalPersistence):
    """Captures statements instead of issuing them."""

    def __init__(self) -> None:
        super().__init__(url="http://127.0.0.1:1/sql")
        self.statements: list[str] = []

    def _sql(self, statement: str) -> list:
        self.statements.append(statement)
        return []


def test_refactor_max_iterations_override_runs_exactly_one_iteration() -> None:
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    calls: list[int] = []

    def step_fn(it: int, state: dict):
        calls.append(it)
        return state, 0.9, "measured"

    trace = [{"type": "JOURNEY_STEP", "source": "noisy", "payload": {"msg": "error"}}]
    goal, result = pipeline.refactor(trace, step_fn=step_fn, max_iterations=1)
    assert goal is not None and result is not None
    # The synthesized budget is 10; the per-run override must win.
    assert calls == [1]
    assert result.iterations_run == 1
    assert not result.converged  # 0.9 error rate against a 0.05 ceiling


def test_refactor_flips_status_only_when_converged() -> None:
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    trace = [{"type": "JOURNEY_STEP", "source": "quiet", "payload": {"msg": "error"}}]

    pipeline.refactor(trace, step_fn=lambda it, s: (s, 0.9, "m"), max_iterations=1)
    assert not any('"status": "converged"' in s for s in persistence.statements)

    persistence.statements.clear()
    pipeline.refactor(trace, step_fn=lambda it, s: (s, 0.0, "m"), max_iterations=1)
    assert any('"status": "converged"' in s for s in persistence.statements)


def test_refactor_honours_an_explicit_verifier() -> None:
    """The pipeline previously closed off the verifier escape entirely."""
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    trace = [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error"}}]
    _, result = pipeline.refactor(
        trace,
        step_fn=lambda it, s: (s, 0.9, "m"),
        verifier_fn=lambda v: v == 0.9,
        max_iterations=1,
    )
    assert result is not None
    assert result.converged


def test_persisted_payloads_carry_direction() -> None:
    """A stored `converged` flag is uninterpretable without polarity."""
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    trace = [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error"}}]
    pipeline.refactor(trace, step_fn=lambda it, s: (s, 0.9, "m"), max_iterations=1)

    goal_stmt = next(s for s in persistence.statements if s.startswith("UPSERT goal:"))
    loop_stmt = next(s for s in persistence.statements if s.startswith("CREATE loop_trace:"))
    assert '"direction": "at_most"' in goal_stmt
    assert '"direction": "at_most"' in loop_stmt


def test_catch_all_predicate_is_shared_with_the_synthesizer() -> None:
    """The measurement must score the SAME quantity that opened the goal.

    A private copy of this predicate in the ops CLI would drift from the
    synthesizer's silently, and the loop would then drive down a different
    number than the one it was opened for.
    """
    assert payload_looks_like_failure({"msg": "error occurred"})
    assert payload_looks_like_failure({"tests": "3 failed"})
    assert not payload_looks_like_failure({"status": "HEALTHY"})
    assert not payload_looks_like_failure({})
    assert not payload_looks_like_failure(None)

    # The synthesizer's catch-all must agree with it on the same payload.
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error occurred"}}]
    )
    assert goal is not None and goal.target_metric == "error_rate"
    assert (
        TraceToLoopTransformer.synthesize_goal_from_real_trace(
            [{"type": "JOURNEY_STEP", "source": "s", "payload": {"status": "HEALTHY"}}]
        )
        is None
    )


def _load_ops_cli():
    """Load the ops CLI by path (it lives in scripts/, not the package)."""
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "refactor_traces_to_goals.py"
    spec = importlib.util.spec_from_file_location("_tg_ops_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_measure_finding_open_returns_unknown_when_the_page_saturates(monkeypatch) -> None:
    """DISCRIMINATING: a saturated page is UNKNOWN, never "still open".

    event_log grows without bound. Once fixed_in-bearing rows exceed the page
    size, a resolved finding's fix record can fall outside it. Returning 1.0
    there would pin a CLOSED goal open forever — the already-fixed defect
    re-entering through the measurement path. An implementation missing the
    saturation guard returns 1.0 here.
    """
    cli = _load_ops_cli()
    saturated = [{"payload": {"finding": "some other finding", "fixed_in": "abc"}}] * (
        cli._FIXED_SCAN_LIMIT
    )
    monkeypatch.setattr(cli, "_sql", lambda *a, **k: saturated)
    assert cli.measure_finding_open("a finding not on this page", "vault") is None


def test_measure_finding_open_reports_open_when_the_page_is_not_saturated(monkeypatch) -> None:
    """The complement: an unsaturated page is authoritative, so 1.0 is real."""
    cli = _load_ops_cli()
    monkeypatch.setattr(
        cli, "_sql", lambda *a, **k: [{"payload": {"finding": "other", "fixed_in": "abc"}}]
    )
    assert cli.measure_finding_open("a genuinely open finding", "vault") == 1.0
    monkeypatch.setattr(
        cli, "_sql", lambda *a, **k: [{"payload": {"finding": "target", "fixed_in": "abc"}}]
    )
    assert cli.measure_finding_open("target", "vault") == 0.0


def test_mark_goal_converged_uses_upsert_merge() -> None:
    """MERGE (not CONTENT) so a later re-synthesis cannot reset the status."""
    persistence = _RecordingPersistence()
    goal = GoalSpecification(
        goal_id="g_flip", title="t", target_metric="error_rate", target_threshold=0.05
    )
    persistence.mark_goal_converged(goal, 0.0)
    assert persistence.statements[0].startswith("UPSERT goal:`g_flip` MERGE")
