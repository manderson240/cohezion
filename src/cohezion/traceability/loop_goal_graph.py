"""Derivation graph over traces and goals, with independently checkable proofs.

The trace -> goal pipeline (``cohezion.flume.loop_goal_refactor_engine``) synthesizes
goals from ``event_log`` traces and then EXECUTES them, emitting further records. That
closes a cycle in principle: a goal's own output can become the trace a later refactor
reads. This has already been observed twice in practice -- the pipeline synthesized goals
from the research daemon's arXiv reading queue, and read 3,405 git-commit ``JOURNEY_STEP``
rows as live failures. Both were caught by a human looking at output, not by a check.

This module is that check. It is deliberately small and depends only on the standard
library (``graphlib``); it holds no I/O and no SurrealDB knowledge.

## What "proof" means here

Not a Coq development. Each property is decided by a total procedure that emits a
**witness**, and every witness has a **checker that shares no code with its producer** and
is cheaper than production:

| theorem | witness (holds) | witness (fails) | checker | cost |
|---|---|---|---|---|
| T1 acyclicity | topological order | the cycle | re-derive ranks, assert rank[u] < rank[v] per edge | O(V+E) |
| T2 coverage | empty orphan set | the orphans | assert each claimed orphan truly has no in-edge | O(V+E) |
| T3 order-independence | canonical digest | the differing digests | recompute from a permuted input | O(E log E) |

That asymmetry -- expensive construction, cheap independent verification -- is what makes
these proofs rather than tests. ``verify_topological_order`` must never call
``graphlib``; if it did, a green result would only prove the same code ran twice.

T1 subsumes termination: on a finite DAG a topological rank IS a well-founded measure that
strictly decreases along every edge, so an acyclic derivation graph cannot regress forever.
They are one theorem, not two.
"""

from __future__ import annotations

import graphlib
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass


__all__ = [
    "Certificate",
    "Edge",
    "acyclicity_certificate",
    "canonical_digest",
    "coverage_certificate",
    "verify_coverage",
    "verify_topological_order",
]

# A directed derivation edge: src produced / justified dst.
# Nodes are opaque strings, conventionally "trace:<id>" or "goal:<id>".
Edge = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Certificate:
    """The outcome of deciding one property, carrying the evidence either way.

    ``holds`` is the verdict; ``witness`` is what an independent checker consumes.
    A certificate is never a bare bool -- a bool cannot be re-checked.
    """

    theorem: str
    holds: bool
    witness: tuple[str, ...]
    detail: str = ""


def _nodes(edges: Iterable[Edge]) -> set[str]:
    out: set[str] = set()
    for src, dst in edges:
        out.add(src)
        out.add(dst)
    return out


# --------------------------------------------------------------- T1 acyclicity


def acyclicity_certificate(edges: Iterable[Edge]) -> Certificate:
    """Decide whether the derivation graph is acyclic (no self-ingestion).

    Producer side. On success the witness is a topological order; on failure it is the
    cycle itself, taken from ``graphlib.CycleError``.
    """
    edges = tuple(edges)
    # graphlib maps node -> its predecessors.
    preds: dict[str, set[str]] = {n: set() for n in _nodes(edges)}
    for src, dst in edges:
        preds[dst].add(src)
    try:
        order = tuple(graphlib.TopologicalSorter(preds).static_order())
    except graphlib.CycleError as exc:
        cycle = tuple(str(n) for n in exc.args[1])
        return Certificate(
            theorem="T1-acyclicity",
            holds=False,
            witness=cycle,
            detail=f"derivation cycle of length {len(cycle) - 1}: a goal's output feeds its own input",
        )
    return Certificate(
        theorem="T1-acyclicity",
        holds=True,
        witness=order,
        detail=f"topological order over {len(order)} nodes, {len(edges)} edges",
    )


def verify_topological_order(edges: Iterable[Edge], order: Iterable[str]) -> bool:
    """INDEPENDENT checker for T1. Must not import or call graphlib.

    Assigns each node its position in ``order`` and asserts every edge points forward.
    An order that omits a node fails: a partial order is not a proof about the whole graph.
    """
    rank = {node: i for i, node in enumerate(order)}
    for src, dst in edges:
        if src not in rank or dst not in rank:
            return False
        if rank[src] >= rank[dst]:
            return False
    return True


# ------------------------------------------------------------------ T2 coverage


def coverage_certificate(goal_ids: Iterable[str], edges: Iterable[Edge]) -> Certificate:
    """Decide whether every goal has provenance -- at least one incoming edge.

    An orphaned goal is one nothing derived: it cannot be audited back to the trace that
    justified it. The witness is the orphan set, empty exactly when the property holds.
    """
    goal_ids = tuple(goal_ids)
    has_inbound = {dst for _, dst in edges}
    orphans = tuple(sorted(g for g in goal_ids if g not in has_inbound))
    total = len(goal_ids)
    covered = total - len(orphans)
    pct = (covered / total * 100.0) if total else 100.0
    return Certificate(
        theorem="T2-coverage",
        holds=not orphans,
        witness=orphans,
        detail=f"{covered}/{total} goals carry provenance ({pct:.2f}%)",
    )


def verify_coverage(goal_ids: Iterable[str], edges: Iterable[Edge], orphans: Iterable[str]) -> bool:
    """INDEPENDENT checker for T2, built from the edge list, not from the producer.

    Confirms both directions: every claimed orphan really has no in-edge, and no goal
    outside the claimed set is an orphan. One direction alone is not a proof -- an empty
    orphan list would pass a check that only verified the claims it was given.
    """
    claimed = set(orphans)
    has_inbound = {dst for _, dst in edges}
    for g in claimed:
        if g in has_inbound:
            return False  # claimed orphan actually has provenance
    # ...and no real orphan went unreported.
    return not any(g not in has_inbound and g not in claimed for g in goal_ids)


# --------------------------------------------------------- T3 order-independence


def canonical_digest(edges: Iterable[Edge]) -> str:
    """Order-independent fingerprint of the edge SET.

    The refactor must read a trace batch as a set, not a sequence: the same events
    arriving in a different order must produce the same graph. Sorting before hashing is
    what makes this testable -- hashing the input order would make the digest trivially
    reproduce whatever it was given.
    """
    unique = sorted({tuple(e) for e in edges})
    payload = json.dumps(unique, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
