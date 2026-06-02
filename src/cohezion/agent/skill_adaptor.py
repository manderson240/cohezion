"""SkillAdaptor — training-free step-level skill adaptation with explicit failure attribution.

Adoption of "SkillAdaptor: Self-Adapting Skills for LLM Agents from Trajectories"
(arXiv 2606.01311, Yu et al., Zhejiang U / Ant Group) onto cohezion's recursive ExecutionTrace.

The paper's thesis: existing skill-adaptation pipelines update from *full trajectories* or
session-level feedback, so failure attribution is coarse and revisions are unstable / overly
broad. SkillAdaptor instead does **step-level** attribution: given a failed trajectory it (1)
finds the *first actionable fault step*, (2) links responsibility to a candidate skill, and (3)
applies a *targeted* update under an *explicit acceptance check*, with the backbone frozen.

Cohezion already has the substrate this needs — the recursive ``ExecutionTrace`` (this session)
records ``tool_calls`` (each a skill invocation with an ``error`` field) across a nested
``walk()`` order, and the compound loop's RetrospectionEngine→SkillRefiner does the *coarse*,
trajectory-level adaptation the paper critiques. This module is the missing fine-grained layer:

  * ``attribute_fault(trace)`` — the first actionable fault step, in execution order, linked to
    the faulting skill (the tool name). The fine-grained "Diagnose" the loop lacked.
  * ``propose_targeted_update(...)`` — a revision scoped to *that one skill* (never broad).
  * ``AcceptanceCheck`` — the explicit gate; pluggable so it can be a QuadratureNexus consensus
    or a test. An accepted/rejected update is a corroboration/contradiction in a
    ``GroundTruthHierarchy`` — composing with the trust layer.

Training-free and backbone-frozen: no weights change; only the skill's textual guidance is
revised, and only when the acceptance check passes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


__all__ = [
    "AcceptanceCheck",
    "FaultAttribution",
    "SkillUpdate",
    "adapt_skill",
    "attribute_fault",
    "mask_volatile",
]

# Volatile tokens (hex addrs, paths, numbers, quoted literals) that vary run-to-run for the SAME
# fault mode. Masking them to '#' yields a stable string so a recurring fault corroborates ONE guard
# instead of creating a fresh trust=0.5 fact each time (which would never cross the injection floor).
# This is the SINGLE source of masking shared with error_loop.error_signature, so the livelock ledger
# key and the trust-store guard key agree — both halves of the loop dedupe a fault to the same mode.
_VOLATILE = re.compile(r"0x[0-9a-fA-F]+|/[^\s'\"]+|\b\d+\.?\d*\b|'[^']*'|\"[^\"]*\"")


def mask_volatile(text: str) -> str:
    """Replace volatile tokens (hex, paths, numbers, quoted literals) with '#'."""
    return _VOLATILE.sub("#", text)


def _tool_error(tc: object) -> str | None:
    """Extract an error string from a ToolCall-like object (``.error`` or ``.result['error']``)."""
    err = getattr(tc, "error", None)
    if err:
        return str(err)
    result = getattr(tc, "result", None)
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])
    return None


@dataclass(frozen=True)
class FaultAttribution:
    """The first actionable fault step, linked to the responsible skill."""

    skill: str  # the faulting skill (tool name)
    reason: str  # the error that made this the fault step
    task_id: str  # which (sub)task the fault occurred in
    depth: int  # recursion depth of that task (0 = top level)
    tool_index: int  # position of the faulting call within its node's tool_calls

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "reason": self.reason,
            "task_id": self.task_id,
            "depth": self.depth,
            "tool_index": self.tool_index,
        }


@dataclass(frozen=True)
class SkillUpdate:
    """A targeted, training-free revision scoped to exactly one skill."""

    skill: str
    revision: str  # the added guidance / guard
    scope: str = "targeted"  # never "broad" — the paper's stability lever
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "revision": self.revision,
            "scope": self.scope,
            "rationale": self.rationale,
        }


def attribute_fault(trace: object) -> FaultAttribution | None:
    """Find the first actionable fault step across the recursive trace, in execution order.

    Walks the trace tree pre-order (``walk()`` — parent before children, approximating execution
    order) and, within each node, scans ``tool_calls`` in order. Returns the first call carrying
    an error, attributed to its skill (tool name). Returns ``None`` if no fault is found (a clean
    trajectory needs no adaptation) — never fabricates an attribution.
    """
    nodes = trace.walk() if hasattr(trace, "walk") else [trace]
    for node in nodes:
        for i, tc in enumerate(getattr(node, "tool_calls", []) or []):
            err = _tool_error(tc)
            if err:
                return FaultAttribution(
                    skill=getattr(tc, "tool_name", "<unknown>"),
                    reason=err,
                    task_id=getattr(node, "task_id", "<unknown>"),
                    depth=getattr(node, "depth", 0),
                    tool_index=i,
                )
    return None


def propose_targeted_update(attribution: FaultAttribution) -> SkillUpdate:
    """Propose a revision scoped to the faulting skill only (targeted, not broad)."""
    return SkillUpdate(
        skill=attribution.skill,
        revision=(
            f"Before invoking '{attribution.skill}', guard against: {attribution.reason}. "
            f"Validate inputs/preconditions for this failure mode and handle it explicitly."
        ),
        scope="targeted",
        rationale=f"first actionable fault at task={attribution.task_id} depth={attribution.depth}",
    )


class AcceptanceCheck:
    """Explicit acceptance gate for a proposed update (the paper's stability guarantee).

    Default checks keep updates *targeted* (scoped to the faulting skill, non-empty). A custom
    ``predicate(update, attribution) -> bool`` can plug in stronger gates — e.g. a QuadratureNexus
    consensus deliberation or a re-run test — so an update is applied only when it clears them.
    """

    def __init__(self, predicate: Callable[[SkillUpdate, FaultAttribution], bool] | None = None):
        self._predicate = predicate

    def accepts(self, update: SkillUpdate, attribution: FaultAttribution) -> bool:
        if update.scope != "targeted":  # reject broad revisions (the paper's instability source)
            return False
        if update.skill != attribution.skill:  # must target the faulting skill, nothing else
            return False
        if not update.revision.strip():
            return False
        if self._predicate is not None:
            return bool(self._predicate(update, attribution))
        return True


def adapt_skill(
    trace: object,
    *,
    acceptance: AcceptanceCheck | None = None,
    trust: object | None = None,
) -> dict:
    """Run the full step-level adaptation: attribute → propose → accept → (optionally) record.

    Returns a structured result. Composition hooks:
      * ``acceptance``: pluggable gate (default targeted-only); pass one wrapping QuadratureNexus.
      * ``trust``: a GroundTruthHierarchy — an accepted update is corroborated as a fact, a
        rejected one recorded as a contradiction, so skill trust accrues across adaptations.
    """
    attribution = attribute_fault(trace)
    if attribution is None:
        return {"adapted": False, "reason": "no fault step (clean trajectory)", "attribution": None}
    update = propose_targeted_update(attribution)
    gate = acceptance or AcceptanceCheck()
    accepted = gate.accepts(update, attribution)
    if trust is not None and hasattr(trust, "add"):
        # Mask volatile tokens so recurrences of the SAME fault mode corroborate one guard (and cross
        # the injection floor) instead of piling up fresh trust=0.5 facts that are never read back.
        fact = f"skill '{update.skill}' guarded against: {mask_volatile(attribution.reason)}"
        trust.add(fact)  # entity-resolved; re-adoption corroborates
        # A rejected revision is a contradiction — but only record it if the trust object actually
        # supports corroborate(); a partial object (add but no corroborate) must not crash the loop.
        if not accepted and hasattr(trust, "corroborate"):
            trust.corroborate(fact, agree=False)
    return {
        "adapted": accepted,
        "attribution": attribution.to_dict(),
        "update": update.to_dict(),
        "reason": "accepted" if accepted else "rejected by acceptance check",
    }
