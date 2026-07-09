"""Harness benefit tracking — disentangles harness updating from harness benefit.

Based on: "Harness Updating Is Not Harness Benefit: Disentangling Evolution
Capabilities in Self-Evolving LLM Agents" (arXiv:2605.30621).

Key insight: generating a useful skill update (harness updating) is nearly
model-tier-agnostic, but *using* that update to improve task outcomes
(harness benefit) varies dramatically — mid-tier models gain most, weak models
fail to activate or follow updated harnesses, and strong models show
diminishing returns.

This module separates measurement of the two capabilities so that the compound
loop can distinguish "we refined a skill" from "the refinement helped".

Failure modes the tracker detects (from the paper):
  - Zero-invocation: refined skill never called after update → benefit = None
  - Negative benefit: post score lower than pre (harmful refinement)
  - Low invocation: refined skill called but performance unchanged (adherence gap)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class HarnessBenefitRecord:
    """Per-skill record tracking pre/post refinement performance.

    Attributes
    ----------
    skill_name:
        Name of the PRIME skill that was refined.
    pre_refinement_score:
        Quality score measured BEFORE the skill was updated (None if unknown).
    post_refinement_score:
        Quality score measured AFTER the skill was updated (None until
        a post-refinement execution is recorded).
    invocation_count:
        How many times the *updated* skill was actually invoked after
        refinement.  Zero = harness updating happened, but harness benefit
        is unmeasurable (the common failure mode the paper identifies).
    instruction_length_delta:
        Increase in skill instruction character count after refinement.
        High values correlate with poor adherence in weak-tier models.
    model_tier:
        The routing tier that ran the post-refinement execution
        (``"npu"`` / ``"igpu"`` / ``"cpu"`` / ``"cloud"``).
    """

    skill_name: str
    pre_refinement_score: float | None = None
    post_refinement_score: float | None = None
    invocation_count: int = 0
    instruction_length_delta: int = 0
    model_tier: str = "unknown"

    @property
    def benefit_score(self) -> float | None:
        """Benefit = post − pre.  Returns None if either score is unknown."""
        if self.pre_refinement_score is None or self.post_refinement_score is None:
            return None
        return self.post_refinement_score - self.pre_refinement_score

    @property
    def was_invoked(self) -> bool:
        """True if the updated harness was actually used at least once."""
        return self.invocation_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "pre_refinement_score": self.pre_refinement_score,
            "post_refinement_score": self.post_refinement_score,
            "benefit_score": self.benefit_score,
            "invocation_count": self.invocation_count,
            "was_invoked": self.was_invoked,
            "instruction_length_delta": self.instruction_length_delta,
            "model_tier": self.model_tier,
        }


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------


class HarnessBenefitTracker:
    """Tracks harness-benefit metrics across the compound loop lifecycle.

    Usage in the SkillRefiner loop:

    .. code-block:: python

        tracker = HarnessBenefitTracker()

        # Before refinement — record baseline
        tracker.record_pre_execution("my-skill", quality_score=0.72)

        # Skill is refined here...

        # After refinement — record improvement
        tracker.record_post_execution(
            "my-skill",
            quality_score=0.85,
            model_tier="igpu",
            instruction_length_delta=240,
        )

        tracker.record_invocation("my-skill")
        benefit = tracker.get_record("my-skill").benefit_score  # 0.13
    """

    def __init__(self) -> None:
        self._records: dict[str, HarnessBenefitRecord] = {}

    def record_pre_execution(self, skill_name: str, quality_score: float) -> None:
        """Record the baseline quality score before a skill refinement.

        Creates the record if it does not yet exist.
        """
        if skill_name not in self._records:
            self._records[skill_name] = HarnessBenefitRecord(skill_name=skill_name)
        self._records[skill_name].pre_refinement_score = quality_score

    def record_post_execution(
        self,
        skill_name: str,
        quality_score: float,
        model_tier: str = "unknown",
        instruction_length_delta: int = 0,
    ) -> None:
        """Record the quality score after a skill refinement was applied.

        Sets ``post_refinement_score`` and metadata on the record.
        Creates the record if it does not yet exist (pre-score stays None).
        """
        if skill_name not in self._records:
            self._records[skill_name] = HarnessBenefitRecord(skill_name=skill_name)
        rec = self._records[skill_name]
        rec.post_refinement_score = quality_score
        rec.model_tier = model_tier
        rec.instruction_length_delta = instruction_length_delta

    def record_invocation(self, skill_name: str) -> None:
        """Increment the invocation count for a skill after refinement.

        Call this every time the *updated* skill is actually used.
        """
        if skill_name not in self._records:
            self._records[skill_name] = HarnessBenefitRecord(skill_name=skill_name)
        self._records[skill_name].invocation_count += 1

    def get_record(self, skill_name: str) -> HarnessBenefitRecord | None:
        """Return the benefit record for a skill, or None if not tracked."""
        return self._records.get(skill_name)

    def all_records(self) -> list[HarnessBenefitRecord]:
        """Return all tracked records."""
        return list(self._records.values())

    def zero_invocation_skills(self) -> list[str]:
        """Skills whose updated harness was never invoked (key failure mode).

        These skills were *updated* (harness updating happened) but never
        *used* after the update (harness benefit cannot be measured).
        """
        return [
            name
            for name, rec in self._records.items()
            if rec.pre_refinement_score is not None and not rec.was_invoked
        ]

    def harmful_refinements(self) -> list[str]:
        """Skills where post-refinement score dropped below pre-refinement.

        Negative benefit — the refinement made the skill worse.
        """
        return [
            name
            for name, rec in self._records.items()
            if rec.benefit_score is not None and rec.benefit_score < 0.0
        ]

    def summary(self) -> dict[str, Any]:
        """Aggregate summary for logging / observability."""
        records = self.all_records()
        measured = [r for r in records if r.benefit_score is not None]
        return {
            "total_tracked": len(records),
            "with_measured_benefit": len(measured),
            "zero_invocation": len(self.zero_invocation_skills()),
            "harmful_refinements": len(self.harmful_refinements()),
            "mean_benefit": (
                sum(r.benefit_score for r in measured) / len(measured)  # type: ignore[arg-type]
                if measured
                else None
            ),
        }
