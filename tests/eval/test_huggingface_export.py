"""Tests for eval/huggingface_export module — JSONL export and dataset card generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.eval.huggingface_export import (
    HuggingFaceDatasetSpec,
    HuggingFaceExporter,
    _infer_archetype,
    _sanitize_for_json,
    generate_dataset_card,
)


class TestHuggingFaceDatasetSpec:
    """Tests for HuggingFaceDatasetSpec dataclass."""

    def test_defaults(self):
        """Default values are sensible."""
        spec = HuggingFaceDatasetSpec(dataset_name="cohezion/test")
        assert spec.version == "1.0.0"
        assert spec.license == "apache-2.0"
        assert spec.task_tags == ("evoloader", "reinforcement-learning", "autonomous-agents", "flume")

    def test_custom_values(self):
        """Custom values are stored."""
        spec = HuggingFaceDatasetSpec(
            dataset_name="cohezion/flume-v1",
            version="2.0.0",
            arxiv_id="2401.12345",
            paper_title="FLUME Journey Benchmark",
        )
        assert spec.version == "2.0.0"
        assert spec.arxiv_id == "2401.12345"


class TestSanitizeForJson:
    """Tests for _sanitize_for_json helper."""

    def test_numpy_float(self):
        """numpy float64 is converted to Python float."""
        import numpy as np

        result = _sanitize_for_json(np.float64(3.14))
        assert isinstance(result, float)
        assert result == pytest.approx(3.14)

    def test_numpy_int(self):
        """numpy int64 is converted to Python int."""
        import numpy as np

        result = _sanitize_for_json(np.int64(42))
        assert isinstance(result, int)
        assert result == 42

    def test_numpy_array(self):
        """numpy array is converted to list."""
        import numpy as np

        result = _sanitize_for_json(np.array([1.0, 2.0, 3.0]))
        assert result == [1.0, 2.0, 3.0]

    def test_nested_dict(self):
        """Nested dict is recursively sanitized."""
        import numpy as np

        d = {"a": np.float64(1.0), "b": {"c": np.int64(2)}}
        result = _sanitize_for_json(d)
        assert result["a"] == 1.0
        assert result["b"]["c"] == 2

    def test_nan_becomes_none(self):
        """NaN values become None."""
        result = _sanitize_for_json(float("nan"))
        assert result is None

    def test_inf_becomes_none(self):
        """Inf values become None."""
        result = _sanitize_for_json(float("inf"))
        assert result is None

    def test_tuple_converted_to_list(self):
        """Tuples are converted to lists."""
        result = _sanitize_for_json((1, 2, 3))
        assert result == [1, 2, 3]


class TestInferArchetype:
    """Tests for _infer_archetype helper."""

    def test_hiho(self):
        assert _infer_archetype({"task_name": "cohezion/hiho_basin_easy"}) == "HIHO_BASIN"

    def test_triune(self):
        assert _infer_archetype({"task_name": "cohezion/triune_balance_medium"}) == "TRIUNE_BALANCE"

    def test_exotic(self):
        assert _infer_archetype({"task_name": "cohezion/exotic_charge_hard"}) == "EXOTIC_CHARGE"

    def test_kordylewski(self):
        assert _infer_archetype({"task_name": "cohezion/kordylewski_orbit_easy"}) == "KORDYLEWSKI_ORBIT"

    def test_interruption(self):
        assert _infer_archetype({"task_name": "cohezion/interruption_recovery_medium"}) == "INTERRUPTION_RECOVERY"

    def test_unknown_defaults_hiho(self):
        assert _infer_archetype({"task_name": "unknown_task"}) == "HIHO_BASIN"


class TestHuggingFaceExporter:
    """Tests for HuggingFaceExporter."""

    @pytest.fixture
    def exporter(self):
        return HuggingFaceExporter(
            dataset_name="cohezion/flume-test-v0",
            dataset_version="1.0.0",
        )

    @pytest.fixture
    def sample_episodes(self):
        return [
            {
                "episode_id": "ep_1",
                "run_id": "run_001",
                "task_name": "cohezion/hiho_basin_easy",
                "archetype": "HIHO_BASIN",
                "difficulty": "easy",
                "reward": 1.5,
                "mean_coherence": 0.8,
                "final_coherence": 0.85,
                "success": True,
                "steps": 150,
                "duration_seconds": 2.5,
                "timestamp": 1700000000.0,
                "metrics": {
                    "coherence": {"mean": 0.8, "std": 0.05, "ci_lower": 0.75, "ci_upper": 0.85},
                },
                "biography": [
                    {"coherence": 0.5, "phase": 0.0},
                    {"coherence": 0.6, "phase": 0.1},
                ],
            },
            {
                "episode_id": "ep_2",
                "run_id": "run_001",
                "task_name": "cohezion/hiho_basin_easy",
                "archetype": "HIHO_BASIN",
                "difficulty": "easy",
                "reward": 1.2,
                "mean_coherence": 0.75,
                "final_coherence": 0.78,
                "success": True,
                "steps": 180,
                "duration_seconds": 3.0,
                "timestamp": 1700000010.0,
                "metrics": {},
                "biography": [],
            },
        ]

    def test_export_jsonl(self, exporter, sample_episodes, tmp_path):
        """export() writes JSONL and metadata files."""
        result = exporter.export(sample_episodes, output_dir=tmp_path)
        assert result["num_episodes"] == 2
        assert result["num_runs"] == 1
        assert Path(result["jsonl_path"]).exists()
        assert Path(result["metadata_path"]).exists()

    def test_export_jsonl_content(self, exporter, sample_episodes, tmp_path):
        """JSONL contains correct episode data."""
        exporter.export(sample_episodes, output_dir=tmp_path)
        jsonl_path = tmp_path / "data.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 2
        record = json.loads(lines[0])
        assert record["episode_id"] == "ep_1"
        assert record["reward"] == 1.5
        assert record["success"] is True

    def test_export_without_biography(self, exporter, sample_episodes, tmp_path):
        """Biographies can be excluded."""
        result = exporter.export(sample_episodes, output_dir=tmp_path, include_biographies=False)
        jsonl_path = tmp_path / "data.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        assert "biography" not in record or record.get("biography") is None

    def test_export_without_metrics(self, exporter, sample_episodes, tmp_path):
        """Metrics can be excluded."""
        exporter.export(sample_episodes, output_dir=tmp_path, include_metrics=False)
        jsonl_path = tmp_path / "data.jsonl"
        lines = jsonl_path.read_text().strip().split("\n")
        record = json.loads(lines[0])
        assert "metrics" not in record or record.get("metrics") is None

    def test_metadata_file(self, exporter, sample_episodes, tmp_path):
        """metadata.json contains correct aggregated stats."""
        exporter.export(sample_episodes, output_dir=tmp_path)
        metadata_path = tmp_path / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        assert metadata["num_episodes"] == 2
        assert metadata["num_runs"] == 1
        assert "reward" in metadata
        assert metadata["success_rate"] == 1.0

    def test_spec_file(self, exporter, sample_episodes, tmp_path):
        """spec.json contains dataset spec."""
        exporter.export(sample_episodes, output_dir=tmp_path)
        spec_path = tmp_path / "spec.json"
        spec = json.loads(spec_path.read_text())
        assert spec["dataset_name"] == "cohezion/flume-test-v0"
        assert spec["version"] == "1.0.0"

    def test_push_to_hub_without_huggingface_hub(self, exporter, sample_episodes, tmp_path):
        """push_to_hub raises ImportError when huggingface_hub unavailable."""
        try:
            import huggingface_hub  # noqa: F401

            hf_available = True
        except ImportError:
            hf_available = False

        exporter.export(sample_episodes, output_dir=tmp_path)

        if not hf_available:
            with pytest.raises(ImportError) as exc_info:
                exporter.push_to_hub(tmp_path, token="hf_test_token")
            assert "huggingface_hub" in str(exc_info.value)
        else:
            with pytest.raises(Exception):
                exporter.push_to_hub(tmp_path, token="hf_test_token")


class TestGenerateDatasetCard:
    """Tests for generate_dataset_card."""

    def test_returns_string(self):
        """Returns a non-empty string."""
        exporter = HuggingFaceExporter(
            dataset_name="cohezion/test",
            dataset_version="1.0.0",
        )
        card = generate_dataset_card(exporter)
        assert isinstance(card, str)
        assert len(card) > 0

    def test_contains_dataset_name(self):
        """Card contains the dataset name."""
        exporter = HuggingFaceExporter(
            dataset_name="cohezion/flume-v0",
            dataset_version="1.2.0",
        )
        card = generate_dataset_card(exporter)
        assert "cohezion/flume-v0" in card
        assert "1.2.0" in card

    def test_contains_metrics(self):
        """Card lists the 6 metric families."""
        exporter = HuggingFaceExporter(dataset_name="cohezion/test")
        card = generate_dataset_card(exporter)
        assert "HIHO Coherence" in card
        assert "TRIUNE Balance" in card
        assert "SPIN Phase" in card

    def test_contains_citation(self):
        """Card contains a citation block."""
        exporter = HuggingFaceExporter(dataset_name="cohezion/test")
        card = generate_dataset_card(exporter)
        assert "@misc{" in card

    def test_with_arxiv(self):
        """Card includes arxiv URL when provided."""
        exporter = HuggingFaceExporter(
            dataset_name="cohezion/test",
            spec=HuggingFaceDatasetSpec(
                dataset_name="cohezion/test",
                arxiv_id="2401.00001",
                paper_title="FLUME Journey Benchmark Study",
            ),
        )
        card = generate_dataset_card(exporter)
        assert "arxiv.org/abs/2401.00001" in card
        assert "Cohezion Research" in card
