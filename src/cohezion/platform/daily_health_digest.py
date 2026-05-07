"""
Daily Platform Health Digest with Charter-aligned scoring.

Charter requirement: "Maximum stability at exactly 50% coherence overlap (HIHO)"
Implements 3-layer health assessment:
1. Data Collection: Repository, tests, dependencies, CI/CD
2. Charter Scoring: 50% HIHO stability + 25% metrics + 25% trends
3. Action Routing: EDL for critical issues, Observable AI for recommendations
"""

import shutil
import subprocess
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.platform.coherence_tracker import CoherenceMetrics, get_coherence_tracker
from cohezion.platform.edl_router import get_edl_router
from cohezion.platform.journey_logger import get_journey_logger
from cohezion.platform.observable_action import get_observable_proposer


# Resolve external executable paths at module load to avoid S607 partial-path warnings.
_DU = shutil.which("du") or "/usr/bin/du"
_BASH = shutil.which("bash") or "/bin/bash"
_GIT = shutil.which("git") or "/usr/bin/git"


class HealthStatus(StrEnum):
    """Health status categories."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class RepositoryMetrics(BaseModel):
    """Repository size and efficiency metrics."""

    size_gb: float
    large_file_count: int
    pack_efficiency: float  # 0-1, higher is better
    loose_objects: int
    pack_count: int


class TestMetrics(BaseModel):
    """Test suite health metrics."""

    total_tests: int
    passing_tests: int
    failing_tests: int
    pass_rate: float


class DependencyMetrics(BaseModel):
    """Dependency health metrics."""

    total_dependencies: int
    outdated_dependencies: int
    vulnerable_dependencies: int
    health_score: float  # 0-1


class CICDMetrics(BaseModel):
    """CI/CD health metrics."""

    last_build_status: str
    last_build_time: datetime
    average_build_duration_seconds: float
    failure_rate_7d: float


class HealthCheckResult(BaseModel):
    """Individual health check result."""

    check_name: str
    status: HealthStatus
    value: float
    threshold_warning: float
    threshold_critical: float
    message: str


class HealthDigest(BaseModel):
    """Complete daily health digest."""

    timestamp: datetime
    overall_health_score: float  # 0-1, Charter-aligned
    overall_status: HealthStatus
    hiho_stable: bool
    coherence_metrics: CoherenceMetrics
    repository_metrics: RepositoryMetrics
    test_metrics: TestMetrics
    dependency_metrics: DependencyMetrics
    cicd_metrics: CICDMetrics | None
    health_checks: list[HealthCheckResult]
    recommendations: list[str]
    trend_7d: float  # -1 to 1, negative = declining
    requires_edl_review: bool


class DailyHealthDigest:
    """
    Daily platform health digest with Charter-aligned scoring.

    Layer 1: Health Data Collection (REPOSITORY_HEALTH_PRIME procedures)
    Layer 2: Charter-aligned Scoring (50% HIHO + 25% metrics + 25% trend)
    Layer 3: Digest Generation with EDL routing for anomalies
    """

    def __init__(self):
        self.coherence_tracker = get_coherence_tracker()
        self.journey_logger = get_journey_logger()
        self.observable_proposer = get_observable_proposer()
        self.edl_router = get_edl_router()
        self.db = get_surreal_client()

        # HIHO stability thresholds (4-8GB per REPOSITORY_HEALTH_PRIME)
        self.hiho_repo_size_min = 4.0
        self.hiho_repo_size_max = 8.0
        self.hiho_repo_size_target = 6.0

    async def generate_digest(self) -> HealthDigest:
        """
        Generate comprehensive health digest.

        Returns:
            Complete health digest with Charter-aligned scoring
        """

        # Start journey tracking
        journey_id = await self.journey_logger.start_journey(
            journey_type="health_check",
            context="Daily platform health assessment",
        )

        # Layer 1: Collect health data
        repo_metrics = await self._collect_repository_metrics()
        test_metrics = await self._collect_test_metrics()
        dep_metrics = await self._collect_dependency_metrics()
        cicd_metrics = await self._collect_cicd_metrics()
        coherence_metrics = await self.coherence_tracker.measure_system_coherence()

        # Layer 2: Charter-aligned scoring
        health_checks = self._run_health_checks(
            repo_metrics, test_metrics, dep_metrics, cicd_metrics
        )

        hiho_stable = self._check_hiho_stability(repo_metrics, coherence_metrics)

        overall_score = await self._calculate_charter_score(
            repo_metrics, test_metrics, dep_metrics, coherence_metrics, health_checks
        )

        trend_7d = await self._calculate_trend(days=7)

        # Layer 3: Generate recommendations
        recommendations = await self._generate_recommendations(
            repo_metrics, test_metrics, dep_metrics, health_checks, hiho_stable
        )

        # Determine if EDL review required (critical issues)
        requires_edl_review = self._requires_edl_review(overall_score, health_checks)

        # Determine overall status
        overall_status = self._determine_overall_status(overall_score, health_checks)

        digest = HealthDigest(
            timestamp=datetime.now(),
            overall_health_score=overall_score,
            overall_status=overall_status,
            hiho_stable=hiho_stable,
            coherence_metrics=coherence_metrics,
            repository_metrics=repo_metrics,
            test_metrics=test_metrics,
            dependency_metrics=dep_metrics,
            cicd_metrics=cicd_metrics,
            health_checks=health_checks,
            recommendations=recommendations,
            trend_7d=trend_7d,
            requires_edl_review=requires_edl_review,
        )

        # Persist digest
        await self._persist_digest(digest)

        # Complete journey
        await self.journey_logger.complete_journey(
            journey_id=journey_id,
            outcome=f"Health digest generated: {overall_status.value}",
            context_end=f"Overall score: {overall_score:.3f}, HIHO stable: {hiho_stable}",
        )

        return digest

    async def _collect_repository_metrics(self) -> RepositoryMetrics:
        """
        Collect repository health metrics.

        Uses REPOSITORY_HEALTH_PRIME procedures.
        """

        try:
            # Get repository size
            result = subprocess.run(
                [_DU, "-sb", ".git"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            size_bytes = int(result.stdout.split()[0])
            size_gb = size_bytes / (1024**3)

            # Count large files (>1MB) in history
            result = subprocess.run(
                [
                    _BASH,
                    "-c",
                    """git rev-list --objects --all | \
                    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
                    awk '$1 == "blob" && $3 > 1048576' | wc -l""",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            large_file_count = int(result.stdout.strip())

            # Get pack efficiency
            result = subprocess.run(
                [_GIT, "count-objects", "-v"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            loose_objects = 0
            pack_count = 0
            for line in result.stdout.split("\n"):
                if line.startswith("count:"):
                    loose_objects = int(line.split(":")[1].strip())
                elif line.startswith("packs:"):
                    pack_count = int(line.split(":")[1].strip())

            # Pack efficiency: 1.0 if <100 loose objects, 0.0 if >10000
            pack_efficiency = max(0.0, min(1.0, 1.0 - (loose_objects / 10000)))

            return RepositoryMetrics(
                size_gb=size_gb,
                large_file_count=large_file_count,
                pack_efficiency=pack_efficiency,
                loose_objects=loose_objects,
                pack_count=pack_count,
            )

        except Exception:
            # Fallback metrics on error
            return RepositoryMetrics(
                size_gb=0.0,
                large_file_count=0,
                pack_efficiency=0.5,
                loose_objects=0,
                pack_count=0,
            )

    async def _collect_test_metrics(self) -> TestMetrics:
        """Collect test suite health metrics."""

        # Query latest test results from SurrealDB
        result = await self.db.query(
            """
            SELECT * FROM test_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            total = metrics.get("total_tests", 0)
            passing = metrics.get("passing_tests", 0)
            failing = total - passing
            pass_rate = passing / total if total > 0 else 0.0

            return TestMetrics(
                total_tests=total,
                passing_tests=passing,
                failing_tests=failing,
                pass_rate=pass_rate,
            )

        # Default fallback
        return TestMetrics(total_tests=0, passing_tests=0, failing_tests=0, pass_rate=0.0)

    async def _collect_dependency_metrics(self) -> DependencyMetrics:
        """Collect dependency health metrics."""

        result = await self.db.query(
            """
            SELECT * FROM dependency_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            total = metrics.get("total_dependencies", 0)
            outdated = metrics.get("outdated_dependencies", 0)
            vulnerable = metrics.get("vulnerable_dependencies", 0)

            # Health score: 1.0 if no outdated/vulnerable, decreases with issues
            health_score = 1.0
            if total > 0:
                health_score = 1.0 - (
                    (outdated * 0.5 + vulnerable * 1.0) / total
                )  # Vulnerabilities weighted higher
                health_score = max(0.0, health_score)

            return DependencyMetrics(
                total_dependencies=total,
                outdated_dependencies=outdated,
                vulnerable_dependencies=vulnerable,
                health_score=health_score,
            )

        # Default fallback
        return DependencyMetrics(
            total_dependencies=0,
            outdated_dependencies=0,
            vulnerable_dependencies=0,
            health_score=0.5,
        )

    async def _collect_cicd_metrics(self) -> CICDMetrics | None:
        """Collect CI/CD health metrics."""

        result = await self.db.query(
            """
            SELECT * FROM cicd_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            return CICDMetrics(
                last_build_status=metrics.get("status", "unknown"),
                last_build_time=datetime.fromisoformat(
                    metrics.get("timestamp", datetime.now().isoformat())
                ),
                average_build_duration_seconds=metrics.get("average_duration_seconds", 0.0),
                failure_rate_7d=metrics.get("failure_rate_7d", 0.0),
            )

        return None

    def _run_health_checks(
        self,
        repo: RepositoryMetrics,
        test: TestMetrics,
        dep: DependencyMetrics,
        cicd: CICDMetrics | None,
    ) -> list[HealthCheckResult]:
        """Run all health checks and generate results."""

        checks = []

        # Repository size check (HIHO range: 4-8GB)
        checks.append(
            HealthCheckResult(
                check_name="Repository Size",
                status=self._check_status(repo.size_gb, 8.0, 10.0, invert=False),
                value=repo.size_gb,
                threshold_warning=8.0,
                threshold_critical=10.0,
                message=f"{repo.size_gb:.2f} GB (HIHO target: {self.hiho_repo_size_target} GB)",
            )
        )

        # Large file count check
        checks.append(
            HealthCheckResult(
                check_name="Large Files (>1MB)",
                status=self._check_status(repo.large_file_count, 50, 100, invert=False),
                value=float(repo.large_file_count),
                threshold_warning=50.0,
                threshold_critical=100.0,
                message=f"{repo.large_file_count} files >1MB in history",
            )
        )

        # Pack efficiency check
        checks.append(
            HealthCheckResult(
                check_name="Pack Efficiency",
                status=self._check_status(repo.pack_efficiency, 0.7, 0.5, invert=True),
                value=repo.pack_efficiency,
                threshold_warning=0.7,
                threshold_critical=0.5,
                message=f"{repo.pack_efficiency:.1%} efficiency, {repo.loose_objects} loose objects",
            )
        )

        # Test pass rate check
        checks.append(
            HealthCheckResult(
                check_name="Test Pass Rate",
                status=self._check_status(test.pass_rate, 0.95, 0.90, invert=True),
                value=test.pass_rate,
                threshold_warning=0.95,
                threshold_critical=0.90,
                message=f"{test.passing_tests}/{test.total_tests} tests passing ({test.pass_rate:.1%})",
            )
        )

        # Dependency health check
        checks.append(
            HealthCheckResult(
                check_name="Dependency Health",
                status=self._check_status(dep.health_score, 0.7, 0.5, invert=True),
                value=dep.health_score,
                threshold_warning=0.7,
                threshold_critical=0.5,
                message=f"{dep.outdated_dependencies} outdated, {dep.vulnerable_dependencies} vulnerable",
            )
        )

        # CI/CD health check (if available)
        if cicd:
            failure_rate_status = self._check_status(cicd.failure_rate_7d, 0.1, 0.2, invert=False)
            checks.append(
                HealthCheckResult(
                    check_name="CI/CD Health",
                    status=failure_rate_status,
                    value=cicd.failure_rate_7d,
                    threshold_warning=0.1,
                    threshold_critical=0.2,
                    message=f"Last: {cicd.last_build_status}, failure rate: {cicd.failure_rate_7d:.1%}",
                )
            )

        return checks

    def _check_status(
        self,
        value: float,
        threshold_warning: float,
        threshold_critical: float,
        invert: bool = False,
    ) -> HealthStatus:
        """
        Determine health status based on thresholds.

        Args:
            value: Current value
            threshold_warning: Warning threshold
            threshold_critical: Critical threshold
            invert: If True, lower values are worse (e.g., test pass rate)
        """

        if invert:
            if value >= threshold_warning:
                return HealthStatus.HEALTHY
            elif value >= threshold_critical:
                return HealthStatus.WARNING
            else:
                return HealthStatus.CRITICAL
        else:
            if value <= threshold_warning:
                return HealthStatus.HEALTHY
            elif value <= threshold_critical:
                return HealthStatus.WARNING
            else:
                return HealthStatus.CRITICAL

    def _check_hiho_stability(self, repo: RepositoryMetrics, coherence: CoherenceMetrics) -> bool:
        """
        Check if system is in HIHO stability range.

        Charter: Maximum stability at 50% coherence overlap.
        HIHO repository range: 4-8GB (6GB ± 2GB).
        """

        repo_hiho = self.hiho_repo_size_min <= repo.size_gb <= self.hiho_repo_size_max
        coherence_hiho = coherence.hiho_stable

        # Both must be in HIHO range
        return repo_hiho and coherence_hiho

    async def _calculate_charter_score(
        self,
        repo: RepositoryMetrics,
        test: TestMetrics,
        dep: DependencyMetrics,
        coherence: CoherenceMetrics,
        health_checks: list[HealthCheckResult],
    ) -> float:
        """
        Calculate Charter-aligned health score.

        Formula: 50% HIHO stability + 25% metrics health + 25% trend improvement

        Returns:
            Score 0-1, higher is better
        """

        # Component 1: HIHO Stability (50% weight)
        # Repository HIHO: 1.0 at 6GB, decreases toward edges
        repo_hiho_delta = abs(repo.size_gb - self.hiho_repo_size_target)
        repo_hiho_score = max(0.0, 1.0 - (repo_hiho_delta / 2.0))  # 0.0 at 4GB or 8GB

        # Coherence HIHO: use stability_score from coherence tracker
        coherence_hiho_score = coherence.stability_score

        # Average HIHO scores
        hiho_stability = (repo_hiho_score + coherence_hiho_score) / 2

        # Component 2: Metrics Health (25% weight)
        # Average of all health check pass rates
        health_scores = []
        for check in health_checks:
            if check.status == HealthStatus.HEALTHY:
                health_scores.append(1.0)
            elif check.status == HealthStatus.WARNING:
                health_scores.append(0.5)
            else:  # CRITICAL
                health_scores.append(0.0)

        metrics_health = sum(health_scores) / len(health_scores) if health_scores else 0.5

        # Component 3: Trend Improvement (25% weight)
        trend_7d = await self._calculate_trend(days=7)
        # Convert -1 to 1 trend to 0-1 score
        trend_improvement = (trend_7d + 1.0) / 2.0  # -1 → 0.0, 0 → 0.5, 1 → 1.0

        # Charter-aligned weighted score
        overall_score = 0.50 * hiho_stability + 0.25 * metrics_health + 0.25 * trend_improvement

        return overall_score

    async def _calculate_trend(self, days: int = 7) -> float:
        """
        Calculate health trend over past N days.

        Returns:
            Trend value -1 to 1 (negative = declining, positive = improving)
        """

        result = await self.db.query(
            """
            SELECT overall_health_score FROM platform_health_digests
            WHERE timestamp >= type::datetime($start_date)
            ORDER BY timestamp ASC;
        """,
            {"start_date": (datetime.now() - timedelta(days=days)).isoformat()},
        )

        if len(result) < 2:
            return 0.0  # Not enough data

        scores = [d["overall_health_score"] for d in result]

        # Simple linear regression slope
        n = len(scores)
        x = list(range(n))
        y = scores

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize to -1 to 1 (assume max slope is ±0.1 per day)
        trend = max(-1.0, min(1.0, slope * 10))

        return trend

    async def _generate_recommendations(
        self,
        repo: RepositoryMetrics,
        test: TestMetrics,
        dep: DependencyMetrics,
        health_checks: list[HealthCheckResult],
        hiho_stable: bool,
    ) -> list[str]:
        """Generate actionable recommendations based on health checks."""

        recommendations = []

        # Repository size recommendations
        if repo.size_gb > 10.0:
            recommendations.append(
                f"❌ CRITICAL: Repository size {repo.size_gb:.2f} GB exceeds limit (>10GB). "
                "Run aggressive gc or filter-repo cleanup."
            )
        elif repo.size_gb > 8.0:
            recommendations.append(
                f"⚠️  WARNING: Repository size {repo.size_gb:.2f} GB exceeds HIHO range (4-8GB). "
                "Consider running git gc --aggressive."
            )
        elif repo.size_gb < 4.0:
            recommendations.append(
                f"⚠️  Repository size {repo.size_gb:.2f} GB below HIHO range. "
                "Consider if critical data is missing."
            )

        # Large file recommendations
        if repo.large_file_count > 100:
            recommendations.append(
                f"❌ CRITICAL: {repo.large_file_count} large files (>1MB) in history. "
                "Migrate to git-lfs or remove with filter-repo."
            )
        elif repo.large_file_count > 50:
            recommendations.append(
                f"⚠️  WARNING: {repo.large_file_count} large files. "
                "Review for git-lfs migration candidates."
            )

        # Pack efficiency recommendations
        if repo.pack_efficiency < 0.5:
            recommendations.append(
                f"❌ CRITICAL: Poor pack efficiency ({repo.pack_efficiency:.1%}), "
                f"{repo.loose_objects} loose objects. Run git gc immediately."
            )
        elif repo.pack_efficiency < 0.7:
            recommendations.append(
                f"⚠️  WARNING: Pack efficiency {repo.pack_efficiency:.1%}. Run git gc --auto."
            )

        # Test recommendations
        if test.pass_rate < 0.90:
            recommendations.append(
                f"❌ CRITICAL: Test pass rate {test.pass_rate:.1%} below 90%. "
                "Fix failing tests immediately."
            )
        elif test.pass_rate < 0.95:
            recommendations.append(
                f"⚠️  WARNING: Test pass rate {test.pass_rate:.1%} below target (95%). "
                "Investigate failing tests."
            )

        # Dependency recommendations
        if dep.vulnerable_dependencies > 0:
            recommendations.append(
                f"❌ CRITICAL: {dep.vulnerable_dependencies} vulnerable dependencies. "
                "Update immediately."
            )
        elif dep.outdated_dependencies > 5:
            recommendations.append(
                f"⚠️  WARNING: {dep.outdated_dependencies} outdated dependencies. "
                "Schedule update sprint."
            )

        # HIHO stability recommendation
        if not hiho_stable:
            recommendations.append(
                "⚠️  System outside HIHO stability range (0.4-0.6 coherence). "
                "Review platform decisions for alignment."
            )

        # If no issues, celebrate!
        if not recommendations:
            recommendations.append("✅ All systems healthy. No actions required.")

        return recommendations

    def _requires_edl_review(
        self, overall_score: float, health_checks: list[HealthCheckResult]
    ) -> bool:
        """
        Determine if EDL review is required.

        Criteria:
        - Overall score < 0.5
        - Any CRITICAL health checks
        """

        if overall_score < 0.5:
            return True

        return any(check.status == HealthStatus.CRITICAL for check in health_checks)

    def _determine_overall_status(
        self, overall_score: float, health_checks: list[HealthCheckResult]
    ) -> HealthStatus:
        """Determine overall health status from score and checks."""

        # If any check is CRITICAL, overall is CRITICAL
        for check in health_checks:
            if check.status == HealthStatus.CRITICAL:
                return HealthStatus.CRITICAL

        # Otherwise, use score
        if overall_score >= 0.7:
            return HealthStatus.HEALTHY
        elif overall_score >= 0.5:
            return HealthStatus.WARNING
        else:
            return HealthStatus.CRITICAL

    async def _persist_digest(self, digest: HealthDigest):
        """Persist digest to SurrealDB for trending."""

        await self.db.query(
            """
            CREATE platform_health_digests CONTENT {
                timestamp: $timestamp,
                overall_health_score: $overall_health_score,
                overall_status: $overall_status,
                hiho_stable: $hiho_stable,
                coherence: $coherence,
                repository_size_gb: $repo_size_gb,
                test_pass_rate: $test_pass_rate,
                dependency_health: $dep_health,
                trend_7d: $trend_7d,
                requires_edl_review: $requires_edl_review
            };
        """,
            {
                "timestamp": digest.timestamp.isoformat(),
                "overall_health_score": digest.overall_health_score,
                "overall_status": digest.overall_status.value,
                "hiho_stable": digest.hiho_stable,
                "coherence": digest.coherence_metrics.coherence,
                "repo_size_gb": digest.repository_metrics.size_gb,
                "test_pass_rate": digest.test_metrics.pass_rate,
                "dep_health": digest.dependency_metrics.health_score,
                "trend_7d": digest.trend_7d,
                "requires_edl_review": digest.requires_edl_review,
            },
        )

    async def route_critical_issues_to_edl(self, digest: HealthDigest):
        """
        Route critical health issues through Expert Domain Lattice.

        Charter requirement: Complex problems must route through EDL.
        """

        if not digest.requires_edl_review:
            return  # No EDL routing needed

        # Build context for EDL
        context = f"""
Platform Health Digest: {digest.timestamp.isoformat()}
Overall Score: {digest.overall_health_score:.3f}
Status: {digest.overall_status.value}
HIHO Stable: {digest.hiho_stable}

Critical Issues:
"""
        for check in digest.health_checks:
            if check.status == HealthStatus.CRITICAL:
                context += f"- {check.check_name}: {check.message}\n"

        context += "\nRecommendations:\n"
        for rec in digest.recommendations:
            if "❌ CRITICAL" in rec:
                context += f"- {rec}\n"

        proposal = "Implement critical health remediation actions"

        # Route through EDL (security domain for platform health)
        consensus = await self.edl_router.route_decision(
            decision_type="security", context=context, proposal=proposal
        )

        # Log EDL consensus
        print(f"\n{'=' * 70}\nEDL CONSENSUS: Platform Health\n{'=' * 70}\n{consensus.reasoning}\n")

    def format_digest_terminal(self, digest: HealthDigest) -> str:
        """Format digest for terminal output."""

        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️ ",
            HealthStatus.CRITICAL: "❌",
        }

        output = f"""
{"=" * 70}
DAILY PLATFORM HEALTH DIGEST
{"=" * 70}
Timestamp: {digest.timestamp.isoformat()}
Overall Score: {digest.overall_health_score:.3f} / 1.0
Status: {status_emoji[digest.overall_status]} {digest.overall_status.value.upper()}
HIHO Stable: {"✅ Yes" if digest.hiho_stable else "⚠️  No"}
Trend (7d): {digest.trend_7d:+.3f} ({"📈 Improving" if digest.trend_7d > 0 else "📉 Declining" if digest.trend_7d < 0 else "→ Stable"})

COHERENCE METRICS
{"─" * 70}
Coherence: {digest.coherence_metrics.coherence:.3f} ({"HIHO ✅" if digest.coherence_metrics.hiho_stable else "Outside HIHO ⚠️"})
Internal State: {digest.coherence_metrics.internal_state:.3f}
External Alignment: {digest.coherence_metrics.external_alignment:.3f}
Stability Score: {digest.coherence_metrics.stability_score:.3f}

REPOSITORY HEALTH
{"─" * 70}
Size: {digest.repository_metrics.size_gb:.2f} GB (HIHO range: 4-8 GB)
Large Files (>1MB): {digest.repository_metrics.large_file_count}
Pack Efficiency: {digest.repository_metrics.pack_efficiency:.1%}
Loose Objects: {digest.repository_metrics.loose_objects}

TEST SUITE
{"─" * 70}
Total Tests: {digest.test_metrics.total_tests}
Passing: {digest.test_metrics.passing_tests}
Failing: {digest.test_metrics.failing_tests}
Pass Rate: {digest.test_metrics.pass_rate:.1%}

DEPENDENCIES
{"─" * 70}
Total: {digest.dependency_metrics.total_dependencies}
Outdated: {digest.dependency_metrics.outdated_dependencies}
Vulnerable: {digest.dependency_metrics.vulnerable_dependencies}
Health Score: {digest.dependency_metrics.health_score:.3f}

HEALTH CHECKS
{"─" * 70}
"""

        for check in digest.health_checks:
            status_icon = status_emoji[check.status]
            output += f"{status_icon} {check.check_name}: {check.message}\n"

        output += f"""
RECOMMENDATIONS
{"─" * 70}
"""
        for rec in digest.recommendations:
            output += f"{rec}\n"

        if digest.requires_edl_review:
            output += f"""
{"─" * 70}
⚠️  REQUIRES EDL REVIEW: Critical issues detected
Run: digest.route_critical_issues_to_edl()
"""

        output += f"\n{'=' * 70}\n"

        return output


# Singleton accessor
_daily_health_digest = None


def get_daily_health_digest() -> DailyHealthDigest:
    """Get global daily health digest instance."""
    global _daily_health_digest
    if _daily_health_digest is None:
        _daily_health_digest = DailyHealthDigest()
    return _daily_health_digest


def reset_daily_health_digest():
    """Reset global daily health digest (for testing)."""
    global _daily_health_digest
    _daily_health_digest = None
