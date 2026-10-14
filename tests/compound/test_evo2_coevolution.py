"""Unit tests for Evo^2 Weight-Harness Co-Evolution Engine (arXiv:2610.13025)."""

import pytest
from cohezion.compound.evo2_coevolution import (
    DualRolePolicy,
    EvoTIDEEngine,
    HarnessNode,
    HarnessTree,
    ReflectionReport,
)


def test_harness_node_ast_validation():
    valid_node = HarnessNode(
        node_id="test_valid",
        parent_id=None,
        harness_code="def evaluate(x): return x * 2\n",
    )
    assert valid_node.is_valid_ast() is True

    invalid_node = HarnessNode(
        node_id="test_invalid",
        parent_id=None,
        harness_code="def broken_func(x): return x * \n",
    )
    assert invalid_node.is_valid_ast() is False


def test_harness_tree_mutation_and_best_tracking():
    root_code = "def loss(): return 0.5"
    tree = HarnessTree(root_code=root_code)

    assert tree.get_best_node().harness_code == root_code
    assert tree.get_best_node().score == 0.0

    # Add child 1
    child1 = tree.add_node(
        harness_code="def loss(): return 0.7",
        score=0.7,
        status="EVALUATED",
    )
    assert tree.get_best_node().node_id == child1.node_id

    # Add child 2 with higher score
    child2 = tree.add_node(
        harness_code="def loss(): return 0.9",
        score=0.9,
        status="EVALUATED",
    )
    assert tree.get_best_node().node_id == child2.node_id

    # Select parent for mutation should pick child2
    parent = tree.select_parent_for_mutation()
    assert parent.node_id == child2.node_id


def test_dual_role_policy_reflection_and_proposal():
    policy = DualRolePolicy(llm_fn=None)
    trace = "Traceback (most recent call last):\n  File 'eval.py', line 42, in <module>\n    RuntimeError: Invariant broken"

    report = policy.reflect(
        task_description="RSNA Knee calibration",
        harness_code="x = 1",
        execution_trace=trace,
        current_score=0.85,
    )

    assert isinstance(report, ReflectionReport)
    assert report.crash_line == 42
    assert len(report.actionable_invariants) > 0

    # Proposer returns valid executable harness
    proposed = policy.propose(
        task_description="RSNA Knee calibration",
        base_harness="x = 1",
        reflection=report,
    )
    assert "x = 1" in proposed


def test_evotide_trajectory_recovery_and_crossover():
    tree = HarnessTree(root_code="def solve(): return 1")
    policy = DualRolePolicy(llm_fn=None)

    def dummy_eval(code: str):
        if "broken" in code:
            return 0.0, "Error: broken token"
        return 0.92, "OK"

    engine = EvoTIDEEngine(tree=tree, policy=policy, eval_fn=dummy_eval)

    # Test trajectory recovery on broken syntax
    broken_code = "def solve(): return 1\ndef error(:"
    recovered = engine.recover_trajectory(broken_code, "Syntax error")
    assert "def solve(): return 1" in recovered

    # Add two distinct nodes with scores to enable crossover
    node_a = tree.add_node("def method_a(): return 'a'", score=0.91, status="EVALUATED")
    node_b = tree.add_node("def method_b(): return 'b'", score=0.93, status="EVALUATED")

    # Perform crossover step
    child = engine.crossover_step("RSNA multi-model blend")
    assert child is not None
    assert child.status == "EVALUATED"
    assert "method_a" in child.harness_code or "method_b" in child.harness_code
