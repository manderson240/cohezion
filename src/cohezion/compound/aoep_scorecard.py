"""AOEP-v0 Scorecard — Always-On Evaluation Protocol (arXiv:2606.30306).

Measures Cohezion's existing systems against the 6 AOEP-v0 governance axes.
Produces an AOEPScore (0.0–1.0 per axis) and a list of gap axes (score < 0.5).

This is a MEASUREMENT tool — no state management, no SurrealDB writes, no LLM calls.
Run it before filling gaps to confirm what's missing; run it after to measure progress.

Design: each `score_*` method accepts an optional concrete system object and a set
of keyword-only probes that mock system state in tests. Production calls pass the
real objects; test calls can pass keyword overrides without constructing heavy objects.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_GAP_THRESHOLD = 0.5  # axes below this appear in AOEPScore.gaps


@dataclass
class AOEPScore:
    """AOEP-v0 governance coverage scores, one per axis."""

    authority: float = 0.0
    scope: float = 0.0
    mutability: float = 0.0
    provenance: float = 0.0
    recoverability: float = 0.0
    actionability: float = 0.0
    overall: float = 0.0
    gaps: list[str] = field(default_factory=list)


class AOEPScorecard:
    """Scores Cohezion's systems against the AOEP-v0 protocol.

    Usage::

        from cohezion.compound.aoep_scorecard import AOEPScorecard
        score = AOEPScorecard().run()
        print(score.gaps)  # axes with coverage < 0.5
    """

    # ── Axis scorers ─────────────────────────────────────────────────────────

    def score_authority(
        self,
        executor: Any = None,
        *,
        has_authority_gate: bool | None = None,
    ) -> float:
        """Authority: does any mechanism gate state-to-action propagation?

        1.0 = authority_tag field in ExecutionMetrics AND a gate in execute_task.
        0.5 = authority_tag field exists but no gate enforces it.
        0.0 = no mechanism (gap).
        """
        # Allow test override
        if has_authority_gate is not None:
            return 1.0 if has_authority_gate else 0.0

        try:
            from cohezion.compound.skill_refiner import ExecutionMetrics

            fields = {f.name for f in __import__("dataclasses").fields(ExecutionMetrics)}
            has_field = "authority_tag" in fields
        except Exception:
            has_field = False

        if not has_field:
            return 0.0

        # Check if execute_task reads authority_tag (basic wiring check)
        try:
            from cohezion.compound.executor import CompoundExecutor

            src = inspect.getsource(CompoundExecutor.execute_task)
            has_gate = "authority_tag" in src
        except Exception:
            has_gate = False

        return 1.0 if has_gate else 0.5

    def score_scope(
        self,
        semantic_cache: Any = None,
        *,
        has_scope_filter: bool | None = None,
    ) -> float:
        """Scope: is access-control enforced per-agent/task in the cache?

        1.0 = scope_filter param AND active per-entry metadata filtering.
        0.5 = scope_filter param exists (structural hook), filtering is additive.
        0.0 = no scope mechanism (gap).
        """
        if has_scope_filter is not None:
            return 0.5 if has_scope_filter else 0.0

        try:
            from cohezion.cache.semantic_cache import SemanticCache

            sig = inspect.signature(SemanticCache.get)
            return 0.5 if "scope_filter" in sig.parameters else 0.0
        except Exception:
            return 0.0

    def score_mutability(
        self,
        skill_refiner: Any = None,
        *,
        has_seesaw: bool | None = None,
    ) -> float:
        """Mutability: are immutability/decay contracts enforced on skill state?

        1.0 = seesaw gate + TTL/decay on revisable state.
        0.5 = seesaw gate exists (blocks PRIME negation) but no TTL.
        0.0 = no contract enforcement.
        """
        if has_seesaw is not None:
            return 0.5 if has_seesaw else 0.0

        try:
            from cohezion.compound.skill_refiner import SkillRefiner

            src = inspect.getsource(SkillRefiner.refine)
            return 0.5 if "_seesaw_check" in src else 0.0
        except Exception:
            return 0.0

    def score_provenance(
        self,
        journey_tracker: Any = None,
        *,
        has_source_field: bool | None = None,
    ) -> float:
        """Provenance: is the full transformation chain recorded?

        1.0 = TrajectoryPoint has source + transformation fields, both non-empty.
        0.5 = action field exists (tier_used, partial provenance).
        0.0 = no provenance mechanism.
        """
        if has_source_field is not None:
            return 1.0 if has_source_field else 0.0

        try:
            from cohezion.compound.journey_tracker import TrajectoryPoint

            fields = {f.name for f in __import__("dataclasses").fields(TrajectoryPoint)}
            if "action" in fields and "operation_type" in fields:
                return 0.5
            return 0.0
        except Exception:
            return 0.0

    def score_recoverability(
        self,
        skill_refiner: Any = None,
        *,
        state_file_exists: bool | None = None,
    ) -> float:
        """Recoverability: can we rollback to a known-good checkpoint?

        1.0 = SkillRefiner durable spine file present AND restore_state callable.
        0.5 = restore_state callable but no persisted state file found.
        0.0 = no recovery mechanism.
        """
        if state_file_exists is not None:
            return 1.0 if state_file_exists else 0.5

        try:
            from cohezion.compound.skill_refiner import SkillRefiner

            has_restore = callable(getattr(SkillRefiner, "restore_state", None))
        except Exception:
            return 0.0

        if not has_restore:
            return 0.0

        import pathlib

        state_path = pathlib.Path.home() / ".cohezion" / "skill_refiner_state.json"
        return 1.0 if state_path.exists() else 0.5

    def score_actionability(
        self,
        journey_tracker: Any = None,
        *,
        action_populated: bool | None = None,
    ) -> float:
        """Actionability: are state types classified (evidence/skill/commitment)?

        1.0 = TrajectoryPoint.action contains semantic state category per paper.
        0.5 = TrajectoryPoint.action populated with tier_used (structural, not semantic).
        0.0 = action field absent or always empty.
        """
        if action_populated is not None:
            return 0.5 if action_populated else 0.0

        # Check via journey_tracker's most recent trajectory points
        if journey_tracker is not None:
            try:
                points = journey_tracker.export_trajectories(last_n=5)
                if points and any(p.get("tier") or p.get("action") for p in points):
                    return 0.5
                return 0.0
            except Exception:
                pass

        # Structural check: does TrajectoryPoint have an action field with a default?
        try:
            from cohezion.compound.journey_tracker import TrajectoryPoint

            fields_map = {f.name: f for f in __import__("dataclasses").fields(TrajectoryPoint)}
            if "action" in fields_map:
                return 0.5
            return 0.0
        except Exception:
            return 0.0

    # ── Composite runner ──────────────────────────────────────────────────────

    def run(
        self,
        executor: Any = None,
        skill_refiner: Any = None,
        journey_tracker: Any = None,
        semantic_cache: Any = None,
    ) -> AOEPScore:
        """Run all 6 scorers and return an AOEPScore with a gaps list.

        All arguments are optional — pass real objects for live scoring or omit for
        structural introspection (the scorers fall back to inspecting module imports).
        """
        axes = {
            "authority": self.score_authority(executor),
            "scope": self.score_scope(semantic_cache),
            "mutability": self.score_mutability(skill_refiner),
            "provenance": self.score_provenance(journey_tracker),
            "recoverability": self.score_recoverability(skill_refiner),
            "actionability": self.score_actionability(journey_tracker),
        }
        overall = sum(axes.values()) / len(axes)
        gaps = [axis for axis, score in axes.items() if score < _GAP_THRESHOLD]
        return AOEPScore(**axes, overall=overall, gaps=gaps)
