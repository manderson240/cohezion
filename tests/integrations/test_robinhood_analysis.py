"""Unit tests for robinhood_analysis.py — portfolio analysis, goals, consensus gate."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.integrations.robinhood_analysis import (
    MultiModelConsensusGate,
    PortfolioAnalyzer,
    PortfolioGoal,
    PortfolioGoalTracker,
    PortfolioSnapshot,
    Position,
    TradingMonitorLoop,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _snapshot(*positions: tuple[str, float, float, float]) -> PortfolioSnapshot:
    """Helper: (symbol, qty, market_value, cost_basis)"""
    pos = [Position(sym, qty, mv, cb) for sym, qty, mv, cb in positions]
    total = sum(p.market_value for p in pos)
    return PortfolioSnapshot(positions=pos, total_value=total + 1000.0, cash=1000.0)


def _balanced() -> PortfolioSnapshot:
    return _snapshot(
        ("AAPL", 10, 2000.0, 1800.0),
        ("MSFT", 5, 2000.0, 1900.0),
        ("NVDA", 3, 2000.0, 1500.0),
        ("TSLA", 8, 2000.0, 2200.0),
    )


def _concentrated() -> PortfolioSnapshot:
    """One position dominates (AAPL = 70% of portfolio)."""
    return _snapshot(
        ("AAPL", 100, 7000.0, 5000.0),
        ("MSFT", 5, 500.0, 450.0),
        ("TSLA", 2, 500.0, 600.0),
    )


# ── Position model ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPosition:
    def test_unrealized_pnl(self):
        p = Position("AAPL", 10, 2000.0, 1800.0)
        assert p.unrealized_pnl == pytest.approx(200.0)

    def test_unrealized_pnl_pct(self):
        p = Position("AAPL", 10, 2000.0, 1000.0)
        assert p.unrealized_pnl_pct == pytest.approx(100.0)

    def test_zero_cost_basis_no_division_error(self):
        p = Position("NEW", 1, 100.0, 0.0)
        assert p.unrealized_pnl_pct == 0.0


@pytest.mark.unit
class TestPortfolioSnapshot:
    def test_concentration_pct(self):
        snap = _concentrated()
        pct = snap.concentration_pct("AAPL")
        assert pct > 60  # AAPL dominates

    def test_unknown_symbol_is_zero(self):
        snap = _balanced()
        assert snap.concentration_pct("XYZ") == 0.0

    def test_invested_value(self):
        snap = _balanced()
        assert snap.invested_value == pytest.approx(8000.0)


# ── PortfolioAnalyzer ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortfolioAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return PortfolioAnalyzer()

    def test_hhi_balanced_is_low(self, analyzer):
        risk = analyzer.concentration_risk(_balanced())
        assert risk["hhi"] < 2500
        assert risk["hhi_label"] in ("LOW", "MODERATE")

    def test_hhi_concentrated_is_high(self, analyzer):
        risk = analyzer.concentration_risk(_concentrated())
        assert risk["hhi"] > 2500
        assert risk["hhi_label"] == "HIGH"

    def test_concentration_warning_for_dominant_position(self, analyzer):
        risk = analyzer.concentration_risk(_concentrated())
        assert any("AAPL" in w for w in risk["warnings"])

    def test_balanced_has_no_high_warnings(self, analyzer):
        risk = analyzer.concentration_risk(_balanced())
        high_warnings = [w for w in risk["warnings"] if "HIGH" in w]
        assert len(high_warnings) == 0

    def test_pnl_summary_counts_gainers_losers(self, analyzer):
        pnl = analyzer.pnl_summary(_balanced())
        # AAPL +200, MSFT +100, NVDA +500, TSLA -200
        assert pnl["gainers"] == 3
        assert pnl["losers"] == 1

    def test_pnl_summary_total(self, analyzer):
        snap = _snapshot(("A", 1, 200.0, 100.0), ("B", 1, 50.0, 100.0))
        pnl = analyzer.pnl_summary(snap)
        assert pnl["total_pnl"] == pytest.approx(50.0)  # 100 - 50

    def test_cluster_returns_symbol_lists(self, analyzer):
        clusters = analyzer.cluster_positions(_balanced(), n_clusters=2)
        all_syms = [sym for syms in clusters.values() for sym in syms]
        assert set(all_syms) == {"AAPL", "MSFT", "NVDA", "TSLA"}

    def test_cluster_fewer_positions_than_clusters(self, analyzer):
        snap = _snapshot(("AAPL", 1, 100.0, 90.0))
        clusters = analyzer.cluster_positions(snap, n_clusters=3)
        assert "AAPL" in str(clusters)

    def test_empty_snapshot_concentration_returns_zero_hhi(self, analyzer):
        snap = PortfolioSnapshot(positions=[], total_value=0.0)
        risk = analyzer.concentration_risk(snap)
        assert risk["hhi"] == 0.0

    def test_format_analysis_contains_key_fields(self, analyzer):
        text = analyzer.format_analysis(_balanced())
        assert "HHI" in text
        assert "$" in text


# ── PortfolioGoalTracker ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestPortfolioGoalTracker:
    @pytest.fixture
    def tracker(self):
        return PortfolioGoalTracker()

    @pytest.fixture
    def analyzer(self):
        return PortfolioAnalyzer()

    def test_concentration_goal_met(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="low-aapl",
            description="Keep AAPL below 30%",
            metric="concentration_pct_AAPL",
            operator="<",
            target=30.0,
        )
        tracker.add_goal(goal)
        # balanced snapshot: AAPL is ~25% → goal should be met
        results = tracker.evaluate(_balanced(), analyzer)
        assert len(results) == 1
        _, met, actual = results[0]
        assert met is True
        assert actual is not None and actual < 30

    def test_concentration_goal_not_met_on_concentrated(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="reduce-aapl",
            description="Reduce AAPL below 30%",
            metric="concentration_pct_AAPL",
            operator="<",
            target=30.0,
        )
        tracker.add_goal(goal)
        results = tracker.evaluate(_concentrated(), analyzer)
        _, met, actual = results[0]
        assert met is False  # AAPL > 30% in concentrated snapshot

    def test_hhi_goal(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="low-hhi",
            description="HHI below 3000",
            metric="hhi",
            operator="<",
            target=3000.0,
        )
        tracker.add_goal(goal)
        results = tracker.evaluate(_balanced(), analyzer)
        _, met, _ = results[0]
        assert met is True

    def test_met_goal_status_updated(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="g1",
            description="HHI below 5000",
            metric="hhi",
            operator="<",
            target=5000.0,
        )
        tracker.add_goal(goal)
        tracker.evaluate(_balanced(), analyzer)
        assert tracker._goals["g1"].status == "met"

    def test_inactive_goals_skipped(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="done",
            description="Already met",
            metric="hhi",
            operator="<",
            target=5000.0,
            status="met",
        )
        tracker.add_goal(goal)
        results = tracker.evaluate(_balanced(), analyzer)
        assert results == []

    def test_unknown_metric_returns_none(self, tracker, analyzer):
        goal = PortfolioGoal(
            goal_id="bad",
            description="Unknown metric",
            metric="nonexistent_metric_xyz",
            operator="<",
            target=10.0,
        )
        tracker.add_goal(goal)
        results = tracker.evaluate(_balanced(), analyzer)
        _, met, actual = results[0]
        assert actual is None

    def test_format_shows_all_goals(self, tracker):
        tracker.add_goal(PortfolioGoal("g1", "Keep HHI low", "hhi", "<", 2500))
        tracker.add_goal(PortfolioGoal("g2", "P&L positive", "total_pnl_usd", ">", 0))
        text = tracker.format_goal_status()
        assert "Keep HHI low" in text
        assert "P&L positive" in text

    @pytest.mark.asyncio
    async def test_persist_does_not_raise_on_surreal_failure(self, tracker, analyzer):
        """SurrealDB failure must be non-fatal."""
        with patch("cohezion.integrations.robinhood_analysis.httpx.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("surreal down"))
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client
            # Should not raise
            await tracker.persist(_balanced(), [])


# ── MultiModelConsensusGate ───────────────────────────────────────────────────


@pytest.mark.unit
class TestMultiModelConsensusGate:
    def _mock_lemonade(self, risk_responses: list[str]):
        """Build a mock httpx.AsyncClient returning risk JSON per model call."""
        call_count = [0]

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                idx = min(call_count[0], len(risk_responses) - 1)
                call_count[0] += 1
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status = MagicMock()
                resp.json.return_value = {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"risk": risk_responses[idx], "reason": "test"}
                                )
                            }
                        }
                    ]
                }
                return resp

        return _Client()

    @pytest.mark.asyncio
    async def test_all_low_votes_consensus_low(self):
        gate = MultiModelConsensusGate(lemonade_url="http://localhost:13305")
        with patch(
            "cohezion.integrations.robinhood_analysis.httpx.AsyncClient",
            return_value=self._mock_lemonade(["LOW", "LOW"]),
        ):
            result = await gate.assess("BUY 5 AAPL", {"symbol": "AAPL"})
        assert result["consensus"] == "LOW"
        assert result["proceed"] is True

    @pytest.mark.asyncio
    async def test_any_high_vote_blocks_order(self):
        """Discriminating: even one HIGH vote must block the order."""
        gate = MultiModelConsensusGate(lemonade_url="http://localhost:13305")
        with patch(
            "cohezion.integrations.robinhood_analysis.httpx.AsyncClient",
            return_value=self._mock_lemonade(["LOW", "HIGH"]),
        ):
            result = await gate.assess("BUY 1000 TSLA", {"symbol": "TSLA", "quantity": 1000})
        assert result["consensus"] == "HIGH"
        assert result["proceed"] is False

    @pytest.mark.asyncio
    async def test_model_failure_defaults_to_medium(self):
        gate = MultiModelConsensusGate(lemonade_url="http://localhost:13305")

        class _FailClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                raise Exception("timeout")

        with patch(
            "cohezion.integrations.robinhood_analysis.httpx.AsyncClient",
            return_value=_FailClient(),
        ):
            result = await gate.assess("SELL 10 NVDA", {})
        # All models default to MEDIUM on failure → consensus MEDIUM, proceed True
        assert result["consensus"] == "MEDIUM"
        assert result["proceed"] is True

    def test_format_assessment_high_shows_blocked(self):
        gate = MultiModelConsensusGate()
        result = {
            "consensus": "HIGH",
            "votes": {"Gemma": "HIGH", "llama": "HIGH"},
            "proceed": False,
        }
        text = gate.format_assessment(result)
        assert "BLOCKED" in text
        assert "🔴" in text

    def test_format_assessment_low_shows_proceed(self):
        gate = MultiModelConsensusGate()
        result = {"consensus": "LOW", "votes": {"Gemma": "LOW", "llama": "LOW"}, "proceed": True}
        text = gate.format_assessment(result)
        assert "Proceed" in text
        assert "🟢" in text


# ── TradingMonitorLoop ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestTradingMonitorLoop:
    @pytest.mark.asyncio
    async def test_run_once_returns_analysis_string(self):
        loop = TradingMonitorLoop()
        with patch("cohezion.integrations.robinhood_analysis.httpx.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_cls.return_value = mock_client

            result = await loop.run_once(_balanced())

        assert isinstance(result, str)
        assert "HHI" in result

    @pytest.mark.asyncio
    async def test_alert_fn_called_on_high_concentration(self):
        """Monitor loop must fire alerts when concentration warnings exist."""
        alerts_received = []

        async def capture(msg):
            alerts_received.append(msg)

        loop = TradingMonitorLoop()
        loop.add_alert_fn(capture)

        # Add a goal that will trigger a warning
        goal = PortfolioGoal(
            goal_id="aapl-check",
            description="AAPL below 30%",
            metric="concentration_pct_AAPL",
            operator="<",
            target=10.0,  # threshold too low — balanced AAPL ~25% → NOT met
        )
        loop.goal_tracker.add_goal(goal)

        with patch("cohezion.integrations.robinhood_analysis.httpx.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_cls.return_value = mock_client

            await loop.run_once(_balanced())

        assert len(alerts_received) == 1

    @pytest.mark.asyncio
    async def test_alert_fn_failure_is_non_fatal(self):
        async def broken(_):
            raise RuntimeError("telegram down")

        loop = TradingMonitorLoop()
        loop.add_alert_fn(broken)

        with patch("cohezion.integrations.robinhood_analysis.httpx.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
            mock_cls.return_value = mock_client

            # Should not raise
            result = await loop.run_once(_balanced())

        assert isinstance(result, str)
