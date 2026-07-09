"""MD2 wiring test — TransitionController + RecursiveTraceLoop wired into executor.

V-Model right-side test for Module Design (integration):
  MD2.1: CompoundExecutor has a transition_controller property.
  MD2.2: The default state machine has the compound-loop states.
  MD2.3: record_state_transition nudges edge weights.
  MD2.4: RecursiveTraceLoop is accessible (None when not injected).
  MD2.5: SurrealDB state_transitions + quality_gate + compound_loop tables exist.
"""

from __future__ import annotations

import json
import urllib.request

import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.inference.transition_controller import (
    TransitionController,
    detect_stuck_loops,
    first_passage,
)


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = "root:root"


class TestTransitionControllerWired:
    def test_md2_1_executor_has_transition_controller(self):
        assert hasattr(CompoundExecutor, "transition_controller"), (
            "CompoundExecutor must expose transition_controller property (MD2 wiring)"
        )

    def test_md2_2_default_state_machine_has_compound_states(self):
        from cohezion.compound.executor import _default_compound_loop_state_machine

        tc = _default_compound_loop_state_machine()
        assert isinstance(tc, TransitionController)
        states = set(tc.matrix.keys())
        expected = {"execute", "retrospect", "refine", "vote", "done"}
        assert expected.issubset(states), f"missing states: {expected - states}"

    def test_md2_3_record_state_transition_nudges_weight(self):
        from cohezion.compound.executor import _default_compound_loop_state_machine

        tc = _default_compound_loop_state_machine()
        initial = tc.weights.get(("execute", "aggregate"), 1.0)
        new_weight = tc.record_transition("execute", "aggregate", reward=0.5)
        assert new_weight != initial
        assert 0.01 <= new_weight <= 2.0

    def test_md2_4_recursive_trace_loop_accessible(self):
        assert hasattr(CompoundExecutor, "recursive_trace_loop"), (
            "CompoundExecutor must expose recursive_trace_loop property (MD2 wiring)"
        )

    def test_md2_4b_detect_stuck_loops_works(self):
        sequence = ["execute", "error_correct", "error_correct", "error_correct", "done"]
        stuck = detect_stuck_loops(sequence, threshold=3)
        assert "error_correct" in stuck

    def test_md2_4c_first_passage_finds_target(self):
        sequence = ["start", "align", "execute", "retrospect", "done"]
        assert first_passage(sequence, "retrospect") == 3
        assert first_passage(sequence, "nonexistent") is None


class TestSurrealDBTables:
    """Verify the SurrealDB tables for compound-loop telemetry exist."""

    @pytest.fixture
    def db_query(self):
        def _q(sql: str) -> dict:
            req = urllib.request.Request(
                SURREAL_URL,
                data=sql.encode(),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                },
                method="POST",
            )
            import base64

            auth = base64.b64encode(SURREAL_AUTH.encode()).decode()
            req.add_header("Authorization", f"Basic {auth}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())

        return _q

    def test_md2_5_state_transitions_table_exists(self, db_query):
        result = db_query("INFO FOR DB;")
        tables = result[0].get("result", {}).get("tables", {})
        assert "state_transitions" in tables, "state_transitions table missing"

    def test_md2_5_quality_gate_table_exists(self, db_query):
        result = db_query("INFO FOR DB;")
        tables = result[0].get("result", {}).get("tables", {})
        assert "quality_gate" in tables, "quality_gate table missing"

    def test_md2_5_compound_loop_table_exists(self, db_query):
        result = db_query("INFO FOR DB;")
        tables = result[0].get("result", {}).get("tables", {})
        assert "compound_loop" in tables, "compound_loop table missing"
