"""
Coherence tracking aligned with 0.5 HIHO stability principle.
Charter requirement: "Maximum stability at exactly 50% coherence overlap"
"""

from datetime import datetime, timedelta

from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client


class CoherenceMetrics(BaseModel):
    """System coherence measurements."""

    timestamp: datetime
    internal_state: float  # 0-1: Test pass rate, code quality, dependencies
    external_alignment: float  # 0-1: Research relevance, security, performance
    coherence: float  # Overlap between internal and external
    hiho_stable: bool  # True if 0.4 <= coherence <= 0.6
    hiho_delta: float  # Distance from perfect 0.5
    stability_score: float  # 1.0 at 0.5, 0.0 at extremes


class CoherenceTracker:
    """Track system coherence against HIHO stability baseline."""

    def __init__(self):
        self.db = get_surreal_client()
        self.target_coherence = 0.5  # Charter mandated

    async def measure_system_coherence(self) -> CoherenceMetrics:
        """
        Measure current system coherence.

        Charter Principle: Coherence = overlap between internal intent
        and external environment. Maximum stability at 0.5.
        """

        # Internal State (How well is the system functioning?)
        internal_state = await self._measure_internal_state()

        # External Alignment (How well aligned with mission/environment?)
        external_alignment = await self._measure_external_alignment()

        # Coherence = Overlap
        coherence = (internal_state + external_alignment) / 2

        # HIHO Stability Check
        hiho_delta = abs(coherence - self.target_coherence)
        hiho_stable = 0.4 <= coherence <= 0.6

        # Stability Score (1.0 at perfect HIHO, 0.0 at extremes)
        stability_score = max(0.0, 1.0 - (hiho_delta * 2))

        metrics = CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=internal_state,
            external_alignment=external_alignment,
            coherence=coherence,
            hiho_stable=hiho_stable,
            hiho_delta=hiho_delta,
            stability_score=stability_score,
        )

        # Persist to SurrealDB
        await self._persist_metrics(metrics)

        return metrics

    async def _measure_internal_state(self) -> float:
        """
        Internal State = System health metrics.

        Components:
        - Test pass rate (40%)
        - Code quality (30%)
        - Dependency health (30%)
        """

        # Query test results
        test_pass_rate = await self._get_test_pass_rate()

        # Query code quality (linter errors, complexity)
        code_quality = await self._get_code_quality()

        # Query dependency health (outdated, vulnerabilities)
        dependency_health = await self._get_dependency_health()

        internal = test_pass_rate * 0.4 + code_quality * 0.3 + dependency_health * 0.3

        return internal

    async def _measure_external_alignment(self) -> float:
        """
        External Alignment = Mission/environment alignment.

        Components:
        - Research relevance (40%)
        - Security posture (30%)
        - Performance vs targets (30%)
        """

        # Research relevance (how current is our knowledge?)
        research_relevance = await self._get_research_relevance()

        # Security posture (CVEs addressed, audit compliance)
        security_posture = await self._get_security_posture()

        # Performance (meeting latency/throughput targets?)
        performance = await self._get_performance_alignment()

        external = research_relevance * 0.4 + security_posture * 0.3 + performance * 0.3

        return external

    async def _get_test_pass_rate(self) -> float:
        """Get current test pass rate (0-1)."""
        result = await self.db.query(
            """
            SELECT * FROM test_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            return metrics.get("pass_rate", 0.0)
        return 0.0

    async def _get_code_quality(self) -> float:
        """Get code quality score (0-1)."""
        # Run ruff check and calculate score
        # Simplified: 1.0 - (errors / max_acceptable_errors)
        import subprocess

        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/", "--statistics"],
            capture_output=True,
            text=True,
        )

        # Parse error count
        error_count = result.stdout.count("error")
        max_acceptable = 100  # Threshold

        quality = max(0.0, 1.0 - (error_count / max_acceptable))
        return quality

    async def _get_dependency_health(self) -> float:
        """Get dependency health score (0-1)."""
        result = await self.db.query(
            """
            SELECT * FROM dependency_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            health_score = metrics.get("health_score", 0.0)
            return health_score / 100  # Convert 0-100 to 0-1
        return 0.5  # Default

    async def _get_research_relevance(self) -> float:
        """Get research relevance score (0-1)."""
        # Days since last research update
        result = await self.db.query(
            """
            SELECT * FROM research_papers
            ORDER BY published_date DESC
            LIMIT 1;
        """
        )

        if result:
            latest = result[0]
            days_old = (datetime.now() - latest["published_date"]).days

            # Score: 1.0 if <7 days, decays to 0.0 at 30+ days
            relevance = max(0.0, 1.0 - (days_old / 30))
            return relevance
        return 0.5  # Default

    async def _get_security_posture(self) -> float:
        """Get security posture score (0-1)."""
        result = await self.db.query(
            """
            SELECT * FROM security_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            # Score based on vulnerabilities
            critical = metrics.get("vulnerabilities_critical", 0)
            high = metrics.get("vulnerabilities_high", 0)

            if critical > 0:
                return 0.0  # Critical vulns = 0 score
            elif high > 0:
                return 0.5 - (high * 0.1)  # -0.1 per high vuln
            else:
                return 1.0  # No vulns = perfect score
        return 0.5  # Default

    async def _get_performance_alignment(self) -> float:
        """Get performance alignment vs targets (0-1)."""
        result = await self.db.query(
            """
            SELECT * FROM performance_metrics
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        )

        if result:
            metrics = result[0]
            latency_ms = metrics.get("compound_executor_latency_ms", 500)

            # Target: <500ms, acceptable: <1000ms
            if latency_ms < 500:
                return 1.0
            elif latency_ms < 1000:
                return 1.0 - ((latency_ms - 500) / 500)
            else:
                return 0.0
        return 0.5  # Default

    async def _persist_metrics(self, metrics: CoherenceMetrics):
        """Persist coherence metrics to SurrealDB."""
        await self.db.query(
            """
            CREATE coherence_metrics CONTENT {
                timestamp: $timestamp,
                internal_state: $internal_state,
                external_alignment: $external_alignment,
                coherence: $coherence,
                hiho_stable: $hiho_stable,
                hiho_delta: $hiho_delta,
                stability_score: $stability_score
            };
        """,
            {
                "timestamp": metrics.timestamp.isoformat(),
                "internal_state": metrics.internal_state,
                "external_alignment": metrics.external_alignment,
                "coherence": metrics.coherence,
                "hiho_stable": metrics.hiho_stable,
                "hiho_delta": metrics.hiho_delta,
                "stability_score": metrics.stability_score,
            },
        )

    def is_hiho_stable(self, coherence: float) -> bool:
        """Check if coherence is within HIHO stability range."""
        return 0.4 <= coherence <= 0.6

    async def get_coherence_trend(self, days: int = 7) -> list[float]:
        """Get historical coherence trend."""
        result = await self.db.query(
            """
            SELECT coherence FROM coherence_metrics
            WHERE timestamp >= type::datetime($start_date)
            ORDER BY timestamp ASC;
        """,
            {"start_date": (datetime.now() - timedelta(days=days)).isoformat()},
        )

        return [m["coherence"] for m in result]


# Singleton accessor
_coherence_tracker = None


def get_coherence_tracker() -> CoherenceTracker:
    """Get global coherence tracker instance."""
    global _coherence_tracker
    if _coherence_tracker is None:
        _coherence_tracker = CoherenceTracker()
    return _coherence_tracker


def reset_coherence_tracker():
    """Reset global coherence tracker (for testing)."""
    global _coherence_tracker
    _coherence_tracker = None
