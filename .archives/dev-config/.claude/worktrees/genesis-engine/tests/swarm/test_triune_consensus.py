"""Tests for Triune Consensus & Homology (Story 2.7)."""

from __future__ import annotations

import pytest

from cohezion.swarm.triune_consensus import AgentProposal, TriuneConsensus


class TestTriuneConsensus:
    def _proposals(self, spread: float = 0.0) -> list[AgentProposal]:
        base = [0.5] * 12
        return [
            AgentProposal("architect", base, confidence=0.9),
            AgentProposal("engineer", [v + spread for v in base], confidence=0.8),
            AgentProposal("biologist", [v - spread for v in base], confidence=0.7),
        ]

    def test_deliberate_returns_report(self):
        tc = TriuneConsensus()
        report = tc.deliberate(self._proposals())
        assert report.quorum_reached is True

    def test_centroid_is_mean_of_proposals(self):
        tc = TriuneConsensus()
        props = self._proposals(spread=0.0)
        report = tc.deliberate(props)
        # All proposals identical → centroid == proposal
        for v in report.equilibrium.centroid_12d:
            assert abs(v - 0.5) < 1e-9

    def test_consensus_within_threshold(self):
        tc = TriuneConsensus(consensus_threshold=0.5)
        report = tc.deliberate(self._proposals(spread=0.01))
        assert report.equilibrium.is_consensus is True

    def test_no_consensus_on_high_divergence(self):
        tc = TriuneConsensus(consensus_threshold=0.1)
        report = tc.deliberate(self._proposals(spread=0.5))
        assert report.equilibrium.is_consensus is False

    def test_kl_divergence_computed(self):
        tc = TriuneConsensus()
        report = tc.deliberate(self._proposals())
        assert report.kl_divergence >= 0.0

    def test_history_accumulated(self):
        tc = TriuneConsensus()
        tc.deliberate(self._proposals())
        tc.deliberate(self._proposals(spread=0.1))
        assert len(tc.get_history()) == 2

    def test_empty_proposals_raises(self):
        tc = TriuneConsensus()
        with pytest.raises(ValueError):
            tc.deliberate([])

    def test_quorum_requires_two_agents(self):
        tc = TriuneConsensus()
        single = [AgentProposal("architect", [0.5] * 12, confidence=0.9)]
        report = tc.deliberate(single)
        assert report.quorum_reached is False
