"""Tests for JourneyTracker EVO dual-write: SurrealDB + Obsidian vault."""

import time
from unittest.mock import MagicMock


def _make_voyage(**kwargs):
    from cohezion.evo import ExperientialVoyage

    defaults = dict(
        voyage_id="test-voyage-001",
        agent_id="evo-agent-01",
        journey_id="journey-run-42",
        phi_score=0.75,
        modalities_used=["image", "text"],
        skill_refinements=[],
        latent_snapshot=[0.5] * 16,
        started_at=time.time() - 1.0,
        completed_at=time.time(),
    )
    defaults.update(kwargs)
    return ExperientialVoyage(**defaults)


class TestExperientialVoyage:
    def test_phi_from_coherence_hiho_peak(self):
        """phi_from_coherence(0.5) == 1.0 (HIHO attractor peak)."""
        from cohezion.evo import phi_from_coherence

        assert phi_from_coherence(0.5) == 1.0

    def test_phi_from_coherence_boundaries(self):
        """phi_from_coherence returns 0.0 at both degenerate extremes."""
        from cohezion.evo import phi_from_coherence

        assert phi_from_coherence(0.0) == 0.0
        assert phi_from_coherence(1.0) == 0.0

    def test_phi_from_coherence_clamped(self):
        """phi_from_coherence clamps inputs outside [0,1]."""
        from cohezion.evo import phi_from_coherence

        assert phi_from_coherence(-0.5) == phi_from_coherence(0.0)
        assert phi_from_coherence(2.0) == phi_from_coherence(1.0)

    def test_is_degenerate_flag(self):
        """is_degenerate is True when phi < 0.3."""
        voyage_degen = _make_voyage(phi_score=0.1)
        voyage_ok = _make_voyage(phi_score=0.75)
        assert voyage_degen.is_degenerate is True
        assert voyage_ok.is_degenerate is False

    def test_is_multimodal(self):
        """is_multimodal is True when more than one modality used."""
        voyage = _make_voyage(modalities_used=["image", "text"])
        voyage_single = _make_voyage(modalities_used=["text"])
        assert voyage.is_multimodal is True
        assert voyage_single.is_multimodal is False

    def test_duration_seconds(self):
        """duration_seconds = completed_at - started_at."""
        now = time.time()
        voyage = _make_voyage(started_at=now - 5.0, completed_at=now)
        assert abs(voyage.duration_seconds - 5.0) < 0.01


class TestJourneyTrackerEVOWrite:
    def _tracker(self, mcp_client=None):
        from cohezion.compound.journey_tracker import JourneyTracker

        return JourneyTracker(mcp_client=mcp_client)

    def test_emit_evo_voyage_appends_to_write_buffer(self):
        """emit_evo_voyage() appends SurQL to _write_buffer."""
        tracker = self._tracker()
        voyage = _make_voyage(phi_score=0.75)
        initial_buf_len = len(tracker._write_buffer)
        tracker.emit_evo_voyage(voyage)
        assert len(tracker._write_buffer) == initial_buf_len + 1
        assert "evo_journey" in tracker._write_buffer[-1]
        assert "test-voyage-001" in tracker._write_buffer[-1]

    def test_emit_evo_voyage_surql_contains_agent_id(self):
        """SurQL entry contains agent_id for identification."""
        tracker = self._tracker()
        voyage = _make_voyage(agent_id="test-agent-XYZ")
        tracker.emit_evo_voyage(voyage)
        assert "test-agent-XYZ" in tracker._write_buffer[-1]

    def test_emit_evo_voyage_calls_vault_mcp(self):
        """emit_evo_voyage() calls mcp_client.vault_log_experiment when mcp_client is set."""
        mock_mcp = MagicMock()
        tracker = self._tracker(mcp_client=mock_mcp)
        voyage = _make_voyage(phi_score=0.75, modalities_used=["text"])
        tracker.emit_evo_voyage(voyage)
        mock_mcp.vault_log_experiment.assert_called_once()
        call_kwargs = mock_mcp.vault_log_experiment.call_args
        # phi_score should appear in results
        results = call_kwargs[1].get("results") or call_kwargs[0][3]
        assert results["phi_score"] == 0.75

    def test_emit_evo_voyage_skips_vault_when_no_mcp_client(self):
        """emit_evo_voyage() silently skips vault write when mcp_client is None."""
        tracker = self._tracker(mcp_client=None)
        voyage = _make_voyage()
        tracker.emit_evo_voyage(voyage)  # must not raise
        # buffer was written (SurrealDB), but vault was skipped (no error)

    def test_emit_evo_voyage_vault_failure_is_silent(self):
        """Vault write failure is non-blocking and does not propagate."""
        mock_mcp = MagicMock()
        mock_mcp.vault_log_experiment.side_effect = RuntimeError("vault down")
        tracker = self._tracker(mcp_client=mock_mcp)
        voyage = _make_voyage()
        tracker.emit_evo_voyage(voyage)  # must not raise even though vault fails

    def test_track_evo_step_returns_trajectory_point(self):
        """track_evo_step() returns a TrajectoryPoint with correct coherence."""
        from cohezion.compound.journey_tracker import TrajectoryPoint

        tracker = self._tracker()
        point = tracker.track_evo_step(
            task_description="synthesize EVO journey",
            operation_type="transform",
            coherence=0.6,
            efficiency=0.8,
        )
        assert isinstance(point, TrajectoryPoint)
        assert point.coherence == 0.6
        assert point.efficiency == 0.8

    def test_mcp_client_defaults_to_none(self):
        """JourneyTracker() without mcp_client has _mcp_client = None."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        assert tracker._mcp_client is None
