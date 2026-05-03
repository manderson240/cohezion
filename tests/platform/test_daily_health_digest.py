"""
Tests for Daily Platform Health Digest.

Charter compliance verification:
- Layer 1: Health data collection (repository, tests, dependencies)
- Layer 2: Charter-aligned scoring (50% HIHO + 25% metrics + 25% trend)
- Layer 3: EDL routing for critical issues
"""

import subprocess
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from cohezion.platform.coherence_tracker import CoherenceMetrics
from cohezion.platform.daily_health_digest import (
    DailyHealthDigest,
    DependencyMetrics,
    HealthCheckResult,
    HealthDigest,
    HealthStatus,
    RepositoryMetrics,
    TestMetrics,
    get_daily_health_digest,
    reset_daily_health_digest,
)


@pytest.fixture
def mock_db():
    """Mock SurrealDB client."""
    db = AsyncMock()
    db.query = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_coherence_tracker():
    """Mock coherence tracker."""
    tracker = AsyncMock()
    tracker.measure_system_coherence = AsyncMock(
        return_value=CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.5,  # Perfect HIHO
            hiho_stable=True,
            hiho_delta=0.0,
            stability_score=1.0,
        )
    )
    return tracker


@pytest.fixture
def mock_journey_logger():
    """Mock journey logger."""
    logger = AsyncMock()
    logger.start_journey = AsyncMock(return_value="journey-123")
    logger.complete_journey = AsyncMock()
    return logger


