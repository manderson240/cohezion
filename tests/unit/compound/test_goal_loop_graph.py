"""Unit tests for Goal and Loop Graph Engineering System."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.goal_loop_graph import (
    Goal,
    GoalLoopGraphEngine,
    GoalStatus,
    GraphRelation,
    Learning,
    Loop,
    Proof,
    ProofType,
    TraceStep,
    VModelLevel,
)


def test_goal_and_loop_instantiation() -> None:
    goal = Goal(
        id="goal_test_01",
        intent="Maximize ROC-AUC on RSNA Knee",
        target_metric="roc_auc",
        target_threshold=0.960,
        current_metric=0.957,
        lyapunov_potential=0.03,
        status=GoalStatus.ACTIVE,
        vmodel_level=VModelLevel.SUBSYSTEM,
    )
    assert goal.to_surreal_record() == "goal:goal_test_01"
    d = goal.to_dict()
    assert d["intent"] == "Maximize ROC-AUC on RSNA Knee"
    assert d["status"] == "active"
    assert d["vmodel_level"] == "SUBSYSTEM"

    loop = Loop(
        id="loop_test_01",
        cycle_pattern="Hypothesis_Verify_Execute_Learn",
        actions=["observe", "propose", "verify", "submit"],
        converged=True,
        iteration_count=4,
        progress_score=1.0,
    )
    assert loop.to_surreal_record() == "autonomous_loop:loop_test_01"
    assert loop.is_progressive is True
    assert loop.is_livelock is False


def test_refactor_trace_sequence() -> None:
    engine = GoalLoopGraphEngine()
    events = [
        {"action": "eda", "status": "SUCCESS", "latency_ms": 100.0, "tokens_spent": 0},
        {"action": "feature_eng", "status": "SUCCESS", "latency_ms": 250.0, "tokens_spent": 0},
        {"action": "validation", "status": "SUCCESS", "latency_ms": 500.0, "tokens_spent": 0},
    ]

    goal, loop, traces, relations = engine.refactor_trace_sequence(
        domain="rsna_knee",
        task_name="Anatomical Bilateral Symmetry",
        events=events,
        target_metric="auc",
        target_threshold=0.960,
    )

    assert goal.status == GoalStatus.SATISFIED
    assert goal.lyapunov_potential == 0.0
    assert loop.converged is True
    assert len(traces) == 3
    assert len(relations) == 4  # 1 executed_by + 3 produces

    # Check relation types
    rel_names = [r.relation for r in relations]
    assert "executed_by" in rel_names
    assert rel_names.count("produces") == 3


def test_build_surrealql_statements() -> None:
    engine = GoalLoopGraphEngine()
    goal = Goal(id="g1", intent="test intent")
    loop = Loop(id="l1", cycle_pattern="PDCA")
    trace = TraceStep(id="t1", action="run")
    proof = Proof(
        id="p1",
        theorem_name="Theorem 1",
        proof_type=ProofType.AST_BYTECODE,
        formal_claim="claim",
        proof_certificate_hash="hash123",
        verified=True,
        verification_duration_ms=0.01,
    )
    learning = Learning(
        id="k1",
        title="Learning 1",
        learning_domain="general",
        vector_12d=[1.0] * 12,
        retrospective_text="retro",
        compound_action="action",
        timestamp="2026-10-16T00:00:00Z",
    )
    relations = [
        GraphRelation(source=goal.to_surreal_record(), relation="executed_by", target=loop.to_surreal_record()),
        GraphRelation(source=loop.to_surreal_record(), relation="produces", target=trace.to_surreal_record()),
        GraphRelation(source=trace.to_surreal_record(), relation="verified_by", target=proof.to_surreal_record()),
        GraphRelation(source=loop.to_surreal_record(), relation="yields", target=learning.to_surreal_record()),
        GraphRelation(source=learning.to_surreal_record(), relation="compounds_into", target=goal.to_surreal_record()),
    ]

    surql = engine.build_surrealql([goal], [loop], [trace], [proof], [learning], relations)
    assert "DEFINE TABLE goal" in surql
    assert "DEFINE TABLE executed_by TYPE RELATION" in surql
    assert "UPSERT goal:g1 CONTENT" in surql
    assert "RELATE goal:g1->executed_by->autonomous_loop:l1" in surql
    assert "RELATE autonomous_loop:l1->produces->loop_trace:t1" in surql
    assert "RELATE loop_trace:t1->verified_by->proof:p1" in surql


def test_persist_graph_mocked() -> None:
    engine = GoalLoopGraphEngine()
    goal = Goal(id="g1", intent="test")
    loop = Loop(id="l1", cycle_pattern="PDCA")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([{"status": "OK"}]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        success = engine.persist_graph([goal], [loop], [], [], [], [])
        assert success is True
