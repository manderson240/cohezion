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
        # DDL legitimately uses the built-in `$value` in ASSERT clauses; DML must be
        # parameter-free.
        if ("$" not in body or body.lstrip().startswith("DEFINE")) and "FAIL" not in body:
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
        metric = max(0.0, 1.0 - it / 2.0)  # finding_open falls 0.5 -> 0.0
        return state, metric, "close the finding"

    goal, result = pipeline.refactor(trace, trace_ids=["event_log:evt1"], step_fn=step_fn)
    assert goal is not None
    assert goal.title.startswith("Resolve: os.system")
    assert result is not None
    assert result.converged  # finding_open reaches 0.0 by iteration 2


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
# MaP-WAM Memory-as-Plans & Progress Modeling (arXiv:2609.11561)
# ---------------------------------------------------------------------------


def test_memory_as_plans_commit_and_bounded_context() -> None:
    from cohezion.flume.loop_goal_refactor_engine import MemoryAsPlans, PlanSegment

    memory = MemoryAsPlans()
    assert len(memory.segments) == 0

    seg1 = PlanSegment(
        segment_id="seg_001",
        goal_id="goal_test_1",
        subgoal_plan="Refactor AST AST-level check",
        contract_guidance={"invariant": "no_syntax_errors"},
        progress=1.0,
        verification_proof="autoharness_proof_abc123",
        committed=True,
    )
    memory.commit(seg1)
    assert len(memory.segments) == 1
    assert memory.segments[0].segment_id == "seg_001"

    goal2 = GoalSpecification(
        goal_id="goal_test_2",
        title="Verify invariant holds",
        target_metric="test_pass_rate",
        target_threshold=1.0,
    )
    context = memory.get_active_context(goal2)
    assert context["current_goal_id"] == "goal_test_2"
    assert context["completed_segments_count"] == 1
    assert context["last_verified_segment"] == "seg_001"
    assert "summary_digest" in context

    # Test serialization
    data = memory.to_dict()
    assert data["segment_count"] == 1
    assert data["segments"][0]["subgoal_plan"] == "Refactor AST AST-level check"


def test_executor_tracks_progress_and_commits_memory_as_plans() -> None:
    from cohezion.flume.loop_goal_refactor_engine import AutonomousGoalExecutor, MemoryAsPlans

    goal = GoalSpecification(
        goal_id="goal_progress_test",
        title="Gradual convergence goal",
        target_metric="coherence",
        target_threshold=0.50,
        max_iterations=5,
    )
    memory = MemoryAsPlans()
    executor = AutonomousGoalExecutor(goal, memory=memory)

    def step_fn(it: int, state: float) -> tuple[float, float, str]:
        val = min(0.50, it * 0.25)
        return val, val, f"Step {it}"

    result = asyncio.run(executor.execute_loop(0.0, step_fn))
    assert result.converged
    assert result.iterations_run == 2
    # Progress starts at 0.5 (0.25 / 0.50) then 1.0 (0.50 / 0.50)
    assert result.history[0].progress == 0.5
    assert result.history[1].progress == 1.0
    assert result.history[1].alignment_verified

    # Verifies MemoryAsPlans segment was committed
    assert result.memory_as_plans is not None
    assert len(result.memory_as_plans.segments) == 1
    committed_seg = result.memory_as_plans.segments[0]
    assert committed_seg.goal_id == "goal_progress_test"
    assert committed_seg.progress == 1.0
    assert committed_seg.verification_proof is not None
    assert committed_seg.verification_proof.startswith("autoharness_proof_")


def test_executor_error_rate_progress_and_custom_progress_fn() -> None:
    from cohezion.flume.loop_goal_refactor_engine import AutonomousGoalExecutor

    goal = GoalSpecification(
        goal_id="goal_error_rate",
        title="Stabilize service error rate",
        target_metric="error_rate",
        target_threshold=0.05,
        max_iterations=4,
        direction="at_most",  # polarity is explicit; the metric NAME no longer implies it
    )
    executor = AutonomousGoalExecutor(goal)

    # Step function driving error down from 0.20 to 0.04
    errors = [0.20, 0.10, 0.04]

    def step_fn(it: int, state: dict) -> tuple[dict, float, str]:
        err = errors[it - 1]
        return state, err, f"Iter {it}"

    result = asyncio.run(executor.execute_loop({}, step_fn))
    assert result.converged
    assert result.iterations_run == 3
    # Final iteration reached 0.04 <= 0.05, so progress is 1.0
    assert result.history[2].progress == 1.0
    assert result.history[2].alignment_verified


