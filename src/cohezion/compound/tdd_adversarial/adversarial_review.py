# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Multiperspective Adversarial Review System for Compound Engineering
Provides multiple perspective analysis to improve compound engineering decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from cohezion.compound.skill_refiner import SkillRefinementInput


logger = structlog.get_logger(__name__)


class ReviewPerspective(Enum):
    """Different perspectives for adversarial review."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    USABILITY = "usability"
    MAINTAINABILITY = "maintainability"
    COMPLIANCE = "compliance"
    INNOVATION = "innovation"
    ETHICS = "ethics"


@dataclass
class ReviewFinding:
    """A finding from an adversarial review perspective."""

    perspective: ReviewPerspective
    title: str
    description: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    evidence: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


@dataclass
class PerspectiveState:
    """State tracking for a specific review perspective."""

    perspective: ReviewPerspective
    session_id: str
    findings: list[ReviewFinding] = field(default_factory=list)
    last_review: datetime | None = None
    review_count: int = 0
    avg_findings_per_review: float = 0.0
    severity_distribution: dict[str, int] = field(
        default_factory=lambda: {"low": 0, "medium": 0, "high": 0, "critical": 0}
    )


@dataclass
class ReviewSession:
    """A complete adversarial review session."""

    session_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    perspectives_consulted: list[ReviewPerspective] = field(default_factory=list)
    findings: list[ReviewFinding] = field(default_factory=list)
    conflicts: list[tuple[ReviewFinding, ReviewFinding]] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    overall_score: float = 0.0  # 0.0 to 1.0, higher is better


class AdversarialReviewSystem:
    """
    Manages multiperspective adversarial review for the compound engineering system.

    Responsibilities:
    - Running analysis from multiple perspectives (security, performance, etc.)
    - Detecting conflicts between perspectives
    - Synthesizing insights from diverse viewpoints
    - Tracking review history and effectiveness
    - Providing feedback to skill refinement based on review outcomes
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = logger.bind(component="AdversarialReviewSystem")
        self._perspective_states: dict[tuple[ReviewPerspective, str], PerspectiveState] = {}
        self._review_sessions: list[ReviewSession] = []
        self._perspective_weights = {
            ReviewPerspective.SECURITY: 0.20,
            ReviewPerspective.PERFORMANCE: 0.15,
            ReviewPerspective.RELIABILITY: 0.15,
            ReviewPerspective.USABILITY: 0.15,
            ReviewPerspective.MAINTAINABILITY: 0.15,
            ReviewPerspective.COMPLIANCE: 0.10,
            ReviewPerspective.INNOVATION: 0.10,
            ReviewPerspective.ETHICS: 0.05,
        }

    def get_or_create_perspective_state(
        self, perspective: ReviewPerspective, session_id: str
    ) -> PerspectiveState:
        """Get or create state for a perspective in a session."""
        key = (perspective, session_id)
        if key not in self._perspective_states:
            self._perspective_states[key] = PerspectiveState(
                perspective=perspective, session_id=session_id
            )
        return self._perspective_states[key]

    async def run_perspective_review(
        self, session_id: str, perspective: ReviewPerspective, focus_areas: list[str] | None = None
    ) -> list[ReviewFinding]:
        """
        Run adversarial review from a specific perspective.

        Args:
            session_id: The compound engineering session ID
            perspective: The perspective to review from
            focus_areas: Specific areas to focus on (None for general review)

        Returns:
            List of findings from this perspective
        """
        perspective_state = self.get_or_create_perspective_state(perspective, session_id)
        focus_areas = focus_areas or []

        self.logger.info(
            "Running perspective review",
            session_id=session_id,
            perspective=perspective.value,
            focus_areas=focus_areas,
        )

        # Simulate perspective-specific analysis
        # In a real implementation, this would use specialized agents or models
        findings = await self._analyze_from_perspective(perspective, session_id, focus_areas)

        # Update perspective state
        perspective_state.findings.extend(findings)
        perspective_state.last_review = datetime.now(UTC)
        perspective_state.review_count += 1

        # Update severity distribution
        for finding in findings:
            perspective_state.severity_distribution[finding.severity] = (
                perspective_state.severity_distribution.get(finding.severity, 0) + 1
            )

        # Update average findings per review
        total_findings = sum(
            len(state.findings)
            for state in self._perspective_states.values()
            if state.session_id == session_id
        )
        perspective_state.avg_findings_per_review = total_findings / max(
            perspective_state.review_count, 1
        )

        self.logger.info(
            "Perspective review completed",
            session_id=session_id,
            perspective=perspective.value,
            findings_count=len(findings),
        )

        return findings

    async def _analyze_from_perspective(
        self, perspective: ReviewPerspective, session_id: str, focus_areas: list[str]
    ) -> list[ReviewFinding]:
        """Analyze the system from a specific perspective."""
        # This is a simplified implementation - in practice this would use
        # specialized agents, models, or analysis tools for each perspective

        findings = []

        # Simulate some findings based on perspective
        if perspective == ReviewPerspective.SECURITY:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.SECURITY,
                        title="Potential input validation issue",
                        description="User input in agent communication lacks sufficient validation",
                        severity="medium",
                        confidence=0.7,
                        evidence=["Review of agent communication patterns"],
                        suggestions=["Add input validation and sanitization"],
                        related_files=["src/cohezion/agents/", "src/cohezion/compound/"],
                    )
                ]
            )
        elif perspective == ReviewPerspective.PERFORMANCE:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.PERFORMANCE,
                        title="Potential bottleneck in feedback loop",
                        description="Feedback processing may become slow with many agents",
                        severity="low",
                        confidence=0.6,
                        evidence=["Analysis of feedback loop architecture"],
                        suggestions=["Consider asynchronous feedback processing"],
                        related_files=["src/cohezion/compound/feedback_loop.py"],
                    )
                ]
            )
        elif perspective == ReviewPerspective.RELIABILITY:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.RELIABILITY,
                        title="Single point of failure in metrics aggregation",
                        description="Global metrics aggregator could lose data if it fails",
                        severity="medium",
                        confidence=0.8,
                        evidence=["Review of metrics persistence architecture"],
                        suggestions=["Implement redundant metrics storage"],
                        related_files=["src/cohezion/compound/global_metrics_aggregator.py"],
                    )
                ]
            )
        elif perspective == ReviewPerspective.MAINTAINABILITY:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.MAINTAINABILITY,
                        title="Complex skill refinement logic",
                        description="Skill refinement decision tree is becoming complex",
                        severity="medium",
                        confidence=0.7,
                        evidence=["Review of skill refiner implementation"],
                        suggestions=["Consider breaking down into smaller, focused functions"],
                        related_files=["src/cohezion/compound/skill_refiner.py"],
                    )
                ]
            )
        elif perspective == ReviewPerspective.USABILITY:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.USABILITY,
                        title="API documentation could be improved",
                        description="Some compound engineering APIs lack clear examples",
                        severity="low",
                        confidence=0.6,
                        evidence=["Review of public APIs"],
                        suggestions=["Add more usage examples and tutorials"],
                        related_files=["src/cohezion/compound/", "docs/"],
                    )
                ]
            )
        elif perspective == ReviewPerspective.INNOVATION:
            findings.extend(
                [
                    ReviewFinding(
                        perspective=ReviewPerspective.INNOVATION,
                        title="Opportunity for predictive skill refinement",
                        description="Could use historical data to predict which skills need refinement",
                        severity="low",
                        confidence=0.5,
                        evidence=["Analysis of skill refinement patterns"],
                        suggestions=["Implement predictive skill refinement using ML"],
                        related_files=[
                            "src/cohezion/compound/skill_refiner.py",
                            "src/cohezion/compound/exp_persistence/",
                        ],
                    )
                ]
            )

        return findings

    async def run_full_adversarial_review(
        self, session_id: str, perspectives: list[ReviewPerspective] | None = None
    ) -> ReviewSession:
        """
        Run a complete adversarial review session from multiple perspectives.

        Args:
            session_id: The compound engineering session ID
            perspectives: Specific perspectives to consult (None for all)

        Returns:
            A complete review session with findings, conflicts, and insights
        """
        perspectives = perspectives or list(ReviewPerspective)
        focus_areas = []  # Could be determined from session context

        self.logger.info(
            "Starting full adversarial review",
            session_id=session_id,
            perspectives=[p.value for p in perspectives],
        )

        review_session = ReviewSession(session_id=session_id)
        review_session.perspectives_consulted = perspectives.copy()

        # Run each perspective
        all_findings: list[ReviewFinding] = []
        perspective_findings: dict[ReviewPerspective, list[ReviewFinding]] = {}

        for perspective in perspectives:
            findings = await self.run_perspective_review(session_id, perspective, focus_areas)
            all_findings.extend(findings)
            perspective_findings[perspective] = findings

        review_session.findings = all_findings

        # Detect conflicts between perspectives
        conflicts = self._detect_conflicts(perspective_findings)
        review_session.conflicts = conflicts

        # Synthesize insights
        insights = self._synthesize_insights(perspective_findings, conflicts)
        review_session.insights = insights

        # Calculate overall score
        review_session.overall_score = self._calculate_overall_score(all_findings)

        # Store the review session
        self._review_sessions.append(review_session)

        self.logger.info(
            "Adversarial review completed",
            session_id=session_id,
            perspectives_consulted=len(perspectives),
            findings=len(all_findings),
            conflicts=len(conflicts),
            insights=len(insights),
            overall_score=review_session.overall_score,
        )

        return review_session

    def _detect_conflicts(
        self, perspective_findings: dict[ReviewPerspective, list[ReviewFinding]]
    ) -> list[tuple[ReviewFinding, ReviewFinding]]:
        """Detect conflicts between findings from different perspectives."""
        conflicts = []

        # Simplified conflict detection - in practice this would be more sophisticated
        perspectives = list(perspective_findings.keys())

        for i in range(len(perspectives)):
            for j in range(i + 1, len(perspectives)):
                persp1, persp2 = perspectives[i], perspectives[j]
                findings1 = perspective_findings[persp1]
                findings2 = perspective_findings[persp2]

                # Look for opposing suggestions or conflicting severity assessments
                for f1 in findings1:
                    for f2 in findings2:
                        # Simple heuristic: if one suggests adding complexity and another
                        # suggests reducing complexity for similar files
                        if self._is_conflicting(f1, f2):
                            conflicts.append((f1, f2))

        return conflicts

    def _is_conflicting(self, f1: ReviewFinding, f2: ReviewFinding) -> bool:
        """Check if two findings represent conflicting viewpoints."""
        # Simplified conflict detection
        # In practice, this would use NLP to understand the semantic meaning

        # Check if they're about similar files
        common_files = set(f1.related_files) & set(f2.related_files)
        if not common_files:
            return False

        # Check for opposing suggestions
        f1_suggestions_lower = [s.lower() for s in f1.suggestions]
        f2_suggestions_lower = [s.lower() for s in f2.suggestions]

        # Look for opposing concepts
        opposing_pairs = [
            ("add", "remove"),
            ("increase", "decrease"),
            ("complex", "simple"),
            ("strict", "lenient"),
            ("more", "less"),
        ]

        for s1 in f1_suggestions_lower:
            for s2 in f2_suggestions_lower:
                for opp1, opp2 in opposing_pairs:
                    if opp1 in s1 and opp2 in s2:
                        return True
                    if opp2 in s1 and opp1 in s2:
                        return True

        return False

    def _synthesize_insights(
        self,
        perspective_findings: dict[ReviewPerspective, list[ReviewFinding]],
        conflicts: list[tuple[ReviewFinding, ReviewFinding]],
    ) -> list[str]:
        """Synthesize insights from multiple perspectives."""
        insights = []

        # Insight 1: Overall health based on findings
        total_findings = sum(len(findings) for findings in perspective_findings.values())
        critical_findings = sum(
            1
            for findings in perspective_findings.values()
            for f in findings
            if f.severity == "critical"
        )
        high_findings = sum(
            1
            for findings in perspective_findings.values()
            for f in findings
            if f.severity == "high"
        )

        if critical_findings > 0:
            insights.append(
                f"Critical issues found requiring immediate attention ({critical_findings} critical)"
            )
        elif high_findings > 2:
            insights.append(f"Multiple high-severity issues identified ({high_findings} high)")
        elif total_findings < 3:
            insights.append("Relatively clean bill of health from all perspectives")
        else:
            insights.append(f"Moderate number of issues identified ({total_findings} total)")

        # Insight 2: Perspective agreement/disagreement
        if len(conflicts) > len(perspective_findings) * 0.5:
            insights.append(
                "High level of disagreement between perspectives - complex tradeoffs present"
            )
        elif len(conflicts) == 0:
            insights.append("Strong consensus across all perspectives")
        else:
            insights.append(f"Some disagreement between perspectives ({len(conflicts)} conflicts)")

        # Insight 3: Perspective coverage
        active_perspectives = [p for p, findings in perspective_findings.items() if findings]
        if len(active_perspectives) >= len(ReviewPerspective) * 0.75:
            insights.append("Good perspective coverage - multiple viewpoints considered")
        else:
            inactive = [p.value for p in ReviewPerspective if p not in active_perspectives]
            insights.append(f"Limited perspective coverage - missing: {', '.join(inactive)}")

        # Insight 4: Trend analysis (if we have history)
        if len(self._review_sessions) >= 2:
            latest_score = self._review_sessions[-1].overall_score
            previous_score = self._review_sessions[-2].overall_score
            if latest_score > previous_score + 0.1:
                insights.append("Improving trend in overall system quality")
            elif latest_score < previous_score - 0.1:
                insights.append(
                    "Declining trend in overall system quality - investigate recent changes"
                )
            else:
                insights.append("Stable trend in overall system quality")

        return insights

    def _calculate_overall_score(self, findings: list[ReviewFinding]) -> float:
        """Calculate an overall score from review findings."""
        if not findings:
            return 1.0  # Perfect score if no findings

        # Weight findings by severity and confidence
        severity_weights = {"critical": 0.0, "high": 0.3, "medium": 0.7, "low": 0.9}

        total_weight = 0.0
        weighted_score = 0.0

        for finding in findings:
            weight = severity_weights.get(finding.severity, 0.5) * finding.confidence
            weighted_score += weight * (1.0 - (1.0 - severity_weights.get(finding.severity, 0.5)))
            total_weight += weight

        if total_weight == 0:
            return 0.5  # Neutral if we can't calculate

        return weighted_score / total_weight

    def get_adversarial_feedback_for_skill_refinement(
        self, session_id: str
    ) -> list[SkillRefinementInput]:
        """
        Generate skill refinement inputs based on adversarial review results.

        Returns feedback that can be used to improve skills based on review outcomes.
        """
        feedback_list = []

        # Get recent review sessions for this session_id
        recent_sessions = [
            session for session in self._review_sessions if session.session_id == session_id
        ]

        if not recent_sessions:
            return feedback_list

        latest_session = recent_sessions[-1]

        # If we have critical findings, suggest improving relevant skills
        critical_findings = [f for f in latest_session.findings if f.severity == "critical"]
        if critical_findings:
            # Group by perspective to suggest perspective-specific skills
            perspective_counts: dict[ReviewPerspective, int] = {}
            for finding in critical_findings:
                perspective_counts[finding.perspective] = (
                    perspective_counts.get(finding.perspective, 0) + 1
                )

            for perspective, count in perspective_counts.items():
                skill_name = self._perspective_to_skill(perspective)
                if skill_name:
                    feedback_list.append(
                        SkillRefinementInput(
                            skill_name=skill_name,
                            performance_metric=0.0,  # Poor performance due to critical issues
                            feedback=f"Critical {perspective.value} issues detected ({count} critical findings)",
                            context={
                                "critical_findings": [f.title for f in critical_findings],
                                "perspective": perspective.value,
                                "session_id": session_id,
                            },
                        )
                    )

        # If overall score is low, suggest improving general engineering skills
        if latest_session.overall_score < 0.6:  # Below 60%
            feedback_list.append(
                SkillRefinementInput(
                    skill_name="system_architect",
                    performance_metric=latest_session.overall_score,
                    feedback=f"Low overall system score: {latest_session.overall_score:.2f}",
                    context={
                        "overall_score": latest_session.overall_score,
                        "findings_count": len(latest_session.findings),
                        "conflicts_count": len(latest_session.conflicts),
                        "session_id": session_id,
                    },
                )
            )

        # If we have many conflicts, suggest improving systems thinking skills
        if len(latest_session.conflicts) > 3:
            feedback_list.append(
                SkillRefinementInput(
                    skill_name="systems_thinker",
                    performance_metric=max(0.0, 1.0 - len(latest_session.conflicts) * 0.1),
                    feedback=f"High number of perspective conflicts detected ({len(latest_session.conflicts)} conflicts)",
                    context={
                        "conflicts_count": len(latest_session.conflicts),
                        "session_id": session_id,
                    },
                )
            )

        return feedback_list

    def _perspective_to_skill(self, perspective: ReviewPerspective) -> str | None:
        """Map a review perspective to a skill name."""
        mapping = {
            ReviewPerspective.SECURITY: "security_engineer",
            ReviewPerspective.PERFORMANCE: "performance_engineer",
            ReviewPerspective.RELIABILITY: "reliability_engineer",
            ReviewPerspective.USABILITY: "ux_designer",
            ReviewPerspective.MAINTAINABILITY: "refactoring_specialist",
            ReviewPerspective.COMPLIANCE: "compliance_officer",
            ReviewPerspective.INNOVATION: "innovation_strategist",
            ReviewPerspective.ETHICS: "ethics_advisor",
        }
        return mapping.get(perspective)

    def get_adversarial_metrics(self, session_id: str) -> dict[str, Any]:
        """Get adversarial review metrics for a session."""
        # Get perspective states for this session
        session_perspective_states = [
            state
            for (persp, sess_id), state in self._perspective_states.items()
            if sess_id == session_id
        ]

        # Get review sessions for this session
        session_reviews = [
            session for session in self._review_sessions if session.session_id == session_id
        ]

        latest_review = session_reviews[-1] if session_reviews else None

        return {
            "session_id": session_id,
            "perspectives_consulted": [
                {
                    "perspective": state.perspective.value,
                    "findings_count": len(state.findings),
                    "review_count": state.review_count,
                    "avg_findings_per_review": state.avg_findings_per_review,
                    "severity_distribution": dict(state.severity_distribution),
                }
                for state in session_perspective_states
            ],
            "latest_review": {
                "timestamp": latest_review.timestamp.isoformat() if latest_review else None,
                "perspectives_consulted": [p.value for p in latest_review.perspectives_consulted]
                if latest_review
                else [],
                "findings_count": len(latest_review.findings) if latest_review else 0,
                "conflicts_count": len(latest_review.conflicts) if latest_review else 0,
                "insights_count": len(latest_review.insights) if latest_review else 0,
                "overall_score": latest_review.overall_score if latest_review else 0.0,
            }
            if latest_review
            else None,
            "review_history_count": len(session_reviews),
            "total_findings_all_time": sum(len(session.findings) for session in session_reviews),
            "total_conflicts_all_time": sum(len(session.conflicts) for session in session_reviews),
        }


# Global instance for easy access
_adversarial_review_system: AdversarialReviewSystem | None = None


def get_adversarial_review_system(project_root: Path | None = None) -> AdversarialReviewSystem:
    """Get or create the global adversarial review system instance."""
    global _adversarial_review_system
    if _adversarial_review_system is None:
        if project_root is None:
            project_root = Path.cwd()
        _adversarial_review_system = AdversarialReviewSystem(project_root)
    return _adversarial_review_system
