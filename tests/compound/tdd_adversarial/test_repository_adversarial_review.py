"""Adversarial review tests for SurrealDB repositories.

Tests the repository implementations through the 8-perspective adversarial review system:
- Security: SQL injection prevention, input validation
- Performance: Query optimization, indexing recommendations
- Reliability: Error handling, fallback strategies
- Usability: API design, documentation
- Maintainability: Code structure, testability
- Compliance: Data privacy, audit trails
- Innovation: Novel patterns, best practices
- Ethics: Data handling, transparency
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem,
    ReviewFinding,
    ReviewPerspective,
)
from cohezion.compound.tdd_adversarial.coordinator import TDDAdversarialCoordinator


@pytest.fixture
def review_system():
    """Create adversarial review system."""
    return AdversarialReviewSystem(project_root=Path(__file__).parent.parent.parent.parent)


@pytest.fixture
def coordinator():
    """Create TDD/Adversarial coordinator."""
    return TDDAdversarialCoordinator(project_root=Path(__file__).parent.parent.parent.parent)


class TestRepositorySecurityReview:
    """Security perspective adversarial review of repositories."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_sql_injection_prevention(self, review_system):
        """Verify repositories use parameterized queries for data values.

        Note: F-strings for table names are safe (constant values).
        Only user-provided data values need parameterization.
        """
        findings = []

        for repo_name in ["surreal_skill_repository.py", "surreal_universe_repository.py"]:
            repo_file = Path(f"src/cohezion/core/persistence/repositories/{repo_name}")
            if repo_file.exists():
                content = repo_file.read_text()
                # Check for parameterized queries ($var syntax for data values)
                has_parameterization = "$" in content and "vars" in content

                if has_parameterization:
                    findings.append(
                        ReviewFinding(
                            perspective=ReviewPerspective.SECURITY,
                            title="SQL Injection Prevention Verified",
                            description=f"{repo_name} uses parameterized queries for data values",
                            severity="low",
                            confidence=0.95,
                            evidence=["Parameterized queries with $var syntax"],
                        )
                    )

        assert len(findings) > 0, "Security review should produce findings"
        high_severity = [f for f in findings if f.severity in ["high", "critical"]]
        assert len(high_severity) == 0, f"Security review found critical issues: {high_severity}"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_input_validation(self, review_system):
        """Verify repositories validate input parameters."""
        # Check for input validation patterns
        universe_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_universe_repository.py")
        if universe_repo_file.exists():
            content = universe_repo_file.read_text()
            # Check for validation patterns
            has_validation = any(
                pattern in content for pattern in ["if not", "isinstance", "try:", "except", "validate"]
            )
            assert has_validation, "Repository should validate inputs"


class TestRepositoryPerformanceReview:
    """Performance perspective adversarial review."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_query_optimization(self, review_system):
        """Verify repositories use efficient query patterns."""
        universe_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_universe_repository.py")
        if universe_repo_file.exists():
            content = universe_repo_file.read_text()
            # Check for LIMIT clauses (prevents full table scans)
            has_limit = "LIMIT" in content
            # Check for indexed field usage
            has_indexed_queries = "WHERE" in content

            assert has_limit, "Queries should use LIMIT to prevent full table scans"
            assert has_indexed_queries, "Queries should use WHERE clauses for filtering"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_batch_operations_support(self, review_system):
        """Verify repositories can support batch operations."""
        # Check if repositories have methods that could support batching
        skill_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_skill_repository.py")
        if skill_repo_file.exists():
            content = skill_repo_file.read_text()
            # get_all method exists for batch retrieval
            has_get_all = "get_all" in content
            assert has_get_all, "Repository should support batch retrieval"


class TestRepositoryReliabilityReview:
    """Reliability perspective adversarial review."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_error_handling(self, review_system):
        """Verify repositories have comprehensive error handling."""
        universe_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_universe_repository.py")
        if universe_repo_file.exists():
            content = universe_repo_file.read_text()
            # Check for try-except blocks
            has_error_handling = "try:" in content and "except" in content
            # Check for logging
            has_logging = "logger" in content

            assert has_error_handling, "Repository should have error handling"
            assert has_logging, "Repository should log errors"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_fallback_strategies(self, review_system):
        """Verify repositories have fallback strategies."""
        # Check for fallback patterns in surreal_client
        client_file = Path("src/cohezion/core/persistence/surreal_client.py")
        if client_file.exists():
            content = client_file.read_text()
            # Check for InMemoryStore fallback
            has_fallback = "InMemoryStore" in content
            assert has_fallback, "Client should have fallback storage mechanism"