def test_chained_sequential_goals_accumulate_memory_as_plans() -> None:
    from cohezion.flume.loop_goal_refactor_engine import AutonomousGoalExecutor, MemoryAsPlans

    shared_memory = MemoryAsPlans()

    # Goal 1: Lint fix
    g1 = GoalSpecification(
        goal_id="g1", title="Fix lints", target_metric="lint_clean", target_threshold=1.0
    )
    exec1 = AutonomousGoalExecutor(g1, memory=shared_memory)
    r1 = asyncio.run(exec1.execute_loop(0, lambda it, s: (s + 1, 1.0, "lint fixed")))
    assert r1.converged
    assert len(shared_memory.segments) == 1

    # Goal 2: Unit tests
    g2 = GoalSpecification(
        goal_id="g2", title="Unit tests green", target_metric="test_pass_rate", target_threshold=1.0
    )
    exec2 = AutonomousGoalExecutor(g2, memory=shared_memory)
    r2 = asyncio.run(exec2.execute_loop(0, lambda it, s: (s + 1, 1.0, "tests passed")))
    assert r2.converged
    assert len(shared_memory.segments) == 2
    assert shared_memory.segments[0].goal_id == "g1"
    assert shared_memory.segments[1].goal_id == "g2"


# ---------------------------------------------------------------------------
# P1 engine hardening (closure semantics, re-cut onto main's engine)
# ---------------------------------------------------------------------------


def test_finding_open_at_most_goal_is_not_converged_by_a_value_above_ceiling() -> None:
    """DISCRIMINATING polarity: `finding_open` is lower-is-better but NOT named
    error_rate, so a name-keyed hack (`metric <= t if name == "error_rate"`) scores it
    with `>=`: 1.0 against a 0.0 ceiling reads CONVERGED. Reverting is_satisfied_by
    to `>=` turns this red."""
    goal = GoalSpecification("g_fo", "Resolve: x", "finding_open", 0.0, 1, direction="at_most")
    assert not goal.is_satisfied_by(1.0)
    assert goal.is_satisfied_by(0.0)
    result = asyncio.run(
        AutonomousGoalExecutor(goal).execute_loop({}, lambda it, s: (s, 1.0, "measured"))
    )
    assert not result.converged
    # progress must follow polarity too, not only is_met (alignment_verified would lie)
    assert result.history[-1].progress == 0.0
    assert not result.history[-1].alignment_verified


def test_default_direction_preserves_at_least_semantics() -> None:
    goal = GoalSpecification("g_default", "Verify fixes", "test_pass_rate", 1.0)
    assert goal.direction == "at_least"
    assert goal.is_satisfied_by(1.0)
    assert not goal.is_satisfied_by(0.97)


def test_stabilize_goal_is_synthesized_with_at_most_direction() -> None:
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [{"type": "JOURNEY_STEP", "source": "flaky-agent", "payload": {"msg": "error occurred"}}]
    )
    assert goal is not None
    assert (goal.target_metric, goal.direction) == ("error_rate", "at_most")


def test_finding_with_fixed_in_yields_no_goal() -> None:
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [
            {
                "type": "SECURITY_VIOLATION",
                "source": "health-campaign",
                "payload": {"finding": "bypass", "fixed_in": "55e625ee2", "severity": "high"},
            }
        ]
    )
    assert goal is None


def test_fixed_in_skip_does_not_fall_through_to_the_catch_all() -> None:
    """DISCRIMINATING: `continue`, not an extra clause -- this payload says "failure",
    so a fall-through re-catches it as a mislabelled Stabilize goal."""
    goal = TraceToLoopTransformer.synthesize_goal_from_real_trace(
        [
            {
                "type": "SECURITY_VIOLATION",
                "source": "health-campaign",
                "payload": {
                    "finding": "bypass caused a test failure",
                    "fixed_in": "55e625ee2",
                    "severity": "high",
                },
            }
        ]
    )
    assert goal is None


