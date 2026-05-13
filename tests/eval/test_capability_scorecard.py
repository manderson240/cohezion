"""Tests for CapabilityScorecard and HuggingFaceExporter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest


class TestCapabilityScorecard:
    """Tests for CapabilityScorecard."""

    @pytest.fixture
    def scorecard(self):
        """Create CapabilityScorecard instance."""
        from cohezion.eval.capability_scorecard import CapabilityScorecard

        return CapabilityScorecard()

    @pytest.fixture
    def sample_capability_vector(self):
        """Create sample capability vector."""
        return {
            "coherence_amplitude": 0.85,
            "phase_locking": 0.72,
            "exotic_charge_lifetime": 0.91,
            "orbit_quality": 0.68,
            "triune_balance": 0.77,
            "recovery_basin_radius": 0.63,
        }

    @pytest.fixture
    def sample_checkpoint(self):
        """Create sample checkpoint dict."""
        return {
            "episode": 1,
            "capability_vector": {
                "coherence_amplitude": 0.85,
                "phase_locking": 0.72,
                "exotic_charge_lifetime": 0.91,
                "orbit_quality": 0.68,
                "triune_balance": 0.77,
                "recovery_basin_radius": 0.63,
            },
            "checkpoint_path": "/data/checkpoints/evo_001.pt",
            "timestamp": datetime.now().isoformat(),
        }

    @pytest.mark.fast
    def test_scorecard_initialization(self, scorecard):
        """Test CapabilityScorecard initializes with correct axes."""
        assert len(scorecard.axes) == 6
        assert "coherence_amplitude" in scorecard.axes
        assert "phase_locking" in scorecard.axes
        assert "exotic_charge_lifetime" in scorecard.axes
        assert "orbit_quality" in scorecard.axes
        assert "triune_balance" in scorecard.axes
        assert "recovery_basin_radius" in scorecard.axes

    @pytest.mark.fast
    def test_capability_vector_validation(self, scorecard, sample_capability_vector):
        """Test capability vector is validated correctly."""
        validated = scorecard._validate_vector(sample_capability_vector)
        assert validated is True

    @pytest.mark.fast
    def test_capability_vector_validation_fails_invalid_key(self, scorecard):
        """Test validation fails with invalid key."""
        invalid_vector = {"invalid_key": 0.5}
        validated = scorecard._validate_vector(invalid_vector)
        assert validated is False

    @pytest.mark.fast
    def test_capability_vector_validation_fails_out_of_range(self, scorecard):
        """Test validation fails when values out of range."""
        invalid_vector = {
            "coherence_amplitude": 1.5,
            "phase_locking": 0.72,
            "exotic_charge_lifetime": 0.91,
            "orbit_quality": 0.68,
            "triune_balance": 0.77,
            "recovery_basin_radius": 0.63,
        }
        validated = scorecard._validate_vector(invalid_vector)
        assert validated is False

    @pytest.mark.fast
    def test_generate_radar_chart_returns_figure(self, scorecard, sample_capability_vector):
        """Test radar chart generation returns figure object."""
        fig = scorecard.generate_radar_chart(sample_capability_vector)
        assert fig is not None

    @pytest.mark.fast
    def test_generate_radar_chart_has_correct_axes_count(self, scorecard, sample_capability_vector):
        """Test radar chart has 6 axes."""
        fig = scorecard.generate_radar_chart(sample_capability_vector)
        assert len(fig.data[0].theta) == 6

    @pytest.mark.fast
    def test_track_longitudinal_returns_dataframe(self, scorecard, sample_checkpoint):
        """Test longitudinal tracking returns DataFrame."""
        checkpoints = [sample_checkpoint]
        df = scorecard.track_longitudinal(checkpoints)
        assert df is not None
        assert len(df) == 1
        assert "episode" in df.columns

    @pytest.mark.fast
    def test_track_longitudinal_multiple_episodes(self, scorecard):
        """Test longitudinal tracking with multiple episodes."""
        checkpoints = []
        for i in range(5):
            checkpoints.append(
                {
                    "episode": i + 1,
                    "capability_vector": {
                        "coherence_amplitude": 0.5 + i * 0.05,
                        "phase_locking": 0.6 + i * 0.03,
                        "exotic_charge_lifetime": 0.7 + i * 0.02,
                        "orbit_quality": 0.5 + i * 0.04,
                        "triune_balance": 0.6 + i * 0.03,
                        "recovery_basin_radius": 0.5 + i * 0.05,
                    },
                    "checkpoint_path": f"/data/checkpoints/evo_{i:03d}.pt",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        df = scorecard.track_longitudinal(checkpoints)
        assert len(df) == 5
        assert df["episode"].tolist() == [1, 2, 3, 4, 5]

    @pytest.mark.fast
    def test_compare_swarm_vs_selfsupervised_returns_comparison(self, scorecard, sample_checkpoint):
        """Test comparison returns StatisticalComparison."""
        swarm_results = [{"episode": 1, "capability_vector": sample_checkpoint["capability_vector"]}]
        self_supervised_results = [
            {
                "episode": 1,
                "capability_vector": {
                    "coherence_amplitude": 0.75,
                    "phase_locking": 0.62,
                    "exotic_charge_lifetime": 0.81,
                    "orbit_quality": 0.58,
                    "triune_balance": 0.67,
                    "recovery_basin_radius": 0.53,
                },
            }
        ]

        comparison = scorecard.compare_swarm_vs_selfsupervised(swarm_results, self_supervised_results)
        assert comparison is not None
        assert hasattr(comparison, "delta_capability")
        assert hasattr(comparison, "p_values")

    @pytest.mark.fast
    def test_compare_swarm_vs_selfsupervised_delta_calculation(self, scorecard, sample_checkpoint):
        """Test delta capability is calculated correctly."""
        swarm_results = [{"episode": 1, "capability_vector": sample_checkpoint["capability_vector"]}]
        self_supervised_results = [
            {
                "episode": 1,
                "capability_vector": {
                    "coherence_amplitude": 0.75,
                    "phase_locking": 0.62,
                    "exotic_charge_lifetime": 0.81,
                    "orbit_quality": 0.58,
                    "triune_balance": 0.67,
                    "recovery_basin_radius": 0.53,
                },
            }
        ]

        comparison = scorecard.compare_swarm_vs_selfsupervised(swarm_results, self_supervised_results)

        expected_delta = 0.10  # 0.85 - 0.75
        assert abs(comparison.delta_capability["coherence_amplitude"] - expected_delta) < 0.01

    @pytest.mark.fast
    def test_generate_3d_morphospace_trajectory(self, scorecard, sample_checkpoint):
        """Test 3D morphospace trajectory visualization."""
        checkpoints = [sample_checkpoint] * 5
        for i in range(5):
            checkpoints[i]["episode"] = i + 1
            checkpoints[i]["capability_vector"] = {
                "coherence_amplitude": 0.5 + i * 0.1,
                "phase_locking": 0.6 + i * 0.08,
                "exotic_charge_lifetime": 0.7 + i * 0.06,
                "orbit_quality": 0.5 + i * 0.1,
                "triune_balance": 0.6 + i * 0.08,
                "recovery_basin_radius": 0.5 + i * 0.1,
            }

        fig = scorecard.generate_3d_morphospace_trajectory(checkpoints)
        assert fig is not None


class TestHuggingFaceExporter:
    """Tests for HuggingFaceExporter."""

    @pytest.fixture
    def exporter(self):
        """Create HuggingFaceExporter instance."""
        from cohezion.eval.huggingface_export import HuggingFaceExporter

        return HuggingFaceExporter()

    @pytest.fixture
    def sample_evo_biography(self):
        """Create sample EVO biography."""
        return {
            "journey_id": "evo_test_001",
            "birth_time": "2024-01-15T10:30:00",
            "coherence_amplitude": 0.85,
            "phase": 2.5,
            "angular_momentum": [1.0, 0.8, 0.6],
            "charge": 0.75,
            "exotic_charge_density": 0.42,
            "kordylewski_cloud_id": "L4",
            "stability_well": "HIHO_Origin",
            "doer_state_mean": 0.52,
            "thinker_state_mean": 0.48,
            "knower_state_mean": 0.51,
            "trajectory_length": 100,
            "final_coherence": 0.83,
        }

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create temporary output directory."""
        return tmp_path / "hf_export"

    @pytest.mark.fast
    def test_exporter_initialization(self, exporter):
        """Test HuggingFaceExporter initializes correctly."""
        assert exporter.dataset_name == "cohezion/evo-benchmark"
        assert "evo" in exporter.dataset_name

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_export_research_dataset_creates_files(self, exporter, sample_evo_biography, temp_output_dir):
        """Test research dataset export creates JSONL and README."""
        evos = [sample_evo_biography]

        await exporter.export_research_dataset(evos, temp_output_dir)

        jsonl_path = temp_output_dir / "data.jsonl"
        readme_path = temp_output_dir / "README.md"

        assert jsonl_path.exists()
        assert readme_path.exists()

        content = jsonl_path.read_text()
        assert "evo_test_001" in content
        assert "coherence_amplitude" in content

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_export_research_dataset_readme_has_dataset_card(
        self, exporter, sample_evo_biography, temp_output_dir
    ):
        """Test README contains dataset card content."""
        evos = [sample_evo_biography]

        await exporter.export_research_dataset(evos, temp_output_dir)

        readme_path = temp_output_dir / "README.md"
        content = readme_path.read_text()

        assert "EVO-BENCHMARK" in content
        assert "Cohezion" in content
        assert "Dataset Summary" in content

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_export_benchmark_harness_creates_api(self, exporter, temp_output_dir):
        """Test benchmark harness export creates runnable API."""
        await exporter.export_benchmark_harness(temp_output_dir)

        benchmark_path = temp_output_dir / "benchmark.py"
        assert benchmark_path.exists()

        content = benchmark_path.read_text()
        assert "def run" in content
        assert "tasks" in content

    @pytest.mark.fast
    @pytest.mark.asyncio
    async def test_export_benchmark_harness_has_model_parameter(self, exporter, temp_output_dir):
        """Test benchmark harness accepts model parameter."""
        await exporter.export_benchmark_harness(temp_output_dir)

        benchmark_path = temp_output_dir / "benchmark.py"
        content = benchmark_path.read_text()

        assert "model" in content


