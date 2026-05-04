"""Tests for JourneyAnalyzer — behavioral clustering and archetype detection."""
import pytest


@pytest.fixture
def analyzer():
    from cohezion.compound.journey_analyzer import JourneyAnalyzer
    return JourneyAnalyzer()


@pytest.fixture
def sample_journey():
    """A minimal journey dict for testing."""
    return {
        "agent_id": "test-agent",
        "steps": [
            {"coherence": 0.8, "novelty": 0.6, "phi": 0.7, "variance": 0.2},
            {"coherence": 0.75, "novelty": 0.65, "phi": 0.72, "variance": 0.18},
        ],
        "mean_coherence": 0.775,
        "mean_novelty": 0.625,
        "mean_phi": 0.71,
        "variance": 0.19,
    }


class TestJourneyAnalyzerThresholds:
    """Verify archetype threshold constants are within valid ranges."""

    def test_explorer_threshold_in_range(self, analyzer):
        assert 0 < analyzer.EXPLORER_NOVELTY_THRESHOLD < 1

    def test_stabilizer_threshold_in_range(self, analyzer):
        assert 0 < analyzer.STABILIZER_COHERENCE_THRESHOLD < 1

    def test_innovator_threshold_in_range(self, analyzer):
        assert 0 < analyzer.INNOVATOR_PHI_THRESHOLD < 1

    def test_oscillator_threshold_in_range(self, analyzer):
        assert 0 < analyzer.OSCILLATOR_VARIANCE_THRESHOLD < 1

    def test_drifter_threshold_in_range(self, analyzer):
        assert 0 < analyzer.DRIFTER_COHERENCE_LOWER < 1


class TestJourneyAnalyzerImport:
    """Structural: JourneyAnalyzer is importable and instantiable."""

    def test_importable(self):
        from cohezion.compound.journey_analyzer import JourneyAnalyzer
        assert JourneyAnalyzer is not None

    def test_archetype_type_enum(self):
        from cohezion.compound.journey_analyzer import ArchetypeType
        assert hasattr(ArchetypeType, "__members__")
        assert len(ArchetypeType.__members__) > 0

    def test_journey_report_dataclass(self):
        from cohezion.compound.journey_analyzer import JourneyReport
        import dataclasses
        assert dataclasses.is_dataclass(JourneyReport)

