"""RED tests for the HarnessPaperLane (Lane 2).

Contracts:
- HarnessPaperLane.run() reads papers from arXiv + the model-scout
  candidate list, and runs the 6-step research-paper-integration ritual.
- For each paper, a 4-verifier gate is run:
  1. card-fit (does the paper's claim violate any registered model's
     known weaknesses?)
  2. cross-model (re-summarize with a different model family; agreement
     on the core claim required)
  3. falsifiability (every "X improves Y" claim must come with an
     experiment that can return False)
  4. recipe-fit (0.0-1.0 score; below 0.6 = discard)
- A synthesis only moves to `verified` if all 4 verifiers pass.
- Cloud-escalation budget is enforced (≤5/run).
- Disagreement on the cross-model verifier marks the synthesis `disputed`
  and never auto-promotes it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.researcher.daily_researcher import DailyResearcher
from cohezion.researcher.lanes.harness_paper import HarnessPaperLane


def _paper_dict(slug: str = "test-paper") -> dict:
    return {
        "slug": slug,
        "title": "A Test Paper",
        "abstract": (
            "We propose a new self-evolving harness pattern. "
            "Strengths: better skill refinement. "
            "Weaknesses: requires mid-tier consumer."
        ),
        "arxiv_id": "2402.00000",
    }


# ── Cloud budget enforcement ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_harness_paper_6th_escalation_returns_exhausted():
    """The lane refuses the 6th cloud escalation with CLOUD_BUDGET_EXHAUSTED."""
    researcher = DailyResearcher()
    researcher._cloud_escalations_today = 5  # already at cap
    lane = HarnessPaperLane(researcher)
    result = await lane._attempt_cloud_escalation("paper:test")
    assert result.status == "CLOUD_BUDGET_EXHAUSTED"


@pytest.mark.asyncio
async def test_harness_paper_under_budget_returns_escalated():
    """Within budget, the escalation counter increments and the result is ESCALATED."""
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    assert researcher._cloud_escalations_today == 0
    result = await lane._attempt_cloud_escalation("paper:test")
    assert result.status == "ESCALATED"
    assert researcher._cloud_escalations_today == 1


# ── Verifier disagreement → disputed ────────────────────────────────────────


@pytest.mark.asyncio
async def test_harness_paper_cross_model_disagreement_marks_disputed():
    """When the cross-model verifier returns a different core claim, the
    synthesis is marked 'disputed' and never auto-promoted."""
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    paper = _paper_dict()

    # First model says "the harness is great for skill refinement"
    # Second model (deliberately different family) says "the harness is
    # mostly noise" — disagreement on the core claim
    with patch.object(lane, "_summarize_with_model", new=AsyncMock(side_effect=[
        "the harness is great for skill refinement",
        "the harness is mostly noise; not a real improvement",
    ])):
        verdict = await lane._verifiers_cross_model(paper)
    assert verdict.status == "disputed"
    assert verdict.promoted is False


@pytest.mark.asyncio
async def test_harness_paper_cross_model_agreement_passes():
    """Two models agreeing on the core claim → verifier passes."""
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    paper = _paper_dict()
    claim = "the harness improves skill refinement by 12% on ARC-AGI"
    with patch.object(lane, "_summarize_with_model", new=AsyncMock(return_value=claim)):
        verdict = await lane._verifiers_cross_model(paper)
    assert verdict.status == "agreed"


# ── Falsifiability verifier ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_harness_paper_non_falsifiable_claim_discarded():
    """A claim without an experiment that can return False is discarded."""
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    paper = {
        **_paper_dict(),
        "claims": [
            {"text": "X is better than Y", "experiment": None},  # no falsifier
        ],
    }
    verdict = await lane._verifiers_falsifiability(paper)
    assert verdict.status == "discarded"
    assert "falsifi" in verdict.reason.lower()


@pytest.mark.asyncio
async def test_harness_paper_falsifiable_claim_passes():
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    paper = {
        **_paper_dict(),
        "claims": [
            {"text": "X beats Y on metric M", "experiment": "scripts/exp_x.py --task=M"},
        ],
    }
    verdict = await lane._verifiers_falsifiability(paper)
    assert verdict.status == "passed"


# ── Card-fit verifier ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_harness_paper_card_violation_discarded():
    """If the paper recommends a model for a task it has a card-listed
    weakness for, the synthesis is discarded."""
    researcher = DailyResearcher()
    lane = HarnessPaperLane(researcher)
    # The paper says "use phi4 for platform-internal synthesis"
    # but phi4's default profile lists "hallucinates on platform-internal
    # terms" as a known failure mode → violation
    paper = {
        **_paper_dict(),
        "recommendation": {
            "model_id": "phi4:latest",
            "task": "platform-internal synthesis",
        },
    }
    verdict = await lane._verifiers_card_fit(paper)
    assert verdict.status == "discarded"
    assert "violation" in verdict.reason.lower() or "phi4" in verdict.reason.lower()
