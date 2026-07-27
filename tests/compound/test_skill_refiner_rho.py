"""Discriminating tests for the RHO→SkillRefiner wiring (item 27, 2026-06-06).

Wires the item-22 RHO selector into SkillRefiner behind an OFF-by-default flag. Report-only
(proposes a harness update, never writes). The falsifiable check (item 27): flag OFF → no RHO
behavior at all (refine() is untouched, so byte-identical by construction); flag ON + a synthetic
fallback coreset → the RHO-selected update surfaces; empty corpus → nothing either way (UNPROVEN).

Each test fails a plausible wrong impl:
  - rho_enabled defaulting True / proposing when off — T_default,
  - a flag-on path that ignores the corpus and always proposes — T_empty,
  - a flag-on path that picks the wrong candidate (ignores the coreset) — T_on.
"""

from __future__ import annotations

import pytest

from cohezion.compound.skill_refiner import SkillRefiner
from cohezion.models.rho_selector import HarnessCandidate


# These tests are PREMATURE on this branch, not broken.
#
# The implementation they exercise — the ``rho_enabled`` kwarg on ``SkillRefiner`` —
# lives in commit 3b2177104 on ``origin/feat/adaptive-calibration-harness``, which has
# NEVER been merged here (verified: ``git merge-base --is-ancestor 3b2177104 HEAD``
# fails). The tests reached this branch separately via #242/#251, without their
# implementation. Nothing was lost or deleted; the RHO *selector* itself
# (``harness_tuning_specialist.py``) IS present — only the SkillRefiner flag wiring is
# absent, so every test here fails with:
#   TypeError: SkillRefiner.__init__() got an unexpected keyword argument 'rho_enabled'
#
# strict=True is deliberate: when that branch lands, these turn XPASS and FAIL the
# suite, forcing this marker to be removed rather than silently masking real coverage.
pytestmark = pytest.mark.xfail(
    strict=True,
    reason="RHO->SkillRefiner wiring (3b2177104) is unmerged; lives on origin/feat/adaptive-calibration-harness",
)


def _fallback_corpus(task: str, n: int = 6) -> list[dict]:
    return [
        {"task_class": task, "chosen_model": None, "fell_back": True, "lane": ""} for _ in range(n)
    ]


_A = HarnessCandidate("A", "irrelevant", frozenset({"CODE_GEN"}))
_B = HarnessCandidate("B", "recruit RERANK specialist", frozenset({"RERANK"}))


def test_rho_disabled_by_default_proposes_nothing() -> None:
    r = SkillRefiner()
    assert r.rho_enabled is False  # must default OFF (no behavior change)
    # Even with a corpus that WOULD yield a selection, the OFF flag proposes nothing.
    assert r.propose_rho_update(_fallback_corpus("RERANK"), [_A, _B]) is None


def test_rho_enabled_surfaces_the_selected_update() -> None:
    r = SkillRefiner(rho_enabled=True)
    sel = r.propose_rho_update(_fallback_corpus("RERANK"), [_A, _B])
    assert sel is not None
    assert sel.winner is not None
    assert sel.winner.candidate_id == "B"  # the candidate covering the fallback coreset
    assert "RERANK" in sel.coreset


def test_rho_enabled_empty_corpus_proposes_nothing() -> None:
    r = SkillRefiner(rho_enabled=True)
    # No corpus → no coreset → RHO is UNPROVEN → no proposal (not a fabricated one).
    assert r.propose_rho_update([], [_A, _B]) is None


def test_refine_signature_unchanged_by_the_flag() -> None:
    # Regression guard: the file-writing refine() path must be untouched (the flag adds a NEW
    # method, it does not thread through refine). A wrong impl that altered refine's params fails.
    import inspect

    params = list(inspect.signature(SkillRefiner.refine).parameters)
    assert params == [
        "self",
        "skill_name",
        "operation_type",
        "execution_result",
        "patterns_extracted",
    ]
