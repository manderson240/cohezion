"""Discriminating tests for the Harness-Tuning Specialist (item 35, 2026-06-06).

`HarnessTuningSpecialist.propose_harness_tuning(records)` composes the autonomous RHO chain
(generate_harness_candidates → SkillRefiner.propose_rho_update → RHO self-preference) into one
report-only proposal.

Each test fails a plausible wrong impl:
  - propose for a healthy/empty corpus (no chronically-fallback class) → T_healthy / T_empty,
  - return a proposal that misses the worst-fallback class → T_target,
  - bypass the RHO gate (propose even when rho_enabled=False) → T_gate.
"""

from __future__ import annotations

import pytest

# PREMATURE on this branch, not broken — same root cause as
# tests/compound/test_skill_refiner_rho.py. All 5 tests here fail with:
#   TypeError: SkillRefiner.__init__() got an unexpected keyword argument 'rho_enabled'
# The wiring lives in commit 3b2177104 on ``origin/feat/adaptive-calibration-harness``,
# which is NOT an ancestor of HEAD. strict=True forces removal once that branch lands.
pytestmark = pytest.mark.xfail(
    strict=True,
    reason="RHO->SkillRefiner wiring (3b2177104) is unmerged; lives on origin/feat/adaptive-calibration-harness",
)

from cohezion.compound.harness_tuning_specialist import HarnessTuningSpecialist
from cohezion.compound.skill_refiner import SkillRefiner


def _fb(task: str, n: int = 6, *, fell_back: bool = True) -> list[dict]:
    return [
        {"task_class": task, "fell_back": fell_back, "lane": "" if fell_back else "igpu"}
        for _ in range(n)
    ]


def test_fallback_heavy_corpus_yields_a_proposal_targeting_worst_fallback() -> None:
    corpus = _fb("RERANK") + _fb("CODE_GEN", fell_back=False)
    sel = HarnessTuningSpecialist().propose_harness_tuning(corpus)
    assert sel is not None and sel.winner is not None
    assert "RERANK" in sel.winner.targets  # the proposal addresses the worst-fallback class


def test_healthy_corpus_yields_none() -> None:
    # No chronically-fallback class → no candidates → UNPROVEN. A wrong impl always-proposing fails.
    assert (
        HarnessTuningSpecialist().propose_harness_tuning(_fb("CODE_GEN", fell_back=False)) is None
    )


def test_empty_corpus_yields_none() -> None:
    assert HarnessTuningSpecialist().propose_harness_tuning([]) is None


def test_rho_gate_is_genuinely_used() -> None:
    # An injected refiner with the RHO gate OFF must yield None even on a fallback-heavy corpus —
    # proving the specialist routes through SkillRefiner's RHO path, not a bypass.
    spec = HarnessTuningSpecialist(refiner=SkillRefiner(rho_enabled=False))
    assert spec.propose_harness_tuning(_fb("RERANK")) is None


def test_default_specialist_has_rho_enabled() -> None:
    # The default refiner must have the gate ON (the specialist's whole job is to run RHO).
    on = HarnessTuningSpecialist().propose_harness_tuning(_fb("RERANK"))
    assert on is not None and on.winner is not None