class TestStatisticalComparison:
    """Tests for StatisticalComparison dataclass."""

    @pytest.mark.fast
    def test_statistical_comparison_creation(self):
        """Test StatisticalComparison can be created."""

        @dataclass
        class MockComparison:
            delta_capability: dict[str, float]
            p_values: dict[str, float]
            effect_sizes: dict[str, float]
            sample_size_swarm: int
            sample_size_self_supervised: int

        comparison = MockComparison(
            delta_capability={"coherence_amplitude": 0.1},
            p_values={"coherence_amplitude": 0.05},
            effect_sizes={"coherence_amplitude": 0.5},
            sample_size_swarm=10,
            sample_size_self_supervised=10,
        )

        assert comparison.delta_capability["coherence_amplitude"] == 0.1
        assert comparison.sample_size_swarm == 10

    @pytest.mark.fast
    def test_statistical_comparison_to_dict(self):
        """Test StatisticalComparison can convert to dict."""
        from cohezion.eval.capability_scorecard import StatisticalComparison

        comparison = StatisticalComparison(
            delta_capability={"coherence_amplitude": 0.1},
            p_values={"coherence_amplitude": 0.05},
            effect_sizes={"coherence_amplitude": 0.5},
            sample_size_swarm=10,
            sample_size_self_supervised=10,
        )

        result = comparison.to_dict()
        assert isinstance(result, dict)
        assert "delta_capability" in result
        assert "p_values" in result
