"""Portfolio analysis, goals, and consensus gate for Robinhood (stub).

Exports consumed by tests/integrations/test_robinhood_analysis.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Position:
    """A single portfolio position."""

    symbol: str
    quantity: float
    market_value: float
    cost_basis: float

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100.0


@dataclass
class PortfolioSnapshot:
    """A snapshot of the full portfolio at a point in time."""

    positions: list[Position]
    total_value: float
    cash: float


@dataclass
class PortfolioGoal:
    """A user-defined portfolio allocation goal."""

    symbol: str
    target_pct: float
    tolerance_pct: float = 5.0


@dataclass
class PortfolioGoalTracker:
    """Track progress toward portfolio goals."""

    goals: list[PortfolioGoal] = field(default_factory=list)

    def add_goal(self, goal: PortfolioGoal) -> None:
        raise NotImplementedError

    def check_drift(self, snapshot: PortfolioSnapshot) -> dict[str, Any]:
        raise NotImplementedError


class PortfolioAnalyzer:
    """Analyze a portfolio snapshot for concentration, performance, and risk."""

    def analyze(self, snapshot: PortfolioSnapshot) -> dict[str, Any]:
        raise NotImplementedError


class MultiModelConsensusGate:
    """Route portfolio decisions through a multi-model consensus vote."""

    def __init__(self, *, threshold: float = 0.6) -> None:
        self.threshold = threshold

    async def vote(self, proposal: Any, snapshot: PortfolioSnapshot) -> bool:
        raise NotImplementedError


class TradingMonitorLoop:
    """Background loop that monitors the portfolio and fires alerts."""

    def __init__(
        self,
        *,
        poll_interval_s: float = 60.0,
        analyzer: PortfolioAnalyzer | None = None,
        gate: MultiModelConsensusGate | None = None,
    ) -> None:
        self.poll_interval_s = poll_interval_s
        self.analyzer = analyzer or PortfolioAnalyzer()
        self.gate = gate or MultiModelConsensusGate()

    async def run_once(self, snapshot: PortfolioSnapshot) -> list[Any]:
        raise NotImplementedError