class _RecordingPersistence(DurableSurrealGoalPersistence):
    """Captures statements instead of issuing them."""

    def __init__(self) -> None:
        super().__init__(url="http://127.0.0.1:1/sql")
        self.statements: list[str] = []

    def _sql(self, statement: str) -> list:
        self.statements.append(statement)
        return []


def test_refactor_max_iterations_override_runs_exactly_one_iteration() -> None:
    pipeline = TraceGoalRefactorPipeline(persistence=_RecordingPersistence())
    calls: list[int] = []

    def step_fn(it: int, state: dict):
        calls.append(it)
        return state, 0.9, "measured"

    trace = [{"type": "JOURNEY_STEP", "source": "noisy", "payload": {"msg": "error"}}]
    goal, result = pipeline.refactor(trace, step_fn=step_fn, max_iterations=1)
    assert goal is not None and result is not None
    assert calls == [1]  # the synthesized budget is 10; the per-run override wins
    assert not result.converged


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
    pipeline = TraceGoalRefactorPipeline(persistence=_RecordingPersistence())
    trace = [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error"}}]
    _, result = pipeline.refactor(
        trace,
        step_fn=lambda it, s: (s, 0.9, "m"),
        verifier_fn=lambda v: v == 0.9,
        max_iterations=1,
    )
    assert result is not None and result.converged


def test_persisted_payloads_carry_direction() -> None:
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    trace = [{"type": "JOURNEY_STEP", "source": "s", "payload": {"msg": "error"}}]
    pipeline.refactor(trace, step_fn=lambda it, s: (s, 0.9, "m"), max_iterations=1)
    goal_stmt = next(s for s in persistence.statements if s.startswith("UPSERT goal:"))
    loop_stmt = next(s for s in persistence.statements if s.startswith("CREATE loop_trace:"))
    assert '"direction": "at_most"' in goal_stmt
    assert '"direction": "at_most"' in loop_stmt


def test_catch_all_predicate_is_shared_with_the_synthesizer() -> None:
    assert payload_looks_like_failure({"msg": "error occurred"})
    assert payload_looks_like_failure({"tests": "3 failed"})
    assert not payload_looks_like_failure({"status": "HEALTHY"})
    assert not payload_looks_like_failure({})
    assert not payload_looks_like_failure(None)
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


def test_mark_goal_converged_uses_upsert_merge() -> None:
    persistence = _RecordingPersistence()
    goal = GoalSpecification("g_flip", "t", "error_rate", 0.05)
    persistence.mark_goal_converged(goal, 0.0)
    assert persistence.statements[0].startswith("UPSERT goal:`g_flip` MERGE")


def test_persist_goal_merge_does_not_name_status() -> None:
    """MERGE preserves fields it OMITS. Naming status='active' re-opens converged goals."""
    persistence = _RecordingPersistence()
    persistence.persist_goal(GoalSpecification("g_m", "t", "error_rate", 0.05, direction="at_most"))
    merge = persistence.statements[0].split(";")[0]
    assert merge.startswith("UPSERT goal:`g_m` MERGE")
    assert '"status"' not in merge
    assert "WHERE status = NONE" in persistence.statements[0]


# -- ABSENT vs UNKNOWN in the measurement layer --------------------------------


def test_measure_finding_open_returns_unknown_when_the_page_saturates(monkeypatch) -> None:
    """DISCRIMINATING: a saturated page is UNKNOWN, never "still open"."""
    from cohezion.flume import trace_goal_sources as src

    saturated = [{"payload": {"finding": "other", "fixed_in": "abc"}}] * src.FIXED_SCAN_LIMIT
    monkeypatch.setattr(src, "sql", lambda *a, **k: saturated)
    assert src.measure_finding_open("not on this page", "vault") is None


def test_measure_finding_open_control_probe(monkeypatch) -> None:
    """Control: the instrument returns 1.0 / 0.0 / None, so it is not a constant."""
    from cohezion.flume import trace_goal_sources as src

    monkeypatch.setattr(
        src, "sql", lambda *a, **k: [{"payload": {"finding": "o", "fixed_in": "a"}}]
    )
    assert src.measure_finding_open("genuinely open", "vault") == 1.0
    monkeypatch.setattr(
        src, "sql", lambda *a, **k: [{"payload": {"finding": "t", "fixed_in": "a"}}]
    )
    assert src.measure_finding_open("t", "vault") == 0.0
    assert src.measure_finding_open("", "vault") is None


def test_measure_error_rate_unknown_on_no_rows_or_bad_source(monkeypatch) -> None:
    from cohezion.flume import trace_goal_sources as src

    monkeypatch.setattr(src, "sql", lambda *a, **k: [])
    assert src.measure_error_rate("good-source", "vault") is None
    assert src.measure_error_rate("bad'; DROP TABLE x;--", "vault") is None
    monkeypatch.setattr(
        src, "sql", lambda *a, **k: [{"payload": {"m": "error"}}, {"payload": {"m": "ok"}}]
    )
    assert src.measure_error_rate("good-source", "vault") == 0.5


# -- un-mocked behavioural falsifier: the MERGE re-open bug --------------------


def _scratch_persistence() -> DurableSurrealGoalPersistence:
    p = DurableSurrealGoalPersistence(database="tgl_test", timeout=3.0)
    try:
        # DEFINE DATABASE is idempotent; a probe that cannot fail would prove nothing
        # so unreachable SurrealDB skips (does not pass).
        DurableSurrealGoalPersistence(database="main", timeout=3.0)._sql(
            "DEFINE DATABASE IF NOT EXISTS tgl_test;"
        )
    except Exception as exc:
        pytest.skip(f"SurrealDB not reachable: {exc}")
    return p


def test_rerun_does_not_reopen_a_converged_goal_live_scratch_db() -> None:
    """DISCRIMINATING (mutation: put status:'active' back in the MERGE -> red).

    persist -> converge -> persist again (a re-run re-synthesizes the same
    content-derived id) -> status must STILL be 'converged'.
    """
    p = _scratch_persistence()
    goal = GoalSpecification("g_rerun_probe", "t", "error_rate", 0.05, direction="at_most")
    try:
        p.persist_goal(goal)
        assert p._sql("SELECT status FROM goal:`g_rerun_probe`;") == [{"status": "active"}]
        p.mark_goal_converged(goal, 0.0)
        p.persist_goal(goal)  # the re-run
        assert p._sql("SELECT status FROM goal:`g_rerun_probe`;") == [{"status": "converged"}]
        assert all(r["id"] != "goal:g_rerun_probe" for r in p.fetch_open_goals(500))
    finally:
        p._sql("DELETE goal:`g_rerun_probe`;")


# ---------------------------------------------------------------------------
# P2 — kanban + vault sources, failure clustering, two-source scan (R1a)
# ---------------------------------------------------------------------------


def _fail_ev(source: str, db: str = "vault", i: int = 0) -> dict:
    return {
        "id": f"event_log:{db}{source}{i}",
        "type": "SYSTEM_HEALTH",
        "source": source,
        "payload": {"msg": "error occurred"},
        "_source_db": db,
        "_source_table": "event_log",
    }


def test_kanban_open_card_becomes_goal_terminal_and_reading_list_do_not() -> None:
    from cohezion.flume.trace_goal_sources import synthesize_goal_from_kanban_item as k

    g = k({"title": "Wire the thing", "status": "in_progress"})
    assert g is not None and g.target_metric == "test_pass_rate" and g.title == "Wire the thing"
    assert k({"title": "Wire the thing", "status": "completed"}) is None
    assert k({"title": "Paper", "status": "backlog", "url": "https://arxiv.org/abs/1"}) is None
    assert k({"title": "  ", "status": "backlog"}) is None
    # content-derived id: identical card -> identical goal (idempotent)
    assert g.goal_id == k({"title": "Wire the thing", "status": "backlog"}).goal_id


def test_failure_cluster_needs_three_from_one_source() -> None:
    from cohezion.flume.trace_goal_sources import failure_cluster

    assert failure_cluster([_fail_ev("a", i=i) for i in range(2)]) is None
    three_unrelated = [_fail_ev("a"), _fail_ev("b"), _fail_ev("c")]
    assert failure_cluster(three_unrelated) is None  # noise across subsystems
    found = failure_cluster([_fail_ev("a", i=i) for i in range(3)] + [_fail_ev("b")])
    assert found is not None and found[0] == "a" and len(found[1]) == 3


def test_scan_single_failing_event_is_noise_but_cluster_is_a_goal() -> None:
    from cohezion.flume.trace_goal_sources import synthesize_scan

    assert synthesize_scan([_fail_ev("solo")]) == []  # catch_all disabled in a scan
    drafts = synthesize_scan([_fail_ev("flaky", i=i) for i in range(3)])
    assert len(drafts) == 1
    assert drafts[0].goal.title == "Stabilize: flaky" and drafts[0].goal.direction == "at_most"
    assert len(drafts[0].derived_from) == 3


def test_scan_provenance_carries_source_db_and_clusters_do_not_span_databases() -> None:
    from cohezion.flume.trace_goal_sources import synthesize_scan

    rows = [_fail_ev("s", "vault", 0), _fail_ev("s", "vault", 1), _fail_ev("s", "main", 2)]
    assert synthesize_scan(rows) == []  # 2 vault + 1 main: no single-db cluster of 3
    rows.append(_fail_ev("s", "vault", 3))
    drafts = synthesize_scan(rows)
    assert len(drafts) == 1
    assert {r["source_db"] for r in drafts[0].derived_from} == {"vault"}
    assert all(r["source_id"] for r in drafts[0].derived_from)


def test_scan_dedupes_same_goal_across_databases_and_merges_provenance() -> None:
    from cohezion.flume.trace_goal_sources import synthesize_scan

    rows = [_fail_ev("s", "vault", i) for i in range(3)] + [
        _fail_ev("s", "main", i) for i in range(3)
    ]
    drafts = synthesize_scan(rows)
    assert len(drafts) == 1
    assert {r["source_db"] for r in drafts[0].derived_from} == {"vault", "main"}


def test_default_scan_reads_vault_main_and_kanban(monkeypatch) -> None:
    """R1a DISCRIMINATING: flipping the default to ONE database is not "one scan, two
    sources". Mutation: make scan_traces read only `main` -> this goes red."""
    from cohezion.flume import trace_goal_sources as src

    seen: list[tuple[str, str]] = []

    def fake_sql(statement: str, database: str):
        table = "kanban_item" if "FROM kanban_item" in statement else "event_log"
        seen.append((database, table))
        return [{"id": f"{table}:x"}]

    monkeypatch.setattr(src, "sql", fake_sql)
    rows = src.scan_traces(5)
    assert ("vault", "event_log") in seen and ("main", "event_log") in seen
    assert ("main", "kanban_item") in seen
    assert {(r["_source_db"], r["_source_table"]) for r in rows} == set(seen)
    seen.clear()
    only_vault = src.scan_traces(5, database="vault")
    assert seen == [("vault", "event_log")] and len(only_vault) == 1


def test_scan_raises_when_a_source_is_unreadable(monkeypatch) -> None:
    """UNKNOWN must not read as "no findings"."""
    from cohezion.flume import trace_goal_sources as src

    def boom(statement: str, database: str):
        raise RuntimeError("db down")

    monkeypatch.setattr(src, "sql", boom)
    with pytest.raises(RuntimeError):
        src.scan_traces(5)


def test_refactor_accepts_a_precomputed_goal() -> None:
    """A cluster/kanban goal cannot be re-synthesized from one event."""
    persistence = _RecordingPersistence()
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    goal = GoalSpecification("g_pre", "Stabilize: x", "error_rate", 0.05, 5, direction="at_most")
    got, result = pipeline.refactor(
        [{"type": "AGENT_START", "payload": {}}],  # not actionable on its own
        step_fn=lambda it, s: (s, 0.0, "m"),
        max_iterations=1,
        goal=goal,
    )
    assert got is not None and got.goal_id == "g_pre" and result is not None and result.converged


def _load_ops_cli():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "refactor_traces_to_goals.py"
    spec = importlib.util.spec_from_file_location("_tg_ops_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_dry_run_without_database_flag_yields_a_vault_derived_goal(monkeypatch, capsys) -> None:
    """R1a falsifier at the CLI: no --database flag, >=1 goal derived from vault."""
    cli = _load_ops_cli()
    rows = [_fail_ev("flaky", "vault", i) for i in range(3)]
    monkeypatch.setattr(cli, "scan_traces", lambda limit, database=None: rows)
    monkeypatch.setattr("sys.argv", ["refactor_traces_to_goals.py", "--dry-run"])
    assert cli.main() == 0
    out = capsys.readouterr().out
    assert "Stabilize: flaky" in out and "derived_from source_db=vault" in out
    assert "no writes" in out  # dry-run wrote nothing


def test_legacy_callers_keep_their_fetch_recent_traces_import(monkeypatch) -> None:
    """cli/main.py (ops refactor-traces) and the perpetual orchestrator's Phase 5 import
    `fetch_recent_traces` from the ops script. The P2 rewrite briefly removed it."""
    from cohezion.flume import trace_goal_sources as src

    cli = _load_ops_cli()
    seen: list[str] = []
    monkeypatch.setattr(src, "sql", lambda stmt, db: seen.append(db) or [{"id": "event_log:x"}])
    rows = cli.fetch_recent_traces(5, database="vault")
    assert seen == ["vault"] and rows[0]["_source_db"] == "vault"


# ---------------------------------------------------------------------------
# P4 — the reader (R4): --status reads goal_graph + canonical nodes only
# ---------------------------------------------------------------------------


def _fake_graph_reader(statements: list[str]):
    def read(stmt: str) -> list[dict]:
        statements.append(stmt)
        if "FROM goal_graph WHERE kind = 'mirrors'" in stmt:
            return [{"out": "doc_path:`references/x.md`", "at": "2026-09-04"}]
        if "FROM goal_graph GROUP BY kind" in stmt:
            return [{"kind": "pursues", "n": 2}, {"kind": "mirrors", "n": 5}]
        if "FROM goal WHERE" in stmt and "NOT IN" in stmt:
            return [{"domain": "alpha", "n": 1}]
        if "FROM loop WHERE" in stmt and "NOT IN" in stmt:
            return [{"domain": "beta", "n": 3}]
        if "FROM goal WHERE" in stmt:
            return [{"domain": "alpha", "n": 4}, {"domain": "beta", "n": 2}]
        if "FROM loop WHERE rung" in stmt:
            return [{"rung": 3, "n": 6}]
        if "FROM loop WHERE" in stmt:
            return [{"domain": "alpha", "n": 7}, {"domain": "beta", "n": 8}]
        return []

    return read


def test_status_reads_goal_graph_not_domain_tables() -> None:
    """R4 mutation target: neutralise the reader (return []) and this goes red.

    The output must be DERIVED from goal_graph + canonical goal/loop rows, and no
    statement may touch a per-domain `<x>_goal` / `<x>_loop` table.
    """
    import re

    from cohezion.flume.goal_graph import format_status, graph_status

    statements: list[str] = []
    status = graph_status(_fake_graph_reader(statements))
    out = format_status(status)

    assert status["domains"] == {
        "alpha": {"goals": 4, "loops": 7, "goals_without_loops": 1},
        "beta": {"goals": 2, "loops": 8, "loops_without_goals": 3},
    }
    assert status["edges"] == {"pursues": 2, "mirrors": 5} and status["rungs"] == {"3": 6}
    assert "alpha" in out and "2 domain(s)" in out and "references/x.md" in out
    assert any("FROM goal_graph" in s for s in statements)
    per_domain = re.compile(r"\b\w+_(?:goal|loop)\b")
    assert not [s for s in statements if per_domain.search(s)], statements


def test_cli_status_prints_the_graph_and_writes_nothing(monkeypatch, capsys) -> None:
    cli = _load_ops_cli()
    statements: list[str] = []
    monkeypatch.setattr(cli, "sql", lambda stmt, db: _fake_graph_reader(statements)(stmt))
    monkeypatch.setattr("sys.argv", ["refactor_traces_to_goals.py", "--status"])
    assert cli.main() == 0
    out = capsys.readouterr().out
    assert "2 domain(s)" in out and "alpha" in out
    assert not any(
        s.lstrip().upper().startswith(("UPSERT", "CREATE", "INSERT", "DELETE")) for s in statements
    )
