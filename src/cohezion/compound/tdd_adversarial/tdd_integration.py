# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
TDD (Test-Driven Development) Integration for Compound Engineering
Provides test-driven development capabilities to the compound engineering system.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from cohezion.compound.skill_refiner import SkillRefinementInput


logger = structlog.get_logger(__name__)


def _python_exec() -> str:
    """Resolve venv python; fall back to sys.executable."""
    repo_root = Path(__file__).resolve().parents[4]
    venv_py = repo_root / ".venv" / "bin" / "python3"
    if venv_py.exists():
        return str(venv_py)
    return shutil.which("python3") or sys.executable


class TestStatus(Enum):
    """Status of test execution."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"


class TestType(Enum):
    """Types of tests in the TDD system."""

    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class TestResult:
    """Result of a test execution."""

    test_name: str
    test_type: TestType
    status: TestStatus
    execution_time: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    message: str | None = None
    traceback: str | None = None
    coverage: float | None = None  # Percentage of code covered


@dataclass
class TDDState:
    """State of the TDD system for a compound engineering session."""

    session_id: str
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_results: list[TestResult] = field(default_factory=list)
    coverage_history: list[tuple[datetime, float]] = field(default_factory=list)
    failing_tests: set[str] = field(default_factory=set)
    passing_tests: set[str] = field(default_factory=set)
    last_test_run: datetime | None = None
    test_generation_count: int = 0
    test_improvement_count: int = 0


class TDDIntegration:
    """
    Manages Test-Driven Development integration with the compound engineering system.

    Responsibilities:
    - Running tests before and after compound engineering operations
    - Generating test cases from specifications and documentation
    - Tracking test coverage and effectiveness
    - Providing feedback to the skill refinement system based on test results
    - Managing the red-green-refactor cycle
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logger.bind(component="TDDIntegration")
        self._tdd_states: dict[str, TDDState] = {}
        self._test_patterns = {
            TestType.UNIT: ["test_*.py", "*_test.py"],
            TestType.INTEGRATION: ["test_integration_*", "*_integration_test.py"],
            TestType.FUNCTIONAL: ["test_functional_*", "*_functional_test.py"],
            TestType.PERFORMANCE: ["test_performance_*", "*_performance_test.py"],
            TestType.SECURITY: ["test_security_*", "*_security_test.py"],
        }

    def get_or_create_tdd_state(self, session_id: str) -> TDDState:
        """Get or create TDD state for a session."""
        if session_id not in self._tdd_states:
            self._tdd_states[session_id] = TDDState(session_id=session_id)
        return self._tdd_states[session_id]

    async def run_tests(
        self,
        session_id: str,
        test_types: list[TestType] | None = None,
        test_path: Path | None = None,
    ) -> list[TestResult]:
        """
        Run tests and update TDD state.

        Args:
            session_id: The compound engineering session ID
            test_types: Types of tests to run (None for all)
            test_path: Specific path to run tests from (None for project root)

        Returns:
            List of test results
        """
        tdd_state = self.get_or_create_tdd_state(session_id)
        search_path = test_path or self.project_root
        test_types = test_types or list(TestType)

        self.logger.info(
            "Running tests",
            session_id=session_id,
            test_types=[t.value for t in test_types],
            path=str(search_path),
        )

        all_results = []

        for test_type in test_types:
            results = await self._run_test_type(test_type, search_path)
            all_results.extend(results)

        # Update TDD state
        tdd_state.tests_run += len(all_results)
        tdd_state.tests_passed += len([r for r in all_results if r.status == TestStatus.PASSED])
        tdd_state.tests_failed += len([r for r in all_results if r.status == TestStatus.FAILED])
        tdd_state.test_results.extend(all_results)
        tdd_state.last_test_run = datetime.now(UTC)

        # Update passing/failing sets
        for result in all_results:
            if result.status == TestStatus.PASSED:
                tdd_state.passing_tests.add(result.test_name)
                tdd_state.failing_tests.discard(result.test_name)
            elif result.status == TestStatus.FAILED:
                tdd_state.failing_tests.add(result.test_name)
                tdd_state.passing_tests.discard(result.test_name)

        # Update coverage if available
        coverage = await self._get_coverage()
        if coverage is not None:
            tdd_state.coverage_history.append((datetime.now(UTC), coverage))

        self.logger.info(
            "Tests completed",
            session_id=session_id,
            total=len(all_results),
            passed=tdd_state.tests_passed,
            failed=tdd_state.tests_failed,
            coverage=coverage,
        )

        return all_results

    async def _run_test_type(self, test_type: TestType, search_path: Path) -> list[TestResult]:
        """Run tests of a specific type."""
        results = []

        # Build pytest command for this test type
        patterns = self._test_patterns[test_type]
        pattern_args = []
        for pattern in patterns:
            pattern_args.extend(["-k", pattern])

        cmd = [
            _python_exec(),
            "-m",
            "pytest",
            str(search_path),
            "-v",
            "--tb=short",
            *pattern_args,
            "--disable-warnings",
        ]

        try:
            start_time = time.time()
            result = subprocess.run(  # noqa: S603 - cmd built from internal config and pytest args
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.project_root),
            )
            execution_time = time.time() - start_time

            # Parse pytest output (simplified - in practice would use pytest-json or similar)
            if result.returncode == 0:
                # All tests passed
                # In a real implementation, we'd parse the JSON output to get individual test results
                results.append(
                    TestResult(
                        test_name=f"{test_type.value}_suite",
                        test_type=test_type,
                        status=TestStatus.PASSED,
                        execution_time=execution_time,
                        message="All tests passed",
                    )
                )
            else:
                # Some tests failed
                # Again, in practice we'd parse detailed results
                results.append(
                    TestResult(
                        test_name=f"{test_type.value}_suite",
                        test_type=test_type,
                        status=TestStatus.FAILED,
                        execution_time=execution_time,
                        message=f"Some tests failed: {result.stdout[:200]}...",
                    )
                )

        except subprocess.TimeoutExpired:
            results.append(
                TestResult(
                    test_name=f"{test_type.value}_suite",
                    test_type=test_type,
                    status=TestStatus.ERROR,
                    execution_time=300.0,
                    message="Test execution timed out",
                )
            )
        except Exception as e:
            results.append(
                TestResult(
                    test_name=f"{test_type.value}_suite",
                    test_type=test_type,
                    status=TestStatus.ERROR,
                    execution_time=0.0,
                    message=f"Test execution failed: {e!s}",
                )
            )

        return results

    async def _get_coverage(self) -> float | None:
        """Get code coverage percentage."""
        try:
            # Run coverage command
            result = subprocess.run(  # noqa: S603 - args fully static
                [_python_exec(), "-m", "coverage", "report", "--format=total"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                # Parse output like "91.2"
                coverage_str = result.stdout.strip()
                return float(coverage_str)
            else:
                self.logger.warning("Failed to get coverage", error=result.stderr)
                return None
        except Exception as e:
            self.logger.warning("Error getting coverage", error=str(e))
            return None

    async def generate_tests_from_specification(
        self, session_id: str, specification: str
    ) -> list[str]:
        """
        Generate test cases from a specification.

        This is a simplified implementation - in practice this would use
        LLMs or other AI systems to generate meaningful tests from specs.
        """
        tdd_state = self.get_or_create_tdd_state(session_id)
        tdd_state.test_generation_count += 1

        # Simplified test generation - in practice this would be much more sophisticated
        generated_tests = [
            f"def test_{specification.lower().replace(' ', '_')}_basic():",
            f'    """Test basic functionality of {specification}."""',
            "    # TODO: Implement test based on specification",
            "    assert True  # Placeholder",
            "",
            f"def test_{specification.lower().replace(' ', '_')}_edge_cases():",
            f'    """Test edge cases for {specification}."""',
            "    # TODO: Implement edge case tests",
            "    assert True  # Placeholder",
        ]

        self.logger.info(
            "Generated tests from specification",
            session_id=session_id,
            specification=specification,
            test_count=len([t for t in generated_tests if t.startswith("def test_")]),
        )

        return generated_tests

    def get_tdd_feedback_for_skill_refinement(self, session_id: str) -> list[SkillRefinementInput]:
        """
        Generate skill refinement inputs based on TDD results.

        Returns feedback that can be used to improve skills based on test performance.
        """
        tdd_state = self._tdd_states.get(session_id)
        if not tdd_state:
            return []

        feedback_list = []

        # If we have failing tests, suggest improving testing-related skills
        if tdd_state.failing_tests:
            feedback_list.append(
                SkillRefinementInput(
                    skill_name="test_engineer",
                    performance_metric=len(tdd_state.failing_tests) / max(tdd_state.tests_run, 1),
                    feedback=f"Failing tests detected: {', '.join(list(tdd_state.failing_tests)[:5])}{'...' if len(tdd_state.failing_tests) > 5 else ''}",
                    context={
                        "failing_tests": list(tdd_state.failing_tests),
                        "session_id": session_id,
                    },
                )
            )

        # If coverage is low, suggest improving test generation skills
        if tdd_state.coverage_history:
            latest_coverage = tdd_state.coverage_history[-1][1]
            if latest_coverage < 80.0:  # Below 80% coverage
                feedback_list.append(
                    SkillRefinementInput(
                        skill_name="test_generator",
                        performance_metric=latest_coverage / 100.0,
                        feedback=f"Low test coverage: {latest_coverage:.1f}%",
                        context={"coverage": latest_coverage, "session_id": session_id},
                    )
                )

        # If tests are passing well, suggest refining the skills that produced the working code
        if tdd_state.tests_passed > tdd_state.tests_failed and tdd_state.tests_run > 0:
            success_rate = tdd_state.tests_passed / tdd_state.tests_run
            if success_rate > 0.8:  # Above 80% success rate
                feedback_list.append(
                    SkillRefinementInput(
                        skill_name="solution_generator",
                        performance_metric=success_rate,
                        feedback=f"High test success rate: {success_rate:.1%}",
                        context={"success_rate": success_rate, "session_id": session_id},
                    )
                )

        return feedback_list

    def get_tdd_metrics(self, session_id: str) -> dict[str, Any]:
        """Get TDD metrics for a session."""
        tdd_state = self._tdd_states.get(session_id)
        if not tdd_state:
            return {}

        return {
            "session_id": session_id,
            "tests_run": tdd_state.tests_run,
            "tests_passed": tdd_state.tests_passed,
            "tests_failed": tdd_state.tests_failed,
            "pass_rate": tdd_state.tests_passed / max(tdd_state.tests_run, 1),
            "latest_coverage": tdd_state.coverage_history[-1][1]
            if tdd_state.coverage_history
            else None,
            "coverage_trend": [
                {"timestamp": ts.isoformat(), "coverage": cov}
                for ts, cov in tdd_state.coverage_history[-10:]
            ],  # Last 10 points
            "failing_tests": list(tdd_state.failing_tests),
            "passing_tests": list(tdd_state.passing_tests),
            "test_generation_count": tdd_state.test_generation_count,
            "test_improvement_count": tdd_state.test_improvement_count,
            "last_test_run": tdd_state.last_test_run.isoformat()
            if tdd_state.last_test_run
            else None,
        }


# Global instance for easy access
_tdd_integration: TDDIntegration | None = None


def get_tdd_integration(project_root: Path | None = None) -> TDDIntegration:
    """Get or create the global TDD integration instance."""
    global _tdd_integration
    if _tdd_integration is None:
        if project_root is None:
            project_root = Path.cwd()
        _tdd_integration = TDDIntegration(project_root)
    return _tdd_integration