@pytest.fixture
def digest(mock_db, mock_coherence_tracker, mock_journey_logger):
    """Create digest instance with mocked dependencies."""
    digest = DailyHealthDigest()
    digest.db = mock_db
    digest.coherence_tracker = mock_coherence_tracker
    digest.journey_logger = mock_journey_logger
    return digest


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before each test."""
    reset_daily_health_digest()
    yield
    reset_daily_health_digest()


# Layer 1: Health Data Collection Tests


@pytest.mark.asyncio
async def test_collect_repository_metrics_healthy(digest):
    """Test collecting healthy repository metrics."""

    with patch("subprocess.run") as mock_run:
        # Mock du -sb .git
        mock_run.side_effect = [
            Mock(stdout="6442450944\t.git\n", returncode=0),  # 6GB
            Mock(stdout="25\n", returncode=0),  # 25 large files
            Mock(stdout="count: 50\npacks: 1\n", returncode=0),  # Good pack efficiency
        ]

        metrics = await digest._collect_repository_metrics()

        assert 5.9 < metrics.size_gb < 6.1  # ~6GB
        assert metrics.large_file_count == 25
        assert metrics.pack_efficiency > 0.99  # <100 loose objects
        assert metrics.loose_objects == 50


@pytest.mark.asyncio
async def test_collect_repository_metrics_warning(digest):
    """Test collecting repository metrics in warning state."""

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(stdout="8589934592\t.git\n", returncode=0),  # 8GB (warning)
            Mock(stdout="60\n", returncode=0),  # 60 large files (warning)
            Mock(stdout="count: 3000\npacks: 5\n", returncode=0),  # Lower efficiency
        ]

        metrics = await digest._collect_repository_metrics()

        assert 7.9 < metrics.size_gb < 8.1
        assert metrics.large_file_count == 60
        assert metrics.pack_efficiency < 0.8  # 3000 loose objects


@pytest.mark.asyncio
async def test_collect_repository_metrics_critical(digest):
    """Test collecting repository metrics in critical state."""

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(stdout="13958643712\t.git\n", returncode=0),  # 13GB (critical)
            Mock(stdout="120\n", returncode=0),  # 120 large files (critical)
            Mock(stdout="count: 15000\npacks: 10\n", returncode=0),  # Poor efficiency
        ]

        metrics = await digest._collect_repository_metrics()

        assert metrics.size_gb > 10.0
        assert metrics.large_file_count > 100
        assert metrics.pack_efficiency < 0.5


@pytest.mark.asyncio
async def test_collect_repository_metrics_error_fallback(digest):
    """Test fallback when git commands fail."""

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        metrics = await digest._collect_repository_metrics()

        # Should return fallback metrics
        assert metrics.size_gb == 0.0
        assert metrics.large_file_count == 0
        assert metrics.pack_efficiency == 0.5


@pytest.mark.asyncio
async def test_collect_test_metrics_from_db(digest):
    """Test collecting test metrics from SurrealDB."""

    digest.db.query = AsyncMock(
        return_value=[{"total_tests": 2850, "passing_tests": 2830, "timestamp": datetime.now()}]
    )

    metrics = await digest._collect_test_metrics()

    assert metrics.total_tests == 2850
    assert metrics.passing_tests == 2830
    assert metrics.failing_tests == 20
    assert abs(metrics.pass_rate - 0.993) < 0.001


@pytest.mark.asyncio
async def test_collect_test_metrics_no_data(digest):
    """Test test metrics fallback when no data available."""

    digest.db.query = AsyncMock(return_value=[])

    metrics = await digest._collect_test_metrics()

    assert metrics.total_tests == 0
    assert metrics.pass_rate == 0.0


@pytest.mark.asyncio
async def test_collect_dependency_metrics_healthy(digest):
    """Test collecting healthy dependency metrics."""

    digest.db.query = AsyncMock(
        return_value=[
            {
                "total_dependencies": 50,
                "outdated_dependencies": 2,
                "vulnerable_dependencies": 0,
            }
        ]
    )

    metrics = await digest._collect_dependency_metrics()

    assert metrics.total_dependencies == 50
    assert metrics.outdated_dependencies == 2
    assert metrics.vulnerable_dependencies == 0
    assert metrics.health_score > 0.9  # Only 2 outdated


@pytest.mark.asyncio
async def test_collect_dependency_metrics_vulnerable(digest):
    """Test dependency metrics with vulnerabilities."""

    digest.db.query = AsyncMock(
        return_value=[
            {
                "total_dependencies": 50,
                "outdated_dependencies": 5,
                "vulnerable_dependencies": 3,
            }
        ]
    )

    metrics = await digest._collect_dependency_metrics()

    assert metrics.vulnerable_dependencies == 3
    assert metrics.health_score < 0.9  # Vulnerabilities lower score


@pytest.mark.asyncio
async def test_collect_cicd_metrics(digest):
    """Test collecting CI/CD metrics."""

    digest.db.query = AsyncMock(
        return_value=[
            {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "average_duration_seconds": 180.0,
                "failure_rate_7d": 0.05,
            }
        ]
    )

    metrics = await digest._collect_cicd_metrics()

    assert metrics is not None
    assert metrics.last_build_status == "success"
    assert metrics.failure_rate_7d == 0.05


# Layer 2: Health Check Logic Tests


def test_check_status_normal_thresholds(digest):
    """Test status determination with normal thresholds."""

    # Lower is better (e.g., repository size)
    assert digest._check_status(5.0, 8.0, 10.0, invert=False) == HealthStatus.HEALTHY
    assert digest._check_status(9.0, 8.0, 10.0, invert=False) == HealthStatus.WARNING
    assert digest._check_status(12.0, 8.0, 10.0, invert=False) == HealthStatus.CRITICAL


def test_check_status_inverted_thresholds(digest):
    """Test status determination with inverted thresholds."""

    # Higher is better (e.g., test pass rate)
    assert digest._check_status(0.98, 0.95, 0.90, invert=True) == HealthStatus.HEALTHY
    assert digest._check_status(0.92, 0.95, 0.90, invert=True) == HealthStatus.WARNING
    assert digest._check_status(0.85, 0.95, 0.90, invert=True) == HealthStatus.CRITICAL


def test_run_health_checks_all_healthy(digest):
    """Test health checks with all metrics healthy."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    test = TestMetrics(total_tests=2850, passing_tests=2830, failing_tests=20, pass_rate=0.993)
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=2,
        vulnerable_dependencies=0,
        health_score=0.95,
    )

    checks = digest._run_health_checks(repo, test, dep, None)

    # All checks should be HEALTHY
    for check in checks:
        assert check.status == HealthStatus.HEALTHY


