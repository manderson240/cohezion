# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Coordination system for TDD and Adversarial Review in Compound Engineering
Integrates test-driven development with multiperspective adversarial review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from cohezion.compound.skill_refiner import SkillRefinementInput
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewPerspective,
    get_adversarial_review_system,
)
from cohezion.compound.tdd_adversarial.tdd_integration import (
    TestType,
    get_tdd_integration,
)


logger = structlog.get_logger(__name__)


@dataclass
class TDDAdversarialState:
    """Combined state for TDD and Adversarial Review systems."""

    session_id: str
    tdd_metrics: dict[str, Any] = field(default_factory=dict)
    adversarial_metrics: dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    integration_cycles: int = 0
    tdd_driven_improvements: int = 0
    review_driven_improvements: int = 0
    conflict_resolutions: int = 0


class TDDAdversarialCoordinator:
    """
    Coordinates TDD and Adversarial Review systems for compound engineering.

    This system integrates:
    1. Test-Driven Development - Ensuring code quality through testing
    2. Multiperspective Adversarial Review - Ensuring robust design through diverse viewpoints

    The coordination creates a virtuous cycle:
    - TDD ensures implementation correctness
    - Adversarial review ensures design robustness
    - Feedback from both systems improves skill refinement
    - Improved skills lead to better implementation and design
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logger.bind(component="TDDAdversarialCoordinator")
        self._tdd_integration = get_tdd_integration(project_root)
        self._adversarial_review = get_adversarial_review_system(project_root)
        self._session_states: dict[str, TDDAdversarialState] = {}
        self._integration_patterns = {
            "tdd_first": [TestType.UNIT, TestType.INTEGRATION],  # Run unit/integration tests first
            "review_first": [
                ReviewPerspective.SECURITY,
                ReviewPerspective.PERFORMANCE,
            ],  # Check critical perspectives first
            "balanced": True,  # Alternate between TDD and review
        }

    def get_or_create_state(self, session_id: str) -> TDDAdversarialState:
        """Get or create combined state for a session."""
        if session_id not in self._session_states:
            self._session_states[session_id] = TDDAdversarialState(session_id=session_id)
        return self._session_states[session_id]

    async def run_pre_engineering_checks(self, session_id: str) -> dict[str, Any]:
        """
        Run checks before compound engineering operations.

        This implements the "red" phase of TDD and initial adversarial scrutiny.
        """
        self.logger.info("Running pre-engineering checks", session_id=session_id)

        state = self.get_or_create_state(session_id)

        # Run quick TDD checks - focus on unit tests and critical functionality
        tdd_results = await self._tdd_integration.run_tests(
            session_id,
            test_types=[TestType.UNIT],  # Start with unit tests
            test_path=self.project_root,
        )

        # Run initial adversarial review - focus on security and performance
        review_session = await self._adversarial_review.run_full_adversarial_review(
            session_id, perspectives=[ReviewPerspective.SECURITY, ReviewPerspective.PERFORMANCE]
        )

        # Update state
        state.tdd_metrics = self._tdd_integration.get_tdd_metrics(session_id)
        state.adversarial_metrics = self._adversarial_review.get_adversarial_metrics(session_id)
        state.last_updated = datetime.now(UTC)
        state.integration_cycles += 1

        self.logger.info(
            "Pre-engineering checks completed",
            session_id=session_id,
            tdd_tests_run=state.tdd_metrics.get("tests_run", 0),
            tdd_pass_rate=state.tdd_metrics.get("pass_rate", 0.0),
            adversarial_score=state.adversarial_metrics.get("latest_review", {}).get(
                "overall_score", 0.0
            ),
        )

        return {
            "tdd_results": tdd_results,
            "review_session": review_session,
            "should_proceed": self._should_proceed_with_engineering(state),
            "blocking_issues": self._get_blocking_issues(state),
            "recommendations": self._get_pre_engineering_recommendations(state),
        }

    async def run_post_engineering_checks(self, session_id: str) -> dict[str, Any]:
        """
        Run checks after compound engineering operations.

        This implements the "green" and "refactor" phases of TDD and comprehensive adversarial review.
        """
        self.logger.info("Running post-engineering checks", session_id=session_id)

        state = self.get_or_create_state(session_id)

        # Run comprehensive TDD checks - all test types
        tdd_results = await self._tdd_integration.run_tests(
            session_id,  # Run all test types
            test_path=self.project_root,
        )

        # Run full adversarial review - all perspectives
        review_session = await self._adversarial_review.run_full_adversarial_review(
            session_id  # All perspectives
        )

        # Update state
        state.tdd_metrics = self._tdd_integration.get_tdd_metrics(session_id)
        state.adversarial_metrics = self._adversarial_review.get_adversarial_metrics(session_id)
        state.last_updated = datetime.now(UTC)
        state.integration_cycles += 1

        # Count improvements driven by each system
        tdd_improvements = self._count_tdd_driven_improvements(state)
        review_improvements = self._count_review_driven_improvements(state)
        state.tdd_driven_improvements += tdd_improvements
        state.review_driven_improvements += review_improvements

        self.logger.info(
            "Post-engineering checks completed",
            session_id=session_id,
            tdd_tests_run=state.tdd_metrics.get("tests_run", 0),
            tdd_pass_rate=state.tdd_metrics.get("pass_rate", 0.0),
            tdd_improvements=tdd_improvements,
            adversarial_score=state.adversarial_metrics.get("latest_review", {}).get(
                "overall_score", 0.0
            ),
            review_improvements=review_improvements,
            integration_cycles=state.integration_cycles,
        )

        return {
            "tdd_results": tdd_results,
            "review_session": review_session,
            "engineering_quality": self._assess_engineering_quality(state),
            "improvements": {
                "tdd_driven": tdd_improvements,
                "review_driven": review_improvements,
                "total": tdd_improvements + review_improvements,
            },
            "recommendations": self._get_post_engineering_recommendations(state),
            "next_actions": self._get_next_actions(state),
        }

    def _should_proceed_with_engineering(self, state: TDDAdversarialState) -> bool:
        """Determine if we should proceed with engineering based on pre-checks."""
        tdd_metrics = state.tdd_metrics
        adversarial_metrics = state.adversarial_metrics

        # Check if we have critical blocking issues
        blocking_issues = self._get_blocking_issues(state)
        if blocking_issues:
            return False

        # Check TDD pass rate - should be reasonably high to proceed
        pass_rate = tdd_metrics.get("pass_rate", 0.0)
        if pass_rate < 0.7:  # Less than 70% passing
            return False

        # Check adversarial score - should not be too low
        latest_review = adversarial_metrics.get("latest_review")
        if latest_review:
            overall_score = latest_review.get("overall_score", 0.0)
            if overall_score < 0.4:  # Less than 40% score
                return False

        return True

    def _get_blocking_issues(self, state: TDDAdversarialState) -> list[str]:
        """Get blocking issues that prevent proceeding with engineering."""
        blocking_issues = []

        # Check for critical adversarial findings
        latest_review = state.adversarial_metrics.get("latest_review")
        if latest_review:
            findings = latest_review.get("findings", [])
            critical_findings = [
                f for f in findings if isinstance(f, dict) and f.get("severity") == "critical"
            ]
            if critical_findings:
                blocking_issues.append(
                    f"Critical adversarial findings: {len(critical_findings)} issues"
                )

        # Check for failing critical tests
        tdd_metrics = state.tdd_metrics
        failing_tests = tdd_metrics.get("failing_tests", [])
        # In a real implementation, we'd identify which tests are critical
        if failing_tests and len(failing_tests) > 5:  # Arbitrary threshold
            blocking_issues.append(f"Many failing tests: {len(failing_tests)} tests failing")

        return blocking_issues

    def _get_pre_engineering_recommendations(self, state: TDDAdversarialState) -> list[str]:
        """Get recommendations before starting engineering work."""
        recommendations = []

        tdd_metrics = state.tdd_metrics
        adversarial_metrics = state.adversarial_metrics

        # TDD-based recommendations
        pass_rate = tdd_metrics.get("pass_rate", 0.0)
        if pass_rate < 0.8:
            recommendations.append(
                f"Improve test pass rate before engineering (current: {pass_rate:.1%})"
            )

        coverage = tdd_metrics.get("latest_coverage")
        if coverage is not None and coverage < 70.0:
            recommendations.append(
                f"Increase test coverage before engineering (current: {coverage:.1f}%)"
            )

        # Adversarial review-based recommendations
        latest_review = adversarial_metrics.get("latest_review")
        if latest_review:
            overall_score = latest_review.get("overall_score", 0.0)
            if overall_score < 0.6:
                recommendations.append(
                    f"Address adversarial review concerns before engineering (score: {overall_score:.2f})"
                )

            findings = latest_review.get("findings", [])
            high_critical = [
                f
                for f in findings
                if isinstance(f, dict) and f.get("severity") in ["high", "critical"]
            ]
            if len(high_critical) > 3:
                recommendations.append(
                    f"Address {len(high_critical)} high/critical adversarial findings"
                )

        return recommendations

    def _get_post_engineering_recommendations(self, state: TDDAdversarialState) -> list[str]:
        """Get recommendations after completing engineering work."""
        recommendations = []

        tdd_metrics = state.tdd_metrics
        adversarial_metrics = state.adversarial_metrics

        # TDD-based recommendations
        pass_rate = tdd_metrics.get("pass_rate", 0.0)
        if pass_rate < 0.9:
            recommendations.append(f"Consider improving test pass rate (current: {pass_rate:.1%})")

        coverage = tdd_metrics.get("latest_coverage")
        if coverage is not None and coverage < 80.0:
            recommendations.append(f"Consider increasing test coverage (current: {coverage:.1f}%)")

        # Adversarial review-based recommendations
        latest_review = adversarial_metrics.get("latest_review")
        if latest_review:
            overall_score = latest_review.get("overall_score", 0.0)
            if overall_score < 0.8:
                recommendations.append(
                    f"Consider addressing adversarial review feedback (score: {overall_score:.2f})"
                )

            conflicts = latest_review.get("conflicts", [])
            if len(conflicts) > 2:
                recommendations.append(f"Consider resolving {len(conflicts)} perspective conflicts")

        return recommendations

    def _get_next_actions(self, state: TDDAdversarialState) -> list[str]:
        """Get suggested next actions based on current state."""
        actions = []

        tdd_metrics = state.tdd_metrics
        adversarial_metrics = state.adversarial_metrics

        # Suggest TDD actions
        test_gen_count = tdd_metrics.get("test_generation_count", 0)
        if test_gen_count == 0:
            actions.append("Consider generating tests from specifications")

        # Suggest adversarial review actions
        latest_review = adversarial_metrics.get("latest_review")
        if latest_review:
            consulted = set(latest_review.get("perspectives_consulted", []))
            all_perspectives = {p.value for p in ReviewPerspective}
            missing = all_perspectives - consulted
            if missing:
                actions.append(
                    f"Consider reviewing from missing perspectives: {', '.join(missing)}"
                )

        # Suggest integration actions
        if state.integration_cycles < 3:
            actions.append("Continue with additional TDD/adversarial review cycles")

        return actions

    def _assess_engineering_quality(self, state: TDDAdversarialState) -> dict[str, Any]:
        """Assess the quality of engineering work based on TDD and review results."""
        tdd_metrics = state.tdd_metrics
        adversarial_metrics = state.adversarial_metrics

        # TDD quality score (0.0 to 1.0)
        tdd_quality = 0.0
        pass_rate = tdd_metrics.get("pass_rate", 0.0)
        coverage = tdd_metrics.get("latest_coverage")

        if pass_rate > 0:
            tdd_quality += pass_rate * 0.6  # 60% weight on pass rate
        if coverage is not None:
            tdd_quality += (coverage / 100.0) * 0.4  # 40% weight on coverage

        # Adversarial review quality score (0.0 to 1.0)
        review_quality = 0.0
        latest_review = adversarial_metrics.get("latest_review")
        if latest_review:
            overall_score = latest_review.get("overall_score", 0.0)
            review_quality = overall_score  # Already 0.0 to 1.0

        # Combined quality score
        combined_quality = (tdd_quality * 0.5) + (review_quality * 0.5)

        return {
            "overall_quality": combined_quality,
            "tdd_quality": tdd_quality,
            "review_quality": review_quality,
            "tdd_metrics": {
                "pass_rate": pass_rate,
                "coverage": coverage,
                "tests_run": tdd_metrics.get("tests_run", 0),
            },
            "review_metrics": {
                "overall_score": latest_review.get("overall_score", 0.0) if latest_review else 0.0,
                "findings_count": latest_review.get("findings_count", 0) if latest_review else 0,
                "conflicts_count": latest_review.get("conflicts_count", 0) if latest_review else 0,
            },
        }

    def _count_tdd_driven_improvements(self, state: TDDAdversarialState) -> int:
        """Count improvements driven by TDD feedback."""
        # In a real implementation, we'd track which skill refinements were driven by TDD
        # For now, we'll estimate based on test improvements
        return state.tdd_metrics.get("test_improvement_count", 0)

    def _count_review_driven_improvements(self, state: TDDAdversarialState) -> int:
        """Count improvements driven by adversarial review feedback."""
        # In a real implementation, we'd track which skill refinements were driven by review
        # For now, we'll estimate based on review metrics
        latest_review = state.adversarial_metrics.get("latest_review")
        if latest_review:
            # Count high/severity findings that would drive improvements
            findings = latest_review.get("findings", [])
            high_critical = [
                f
                for f in findings
                if isinstance(f, dict) and f.get("severity") in ["high", "critical"]
            ]
            return len(high_critical)
        return 0

    def get_integration_feedback_for_skill_refinement(
        self, session_id: str
    ) -> list[SkillRefinementInput]:
        """
        Get skill refinement inputs from both TDD and adversarial review systems.

        This is the main integration point where both systems provide feedback
        to improve the compound engineering skills.
        """
        feedback_list = []

        # Get TDD feedback
        tdd_feedback = self._tdd_integration.get_tdd_feedback_for_skill_refinement(session_id)
        feedback_list.extend(tdd_feedback)

        # Get adversarial review feedback
        review_feedback = self._adversarial_review.get_adversarial_feedback_for_skill_refinement(
            session_id
        )
        feedback_list.extend(review_feedback)

        # Add integration-specific feedback
        state = self._session_states.get(session_id)
        if state:
            # If both systems agree on an area for improvement, boost the signal
            tdd_skill_names = {f.skill_name for f in tdd_feedback}
            review_skill_names = {f.skill_name for f in review_feedback}
            common_skills = tdd_skill_names & review_skill_names

            for skill_name in common_skills:
                # Find the feedback entries for this skill from both systems
                tdd_feedback_entry = next(
                    (f for f in tdd_feedback if f.skill_name == skill_name), None
                )
                review_feedback_entry = next(
                    (f for f in review_feedback if f.skill_name == skill_name), None
                )

                if tdd_feedback_entry and review_feedback_entry:
                    # Boost the feedback when both systems agree
                    feedback_list.append(
                        SkillRefinementInput(
                            skill_name=skill_name,
                            performance_metric=min(
                                tdd_feedback_entry.performance_metric,
                                review_feedback_entry.performance_metric,
                            ),
                            feedback=f"Both TDD and Adversarial Review suggest improving {skill_name}",
                            context={
                                "tdd_feedback": tdd_feedback_entry.context,
                                "review_feedback": review_feedback_entry.context,
                                "session_id": session_id,
                                "integration_boost": True,
                            },
                        )
                    )

        # Update the "last_updated" timestamp
        if state:
            state.last_updated = datetime.now(UTC)

        return feedback_list

    def get_integration_metrics(self, session_id: str) -> dict[str, Any]:
        """Get combined metrics from both systems."""
        state = self._session_states.get(session_id)
        if not state:
            return {}

        return {
            "session_id": session_id,
            "integration_cycles": state.integration_cycles,
            "last_updated": state.last_updated.isoformat(),
            "tdd_metrics": state.tdd_metrics,
            "adversarial_metrics": state.adversarial_metrics,
            "improvements": {
                "tdd_driven": state.tdd_driven_improvements,
                "review_driven": state.review_driven_improvements,
                "total": state.tdd_driven_improvements + state.review_driven_improvements,
            },
            "conflict_resolutions": state.conflict_resolutions,
        }


# Global instance for easy access
_tdd_adversarial_coordinator: TDDAdversarialCoordinator | None = None


def get_tdd_adversarial_coordinator(project_root: Path | None = None) -> TDDAdversarialCoordinator:
    """Get or create the global TDD-Adversarial coordination instance."""
    global _tdd_adversarial_coordinator
    if _tdd_adversarial_coordinator is None:
        if project_root is None:
            project_root = Path.cwd()
        _tdd_adversarial_coordinator = TDDAdversarialCoordinator(project_root)
    return _tdd_adversarial_coordinator
