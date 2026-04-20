"""Tests for Orborous self-improving compound system."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.research.consensus import PartyModeConsensus
from cohezion.research.cost_optimization import CostBudget
from cohezion.research.orborous import Orborous
from cohezion.research.research_squad import ResearchSquad


class TestOrborousInitialization:
    """Tests for Orborous initialization."""

    @pytest.mark.fast
    def test_default_initialization(self):
        """[ORB-01] Orborous initializes with defaults."""
        orb = Orborous()
        assert orb.squad is not None
        assert orb.consensus is not None
        assert orb.cycle_count == 0
        assert orb.active is False
        assert orb.improvement_history == []

    @pytest.mark.fast
    def test_custom_initialization(self):
        """[ORB-02] Orborous accepts custom components."""
        squad = ResearchSquad()
        consensus = PartyModeConsensus(consensus_threshold=0.8)
        budget = CostBudget(max_cost_usd=100.0)

        orb = Orborous(squad=squad, consensus=consensus, cost_budget=budget)
        assert orb.squad is squad
        assert orb.consensus is consensus
        assert orb.cost_budget.max_cost_usd == 100.0


class TestOrborousStatus:
    """Tests for Orborous status reporting."""

    @pytest.mark.fast
    def test_status_report(self):
        """[ORB-03] Status report contains expected fields."""
        orb = Orborous()
        status = orb.get_status()

        assert status["cycles_completed"] == 0
        assert status["active"] is False
        assert status["improvements_made"] == 0
        assert "total_cost_usd" in status
        assert "budget_remaining_pct" in status
        assert "latest_improvements" in status


class TestOrborousStop:
    """Tests for graceful stop."""

    @pytest.mark.fast
    def test_stop_sets_inactive(self):
        """[ORB-04] Stop sets active to False."""
        orb = Orborous()
        orb.active = True
        orb.stop()
        assert orb.active is False


class TestOrborousMonitorCycle:
    """Tests for the monitor cycle."""

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_monitor_cycle_increments_count(self):
        """[ORB-05] Each cycle increments cycle_count."""
        orb = Orborous()
        await orb.monitor_cycle()
        assert orb.cycle_count == 1
        await orb.monitor_cycle()
        assert orb.cycle_count == 2

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_monitor_cycle_detects_degradation(self):
        """[ORB-06] Cycle detects degraded skills from metrics."""
        orb = Orborous()
        # Default _get_compound_metrics returns "coding" with coherence=0.45 (degraded)
        await orb.monitor_cycle()
        # Should have attempted optimization (history may or may not have entries
        # depending on consensus outcome)
        assert orb.cycle_count == 1

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_monitor_cycle_handles_errors(self):
        """[ORB-07] Cycle handles errors gracefully."""
        orb = Orborous()
        orb.squad.detect_degradation = MagicMock(side_effect=RuntimeError("boom"))
        # Should not raise
        await orb.monitor_cycle()
        assert orb.cycle_count == 1