def test_run_health_checks_some_warnings(digest):
    """Test health checks with warning conditions."""

    repo = RepositoryMetrics(
        size_gb=8.5,  # Warning
        large_file_count=60,  # Warning
        pack_efficiency=0.65,  # Warning
        loose_objects=4000,
        pack_count=2,
    )
    test = TestMetrics(
        total_tests=100, passing_tests=92, failing_tests=8, pass_rate=0.92
    )  # Warning
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=3,
        vulnerable_dependencies=0,
        health_score=0.65,  # Warning
    )

    checks = digest._run_health_checks(repo, test, dep, None)

    warning_count = sum(1 for c in checks if c.status == HealthStatus.WARNING)
    assert warning_count >= 3  # At least 3 warnings


def test_run_health_checks_critical(digest):
    """Test health checks with critical conditions."""

    repo = RepositoryMetrics(
        size_gb=12.0,  # Critical
        large_file_count=150,  # Critical
        pack_efficiency=0.3,  # Critical
        loose_objects=20000,
        pack_count=5,
    )
    test = TestMetrics(
        total_tests=100, passing_tests=85, failing_tests=15, pass_rate=0.85
    )  # Critical
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=10,
        vulnerable_dependencies=5,  # Critical
        health_score=0.3,
    )

    checks = digest._run_health_checks(repo, test, dep, None)

    critical_count = sum(1 for c in checks if c.status == HealthStatus.CRITICAL)
    assert critical_count >= 3


def test_check_hiho_stability_both_stable(digest, mock_coherence_tracker):
    """Test HIHO stability when both repo and coherence are in range."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.9,
        loose_objects=50,
        pack_count=1,
    )
    coherence = CoherenceMetrics(
        timestamp=datetime.now(),
        internal_state=0.5,
        external_alignment=0.5,
        coherence=0.5,
        hiho_stable=True,
        hiho_delta=0.0,
        stability_score=1.0,
    )

    assert digest._check_hiho_stability(repo, coherence) is True


def test_check_hiho_stability_repo_outside(digest):
    """Test HIHO stability when repo size is outside range."""

    repo = RepositoryMetrics(
        size_gb=10.0,  # Outside HIHO range
        large_file_count=20,
        pack_efficiency=0.9,
        loose_objects=50,
        pack_count=1,
    )
    coherence = CoherenceMetrics(
        timestamp=datetime.now(),
        internal_state=0.5,
        external_alignment=0.5,
        coherence=0.5,
        hiho_stable=True,
        hiho_delta=0.0,
        stability_score=1.0,
    )

    assert digest._check_hiho_stability(repo, coherence) is False


def test_check_hiho_stability_coherence_outside(digest):
    """Test HIHO stability when coherence is outside range."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.9,
        loose_objects=50,
        pack_count=1,
    )
    coherence = CoherenceMetrics(
        timestamp=datetime.now(),
        internal_state=0.9,
        external_alignment=0.9,
        coherence=0.9,  # Outside HIHO
        hiho_stable=False,
        hiho_delta=0.4,
        stability_score=0.2,
    )

    assert digest._check_hiho_stability(repo, coherence) is False


# Layer 3: Charter-Aligned Scoring Tests


@pytest.mark.asyncio
async def test_calculate_charter_score_perfect_hiho(digest):
    """Test Charter score calculation with perfect HIHO alignment."""

    repo = RepositoryMetrics(
        size_gb=6.0,  # Perfect HIHO
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    test = TestMetrics(total_tests=100, passing_tests=98, failing_tests=2, pass_rate=0.98)
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=1,
        vulnerable_dependencies=0,
        health_score=0.95,
    )
    coherence = CoherenceMetrics(
        timestamp=datetime.now(),
        internal_state=0.5,
        external_alignment=0.5,
        coherence=0.5,  # Perfect HIHO
        hiho_stable=True,
        hiho_delta=0.0,
        stability_score=1.0,
    )

    checks = digest._run_health_checks(repo, test, dep, None)

    # Mock trend
    digest._calculate_trend = AsyncMock(return_value=0.1)  # Positive trend

    score = await digest._calculate_charter_score(repo, test, dep, coherence, checks)

    # Should be high score (>0.8) with perfect HIHO + healthy metrics + positive trend
    assert score > 0.8


