"""Usage log for tracking inference spend (stub).

Consumed by:
  - cohezion.inference.frontier_oracle
  - tests/inference/test_frontier_oracle.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageRecord:
    """A single recorded inference usage event."""

    model: str
    tokens: int
    cost_usd: float
    timestamp: float = 0.0


def record_usage(
    model: str,
    tokens: int,
    cost_usd: float,
    *,
    log_path: str | None = None,
) -> None:
    """Append a usage record to the usage log."""
    raise NotImplementedError


def read_usage_log(log_path: str | None = None) -> list[UsageRecord]:
    """Return all usage records from the log file."""
    raise NotImplementedError
