"""Coverage batch Z30: kaggle_eval, plasma_theosophy, surreal_server_mcp, vault_integration, geometric_bridge."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# Module 1: integrations/kaggle_eval.py
# ---------------------------------------------------------------------------


class TestKaggleEvaluator:
    def test_extract_answer_simple(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.extract_answer(r"The answer is \boxed{42}.")
        assert result == "42"

    def test_extract_answer_returns_last_boxed(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.extract_answer(r"First \boxed{1}, then \boxed{7}.")
        assert result == "7"

    def test_extract_answer_returns_none_when_no_boxed(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.extract_answer("No answer here.")
        assert result is None

    def test_extract_answer_with_expression(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.extract_answer(r"\boxed{x^2 + 1}")
        assert result == "x^2 + 1"

    def test_extract_answer_nested_braces(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.extract_answer(r"\boxed{\frac{1}{2}}")
        assert result == r"\frac{1}{2}"

    def test_score_all_correct(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.score(["42", "7", "abc"], ["42", "7", "abc"])
        assert result["accuracy"] == pytest.approx(1.0)
        assert result["correct"] == 3
        assert result["total"] == 3

    def test_score_some_wrong(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.score(["1", "WRONG", "3"], ["1", "2", "3"])
        assert result["accuracy"] == pytest.approx(2 / 3)
        assert result["correct"] == 2

    def test_score_empty_lists(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.score([], [])
        assert result["accuracy"] == pytest.approx(0.0)
        assert result["total"] == 0

    def test_score_raises_on_length_mismatch(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        with pytest.raises(ValueError, match="same length"):
            ev.score(["1", "2"], ["1"])

    def test_score_strips_whitespace(self):
        from cohezion.integrations.kaggle_eval import KaggleEvaluator

        ev = KaggleEvaluator()
        result = ev.score(["  42  "], ["42"])
        assert result["correct"] == 1


# ---------------------------------------------------------------------------
# Module 2: compound/plasma_theosophy_synthesizer.py
# ---------------------------------------------------------------------------


class TestPlasmaTheosophySynthesizer:
    @pytest.fixture(autouse=True)
    def _mock_deps(self):
        with (
            patch("cohezion.compound.plasma_theosophy_synthesizer.DynamicModelRouter") as mock_router_cls,
            patch("cohezion.compound.plasma_theosophy_synthesizer.get_circuit") as mock_circuit_fn,
        ):
            self.mock_router = MagicMock()
            self.mock_router.execute_request = AsyncMock(
                return_value={"result": {"text": "Fohatic lines align with Hall effect."}}
            )
            mock_router_cls.return_value = self.mock_router

            self.mock_circuit = MagicMock()
            self.mock_circuit.allow_request.return_value = True
            mock_circuit_fn.return_value = self.mock_circuit
            yield

    def test_plasma_anomaly_data_model(self):
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData

        d = PlasmaAnomalyData(
            electron_density=0.5, magnetic_chirality=0.3, akashic_viscosity=0.7, fohatic_impulse=0.9
        )
        assert d.electron_density == pytest.approx(0.5)

    def test_analyze_anomaly_returns_string(self):
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        data = PlasmaAnomalyData(electron_density=0.5, magnetic_chirality=0.3, akashic_viscosity=0.7, fohatic_impulse=0.9)
        result = asyncio.run(synth.analyze_anomaly(data))
        assert isinstance(result, str)

    def test_analyze_anomaly_calls_execute_request(self):
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        asyncio.run(synth.analyze_anomaly(PlasmaAnomalyData(electron_density=0.1, magnetic_chirality=0.2, akashic_viscosity=0.3, fohatic_impulse=0.4)))
        self.mock_router.execute_request.assert_awaited_once()

    def test_analyze_anomaly_records_success(self):
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        asyncio.run(synth.analyze_anomaly(PlasmaAnomalyData(electron_density=0.1, magnetic_chirality=0.2, akashic_viscosity=0.3, fohatic_impulse=0.4)))
        self.mock_circuit.record_success.assert_called_once()

    def test_analyze_anomaly_circuit_open(self):
        self.mock_circuit.allow_request.return_value = False
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        result = asyncio.run(synth.analyze_anomaly(PlasmaAnomalyData(electron_density=0.1, magnetic_chirality=0.2, akashic_viscosity=0.3, fohatic_impulse=0.4)))
        assert "Circuit open" in result

    def test_analyze_anomaly_exception_records_failure(self):
        self.mock_router.execute_request = AsyncMock(side_effect=RuntimeError("model down"))
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        result = asyncio.run(synth.analyze_anomaly(PlasmaAnomalyData(electron_density=0.1, magnetic_chirality=0.2, akashic_viscosity=0.3, fohatic_impulse=0.4)))
        self.mock_circuit.record_failure.assert_called_once()
        assert "Synthesis failed" in result

    def test_analyze_anomaly_non_dict_result(self):
        self.mock_router.execute_request = AsyncMock(return_value={"result": "raw string"})
        from cohezion.compound.plasma_theosophy_synthesizer import PlasmaAnomalyData, PlasmaTheosophySynthesizer

        synth = PlasmaTheosophySynthesizer()
        result = asyncio.run(synth.analyze_anomaly(PlasmaAnomalyData(electron_density=0.1, magnetic_chirality=0.2, akashic_viscosity=0.3, fohatic_impulse=0.4)))
        assert result == "No content returned."


# ---------------------------------------------------------------------------
# Module 3: mcp/surreal_server_mcp.py
# ---------------------------------------------------------------------------


class TestSurrealServerMcp:
    @pytest.fixture(autouse=True)
    def _mock_server(self):
        self.mock_server = MagicMock()
        self.mock_server.query_nodes = AsyncMock(return_value=[{"id": "node1"}])
        self.mock_server.store_node = AsyncMock(return_value={"id": "new_node"})
        self.mock_server.search_similar = AsyncMock(return_value=[])
        self.mock_server.store_learning = AsyncMock(return_value={"id": "learning1"})
        self.mock_server.query_learnings = AsyncMock(return_value=[])
        self.mock_server.sync_key_learnings = AsyncMock(return_value={"synced": 5})

        with patch("cohezion.mcp.surreal_server_mcp.get_server", return_value=self.mock_server):
            yield

    def test_query_nodes_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import query_nodes

        result = asyncio.run(query_nodes(limit=5))
        self.mock_server.query_nodes.assert_awaited_once_with(5, None)
        assert result[0]["id"] == "node1"

    def test_query_nodes_with_filter(self):
        from cohezion.mcp.surreal_server_mcp import query_nodes

        asyncio.run(query_nodes(limit=3, filter_type="document"))
        self.mock_server.query_nodes.assert_awaited_once_with(3, "document")

    def test_store_node_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import store_node

        result = asyncio.run(store_node("content text", "agent", {"dim": 0.5}))
        self.mock_server.store_node.assert_awaited_once_with("content text", "agent", {"dim": 0.5})
        assert result["id"] == "new_node"

    def test_search_similar_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import search_similar

        asyncio.run(search_similar([0.1, 0.2, 0.3], limit=3))
        self.mock_server.search_similar.assert_awaited_once_with([0.1, 0.2, 0.3], 3)

    def test_store_learning_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import store_learning

        result = asyncio.run(store_learning("L-001", "Key Insight", "Details here", "HIHO", 0.9))
        self.mock_server.store_learning.assert_awaited_once_with("L-001", "Key Insight", "Details here", "HIHO", 0.9)

    def test_query_learnings_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import query_learnings

        asyncio.run(query_learnings(limit=10, min_score=0.5))
        self.mock_server.query_learnings.assert_awaited_once_with(10, 0.5)

    def test_sync_key_learnings_calls_server(self):
        from cohezion.mcp.surreal_server_mcp import sync_key_learnings

        result = asyncio.run(sync_key_learnings("path/to/KEY_LEARNINGS.md"))
        self.mock_server.sync_key_learnings.assert_awaited_once_with("path/to/KEY_LEARNINGS.md")
        assert result["synced"] == 5


# ---------------------------------------------------------------------------
# Module 4: compound/executor_helpers/vault_integration.py
# ---------------------------------------------------------------------------


class TestVaultIntegration:
    def test_fetch_experience_guidance_base_path(self):
        import sys

        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        mock_vault.get_experience_guidance.return_value = {"decisions": [], "patterns": []}

        # Lazy imports inside function — make them fail to trigger fallback path
        with patch.dict(
            sys.modules,
            {
                "cohezion.compound.guidance_enhancer": None,
                "cohezion.compound.trajectory_search": None,
                "cohezion.flume.experience_collector": None,
                "cohezion.flume.experience_encoder": None,
            },
        ):
            result = fetch_experience_guidance(mock_vault, "implement feature X")

        mock_vault.get_experience_guidance.assert_called_once_with(task_description="implement feature X", project="cohezion")
        assert "decisions" in result

    def test_fetch_experience_guidance_trajectory_exception_falls_back(self):
        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        base = {"guidance": "base_value"}
        mock_vault.get_experience_guidance.return_value = base

        # Patch to trigger the except block — ImportError on GuidanceEnhancer import
        with patch.dict(
            "sys.modules",
            {
                "cohezion.compound.guidance_enhancer": None,
                "cohezion.compound.trajectory_search": None,
                "cohezion.flume.experience_collector": None,
                "cohezion.flume.experience_encoder": None,
            },
        ):
            result = fetch_experience_guidance(mock_vault, "some task")

        assert result["guidance"] == "base_value"

    def test_fetch_experience_guidance_surreal_exception_falls_back(self):
        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        mock_vault.get_experience_guidance.return_value = {"base": True}

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = fetch_experience_guidance(mock_vault, "test task")

        # Should still return base guidance without crashing
        assert "base" in result

    def test_fetch_experience_guidance_uses_project_param(self):
        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        mock_vault.get_experience_guidance.return_value = {}

        fetch_experience_guidance(mock_vault, "task", project="my_project")
        mock_vault.get_experience_guidance.assert_called_once_with(task_description="task", project="my_project")

    def test_fetch_experience_guidance_trajectory_search_happy_path(self):
        import sys

        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        mock_vault.get_experience_guidance.return_value = {"guidance": "base"}

        # Mock all lazy imports to succeed
        mock_enhancer = MagicMock()
        mock_enhanced = MagicMock()
        mock_enhanced.similar_task_count = 3
        mock_enhanced.confidence = 0.85
        mock_enhancer_cls = MagicMock(return_value=mock_enhancer)
        mock_enhancer.enhance_guidance.return_value = mock_enhanced
        mock_enhancer.to_dict.return_value = {"guidance": "enhanced", "confidence": 0.85}

        mock_search = MagicMock()
        mock_search_cls = MagicMock(return_value=mock_search)
        mock_search.find_similar_trajectories.return_value = [{"task": "similar"}]

        mock_guidance_mod = MagicMock()
        mock_guidance_mod.GuidanceEnhancer = mock_enhancer_cls

        mock_search_mod = MagicMock()
        mock_search_mod.TrajectorySearchEngine = mock_search_cls

        mock_collector_mod = MagicMock()
        mock_encoder_mod = MagicMock()

        with (
            patch.dict(
                sys.modules,
                {
                    "cohezion.compound.guidance_enhancer": mock_guidance_mod,
                    "cohezion.compound.trajectory_search": mock_search_mod,
                    "cohezion.flume.experience_collector": mock_collector_mod,
                    "cohezion.flume.experience_encoder": mock_encoder_mod,
                },
            ),
            patch("urllib.request.urlopen", side_effect=OSError("no surreal")),
        ):
            result = fetch_experience_guidance(mock_vault, "implement cache")

        mock_enhancer.to_dict.assert_called_once_with(mock_enhanced)
        assert "confidence" in result

    def test_fetch_experience_guidance_enriches_with_surreal_data(self):
        import json
        import sys

        from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance

        mock_vault = MagicMock()
        mock_vault.get_experience_guidance.return_value = {}

        # Mock urlopen to return SurrealDB-like response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            [{"status": "OK", "result": [{"skill": "summarize", "should_refine": True}]}]
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        with (
            patch.dict(sys.modules, {"cohezion.compound.guidance_enhancer": None, "cohezion.compound.trajectory_search": None, "cohezion.flume.experience_collector": None, "cohezion.flume.experience_encoder": None}),
            patch("urllib.request.urlopen", return_value=mock_response),
        ):
            result = fetch_experience_guidance(mock_vault, "task")

        assert "recent_retrospections" in result
        assert result["recent_retrospections"][0]["skill"] == "summarize"


# ---------------------------------------------------------------------------
# Module 5: flume/geometric_bridge.py
# ---------------------------------------------------------------------------


class TestGeometricLatentBridge:
    def _make_bridge(self):
        from cohezion.flume.geometric_bridge import GeometricLatentBridge

        mock_projector = MagicMock()
        lift_result = MagicMock()
        lift_result.vertex_type = "A"
        mock_projector.lift.return_value = lift_result
        mock_projector.project.return_value = np.array([1.0, 0.0, 0.0])
        return GeometricLatentBridge(projector=mock_projector), mock_projector

    def test_init_symmetry_projection_shape(self):
        from cohezion.flume.geometric_bridge import GeometricLatentBridge

        bridge, _ = self._make_bridge()
        assert bridge.projection_weight.shape == (4, 256)

    def test_init_projection_normalized_rows(self):
        from cohezion.flume.geometric_bridge import GeometricLatentBridge

        bridge, _ = self._make_bridge()
        norms = torch.norm(bridge.projection_weight, dim=1)
        assert torch.allclose(norms, torch.ones(4), atol=1e-5)

    def test_map_to_regime_calls_projector_lift(self):
        bridge, mock_projector = self._make_bridge()
        latent = torch.randn(256)
        vertex_type = bridge.map_to_regime(latent)
        mock_projector.lift.assert_called_once()
        assert vertex_type == "A"

    def test_map_to_regime_handles_2d_input(self):
        bridge, _ = self._make_bridge()
        latent = torch.randn(1, 256)  # 2D input
        # Should not crash — handles ndim > 1 case
        bridge.map_to_regime(latent)

    def test_project_to_coordinates_returns_ndarray(self):
        bridge, _ = self._make_bridge()
        latent = torch.randn(256)
        coords = bridge.project_to_coordinates(latent)
        assert isinstance(coords, np.ndarray)
        assert coords.shape == (3,)

    def test_project_to_coordinates_handles_2d_input(self):
        bridge, _ = self._make_bridge()
        latent = torch.randn(2, 256)  # 2D input
        bridge.project_to_coordinates(latent)  # should not crash

    def test_get_coherence_score_match(self):
        bridge, mock_projector = self._make_bridge()
        # lift returns vertex_type="A"
        latent = torch.randn(256)
        score = bridge.get_coherence_score(latent, "A")
        assert score == pytest.approx(1.0)

    def test_get_coherence_score_mismatch(self):
        bridge, mock_projector = self._make_bridge()
        latent = torch.randn(256)
        score = bridge.get_coherence_score(latent, "B")
        assert score == pytest.approx(0.0)

    def test_save_weights_creates_file(self, tmp_path):
        bridge, _ = self._make_bridge()
        path = str(tmp_path / "weights.pt")
        bridge.save_weights(path)
        assert Path(path).exists()

    def test_load_weights_from_file(self, tmp_path):
        from cohezion.flume.geometric_bridge import GeometricLatentBridge

        path = str(tmp_path / "weights.pt")
        w = torch.randn(4, 256)
        torch.save(w, path)
        bridge = GeometricLatentBridge(weights_path=path)
        assert bridge.projection_weight.shape == (4, 256)
