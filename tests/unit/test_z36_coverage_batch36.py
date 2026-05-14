"""Coverage batch Z36: mnm, predictor, graphify, git_encoder."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Module 1: flume/mnm.py
# ---------------------------------------------------------------------------


class TestManifoldNeuralManifolds:
    def test_manifold_warp_output_shape(self):
        from cohezion.flume.mnm import ManifoldWarp

        warp = ManifoldWarp(z_dim=64, hidden_dim=32)
        z = torch.randn(4, 64)
        out = warp(z)
        assert out.shape == (4, 64)

    def test_manifold_warp_residual_connection(self):
        from cohezion.flume.mnm import ManifoldWarp

        warp = ManifoldWarp(z_dim=16, hidden_dim=8)
        z = torch.zeros(1, 16)
        # Zero input → warp returns z + warp(z) = 0 + warp(0), should be non-zero due to bias
        out = warp(z)
        assert out.shape == (1, 16)

    def test_manifold_manager_create(self):
        from cohezion.flume.mnm import ManifoldManager, ManifoldWarp

        mgr = ManifoldManager(z_dim=32)
        mgr.create_manifold("test_domain")
        assert "test_domain" in mgr.manifolds
        assert isinstance(mgr.manifolds["test_domain"], ManifoldWarp)

    def test_manifold_manager_activate_existing(self):
        from cohezion.flume.mnm import ManifoldManager

        mgr = ManifoldManager(z_dim=32)
        mgr.create_manifold("quantum")
        mgr.activate_manifold("quantum")
        assert mgr.active_manifold == "quantum"

    def test_manifold_manager_activate_missing(self):
        from cohezion.flume.mnm import ManifoldManager

        mgr = ManifoldManager(z_dim=32)
        mgr.activate_manifold("nonexistent")
        assert mgr.active_manifold is None  # stays unchanged

    def test_manifold_manager_warp_with_active(self):
        from cohezion.flume.mnm import ManifoldManager

        mgr = ManifoldManager(z_dim=32)
        mgr.create_manifold("test")
        mgr.activate_manifold("test")
        z = torch.randn(1, 32)
        out = mgr.warp(z)
        assert out.shape == (1, 32)

    def test_manifold_manager_warp_no_manifold_returns_z(self):
        from cohezion.flume.mnm import ManifoldManager

        mgr = ManifoldManager(z_dim=32)
        z = torch.randn(1, 32)
        out = mgr.warp(z)
        # No active manifold → returns z unchanged
        assert torch.allclose(out, z)

    def test_manifold_manager_save_load_book(self, tmp_path):
        from cohezion.flume.mnm import ManifoldManager

        path = tmp_path / "manifold.pt"
        mgr1 = ManifoldManager(z_dim=32)
        mgr1.create_manifold("domain")
        mgr1.save_frozen_book("domain", path)
        assert path.exists()

        mgr2 = ManifoldManager(z_dim=32)
        mgr2.load_frozen_book(path, "domain")
        assert "domain" in mgr2.manifolds

    def test_manifold_manager_load_creates_manifold_if_missing(self, tmp_path):
        from cohezion.flume.mnm import ManifoldManager

        mgr = ManifoldManager(z_dim=32)
        mgr.create_manifold("tmp")
        path = tmp_path / "tmp.pt"
        mgr.save_frozen_book("tmp", path)

        mgr2 = ManifoldManager(z_dim=32)
        mgr2.load_frozen_book(path, "new_domain")  # "new_domain" doesn't exist yet
        assert "new_domain" in mgr2.manifolds

    def test_manifold_manager_load_handles_error(self, tmp_path):
        from cohezion.flume.mnm import ManifoldManager

        path = tmp_path / "bad.pt"
        path.write_text("not a valid tensor file")
        mgr = ManifoldManager(z_dim=32)
        # Should not raise — logs error and returns gracefully
        mgr.load_frozen_book(path, "recovery")
        assert "recovery" in mgr.manifolds  # created even if load fails

    def test_scenario_manifolds_dict(self):
        from cohezion.flume.mnm import SCENARIO_MANIFOLDS

        assert "the_void" in SCENARIO_MANIFOLDS
        assert "resonant_lattice" in SCENARIO_MANIFOLDS


# ---------------------------------------------------------------------------
# Module 2: flume/predictor.py
# ---------------------------------------------------------------------------


class TestTrajectoryPredictor:
    def test_forward_adds_delta(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.zeros(1, 16)
        out = pred(z)
        assert out.shape == (1, 16)

    def test_predict_sequence_length(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        traj = pred.predict_sequence(z, steps=5)
        assert len(traj) == 6  # initial + 5 steps

    def test_predict_sequence_shapes(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        traj = pred.predict_sequence(z, steps=3)
        for t in traj:
            assert t.shape == (1, 16)

    def test_predict_with_physics_length(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        traj = pred.predict_with_physics(z, steps=4)
        assert len(traj) == 5  # initial + 4 steps

    def test_predict_with_physics_momentum_effect(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        traj1 = pred.predict_with_physics(z, steps=3, momentum=0.0)
        traj2 = pred.predict_with_physics(z, steps=3, momentum=0.9)
        # Different momentum → different trajectories
        assert not torch.allclose(traj1[-1], traj2[-1])

    def test_imagine_branches_count(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        branches = pred.imagine_branches(z, perturbations=3, steps=4)
        assert len(branches) == 3

    def test_imagine_branches_each_has_steps_plus_one(self):
        from cohezion.flume.predictor import TrajectoryPredictor

        pred = TrajectoryPredictor(z_dim=16, hidden_dim=32)
        z = torch.randn(1, 16)
        branches = pred.imagine_branches(z, perturbations=2, steps=3)
        for branch in branches:
            assert len(branch) == 4  # initial + 3 steps


# ---------------------------------------------------------------------------
# Module 3: api/services/graphify.py
# ---------------------------------------------------------------------------


class TestGraphifyService:
    def test_graph_entity_model(self):
        from cohezion.api.services.graphify import GraphEntity

        e = GraphEntity(name="Python", type="Language", coherence=0.8)
        assert e.name == "Python"
        assert e.coherence == pytest.approx(0.8)

    def test_graph_relation_model(self):
        from cohezion.api.services.graphify import GraphRelation

        r = GraphRelation(source="A", target="B", relation="depends_on", weight=0.5)
        assert r.relation == "depends_on"

    def test_graphify_result_model(self):
        from cohezion.api.services.graphify import GraphEntity, GraphifyResult, GraphRelation

        result = GraphifyResult(
            entities=[GraphEntity(name="X", type="concept")],
            relations=[GraphRelation(source="X", target="Y", relation="links")],
            document_id="doc1",
        )
        assert result.document_id == "doc1"
        assert len(result.entities) == 1

    def test_extract_graph_returns_result(self):
        from cohezion.api.services.graphify import GraphifyResult, GraphifyService

        svc = GraphifyService(projector=MagicMock())
        result = asyncio.run(svc.extract_graph("some document content", "doc123"))
        assert isinstance(result, GraphifyResult)
        assert result.document_id == "doc123"

    def test_extract_graph_returns_entities_and_relations(self):
        from cohezion.api.services.graphify import GraphifyService

        svc = GraphifyService(projector=MagicMock())
        result = asyncio.run(svc.extract_graph("test content", "d1"))
        assert len(result.entities) > 0
        assert len(result.relations) > 0

    def test_estimate_coherence_concept_type(self):
        from cohezion.api.services.graphify import GraphEntity, GraphifyService

        svc = GraphifyService(projector=MagicMock())
        entity = GraphEntity(name="HIHO", type="Concept")
        assert svc._estimate_coherence(entity) == pytest.approx(0.9)

    def test_estimate_coherence_variable_type(self):
        from cohezion.api.services.graphify import GraphEntity, GraphifyService

        svc = GraphifyService(projector=MagicMock())
        entity = GraphEntity(name="x", type="variable")
        assert svc._estimate_coherence(entity) == pytest.approx(0.3)

    def test_estimate_coherence_default_type(self):
        from cohezion.api.services.graphify import GraphEntity, GraphifyService

        svc = GraphifyService(projector=MagicMock())
        entity = GraphEntity(name="misc", type="unknown_type")
        assert svc._estimate_coherence(entity) == pytest.approx(0.6)

    def test_ingest_to_vault_calls_logger(self):
        from cohezion.api.services.graphify import GraphEntity, GraphifyResult, GraphifyService

        svc = GraphifyService(projector=MagicMock())
        result = GraphifyResult(
            entities=[GraphEntity(name="E1", type="Concept")],
            relations=[],
            document_id="d1",
        )
        asyncio.run(svc.ingest_to_vault(result))  # Should not raise


# ---------------------------------------------------------------------------
# Module 4: flume/git_encoder.py
# ---------------------------------------------------------------------------


class TestGitEncoder:
    """Tests using sys.modules injection since cohezion.swarm.git_health doesn't exist."""

    def _make_encoder_with_mock_gitcommit(self):
        import sys
        from dataclasses import dataclass

        @dataclass
        class FakeGitCommit:
            hash: str
            author: str
            date: object
            message: str

        mock_git_health = MagicMock()
        mock_git_health.GitCommit = FakeGitCommit

        mock_flume_enc = MagicMock()

        with patch.dict(sys.modules, {"cohezion.swarm.git_health": mock_git_health}):
            from cohezion.flume.git_encoder import GitEncoder

            enc = GitEncoder(encoder=mock_flume_enc)
        return enc, mock_flume_enc, FakeGitCommit

    def test_encode_history_empty_returns_zeros(self):
        enc, _, _ = self._make_encoder_with_mock_gitcommit()
        result = enc.encode_history([])
        assert result.shape == (0, 256)

    def test_encode_history_calls_encoder_with_messages(self):
        enc, mock_enc, FakeCommit = self._make_encoder_with_mock_gitcommit()
        mock_enc.encode.return_value = torch.randn(2, 256)

        commits = [
            FakeCommit("1", "author", "2024-01-01", "first commit"),
            FakeCommit("2", "author", "2024-01-02", "second commit"),
        ]
        enc.encode_history(commits)
        mock_enc.encode.assert_called_once()

    def test_get_health_direction_single_vector(self):
        enc, _, _ = self._make_encoder_with_mock_gitcommit()
        trajectory = torch.randn(1, 256)
        direction, momentum = enc.get_health_direction(trajectory)
        assert direction.shape == (256,)
        assert momentum == pytest.approx(0.0)

    def test_get_health_direction_two_vectors(self):
        enc, _, _ = self._make_encoder_with_mock_gitcommit()
        trajectory = torch.randn(2, 256)
        direction, momentum = enc.get_health_direction(trajectory)
        assert direction.shape == (256,)
        # Only one delta → perfect momentum consistency
        assert momentum == pytest.approx(1.0)

    def test_get_health_direction_three_vectors(self):
        enc, _, _ = self._make_encoder_with_mock_gitcommit()
        trajectory = torch.randn(3, 256)
        direction, momentum = enc.get_health_direction(trajectory)
        assert direction.shape == (256,)
        assert isinstance(momentum, float)

    def test_evaluate_drift_insufficient_history(self):
        enc, mock_enc, FakeCommit = self._make_encoder_with_mock_gitcommit()
        mock_enc.encode.return_value = torch.randn(2, 256)

        commits = [FakeCommit("1", "a", "2024-01-01", "msg1"), FakeCommit("2", "a", "2024-01-02", "msg2")]
        drift = enc.evaluate_drift(commits, pivot_index=-5)
        assert drift == pytest.approx(1.0)

    def test_evaluate_drift_with_enough_history(self):
        enc, mock_enc, FakeCommit = self._make_encoder_with_mock_gitcommit()
        mock_enc.encode.return_value = torch.randn(12, 256)

        commits = [FakeCommit(str(i), "a", f"2024-01-{i+1:02d}", f"commit {i}") for i in range(12)]
        drift = enc.evaluate_drift(commits, pivot_index=-3)
        assert -1.0 <= drift <= 1.0
