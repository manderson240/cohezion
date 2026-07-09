"""RED tests for the VerifyEvolveLane (Lane 4).

Contracts:
- VerifyEvolveLane runs the 4 verifier passes (card-fit, cross-model,
  falsifiability, recipe-fit) on yesterday's pending syntheses.
- A synthesis only moves to `verified` if all 4 verifiers pass.
- The experiment budget is enforced: ≤2 experiments / run. The 3rd
  returns EXPERIMENT_BUDGET_EXHAUSTED.
- The recipe-fit score threshold is 0.6; below that, discard with
  reason "recipe_misalignment".
- The lane produces a DryRunReport with verifications list (the
  per-synthesis verdicts).
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.researcher.daily_researcher import DailyResearcher
from cohezion.researcher.lanes.verify_evolve import VerifyEvolveLane


def _synthesis(slug: str, recipe_fit: float = 0.8) -> dict:
    return {
        "slug": slug,
        "title": f"Synthesis {slug}",
        "body": "body",
        "model_card_profile_id": slug,
        "recipe_fit_score": recipe_fit,
        "created_at": datetime(2026, 6, 3, tzinfo=None).isoformat(),
    }


# ── Recipe-fit threshold ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recipe_fit_below_threshold_discards_synthesis():
    """A synthesis with recipe_fit_score < 0.6 is discarded."""
    researcher = DailyResearcher()
    lane = VerifyEvolveLane(researcher)
    with patch.object(
        lane,
        "_read_pending_syntheses",
        new=AsyncMock(
            return_value=[
                _synthesis("low", recipe_fit=0.3),
            ]
        ),
    ):
        report = await lane.run(dry_run=False)
    assert any(v["slug"] == "low" and v["verdict"] == "discarded" for v in report.verifications)


@pytest.mark.asyncio
async def test_recipe_fit_above_threshold_passes():
    researcher = DailyResearcher()
    lane = VerifyEvolveLane(researcher)
    with (
        patch.object(
            lane,
            "_read_pending_syntheses",
            new=AsyncMock(
                return_value=[
                    _synthesis("good", recipe_fit=0.9),
                ]
            ),
        ),
        patch.object(lane, "_run_card_fit", new=AsyncMock(return_value="passed")),
        patch.object(lane, "_run_cross_model", new=AsyncMock(return_value="agreed")),
        patch.object(lane, "_run_falsifiability", new=AsyncMock(return_value="passed")),
    ):
        report = await lane.run(dry_run=False)
    assert any(v["slug"] == "good" and v["verdict"] == "verified" for v in report.verifications)


# ── Experiment budget ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_experiment_budget_caps_at_two():
    """The 3rd experiment is refused with EXPERIMENT_BUDGET_EXHAUSTED."""
    researcher = DailyResearcher()
    researcher._experiments_today = 2
    lane = VerifyEvolveLane(researcher)
    result = await lane._run_one_experiment("exp-3")
    assert result.status == "EXPERIMENT_BUDGET_EXHAUSTED"


@pytest.mark.asyncio
async def test_experiment_under_budget_queues():
    researcher = DailyResearcher()
    researcher._experiments_today = 0
    lane = VerifyEvolveLane(researcher)
    result = await lane._run_one_experiment("exp-1")
    assert result.status == "EXPERIMENT_QUEUED"
    assert researcher._experiments_today == 1


# ── Quality override: a verified-mandatory experiment may bump ─────────────


@pytest.mark.asyncio
async def test_quality_override_queues_mandatory_experiment_even_at_cap():
    """If the lane is at the cap but a synthesis is verified-mandatory,
    the experiment still queues (the budget is a floor, not a ceiling)."""
    researcher = DailyResearcher()
    researcher._experiments_today = 2
    lane = VerifyEvolveLane(researcher)
    result = await lane._run_one_experiment("exp-mandatory", mandatory=True)
    assert result.status == "EXPERIMENT_QUEUED"
    # The override bumps the counter
    assert researcher._experiments_today == 3
