"""Regression tests for Anthropic per-model pricing constants.

Both pricing tables had drifted out of date, in opposite directions, and both
are consumed live (cost_aware_router.py:1047, api_llm_executor.py:303):

  * ``APILLMExecutor.COSTS`` priced ``claude-opus-4-6`` at 15/75 -- 3x the real
    5/25 -- and had no entry at all for Opus 5, Opus 4.8, Sonnet 5 or Haiku 4.5,
    so those models reported **$0.00** for real spend.
  * ``SessionCostTracker.model_costs`` knew only retired claude-3-* models, so
    every current model fell through to the 0.015 default ($15/MTok): a 3x to
    15x overestimate that biased cost-aware routing against the cloud.

Rates verified 2026-08-29 against
https://platform.claude.com/docs/en/about-claude/pricing

These tests assert exact values on purpose. Constants expire like dependencies;
the point is that a silent revert or a stale copy fails loudly here.
"""

from __future__ import annotations

import pytest

from cohezion.cost_optimization.cost_tracker import SessionCostTracker
from cohezion.integrations.agentverse.api_llm_executor import APILLMExecutor


MTOK = 1_000_000

# Retired models the tracker keeps on purpose so historical records still price
# correctly. They are deliberately absent from APILLMExecutor.COSTS, which prices
# only models you can still call.
RETIRED_TRACKER_ONLY = {"claude-3-opus", "claude-3-sonnet", "claude-3-haiku"}

# (model, input $/MTok, output $/MTok) -- straight from the pricing page.
CURRENT_RATES = [
    ("claude-opus-5", 5.00, 25.00),
    ("claude-opus-4-8", 5.00, 25.00),
    ("claude-opus-4-7", 5.00, 25.00),
    ("claude-opus-4-6", 5.00, 25.00),
    ("claude-opus-4-5", 5.00, 25.00),
    ("claude-sonnet-5", 2.00, 10.00),
    ("claude-sonnet-4-6", 3.00, 15.00),
    ("claude-sonnet-4-5", 3.00, 15.00),
    ("claude-haiku-4-5", 1.00, 5.00),
    ("claude-fable-5", 10.00, 50.00),
    ("claude-mythos-5", 10.00, 50.00),
]


