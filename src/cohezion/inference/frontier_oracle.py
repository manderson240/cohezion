"""Frontier oracle — route only genuinely-hard tasks to Claude Fable 5 (stub).

Exports consumed by tests/inference/test_frontier_oracle.py.
"""

from __future__ import annotations

from typing import Any


def is_frontier_task(prompt: str) -> bool:
    """Return True when *prompt* requires frontier-level reasoning.

    Must stay SPARING — only genuinely hard tasks qualify.
    """
    raise NotImplementedError


def fable_spend_usd(log_path: str | None = None) -> float:
    """Return the total USD spent on Fable-class models from the usage log."""
    raise NotImplementedError


async def decide_frontier(
    prompt: str,
    *,
    budget_cap_usd: float = 1.0,
    log_path: str | None = None,
) -> bool:
    """Return True when it is appropriate to route *prompt* to Fable.

    Returns False if:
    - The task is not frontier-hard (via is_frontier_task), or
    - The Fable budget has been exhausted (via fable_spend_usd).
    """
    raise NotImplementedError


async def frontier_complete(
    prompt: str,
    *,
    model: str = "claude-fable-5",
    timeout: float = 60.0,
) -> Any:
    """Complete *prompt* using a frontier model and return the RouteResult."""
    raise NotImplementedError
