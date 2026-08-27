"""Portfolio analysis, goals, and consensus gate for Robinhood.

Exports consumed by tests/integrations/test_robinhood_analysis.py.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


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
    cash: float = 0.0

    def concentration_pct(self, symbol: str) -> float:
        if self.total_value == 0:
            return 0.0
        for pos in self.positions:
            if pos.symbol == symbol:
                return (pos.market_value / self.total_value) * 100.0
        return 0.0

    @property
    def invested_value(self) -> float:
        return sum(p.market_value for p in self.positions)


@dataclass
class PortfolioGoal:
    """A user-defined portfolio allocation goal."""

    goal_id: str
    description: str
    metric: str
    operator: str
    target: float
    status: str = "active"
    tolerance_pct: float = 5.0


class PortfolioGoalTracker:
    """Track progress toward portfolio goals."""

    def __init__(self, goals: list[PortfolioGoal] | None = None) -> None:
        self._goals: dict[str, PortfolioGoal] = {}
        if goals:
            for g in goals:
                self.add_goal(g)

    def add_goal(self, goal: PortfolioGoal) -> None:
        self._goals[goal.goal_id] = goal

    def evaluate(
        self, snapshot: PortfolioSnapshot, analyzer: PortfolioAnalyzer
    ) -> list[tuple[PortfolioGoal, bool, float | None]]:
        results: list[tuple[PortfolioGoal, bool, float | None]] = []

        for goal in list(self._goals.values()):
            if goal.status == "met":
                continue

            actual: float | None = None
            if goal.metric.startswith("concentration_pct_"):
                sym = goal.metric.removeprefix("concentration_pct_")
                actual = snapshot.concentration_pct(sym)
            elif goal.metric == "hhi":
                risk = analyzer.concentration_risk(snapshot)
                actual = risk["hhi"]
            elif goal.metric == "total_pnl_usd":
                pnl = analyzer.pnl_summary(snapshot)
                actual = pnl["total_pnl"]

            met = False
            if actual is not None:
                if goal.operator == "<":
                    met = actual < goal.target
                elif goal.operator == ">":
                    met = actual > goal.target

            if met:
                goal.status = "met"

            results.append((goal, met, actual))

        return results

    def format_goal_status(self) -> str:
        lines = ["Portfolio Goals:"]
        for g in self._goals.values():
            lines.append(
                f"- [{g.status.upper()}] {g.description} ({g.metric} {g.operator} {g.target})"
            )
        return "\n".join(lines)

    async def persist(
        self,
        snapshot: PortfolioSnapshot,
        results: list[Any],
        surreal_url: str = "http://localhost:8001",
    ) -> None:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "snapshot_total": snapshot.total_value,
                    "goals_count": len(self._goals),
                }
                await client.post(f"{surreal_url}/sql", json=payload, timeout=2.0)
        except Exception:
            pass


class PortfolioAnalyzer:
    """Analyze a portfolio snapshot for concentration, performance, and risk."""

    def concentration_risk(self, snapshot: PortfolioSnapshot) -> dict[str, Any]:
        if not snapshot.positions or snapshot.total_value == 0:
            return {"hhi": 0.0, "hhi_label": "LOW", "warnings": []}

        hhi = 0.0
        warnings: list[str] = []

        for p in snapshot.positions:
            pct = (p.market_value / snapshot.total_value) * 100.0
            hhi += pct**2
            if pct > 30.0:
                warnings.append(f"HIGH concentration in {p.symbol}: {pct:.1f}%")

        if hhi >= 2500:
            hhi_label = "HIGH"
        elif hhi >= 1500:
            hhi_label = "MODERATE"
        else:
            hhi_label = "LOW"

        return {"hhi": hhi, "hhi_label": hhi_label, "warnings": warnings}

    def pnl_summary(self, snapshot: PortfolioSnapshot) -> dict[str, Any]:
        gainers = sum(1 for p in snapshot.positions if p.unrealized_pnl > 0)
        losers = sum(1 for p in snapshot.positions if p.unrealized_pnl < 0)
        total_pnl = sum(p.unrealized_pnl for p in snapshot.positions)
        return {"gainers": gainers, "losers": losers, "total_pnl": total_pnl}

    def cluster_positions(
        self, snapshot: PortfolioSnapshot, n_clusters: int = 2
    ) -> dict[str, list[str]]:
        if not snapshot.positions:
            return {}
        clusters: dict[str, list[str]] = {f"cluster_{i}": [] for i in range(n_clusters)}
        for i, p in enumerate(snapshot.positions):
            cluster_key = f"cluster_{i % n_clusters}"
            clusters[cluster_key].append(p.symbol)
        return clusters

    def format_analysis(self, snapshot: PortfolioSnapshot) -> str:
        risk = self.concentration_risk(snapshot)
        pnl = self.pnl_summary(snapshot)
        return (
            f"Portfolio Analysis: Total Value = ${snapshot.total_value:,.2f}\n"
            f"HHI Index: {risk['hhi']:.1f} ({risk['hhi_label']})\n"
            f"Gainers: {pnl['gainers']}, Losers: {pnl['losers']}, Total PnL: ${pnl['total_pnl']:,.2f}\n"
            f"Warnings: {', '.join(risk['warnings']) if risk['warnings'] else 'None'}"
        )


class MultiModelConsensusGate:
    """Route portfolio decisions through a multi-model consensus vote."""

    def __init__(
        self,
        *,
        lemonade_url: str = "http://localhost:13305",
        threshold: float = 0.6,
    ) -> None:
        self.lemonade_url = lemonade_url
        self.threshold = threshold

    async def assess(self, order_summary: str, mcp_params: dict) -> dict[str, Any]:
        models = ["Gemma-4-E4B-it-GGUF", "Llama-3.2-3B-Instruct"]
        votes: dict[str, str] = {}

        try:
            async with httpx.AsyncClient() as client:
                for model in models:
                    try:
                        url = f"{self.lemonade_url}/v1/chat/completions"
                        payload = {
                            "model": model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Assess trade risk: LOW, MEDIUM, or HIGH.",
                                },
                                {"role": "user", "content": order_summary},
                            ],
                        }
                        resp = await client.post(url, json=payload, timeout=5.0)
                        resp.raise_for_status()
                        body = resp.json()
                        content = body["choices"][0]["message"]["content"]
                        data = json.loads(content)
                        risk = data.get("risk", "MEDIUM").upper()
                        votes[model] = risk
                    except Exception:
                        votes[model] = "MEDIUM"
        except Exception:
            votes = dict.fromkeys(models, "MEDIUM")

        vote_values = list(votes.values())
        if any(v == "HIGH" for v in vote_values):
            consensus = "HIGH"
            proceed = False
        elif all(v == "LOW" for v in vote_values):
            consensus = "LOW"
            proceed = True
        else:
            consensus = "MEDIUM"
            proceed = True

        return {"consensus": consensus, "votes": votes, "proceed": proceed}

    def format_assessment(self, result: dict[str, Any]) -> str:
        proceed = result.get("proceed", False)
        consensus = result.get("consensus", "HIGH")
        if not proceed or consensus == "HIGH":
            return f"🔴 Consensus Assessment: BLOCKED ({consensus})"
        return f"🟢 Consensus Assessment: Proceed ({consensus})"


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
        self.goal_tracker = PortfolioGoalTracker()
        self.alert_fns: list[Callable[[str], Awaitable[None]]] = []

    def add_alert_fn(self, fn: Callable[[str], Awaitable[None]]) -> None:
        self.alert_fns.append(fn)

    async def run_once(self, snapshot: PortfolioSnapshot) -> str:
        analysis_str = self.analyzer.format_analysis(snapshot)
        eval_results = self.goal_tracker.evaluate(snapshot, self.analyzer)

        unmet_goals = [goal for goal, met, _ in eval_results if not met]
        risk = self.analyzer.concentration_risk(snapshot)

        if unmet_goals or risk["warnings"]:
            alert_msg = f"Alert: {len(unmet_goals)} goals unmet. Warnings: {risk['warnings']}"
            for alert_fn in self.alert_fns:
                try:
                    await alert_fn(alert_msg)
                except Exception:
                    pass

        return analysis_str
