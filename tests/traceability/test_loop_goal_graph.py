"""V-model tests for the loop/goal derivation graph.

Structure mirrors `verification-depth.md`: a structural tier that pins the contract a
refactor could silently break, and a discriminating tier where every test is paired with
the mutation that must turn it red.

The tests that matter are NOT "the checker accepts a correct witness" -- a checker that
returns True unconditionally passes those. They are "the checker REJECTS a wrong witness".
"""

from __future__ import annotations

import ast
import inspect
import textwrap

import pytest

from cohezion.traceability.loop_goal_graph import (
    Certificate,
    acyclicity_certificate,
    canonical_digest,
    coverage_certificate,
    verify_coverage,
    verify_topological_order,
)


# A trace -> goal -> emitted-trace chain. Acyclic: nothing loops back.
LINEAR: tuple[tuple[str, str], ...] = (
    ("trace:t1", "goal:g1"),
    ("goal:g1", "trace:t2"),
    ("trace:t2", "goal:g2"),
)

# The self-ingestion failure: g1's emitted trace synthesizes a goal that feeds g1 again.
SELF_INGESTING: tuple[tuple[str, str], ...] = (*LINEAR, ("goal:g2", "trace:t1"))


# ------------------------------------------------------------------ T0 structural


def test_t0_checker_is_independent_of_its_producer() -> None:
    """The load-bearing structural claim: verify_* must not call the producer.

    If verify_topological_order used graphlib, a green result would prove only that the
    same algorithm ran twice -- not that the witness is correct. This pins the asymmetry
    that makes the certificate a proof rather than a duplicate execution.

    Checked against the AST, not the source text: the docstrings legitimately NAME the
    thing they must not call, so a substring scan reports its own prose as a violation.
    Grep the references, never the characters.
    """

    def referenced_names(fn) -> set[str]:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
            n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
        }

    topo_refs = referenced_names(verify_topological_order)
    assert "graphlib" not in topo_refs
    assert "TopologicalSorter" not in topo_refs
    assert "acyclicity_certificate" not in topo_refs

    assert "coverage_certificate" not in referenced_names(verify_coverage)


def test_t0_certificate_carries_a_rechecking_witness() -> None:
    """A bare bool cannot be re-checked, so a Certificate must never be one."""
    cert = acyclicity_certificate(LINEAR)
    assert isinstance(cert, Certificate)
    assert isinstance(cert.witness, tuple)
    assert cert.witness, "a holding certificate with an empty witness proves nothing"


# ---------------------------------------------------------------- T1 acyclicity


def test_t1_acyclic_graph_yields_a_valid_topological_order() -> None:
    cert = acyclicity_certificate(LINEAR)
    assert cert.holds
    assert verify_topological_order(LINEAR, cert.witness)


def test_t1_self_ingestion_is_detected_and_the_cycle_is_the_witness() -> None:
    """The real failure mode: a goal's output becoming its own input."""
    cert = acyclicity_certificate(SELF_INGESTING)
    assert not cert.holds
    assert len(cert.witness) >= 2
    assert "cycle" in cert.detail


def test_t1_DISCRIMINATING_checker_rejects_a_wrong_order() -> None:
    """The test that gives the checker meaning.

    A checker that returns True unconditionally passes every other T1 test. Only this one
    fails it. Reversing a valid order must be rejected.
    """
    cert = acyclicity_certificate(LINEAR)
    assert verify_topological_order(LINEAR, cert.witness)
    assert not verify_topological_order(LINEAR, tuple(reversed(cert.witness)))


def test_t1_DISCRIMINATING_partial_order_is_not_a_proof() -> None:
    """An order omitting a node says nothing about edges touching it."""
    cert = acyclicity_certificate(LINEAR)
    truncated = cert.witness[:-1]
    assert not verify_topological_order(LINEAR, truncated)


def test_t1_empty_graph_is_vacuously_acyclic() -> None:
    cert = acyclicity_certificate(())
    assert cert.holds
    assert verify_topological_order((), cert.witness)


# ------------------------------------------------------------------ T2 coverage


def test_t2_orphaned_goal_is_reported_as_the_witness() -> None:
    goals = ("goal:g1", "goal:g2", "goal:orphan")
    cert = coverage_certificate(goals, LINEAR)
    assert not cert.holds
    assert cert.witness == ("goal:orphan",)
    assert "2/3" in cert.detail


def test_t2_full_provenance_holds_with_an_empty_witness() -> None:
    cert = coverage_certificate(("goal:g1", "goal:g2"), LINEAR)
    assert cert.holds
    assert cert.witness == ()


def test_t2_DISCRIMINATING_checker_rejects_an_under_reporting_producer() -> None:
    """A producer that hides an orphan must not pass verification."""
    goals = ("goal:g1", "goal:g2", "goal:orphan")
    assert verify_coverage(goals, LINEAR, ("goal:orphan",))
    assert not verify_coverage(goals, LINEAR, ())  # orphan concealed


def test_t2_DISCRIMINATING_checker_rejects_an_over_reporting_producer() -> None:
    """Claiming a covered goal is an orphan is equally wrong."""
    goals = ("goal:g1", "goal:g2")
    assert not verify_coverage(goals, LINEAR, ("goal:g1",))


# ------------------------------------------------------- T3 order-independence


def test_t3_digest_is_invariant_under_input_permutation() -> None:
    """The refactor must read a trace batch as a SET, not a sequence."""
    shuffled = (LINEAR[2], LINEAR[0], LINEAR[1])
    assert canonical_digest(LINEAR) == canonical_digest(shuffled)


def test_t3_duplicate_edges_do_not_change_the_graph() -> None:
    assert canonical_digest(LINEAR) == canonical_digest((*LINEAR, LINEAR[0]))


def test_t3_DISCRIMINATING_a_different_edge_set_differs() -> None:
    """Without this, a constant digest would satisfy every other T3 test."""
    assert canonical_digest(LINEAR) != canonical_digest(SELF_INGESTING)


@pytest.mark.parametrize(
    "edges",
    [(), LINEAR, SELF_INGESTING],
    ids=["empty", "acyclic", "cyclic"],
)
def test_t3_digest_is_total_and_stable(edges) -> None:
    assert canonical_digest(edges) == canonical_digest(edges)
    assert len(canonical_digest(edges)) == 64