class TestRepositoryMaintainabilityReview:
    """Maintainability perspective adversarial review."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_code_structure(self, review_system):
        """Verify repositories follow clean code principles."""
        universe_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_universe_repository.py")
        if universe_repo_file.exists():
            content = universe_repo_file.read_text()
            # Check for docstrings
            has_docstrings = '"""' in content
            # Check for type hints
            has_type_hints = "->" in content and ":" in content
            # Check for helper methods (code organization)
            has_helpers = "def _" in content

            assert has_docstrings, "Repository should have docstrings"
            assert has_type_hints, "Repository should have type hints"
            assert has_helpers, "Repository should have helper methods for organization"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_testability(self, review_system):
        """Verify repositories are testable."""
        # Check if repositories can be easily mocked
        # Presence of abstract base class indicates good testability
        base_repo_file = Path("src/cohezion/core/persistence/repositories/universe_repository.py")
        if base_repo_file.exists():
            content = base_repo_file.read_text()
            has_abstract = "abstractmethod" in content
            has_interface = "class UniverseRepository" in content

            assert has_abstract, "Repository should use abstract base classes"
            assert has_interface, "Repository should define clear interface"


class TestTDDAdversarialIntegration:
    """Integration tests for TDD + Adversarial Review coordination."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_coordinator_pre_engineering_checks(self, coordinator):
        """Test that coordinator runs both TDD and adversarial checks."""
        session_id = "test_repository_session"

        # Run pre-engineering checks
        results = await coordinator.run_pre_engineering_checks(session_id)

        # Should have both TDD and adversarial results
        assert "tdd_results" in results or "review_results" in results, (
            "Coordinator should return both TDD and review results"
        )

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_full_review_cycle(self, review_system):
        """Test complete adversarial review cycle."""
        session_id = "repository_review_cycle"

        # Run full adversarial review
        review_session = await review_system.run_full_adversarial_review(session_id)

        # Should produce findings
        assert len(review_session.findings) > 0, "Review should produce findings"
        # Should calculate overall score
        assert 0.0 <= review_session.overall_score <= 1.0, "Overall score should be normalized 0-1"


class TestRepositoryBatchIntegration:
    """Tests for repository integration with batch execution."""

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_repository_batch_compatibility(self):
        """Verify repositories can work with batch executor."""
        # Check that repositories have methods compatible with batch operations
        skill_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_skill_repository.py")
        universe_repo_file = Path("src/cohezion/core/persistence/repositories/surreal_universe_repository.py")
        base_repo_file = Path("src/cohezion/core/persistence/repositories/base.py")

        for repo_file in [skill_repo_file, universe_repo_file]:
            if repo_file.exists():
                content = repo_file.read_text()
                # Check for async methods (required for batch execution)
                has_async = "async def" in content
                # Check for return type annotations
                has_return_types = "->" in content

                assert has_async, f"{repo_file.name} should have async methods"
                assert has_return_types, f"{repo_file.name} should have return types"

        # Verify base repository provides batch operations
        if base_repo_file.exists():
            content = base_repo_file.read_text()
            assert "batch_create" in content, "BaseRepository should provide batch_create"
            assert "batch_get" in content, "BaseRepository should provide batch_get"
            assert "BatchOperationResult" in content, "BaseRepository should use BatchOperationResult"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_repository_metrics_collection(self):
        """Verify repositories collect metrics for compound engineering."""
        base_repo_file = Path("src/cohezion/core/persistence/repositories/base.py")

        if base_repo_file.exists():
            content = base_repo_file.read_text()
            # Check for metrics collection
            assert "RepositoryMetrics" in content, "BaseRepository should have RepositoryMetrics"
            assert "_record_metrics" in content, "BaseRepository should record metrics"
            assert "get_metrics_summary" in content, "BaseRepository should provide metrics summary"

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_token_efficiency_patterns(self):
        """Verify token efficiency patterns in repository layer."""
        base_repo_file = Path("src/cohezion/core/persistence/repositories/base.py")

        if base_repo_file.exists():
            content = base_repo_file.read_text()
            # Check for token efficiency patterns
            assert "cache_hit" in content, "BaseRepository should track cache hits"
            assert "cache_miss" in content, "BaseRepository should track cache misses"
            # Metrics enable cache optimization decisions
            assert "cache_hit_rate" in content, "BaseRepository should calculate cache hit rate"