@pytest.mark.asyncio
async def test_calculate_charter_score_weights(digest):
    """Test Charter score weighting: 50% HIHO + 25% metrics + 25% trend."""

    repo = RepositoryMetrics(
        size_gb=6.0,  # Perfect HIHO = 1.0
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    test = TestMetrics(total_tests=100, passing_tests=100, failing_tests=0, pass_rate=1.0)
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=0,
        vulnerable_dependencies=0,
        health_score=1.0,
    )
    coherence = CoherenceMetrics(
        timestamp=datetime.now(),
        internal_state=0.5,
        external_alignment=0.5,
        coherence=0.5,
        hiho_stable=True,
        hiho_delta=0.0,
        stability_score=1.0,  # Perfect HIHO
    )

    checks = digest._run_health_checks(repo, test, dep, None)

    # Mock trend to 0 (neutral)
    digest._calculate_trend = AsyncMock(return_value=0.0)

    score = await digest._calculate_charter_score(repo, test, dep, coherence, checks)

    # Perfect HIHO (1.0) * 0.5 + Perfect metrics (1.0) * 0.25 + Neutral trend (0.5) * 0.25
    # = 0.5 + 0.25 + 0.125 = 0.875
    assert abs(score - 0.875) < 0.05


@pytest.mark.asyncio
async def test_calculate_trend_improving(digest):
    """Test trend calculation with improving scores."""

    digest.db.query = AsyncMock(
        return_value=[
            {"overall_health_score": 0.5},
            {"overall_health_score": 0.55},
            {"overall_health_score": 0.6},
            {"overall_health_score": 0.65},
            {"overall_health_score": 0.7},
        ]
    )

    trend = await digest._calculate_trend(days=7)

    assert trend > 0.0  # Positive trend


@pytest.mark.asyncio
async def test_calculate_trend_declining(digest):
    """Test trend calculation with declining scores."""

    digest.db.query = AsyncMock(
        return_value=[
            {"overall_health_score": 0.7},
            {"overall_health_score": 0.65},
            {"overall_health_score": 0.6},
            {"overall_health_score": 0.55},
            {"overall_health_score": 0.5},
        ]
    )

    trend = await digest._calculate_trend(days=7)

    assert trend < 0.0  # Negative trend


@pytest.mark.asyncio
async def test_calculate_trend_insufficient_data(digest):
    """Test trend calculation with insufficient data."""

    digest.db.query = AsyncMock(return_value=[{"overall_health_score": 0.7}])

    trend = await digest._calculate_trend(days=7)

    assert trend == 0.0  # Neutral when insufficient data


# Recommendation Generation Tests


