"""Regression tests for DEFAULT_COSTS units in research/cost_optimization.

`CostTracker.track_experiment` computes `(tokens / 1000) * cost_per_1k`, so the
dict is dollars per 1K tokens. Every entry used to hold the per-MILLION-token
list price instead — a silent 1000x overestimate on every model, while the
inline comments claimed per-1K. The comments agreeing with the code's unit is
what hid it: only the numbers were wrong.

Measured before the fix, one 1M-token `claude-3-sonnet` experiment reported
$3,000.00 against a $10 budget (true cost $3.00), so any non-trivial run blew
its budget on the first call and forced a downgrade. The module is live:
`research_squad.py` and `orborous.py` import it, and `CostAwareRouter` uses it
to make downgrade decisions.

These tests assert the UNIT, not just the value — a unit error is what happened,
so re-pasting per-MTok prices must fail here.
"""

from __future__ import annotations

import pytest

from cohezion.research.cost_optimization import DEFAULT_COSTS


MTOK = 1_000_000

# (key, true $ per MILLION input tokens)
TRUE_PER_MTOK = [
    ("anthropic/claude-opus-5", 5.00),
    ("anthropic/claude-opus-4-8", 5.00),
    ("anthropic/claude-sonnet-5", 2.00),
    ("anthropic/claude-sonnet-4-6", 3.00),
    ("anthropic/claude-haiku-4-5", 1.00),
    ("anthropic/claude-3-haiku", 0.25),
    ("anthropic/claude-3-sonnet", 3.00),
    ("openai/gpt-4o-mini", 0.15),
    ("openai/gpt-4o", 2.50),
]


def _cost_of(model: str, tokens: int) -> float:
    """Replicate CostTracker.calculate_cost's arithmetic exactly."""
    return (tokens / 1000) * DEFAULT_COSTS[model]


@pytest.mark.parametrize(("model", "per_mtok"), TRUE_PER_MTOK)
def test_entry_is_per_1k_not_per_mtok(model: str, per_mtok: float) -> None:
    """The stored value must be the per-1K rate: per-MTok price / 1000."""
    assert DEFAULT_COSTS[model] == pytest.approx(per_mtok / 1000.0)


@pytest.mark.parametrize(("model", "per_mtok"), TRUE_PER_MTOK)
def test_one_million_tokens_costs_the_list_price(model: str, per_mtok: float) -> None:
    """Discriminating: with the old per-MTok values this returned 1000x too much."""
    assert _cost_of(model, MTOK) == pytest.approx(per_mtok)


@pytest.mark.parametrize(("model", "per_mtok"), TRUE_PER_MTOK)
def test_no_entry_is_off_by_a_factor_of_a_thousand(model: str, per_mtok: float) -> None:
    """The exact historical defect, asserted as absent rather than merely fixed."""
    assert DEFAULT_COSTS[model] != pytest.approx(per_mtok), (
        f"{model} holds the per-MTok price where a per-1K rate belongs — "
        f"that is the 1000x unit error this test exists to catch"
    )


def test_a_modest_budget_survives_a_million_token_experiment() -> None:
    """Pre-fix, one 1M-token sonnet run reported $3,000 against a $10 budget."""
    assert _cost_of("anthropic/claude-3-sonnet", MTOK) < 10.00


def test_local_models_are_free() -> None:
    for model in ("ollama/phi3:mini", "ollama/llama3.1:8b", "ollama/qwen2.5:7b"):
        assert DEFAULT_COSTS[model] == 0.0


def test_unknown_model_fails_safe_not_free(caplog: pytest.LogCaptureFixture) -> None:
    """An unknown model must NOT price at $0.00.

    This value feeds a budget enforcer: a free unknown model means the spend
    limit never trips. Raised by a local Gemma-4-26B review lane, then verified —
    nothing in production depended on the previous 0.0, and the sibling
    SessionCostTracker already uses a conservative non-zero default.

    Bypasses __init__ via __new__: the constructor mkdir's a data/ directory,
    which fails on a read-only checkout and is irrelevant to the arithmetic.
    """
    from cohezion.research.cost_optimization import (
        UNKNOWN_MODEL_COST_PER_1K,
        CostTracker,
    )

    tracker = CostTracker.__new__(CostTracker)
    tracker.costs_per_1k = dict(DEFAULT_COSTS)

    with caplog.at_level("WARNING"):
        cost = tracker.calculate_cost(tokens=MTOK, model="no-such-model")

    assert cost > 0.0, "an unknown model priced as free lets the budget never trip"
    assert cost == pytest.approx(MTOK / 1000 * UNKNOWN_MODEL_COST_PER_1K)
    assert any("No cost entry" in r.message for r in caplog.records)


def test_unknown_default_exceeds_every_known_model() -> None:
    """Conservative means conservative: the fallback must over-, never under-estimate."""
    from cohezion.research.cost_optimization import UNKNOWN_MODEL_COST_PER_1K

    assert max(DEFAULT_COSTS.values()) < UNKNOWN_MODEL_COST_PER_1K


def test_known_model_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    """Discriminating: proves the warning is conditional, not unconditional."""
    from cohezion.research.cost_optimization import CostTracker

    tracker = CostTracker.__new__(CostTracker)
    tracker.costs_per_1k = dict(DEFAULT_COSTS)

    with caplog.at_level("WARNING"):
        cost = tracker.calculate_cost(tokens=MTOK, model="anthropic/claude-sonnet-5")

    assert cost == pytest.approx(2.00)
    assert not any("No cost entry" in r.message for r in caplog.records)
