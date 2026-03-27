"""Tests for HuggingFaceExporter."""

from __future__ import annotations

import pytest


class TestHuggingFaceExporter:
    """Tests for HuggingFaceExporter."""

    @pytest.mark.fast
    def test_initialization(self):
        """Test HuggingFaceExporter initializes correctly."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exporter = HuggingFaceExporter()
        assert exporter.dataset_name == "cohezion/evo-benchmark"
        assert "cohezion/evo-benchmark" in exporter.dataset_url

    @pytest.mark.fast
    def test_export_research_dataset(self, tmp_path):
        """Test exporting research dataset as JSONL."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exporter = HuggingFaceExporter()
        evos = [
            {
                "journey_id": "test_1",
                "coherence_amplitude": 0.85,
                "phase": 1.0,
                "trajectory_length": 100,
            },
            {
                "journey_id": "test_2",
                "coherence_amplitude": 0.90,
                "phase": 1.5,
                "trajectory_length": 150,
            },
        ]
        import asyncio

        asyncio.run(exporter.export_research_dataset(evos, tmp_path))

        jsonl_path = tmp_path / "data.jsonl"
        readme_path = tmp_path / "README.md"
        assert jsonl_path.exists()
        assert readme_path.exists()
        content = jsonl_path.read_text()
        assert "test_1" in content
        assert "test_2" in content

    @pytest.mark.fast
    def test_export_benchmark_harness(self, tmp_path):
        """Test exporting benchmark harness."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exporter = HuggingFaceExporter()
        import asyncio

        asyncio.run(exporter.export_benchmark_harness(tmp_path))

        benchmark_path = tmp_path / "benchmark.py"
        assert benchmark_path.exists()
        content = benchmark_path.read_text()
        assert "EVOTask" in content
        assert "BenchmarkResults" in content
        assert "def run(model" in content

    @pytest.mark.fast
    def test_generate_dataset_card(self):
        """Test dataset card generation."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exporter = HuggingFaceExporter()
        card = exporter._generate_dataset_card(100)
        assert "EVO-BENCHMARK" in card
        assert "100" in card
        assert "annotations_creators" in card
        assert "language:" in card

    @pytest.mark.fast
    def test_generate_benchmark_harness(self):
        """Test benchmark harness generation."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        exporter = HuggingFaceExporter()
        harness = exporter._generate_benchmark_harness()
        assert "EVOTask" in harness
        assert "EVOResult" in harness
        assert "BenchmarkResults" in harness
        assert "def run(model" in harness