@pytest.mark.asyncio
async def test_generate_recommendations_healthy(digest):
    """Test recommendation generation for healthy system."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    test = TestMetrics(total_tests=2850, passing_tests=2830, failing_tests=20, pass_rate=0.993)
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=1,
        vulnerable_dependencies=0,
        health_score=0.95,
    )
    checks = digest._run_health_checks(repo, test, dep, None)

    recommendations = await digest._generate_recommendations(
        repo, test, dep, checks, hiho_stable=True
    )

    # Should have "All systems healthy" message
    assert any("All systems healthy" in r for r in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_repo_critical(digest):
    """Test recommendations for critical repository size."""

    repo = RepositoryMetrics(
        size_gb=12.0,  # Critical
        large_file_count=150,  # Critical
        pack_efficiency=0.3,  # Critical
        loose_objects=20000,
        pack_count=5,
    )
    test = TestMetrics(total_tests=100, passing_tests=98, failing_tests=2, pass_rate=0.98)
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=1,
        vulnerable_dependencies=0,
        health_score=0.95,
    )
    checks = digest._run_health_checks(repo, test, dep, None)

    recommendations = await digest._generate_recommendations(
        repo, test, dep, checks, hiho_stable=False
    )

    # Should recommend cleanup
    assert any("CRITICAL" in r and "Repository size" in r for r in recommendations)
    assert any("large files" in r.lower() for r in recommendations)
    assert any("pack efficiency" in r.lower() for r in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_vulnerable_deps(digest):
    """Test recommendations for vulnerable dependencies."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=5,
        vulnerable_dependencies=3,  # Critical
        health_score=0.5,
    )
    checks = digest._run_health_checks(repo, test, dep, None)

    recommendations = await digest._generate_recommendations(
        repo, test, dep, checks, hiho_stable=True
    )

    # Should recommend immediate update
    assert any("vulnerable" in r.lower() and "CRITICAL" in r for r in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_failing_tests(digest):
    """Test recommendations for failing tests."""

    repo = RepositoryMetrics(
        size_gb=6.0,
        large_file_count=20,
        pack_efficiency=0.95,
        loose_objects=50,
        pack_count=1,
    )
    test = TestMetrics(
        total_tests=100, passing_tests=85, failing_tests=15, pass_rate=0.85
    )  # Critical
    dep = DependencyMetrics(
        total_dependencies=50,
        outdated_dependencies=1,
        vulnerable_dependencies=0,
        health_score=0.95,
    )
    checks = digest._run_health_checks(repo, test, dep, None)

    recommendations = await digest._generate_recommendations(
        repo, test, dep, checks, hiho_stable=True
    )

    # Should recommend fixing tests
    assert any("Test pass rate" in r and "CRITICAL" in r for r in recommendations)


# EDL Routing Tests


def test_requires_edl_review_low_score(digest):
    """Test EDL review required for low score."""

    checks = [
        HealthCheckResult(
            check_name="Test",
            status=HealthStatus.WARNING,
            value=0.5,
            threshold_warning=0.7,
            threshold_critical=0.5,
            message="Warning",
        )
    ]

    assert digest._requires_edl_review(overall_score=0.4, health_checks=checks) is True


def test_requires_edl_review_critical_check(digest):
    """Test EDL review required for critical check."""

    checks = [
        HealthCheckResult(
            check_name="Test",
            status=HealthStatus.CRITICAL,
            value=0.3,
            threshold_warning=0.7,
            threshold_critical=0.5,
            message="Critical",
        )
    ]

    assert digest._requires_edl_review(overall_score=0.7, health_checks=checks) is True


def test_requires_edl_review_healthy(digest):
    """Test EDL review not required for healthy system."""

    checks = [
        HealthCheckResult(
            check_name="Test",
            status=HealthStatus.HEALTHY,
            value=0.9,
            threshold_warning=0.7,
            threshold_critical=0.5,
            message="Healthy",
        )
    ]

    assert digest._requires_edl_review(overall_score=0.85, health_checks=checks) is False


def test_determine_overall_status_critical_check(digest):
    """Test overall status with critical check."""

    checks = [
        HealthCheckResult(
            check_name="Test",
            status=HealthStatus.CRITICAL,
            value=0.3,
            threshold_warning=0.7,
            threshold_critical=0.5,
            message="Critical",
        )
    ]

    status = digest._determine_overall_status(overall_score=0.9, health_checks=checks)
    assert status == HealthStatus.CRITICAL


def test_determine_overall_status_from_score(digest):
    """Test overall status determined from score."""

    checks = [
        HealthCheckResult(
            check_name="Test",
            status=HealthStatus.HEALTHY,
            value=0.9,
            threshold_warning=0.7,
            threshold_critical=0.5,
            message="Healthy",
        )
    ]

    # High score
    status = digest._determine_overall_status(overall_score=0.85, health_checks=checks)
    assert status == HealthStatus.HEALTHY

    # Medium score
    status = digest._determine_overall_status(overall_score=0.6, health_checks=checks)
    assert status == HealthStatus.WARNING

    # Low score
    status = digest._determine_overall_status(overall_score=0.4, health_checks=checks)
    assert status == HealthStatus.CRITICAL


# Integration Tests


@pytest.mark.asyncio
async def test_generate_digest_full_workflow(digest):
    """Test complete digest generation workflow."""

    # Mock subprocess calls for repository metrics
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            Mock(stdout="6442450944\t.git\n", returncode=0),  # 6GB
            Mock(stdout="25\n", returncode=0),  # 25 large files
            Mock(stdout="count: 50\npacks: 1\n", returncode=0),  # Good pack
        ]

        # Create separate mocks for each DB query call
        async def mock_query_side_effect(query, *args, **kwargs):
            if "test_metrics" in query:
                return [{"total_tests": 2850, "passing_tests": 2830}]
            elif "dependency_metrics" in query:
                return [
                    {
                        "total_dependencies": 50,
                        "outdated_dependencies": 2,
                        "vulnerable_dependencies": 0,
                    }
                ]
            elif "cicd_metrics" in query:
                return []  # No CI/CD metrics
            elif "platform_health_digests" in query and "SELECT" in query:
                return []  # No trend data
            elif "CREATE platform_health_digests" in query:
                return []  # Persist digest
            else:
                return []

        digest.db.query = AsyncMock(side_effect=mock_query_side_effect)

        result = await digest.generate_digest()

        assert isinstance(result, HealthDigest)
        assert result.overall_health_score > 0.0
        assert result.overall_status in [
            HealthStatus.HEALTHY,
            HealthStatus.WARNING,
            HealthStatus.CRITICAL,
        ]
        assert len(result.health_checks) > 0
        assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_persist_digest(digest):
    """Test digest persistence to SurrealDB."""

    test_digest = HealthDigest(
        timestamp=datetime.now(),
        overall_health_score=0.85,
        overall_status=HealthStatus.HEALTHY,
        hiho_stable=True,
        coherence_metrics=CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.5,
            hiho_stable=True,
            hiho_delta=0.0,
            stability_score=1.0,
        ),
        repository_metrics=RepositoryMetrics(
            size_gb=6.0,
            large_file_count=20,
            pack_efficiency=0.95,
            loose_objects=50,
            pack_count=1,
        ),
        test_metrics=TestMetrics(
            total_tests=100, passing_tests=98, failing_tests=2, pass_rate=0.98
        ),
        dependency_metrics=DependencyMetrics(
            total_dependencies=50,
            outdated_dependencies=2,
            vulnerable_dependencies=0,
            health_score=0.95,
        ),
        cicd_metrics=None,
        health_checks=[],
        recommendations=["All healthy"],
        trend_7d=0.1,
        requires_edl_review=False,
    )

    await digest._persist_digest(test_digest)

    # Verify DB query was called
    digest.db.query.assert_called_once()
    call_args = digest.db.query.call_args
    assert "platform_health_digests" in call_args[0][0]


