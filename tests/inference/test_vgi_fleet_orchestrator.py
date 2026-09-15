"""Tests for VGIFleetOrchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cohezion.inference.vgi_fleet_orchestrator import (
    ACTIVE_COMPETITIONS,
    VGIFleetOrchestrator,
)


class TestVGIFleetOrchestrator:
    def test_active_competitions_strict_whitelist(self) -> None:
        """Verify only active competitions are in whitelist and Pokemon is excluded."""
        assert "arc-prize-2026-arc-agi-3" in ACTIVE_COMPETITIONS
        assert "arc-prize-2026-arc-agi-2" in ACTIVE_COMPETITIONS
        assert "rsna-knee-abnormality-detection" in ACTIVE_COMPETITIONS
        assert "biohub-cell-tracking-during-development" in ACTIVE_COMPETITIONS
        assert "kaggriculture" in ACTIVE_COMPETITIONS
        assert not any("pokemon" in comp.lower() for comp in ACTIVE_COMPETITIONS)

    def test_extract_spatial_invariants_local(self) -> None:
        orchestrator = VGIFleetOrchestrator()
        grid = [
            [0, 1, 0],
            [1, 2, 1],
            [0, 1, 0],
        ]
        inv = orchestrator.extract_spatial_invariants_local(grid)
        assert inv["height"] == 3
        assert inv["width"] == 3
        assert inv["color_counts"][0] == 4
        assert inv["color_counts"][1] == 4
        assert inv["color_counts"][2] == 1
        # Least frequent non-background color first
        assert inv["rarity_order"] == [2, 1]
        assert inv["bounding_boxes"][2] == {
            "min_r": 1,
            "max_r": 1,
            "min_c": 1,
            "max_c": 1,
        }

    def test_verify_candidate_code_autoharness(self) -> None:
        orchestrator = VGIFleetOrchestrator()
        valid_code = "def transform(grid: list[list[int]]) -> list[list[int]]:\n    return grid"
        res_valid = orchestrator.verify_candidate_code_autoharness(valid_code)
        assert res_valid.valid
        assert len(res_valid.violations) == 0

        # Disallowed dangerous call
        invalid_code = "def transform(grid):\n    return eval('grid')"
        res_invalid = orchestrator.verify_candidate_code_autoharness(invalid_code)
        assert not res_invalid.valid
        assert any("eval" in v for v in res_invalid.violations)

    def test_execute_vgi_cycle_mocked_cloud(self) -> None:
        orchestrator = VGIFleetOrchestrator()
        sample_grid = [[1, 2], [3, 4]]

        with patch.object(
            orchestrator,
            "synthesize_code_as_perception_cloud",
            return_value=(
                "def transform(grid: list[list[int]]) -> list[list[int]]:\n    return [[c * 2 for c in row] for row in grid]",
                "mock_cloud_model",
            ),
        ):
            res = orchestrator.execute_vgi_cycle(
                competition="arc-prize-2026-arc-agi-3",
                task_id="test-task-1",
                task_desc="Double pixel values",
                grid=sample_grid,
            )
            assert res.competition == "arc-prize-2026-arc-agi-3"
            assert res.task_id == "test-task-1"
            assert res.autoharness_verified
            assert res.execution_success
            assert "Transformed grid shape: 2x2" in res.execution_output
            assert "mock_cloud_model" in res.model_chain

    def test_check_fleet_health_mock(self) -> None:
        orchestrator = VGIFleetOrchestrator()
        with (
            patch("httpx.get") as mock_get,
        ):
            # Lemonade response
            mock_res_lemonade = MagicMock()
            mock_res_lemonade.status_code = 200
            mock_res_lemonade.json.return_value = {
                "data": [{"id": "deepseek-r1-0528-8b-FLM"}, {"id": "Qwen3-Coder-30B-GGUF"}]
            }
            # Ollama response
            mock_res_ollama = MagicMock()
            mock_res_ollama.status_code = 200
            mock_res_ollama.json.return_value = {"models": [{"name": "qwen3.5:397b-cloud"}]}

            def side_effect(url, **kwargs):
                if "13305" in url:
                    return mock_res_lemonade
                return mock_res_ollama

            mock_get.side_effect = side_effect
            health = orchestrator.check_fleet_health()
            assert health.local_npu_healthy
            assert health.local_igpu_healthy
            assert health.cloud_healthy
            assert "deepseek-r1-0528-8b-FLM" in health.loaded_models
            assert "qwen3.5:397b-cloud" in health.cloud_models
