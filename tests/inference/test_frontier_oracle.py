"""Frontier oracle — route ONLY the genuinely-hardest tasks to Claude Fable 5.

Token-efficient by construction: local silicon ($0) handles the bulk; Fable (the most
capable, most expensive model) fires only when a task is frontier-hard AND the Fable budget
has headroom. The gate reads the SAME usage_log the monitor writes, closing the loop:
recorded Fable spend → gate → blocks Fable once the cap is hit.

The discriminating tests pin the two failure modes that would waste money: over-triggering
(treating ordinary long tasks as frontier) and ignoring the budget cap.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.frontier_oracle import (
    decide_frontier,
    fable_spend_usd,
    frontier_complete,
    is_frontier_task,
)
from cohezion.inference.usage_log import record_usage


# --------------------------------------------------------------------------- #
# is_frontier_task — the difficulty gate (must stay SPARING)
# --------------------------------------------------------------------------- #


def test_trivial_short_task_is_not_frontier():
    assert is_frontier_task("What is 2+2?") is False
    assert is_frontier_task("reverse a string") is False


def test_explicit_frontier_intent_in_substantial_prompt_is_frontier():
    assert is_frontier_task(
        "Prove that the tiered orchestrator's escalation always terminates given a finite tier list"
    )
    assert is_frontier_task(
        "Design the architecture for a fault-tolerant distributed cache that survives node loss"
    )


def test_long_ordinary_generation_is_not_frontier():
    """DISCRIMINATING: not every long task is frontier. A 500-word blog post is long but
    ordinary — an impl that flagged all `long_generation` would waste Fable money here."""
    assert (
        is_frontier_task(
            "Write a detailed 500-word blog post about the history of domestic cats and "
            "their behavior, covering breeds, diet, and common myths about them"
        )
        is False
    )


def test_keyword_trap_improve_is_not_frontier():
    """DISCRIMINATING word-boundary guard: 'improve' contains the substring 'prove' but is
    NOT a frontier signal. A naive substring match would over-trigger Fable on every
    'improve the X' request."""
    assert is_frontier_task("Please improve the architecture documentation wording a little") is False


def test_frontier_keyword_but_too_short_is_not_frontier():
    """Sparing: a bare 'prove it' must not reach Fable — frontier problems are substantial."""
    assert is_frontier_task("prove it") is False


# --------------------------------------------------------------------------- #
# fable_spend_usd — budget read from the usage corpus
# --------------------------------------------------------------------------- #


def test_fable_spend_counts_only_fable(tmp_path):
    """DISCRIMINATING: only claude-fable-5 spend counts toward the Fable budget — a Sonnet
    row in the same log must NOT inflate it."""
    p = tmp_path / "usage_log.jsonl"
    record_usage(model="claude-fable-5", lane="cloud", input_tokens=100, output_tokens=50,
                 cost_usd=0.0035, local=False, path=p)
    record_usage(model="claude-sonnet-4-6", lane="cloud", input_tokens=100, output_tokens=50,
                 cost_usd=0.0009, local=False, path=p)
    record_usage(model="claude-fable-5", lane="cloud", input_tokens=200, output_tokens=100,
                 cost_usd=0.0070, local=False, path=p)
    assert fable_spend_usd(path=p) == pytest.approx(0.0105, abs=1e-9)  # 0.0035+0.0070, NOT sonnet


# --------------------------------------------------------------------------- #
# decide_frontier — the composed decision (difficulty AND budget)
# --------------------------------------------------------------------------- #


def test_non_frontier_decision_stays_local(tmp_path):
    d = decide_frontier("What is 2+2?", monthly_budget_usd=10.0, path=tmp_path / "u.jsonl")
    assert d.use_frontier is False
    assert "frontier" in d.reason.lower()


def test_frontier_within_budget_uses_fable(tmp_path):
    d = decide_frontier(
        "Prove the orchestrator escalation terminates for any finite tier configuration",
        monthly_budget_usd=10.0, path=tmp_path / "u.jsonl",
    )
    assert d.use_frontier is True


def test_frontier_over_budget_is_blocked(tmp_path):
    """DISCRIMINATING budget guard: a frontier task whose Fable spend has hit the cap must
    NOT use Fable. An impl that ignored the budget would keep spending."""
    p = tmp_path / "u.jsonl"
    record_usage(model="claude-fable-5", lane="cloud", input_tokens=1, output_tokens=1,
                 cost_usd=10.5, local=False, path=p)  # already over a $10 cap
    d = decide_frontier(
        "Design the architecture for a fault-tolerant distributed consensus layer end to end",
        monthly_budget_usd=10.0, path=p,
    )
    assert d.use_frontier is False
    assert "budget" in d.reason.lower()


# --------------------------------------------------------------------------- #
# frontier_complete — routing (token-efficiency guarantee: cheap tasks never reach Fable)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_frontier_task_routes_through_extend_claude_to_fable(tmp_path):
    fake = MagicMock(text="frontier answer")
    with (
        patch("cohezion.inference.frontier_oracle.extend_claude", new=AsyncMock(return_value=fake)) as ec,
        patch("cohezion.inference.frontier_oracle.build_triune_orchestrator") as bto,
    ):
        text, decision = await frontier_complete(
            "Prove that the escalation ladder terminates for a finite, fixed tier list",
            monthly_budget_usd=10.0, path=tmp_path / "u.jsonl",
        )
    assert decision.use_frontier is True
    assert text == "frontier answer"
    assert ec.call_args.kwargs["claude_model"] == "claude-fable-5"
    bto.assert_not_called()  # frontier path does NOT spin up the local-only orchestrator


@pytest.mark.asyncio
async def test_non_frontier_task_never_touches_fable(tmp_path):
    """DISCRIMINATING token-efficiency guarantee: an ordinary task must route to the local
    orchestrator and NEVER call extend_claude (the Fable path)."""
    orch = MagicMock()
    orch.run = AsyncMock(return_value=MagicMock(text="local answer"))
    with (
        patch("cohezion.inference.frontier_oracle.extend_claude", new=AsyncMock()) as ec,
        patch("cohezion.inference.frontier_oracle.build_triune_orchestrator", return_value=orch),
    ):
        text, decision = await frontier_complete("What is 2+2?", path=tmp_path / "u.jsonl")
    assert decision.use_frontier is False
    assert text == "local answer"
    ec.assert_not_called()  # cheap task never reaches Fable
