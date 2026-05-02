"""
Tests for CoherenceTracker - HIHO stability measurement.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.platform.coherence_tracker import (
    CoherenceMetrics,
    CoherenceTracker,
    get_coherence_tracker,
    reset_coherence_tracker,
)


@pytest.fixture
def mock_surreal_client():
    """Mock SurrealDB client."""
    mock_client = AsyncMock()
    mock_client.query = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def coherence_tracker(mock_surreal_client):
    """Create CoherenceTracker with mocked DB."""
    with patch(
        "cohezion.platform.coherence_tracker.get_surreal_client",
        return_value=mock_surreal_client,
    ):
        tracker = CoherenceTracker()
        yield tracker


class TestCoherenceMetrics:
    """Test CoherenceMetrics model."""

    def test_coherence_metrics_creation(self):
        """Test creating CoherenceMetrics."""
        metrics = CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.75,
            hiho_stable=False,
            hiho_delta=0.25,
            stability_score=0.5,
        )

        assert metrics.internal_state == 0.8
        assert metrics.external_alignment == 0.7
        assert metrics.coherence == 0.75
        assert metrics.hiho_stable is False
        assert metrics.hiho_delta == 0.25
        assert metrics.stability_score == 0.5


class TestCoherenceTracker:
    """Test CoherenceTracker class."""

    def test_initialization(self, coherence_tracker):
        """Test CoherenceTracker initialization."""
        assert coherence_tracker.target_coherence == 0.5

    def test_is_hiho_stable(self, coherence_tracker):
        """Test HIHO stability check."""
        assert coherence_tracker.is_hiho_stable(0.5) is True
        assert coherence_tracker.is_hiho_stable(0.4) is True
        assert coherence_tracker.is_hiho_stable(0.6) is True
        assert coherence_tracker.is_hiho_stable(0.39) is False
        assert coherence_tracker.is_hiho_stable(0.61) is False
        assert coherence_tracker.is_hiho_stable(0.0) is False
        assert coherence_tracker.is_hiho_stable(1.0) is False

    @pytest.mark.asyncio
    async def test_get_test_pass_rate_with_data(self, coherence_tracker, mock_surreal_client):
        """Test getting test pass rate from DB."""
        mock_surreal_client.query.return_value = [{"pass_rate": 0.99}]

        rate = await coherence_tracker._get_test_pass_rate()

        assert rate == 0.99
        mock_surreal_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_test_pass_rate_no_data(self, coherence_tracker, mock_surreal_client):
        """Test getting test pass rate with no data."""
        mock_surreal_client.query.return_value = []

        rate = await coherence_tracker._get_test_pass_rate()

        assert rate == 0.0

    @pytest.mark.asyncio
    async def test_get_code_quality(self, coherence_tracker):
        """Test code quality measurement."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="2 error found", returncode=0)

            quality = await coherence_tracker._get_code_quality()

            assert 0.0 <= quality <= 1.0
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dependency_health_with_data(self, coherence_tracker, mock_surreal_client):
        """Test dependency health with data."""
        mock_surreal_client.query.return_value = [{"health_score": 95.0}]

        health = await coherence_tracker._get_dependency_health()

        assert health == 0.95

    @pytest.mark.asyncio
    async def test_get_dependency_health_no_data(self, coherence_tracker, mock_surreal_client):
        """Test dependency health with no data."""
        mock_surreal_client.query.return_value = []

        health = await coherence_tracker._get_dependency_health()

        assert health == 0.5

    @pytest.mark.asyncio
    async def test_get_security_posture_no_vulns(self, coherence_tracker, mock_surreal_client):
        """Test security posture with no vulnerabilities."""
        mock_surreal_client.query.return_value = [{"vulnerabilities_critical": 0, "vulnerabilities_high": 0}]

        posture = await coherence_tracker._get_security_posture()

        assert posture == 1.0

    @pytest.mark.asyncio
    async def test_get_security_posture_critical_vulns(self, coherence_tracker, mock_surreal_client):
        """Test security posture with critical vulnerabilities."""
        mock_surreal_client.query.return_value = [{"vulnerabilities_critical": 1, "vulnerabilities_high": 0}]

        posture = await coherence_tracker._get_security_posture()

        assert posture == 0.0

    @pytest.mark.asyncio
    async def test_get_security_posture_high_vulns(self, coherence_tracker, mock_surreal_client):
        """Test security posture with high vulnerabilities."""
        mock_surreal_client.query.return_value = [{"vulnerabilities_critical": 0, "vulnerabilities_high": 2}]

        posture = await coherence_tracker._get_security_posture()

        assert posture == 0.3  # 0.5 - (2 * 0.1)

    @pytest.mark.asyncio
    async def test_get_performance_alignment_excellent(self, coherence_tracker, mock_surreal_client):
        """Test performance alignment with excellent latency."""
        mock_surreal_client.query.return_value = [{"compound_executor_latency_ms": 300}]

        performance = await coherence_tracker._get_performance_alignment()

        assert performance == 1.0

    @pytest.mark.asyncio
    async def test_get_performance_alignment_acceptable(self, coherence_tracker, mock_surreal_client):
        """Test performance alignment with acceptable latency."""
        mock_surreal_client.query.return_value = [{"compound_executor_latency_ms": 750}]

        performance = await coherence_tracker._get_performance_alignment()

        assert 0.0 < performance < 1.0

    @pytest.mark.asyncio
    async def test_get_performance_alignment_poor(self, coherence_tracker, mock_surreal_client):
        """Test performance alignment with poor latency."""
        mock_surreal_client.query.return_value = [{"compound_executor_latency_ms": 1500}]

        performance = await coherence_tracker._get_performance_alignment()

        assert performance == 0.0

    @pytest.mark.asyncio
    async def test_measure_internal_state(self, coherence_tracker):
        """Test internal state measurement."""
        with (
            patch.object(coherence_tracker, "_get_test_pass_rate", return_value=0.99),
            patch.object(coherence_tracker, "_get_code_quality", return_value=0.95),
            patch.object(coherence_tracker, "_get_dependency_health", return_value=0.90),
        ):
            internal = await coherence_tracker._measure_internal_state()

            # 0.99*0.4 + 0.95*0.3 + 0.90*0.3 = 0.951
            assert 0.95 <= internal <= 0.96

    @pytest.mark.asyncio
    async def test_measure_external_alignment(self, coherence_tracker):
        """Test external alignment measurement."""
        with (
            patch.object(coherence_tracker, "_get_research_relevance", return_value=0.8),
            patch.object(coherence_tracker, "_get_security_posture", return_value=1.0),
            patch.object(coherence_tracker, "_get_performance_alignment", return_value=0.9),
        ):
            external = await coherence_tracker._measure_external_alignment()

            # 0.8*0.4 + 1.0*0.3 + 0.9*0.3 = 0.89
            assert 0.88 <= external <= 0.90

    @pytest.mark.asyncio
    async def test_measure_system_coherence_hiho_stable(self, coherence_tracker, mock_surreal_client):
        """Test system coherence measurement in HIHO stable range."""
        with (
            patch.object(coherence_tracker, "_measure_internal_state", return_value=0.5),
            patch.object(coherence_tracker, "_measure_external_alignment", return_value=0.5),
        ):
            metrics = await coherence_tracker.measure_system_coherence()

            assert metrics.internal_state == 0.5
            assert metrics.external_alignment == 0.5
            assert metrics.coherence == 0.5
            assert metrics.hiho_stable is True
            assert metrics.hiho_delta == 0.0
            assert metrics.stability_score == 1.0

    @pytest.mark.asyncio
    async def test_measure_system_coherence_unstable_high(self, coherence_tracker, mock_surreal_client):
        """Test system coherence measurement with high coherence (unstable)."""
        with (
            patch.object(coherence_tracker, "_measure_internal_state", return_value=0.9),
            patch.object(coherence_tracker, "_measure_external_alignment", return_value=0.9),
        ):
            metrics = await coherence_tracker.measure_system_coherence()

            assert metrics.coherence == 0.9
            assert metrics.hiho_stable is False
            assert metrics.hiho_delta == 0.4
            assert metrics.stability_score == pytest.approx(0.2)  # 1.0 - (0.4 * 2)

    @pytest.mark.asyncio
    async def test_measure_system_coherence_unstable_low(self, coherence_tracker, mock_surreal_client):
        """Test system coherence measurement with low coherence (unstable)."""
        with (
            patch.object(coherence_tracker, "_measure_internal_state", return_value=0.1),
            patch.object(coherence_tracker, "_measure_external_alignment", return_value=0.1),
        ):
            metrics = await coherence_tracker.measure_system_coherence()

            assert metrics.coherence == 0.1
            assert metrics.hiho_stable is False
            assert metrics.hiho_delta == 0.4
            assert metrics.stability_score == pytest.approx(0.2)

    @pytest.mark.asyncio
    async def test_get_coherence_trend(self, coherence_tracker, mock_surreal_client):
        """Test getting coherence trend."""
        mock_surreal_client.query.return_value = [
            {"coherence": 0.45},
            {"coherence": 0.50},
            {"coherence": 0.55},
            {"coherence": 0.48},
        ]

        trend = await coherence_tracker.get_coherence_trend(days=7)

        assert trend == [0.45, 0.50, 0.55, 0.48]

    @pytest.mark.asyncio
    async def test_persist_metrics(self, coherence_tracker, mock_surreal_client):
        """Test persisting metrics to SurrealDB."""
        metrics = CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.75,
            hiho_stable=False,
            hiho_delta=0.25,
            stability_score=0.5,
        )

        await coherence_tracker._persist_metrics(metrics)

        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "CREATE coherence_metrics" in call_args[0][0]
        assert call_args[0][1]["coherence"] == 0.75


class TestSingletonAccessor:
    """Test singleton accessor functions."""

    def test_get_coherence_tracker(self):
        """Test getting global coherence tracker."""
        reset_coherence_tracker()

        tracker1 = get_coherence_tracker()
        tracker2 = get_coherence_tracker()

        assert tracker1 is tracker2

    def test_reset_coherence_tracker(self):
        """Test resetting global coherence tracker."""
        tracker1 = get_coherence_tracker()
        reset_coherence_tracker()
        tracker2 = get_coherence_tracker()

        assert tracker1 is not tracker2
