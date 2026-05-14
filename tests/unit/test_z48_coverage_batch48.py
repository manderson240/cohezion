"""Coverage batch Z48: api_helpers, triune_consensus."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: api/_helpers.py
# ---------------------------------------------------------------------------


class TestApiHelpers:
    def test_compute_coherence_all_half(self):
        from cohezion.api._helpers import compute_coherence

        z = [0.5] * 256
        coherence = compute_coherence(z)
        assert coherence == pytest.approx(1.0)

    def test_compute_coherence_all_zeros(self):
        from cohezion.api._helpers import compute_coherence

        z = [0.0] * 256
        coherence = compute_coherence(z)
        assert 0.0 <= coherence <= 1.0

    def test_compute_coherence_mixed(self):
        from cohezion.api._helpers import compute_coherence

        z = [0.5 if i % 2 == 0 else 0.0 for i in range(256)]
        coherence = compute_coherence(z)
        assert 0.0 <= coherence <= 1.0

    def test_compute_coherence_custom_z_dim(self):
        from cohezion.api._helpers import compute_coherence

        z = [0.5] * 128
        coherence = compute_coherence(z, z_dim=128)
        assert coherence == pytest.approx(1.0)

    def test_get_vae_returns_trainer(self):
        from cohezion.api._helpers import get_vae

        mock_trainer = MagicMock()
        with patch("cohezion.api._vae_trainer", mock_trainer, create=True):
            import cohezion.api as api_mod

            api_mod._vae_trainer = mock_trainer
            result = get_vae()
        assert result is mock_trainer

    def test_get_rl_policy_returns_policy(self):
        from cohezion.api._helpers import get_rl_policy

        mock_policy = MagicMock()
        import cohezion.api as api_mod

        api_mod._rl_policy = mock_policy
        result = get_rl_policy()
        assert result is mock_policy
        api_mod._rl_policy = None  # cleanup


# ---------------------------------------------------------------------------
# Module 2: swarm/triune_consensus.py
# ---------------------------------------------------------------------------


class TestTriuneConsensus:
    def _make_council(self, threshold=0.5):
        from cohezion.swarm.triune_consensus import TriuneConsensus

        return TriuneConsensus(consensus_threshold=threshold)

    def _make_proposal(self, agent_id, state=None, confidence=0.8):
        from cohezion.swarm.triune_consensus import AgentProposal

        if state is None:
            state = [0.5] * 12
        return AgentProposal(agent_id=agent_id, state_12d=state, confidence=confidence)

    def test_agent_proposal_dataclass(self):
        p = self._make_proposal("architect")
        assert p.agent_id == "architect"
        assert len(p.state_12d) == 12

    def test_geometric_equilibrium_to_dict(self):
        from cohezion.swarm.triune_consensus import GeometricEquilibrium

        eq = GeometricEquilibrium(centroid_12d=[0.5] * 12, max_divergence=0.1, is_consensus=True)
        d = eq.to_dict()
        assert "centroid_12d" in d
        assert d["is_consensus"] is True

    def test_deliberate_three_identical_proposals(self):
        council = self._make_council()
        proposals = [self._make_proposal(a) for a in ["architect", "engineer", "biologist"]]
        report = council.deliberate(proposals)
        assert report.equilibrium.is_consensus is True
        assert report.equilibrium.max_divergence == pytest.approx(0.0)
        assert report.quorum_reached is True

    def test_deliberate_divergent_proposals(self):
        council = self._make_council(threshold=0.1)
        p1 = self._make_proposal("architect", state=[0.0] * 12)
        p2 = self._make_proposal("engineer", state=[1.0] * 12)
        p3 = self._make_proposal("biologist", state=[0.5] * 12)
        report = council.deliberate([p1, p2, p3])
        assert report.equilibrium.is_consensus is False
        assert report.equilibrium.max_divergence > 0

    def test_deliberate_single_proposal_no_quorum(self):
        council = self._make_council()
        report = council.deliberate([self._make_proposal("architect")])
        assert report.quorum_reached is False
        assert report.equilibrium.is_consensus is False

    def test_deliberate_raises_on_empty(self):
        council = self._make_council()
        with pytest.raises(ValueError):
            council.deliberate([])

    def test_deliberate_computes_centroid(self):
        council = self._make_council()
        p1 = self._make_proposal("a", state=[0.0] * 12)
        p2 = self._make_proposal("b", state=[1.0] * 12)
        report = council.deliberate([p1, p2])
        centroid = report.equilibrium.centroid_12d
        assert all(abs(c - 0.5) < 1e-5 for c in centroid)

    def test_kl_divergence_uniform_is_zero(self):
        council = self._make_council()
        kl = council._compute_kl_divergence([0.5, 0.5])
        assert abs(kl) < 1e-5

    def test_kl_divergence_single_is_zero(self):
        council = self._make_council()
        kl = council._compute_kl_divergence([1.0])
        assert kl == pytest.approx(0.0)

    def test_history_accumulates(self):
        council = self._make_council()
        proposals = [self._make_proposal(a) for a in ["architect", "engineer"]]
        council.deliberate(proposals)
        council.deliberate(proposals)
        assert len(council.get_history()) == 2

    def test_report_to_dict(self):
        council = self._make_council()
        proposals = [self._make_proposal(a) for a in ["architect", "engineer"]]
        report = council.deliberate(proposals)
        d = report.to_dict()
        assert "equilibrium" in d
        assert "kl_divergence" in d