def test_format_digest_terminal(digest):
    """Test terminal formatting of digest."""

    test_digest = HealthDigest(
        timestamp=datetime.now(),
        overall_health_score=0.85,
        overall_status=HealthStatus.HEALTHY,
        hiho_stable=True,
        coherence_metrics=CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.5,
            hiho_stable=True,
            hiho_delta=0.0,
            stability_score=1.0,
        ),
        repository_metrics=RepositoryMetrics(
            size_gb=6.0,
            large_file_count=20,
            pack_efficiency=0.95,
            loose_objects=50,
            pack_count=1,
        ),
        test_metrics=TestMetrics(
            total_tests=2850, passing_tests=2830, failing_tests=20, pass_rate=0.993
        ),
        dependency_metrics=DependencyMetrics(
            total_dependencies=50,
            outdated_dependencies=2,
            vulnerable_dependencies=0,
            health_score=0.95,
        ),
        cicd_metrics=None,
        health_checks=[
            HealthCheckResult(
                check_name="Repository Size",
                status=HealthStatus.HEALTHY,
                value=6.0,
                threshold_warning=8.0,
                threshold_critical=10.0,
                message="6.00 GB (HIHO target: 6.0 GB)",
            )
        ],
        recommendations=["✅ All systems healthy. No actions required."],
        trend_7d=0.1,
        requires_edl_review=False,
    )

    output = digest.format_digest_terminal(test_digest)

    # Verify key sections present
    assert "DAILY PLATFORM HEALTH DIGEST" in output
    assert "Overall Score" in output
    assert "COHERENCE METRICS" in output
    assert "REPOSITORY HEALTH" in output
    assert "TEST SUITE" in output
    assert "DEPENDENCIES" in output
    assert "HEALTH CHECKS" in output
    assert "RECOMMENDATIONS" in output


# Singleton Tests


def test_singleton_accessor():
    """Test singleton accessor pattern."""

    digest1 = get_daily_health_digest()
    digest2 = get_daily_health_digest()

    assert digest1 is digest2


def test_singleton_reset():
    """Test singleton reset."""

    digest1 = get_daily_health_digest()
    reset_daily_health_digest()
    digest2 = get_daily_health_digest()

    assert digest1 is not digest2