class TestExecutorCosts:
    """APILLMExecutor.COSTS -- the table behind APIResult.cost_usd."""

    @pytest.mark.parametrize(("model", "want_in", "want_out"), CURRENT_RATES)
    def test_rate_matches_published_pricing(
        self, model: str, want_in: float, want_out: float
    ) -> None:
        entry = APILLMExecutor.COSTS["anthropic"][model]
        assert entry["input"] == want_in
        assert entry["output"] == want_out

    @pytest.mark.parametrize(("model", "want_in", "want_out"), CURRENT_RATES)
    def test_cost_of_one_mtok_each_way(self, model: str, want_in: float, want_out: float) -> None:
        executor = APILLMExecutor(provider="anthropic", model=model)
        cost = executor._calculate_cost_with_cache(MTOK, MTOK)
        assert cost == pytest.approx(want_in + want_out)

    def test_opus_4_6_is_not_the_retired_15_75_rate(self) -> None:
        """The exact historical defect: only Opus 4.1 and Opus 4 were 15/75.

        Opus 4.5 and later all price at 5/25. This asserts the wrong value is
        gone, not merely that some value is present.
        """
        entry = APILLMExecutor.COSTS["anthropic"]["claude-opus-4-6"]
        assert (entry["input"], entry["output"]) != (15.00, 75.00)
        assert (entry["input"], entry["output"]) == (5.00, 25.00)

    @pytest.mark.parametrize(("model", "_in", "_out"), CURRENT_RATES)
    def test_current_models_never_report_zero_cost(
        self, model: str, _in: float, _out: float
    ) -> None:
        """Silent $0 is worse than a wrong estimate -- real spend read as free."""
        executor = APILLMExecutor(provider="anthropic", model=model)
        assert executor._calculate_cost_with_cache(MTOK, MTOK) > 0.0

    def test_unknown_model_still_returns_zero_but_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Documents the retained contract, and that the gap is now visible."""
        executor = APILLMExecutor(provider="anthropic", model="claude-not-a-model")
        with caplog.at_level("WARNING"):
            cost = executor._calculate_cost_with_cache(MTOK, MTOK)
        assert cost == 0.0
        assert any("No pricing entry" in r.message for r in caplog.records)


class TestSessionCostTrackerRates:
    """SessionCostTracker.model_costs -- per-1K INPUT rate, existing convention."""

    @pytest.mark.parametrize(("model", "want_in", "_out"), CURRENT_RATES)
    def test_current_model_is_priced_explicitly(
        self, model: str, want_in: float, _out: float
    ) -> None:
        tracker = SessionCostTracker(session_id="test-pricing")
        assert model in tracker.model_costs, f"{model} would fall to the default"
        cost = tracker.track_usage_fast(model=model, tokens=MTOK, duration_ms=1.0)
        assert cost == pytest.approx(want_in)

    @pytest.mark.parametrize(("model", "_in", "_out"), CURRENT_RATES)
    def test_current_model_does_not_hit_the_conservative_default(
        self, model: str, _in: float, _out: float
    ) -> None:
        """Discriminating: pre-fix, every one of these returned exactly 15.00."""
        tracker = SessionCostTracker(session_id="test-pricing")
        cost = tracker.track_usage_fast(model=model, tokens=MTOK, duration_ms=1.0)
        assert cost != pytest.approx(15.00), "fell through to the 0.015 default"

    def test_retired_claude_3_rates_are_preserved(self) -> None:
        """Historical records must keep pricing correctly."""
        tracker = SessionCostTracker(session_id="test-pricing")
        assert tracker.model_costs["claude-3-opus"] == 0.015
        assert tracker.model_costs["claude-3-sonnet"] == 0.003
        assert tracker.model_costs["claude-3-haiku"] == 0.00025


class TestOutputTokenPricing:
    """Output costs 5x input; pricing everything at the input rate under-counts.

    Raised independently by two cross-family cloud review lanes (gpt-oss-120b,
    glm-5.2) against the first version of this patch, which priced a whole
    request at the input rate and so reported $5.00 for 1M opus-5 tokens whose
    true 50/50 cost is $15.00.
    """

    @pytest.mark.parametrize(("model", "want_in", "want_out"), CURRENT_RATES)
    def test_full_output_request_is_priced_at_the_output_rate(
        self, model: str, want_in: float, want_out: float
    ) -> None:
        tracker = SessionCostTracker(session_id="test-pricing")
        cost = tracker.track_usage_fast(
            model=model, tokens=MTOK, duration_ms=1.0, output_tokens=MTOK
        )
        assert cost == pytest.approx(want_out)

    @pytest.mark.parametrize(("model", "want_in", "want_out"), CURRENT_RATES)
    def test_even_split_is_the_mean_of_the_two_rates(
        self, model: str, want_in: float, want_out: float
    ) -> None:
        """Discriminating: input-only pricing returns want_in, not the blend."""
        tracker = SessionCostTracker(session_id="test-pricing")
        cost = tracker.track_usage_fast(
            model=model, tokens=MTOK, duration_ms=1.0, output_tokens=MTOK // 2
        )
        assert cost == pytest.approx((want_in + want_out) / 2)
        assert cost != pytest.approx(want_in), "output tokens priced as input"

    def test_omitting_output_tokens_preserves_historical_behaviour(self) -> None:
        """Backward compatibility: callers that don't know the split are unchanged."""
        tracker = SessionCostTracker(session_id="test-pricing")
        cost = tracker.track_usage_fast(model="claude-opus-5", tokens=MTOK, duration_ms=1.0)
        assert cost == pytest.approx(5.00)

    def test_output_tokens_cannot_exceed_total(self) -> None:
        """A caller passing a larger output count must not inflate the bill."""
        tracker = SessionCostTracker(session_id="test-pricing")
        cost = tracker.track_usage_fast(
            model="claude-opus-5", tokens=1000, duration_ms=1.0, output_tokens=999_999
        )
        assert cost == pytest.approx(0.025)

    def test_output_rate_table_covers_every_priced_model(self) -> None:
        """Third hand-maintained table -- guard it the same way as the other two."""
        tracker = SessionCostTracker(session_id="test-pricing")
        missing = sorted(set(tracker.model_costs) - set(tracker.model_output_costs))
        claude_missing = [m for m in missing if m.startswith("claude-")]
        assert not claude_missing, f"no output rate for: {claude_missing}"

    @pytest.mark.parametrize(("model", "_in", "want_out"), CURRENT_RATES)
    def test_output_rate_matches_the_executor_table(
        self, model: str, _in: float, want_out: float
    ) -> None:
        tracker = SessionCostTracker(session_id="test-pricing")
        assert tracker.model_output_costs[model] == pytest.approx(want_out / 1000.0)
        assert tracker.model_output_costs[model] == pytest.approx(
            APILLMExecutor.COSTS["anthropic"][model]["output"] / 1000.0
        )


def test_the_two_tables_agree_on_which_models_exist() -> None:
    """Structural guard against fixing one table and forgetting the other.

    This is how the drift happened: the two tables are maintained by hand, in
    different packages, with different units, and nothing tied them together.

    Checked in BOTH directions. A one-directional guard passes while a model
    added only to the tracker is billed at $0 by the executor.
    """
    executor_models = set(APILLMExecutor.COSTS["anthropic"])
    tracker_models = set(SessionCostTracker(session_id="test-pricing").model_costs)

    missing = sorted(executor_models - tracker_models)
    assert not missing, (
        f"priced in APILLMExecutor.COSTS but unknown to SessionCostTracker: {missing}"
    )

    # The reverse direction, minus the retired entries the tracker keeps on
    # purpose so historical records still price correctly.
    tracker_claude = {m for m in tracker_models if m.startswith("claude-")}
    extra = sorted(tracker_claude - executor_models - RETIRED_TRACKER_ONLY)
    assert not extra, (
        f"known to SessionCostTracker but absent from APILLMExecutor.COSTS, so the "
        f"executor bills them at $0.00: {extra}"
    )


def test_executor_input_rate_matches_tracker_rate() -> None:
    """The tracker's per-1K value must be the executor's per-MTok input / 1000.

    Iterates the tables' ACTUAL shared keys, not CURRENT_RATES. Driving this off
    the constant would let a model added to both tables with mismatched rates
    pass simply by not being listed here.
    """
    tracker = SessionCostTracker(session_id="test-pricing")
    executor_models = set(APILLMExecutor.COSTS["anthropic"])
    shared = sorted(executor_models & set(tracker.model_costs))
    assert shared, "no shared models -- the tables or this test have drifted apart"

    for model in shared:
        assert tracker.model_costs[model] == pytest.approx(
            APILLMExecutor.COSTS["anthropic"][model]["input"] / 1000.0
        ), f"{model}: the two tables disagree on the input rate"

    # …and the published rates this file asserts must themselves be covered.
    for model, want_in, _ in CURRENT_RATES:
        assert model in shared, f"{model} dropped out of one of the tables"
        assert tracker.model_costs[model] == pytest.approx(want_in / 1000.0)
