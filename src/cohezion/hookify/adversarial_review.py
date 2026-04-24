# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
Adversarial Review Harness with Multi-Perspective Analysis
Graph-aware review system with adversarial test generation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pathlib import Path

    from cohezion.hookify.validator import Rule


logger = logging.getLogger(__name__)


@dataclass
class ReviewPerspective:
    """Single perspective review result"""

    name: str  # "architect", "engineer", "tester", "security"
    passed: bool
    score: float  # 0.0-1.0
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class AdversarialReviewResult:
    """Complete multi-perspective review"""

    rule_id: str
    overall_score: float
    consensus_reached: bool
    perspectives: list[ReviewPerspective]
    adversarial_tests: list[str]
    graph_insights: dict[str, Any]


class AdversarialReviewHarness:
    """
    Multi-perspective adversarial review for Hookify rules

    Reviews from four perspectives:
    - Architect: Design alignment and system integrity
    - Engineer: Implementation robustness and edge cases
    - Tester: Test coverage and adversarial scenarios
    - Security: Safety and injection prevention

    Leverages vault graph for:
    - Historical violation patterns
    - Cross-rule dependencies
    - Learning from past failures
    """

    def __init__(self, vault_path: Path, surrealdb_client: Any | None = None):
        self.vault_path = vault_path
        self.db = surrealdb_client

    async def review_rule(self, rule: Rule) -> AdversarialReviewResult:
        """
        Perform multi-perspective adversarial review

        Returns complete review with consensus assessment
        """
        # Collect perspectives
        perspectives = []

        architect = await self._review_as_architect(rule)
        perspectives.append(architect)

        engineer = await self._review_as_engineer(rule)
        perspectives.append(engineer)

        tester = await self._review_as_tester(rule)
        perspectives.append(tester)

        security = await self._review_as_security(rule)
        perspectives.append(security)

        # Calculate consensus
        scores = [p.score for p in perspectives]
        overall_score = sum(scores) / len(scores)
        consensus_reached = all(p.passed for p in perspectives)

        # Generate adversarial tests
        adversarial_tests = await self._generate_adversarial_tests(rule, perspectives)

        # Query graph for insights
        graph_insights = await self._query_graph_insights(rule)

        return AdversarialReviewResult(
            rule_id=rule.id,
            overall_score=overall_score,
            consensus_reached=consensus_reached,
            perspectives=perspectives,
            adversarial_tests=adversarial_tests,
            graph_insights=graph_insights,
        )

    async def _review_as_architect(self, rule: Rule) -> ReviewPerspective:
        """
        Architect perspective: Design alignment

        Checks:
        - Rule follows HIHO principles
        - Consistent with compound engineering
        - Proper integration with session lifecycle
        - No architectural conflicts
        """
        findings = []
        score = 1.0

        # Check HIHO compliance
        if "coherence" not in rule.condition.lower():
            findings.append(
                {
                    "severity": "warning",
                    "message": "Rule doesn't reference coherence - may bypass HIHO gate",
                    "recommendation": "Consider adding coherence threshold condition",
                }
            )
            score -= 0.1

        # Check action appropriateness
        valid_actions = [
            "block_if_coherence_below_threshold",
            "ralph_loop.orchestrate",
            "auto_commit_and_push",
            "allow",
            "log_violation",
        ]

        if rule.action not in valid_actions:
            findings.append(
                {
                    "severity": "error",
                    "message": f"Unknown action: {rule.action}",
                    "recommendation": f"Use one of: {', '.join(valid_actions)}",
                }
            )
            score -= 0.3

        # Check lever design
        if len(rule.levers) == 0:
            findings.append(
                {
                    "severity": "info",
                    "message": "No configurable levers - reduces flexibility",
                    "recommendation": "Consider adding threshold or boolean levers",
                }
            )
            score -= 0.05

        return ReviewPerspective(
            name="architect",
            passed=score >= 0.7,
            score=max(0.0, score),
            findings=findings,
            recommendations=[f["recommendation"] for f in findings],
        )

    async def _review_as_engineer(self, rule: Rule) -> ReviewPerspective:
        """
        Engineer perspective: Implementation robustness

        Checks:
        - Condition expression safety
        - Lever value validation
        - Error handling
        - Edge case coverage
        """
        findings = []
        score = 1.0

        # Parse and validate condition
        try:
            condition_safe = self._validate_condition_safety(rule.condition)
            if not condition_safe:
                findings.append(
                    {
                        "severity": "critical",
                        "message": "Condition contains potentially dangerous patterns",
                        "recommendation": "Sanitize condition expression",
                    }
                )
                score -= 0.5
        except Exception as e:
            findings.append(
                {
                    "severity": "error",
                    "message": f"Condition parsing failed: {e}",
                    "recommendation": "Review condition syntax",
                }
            )
            score -= 0.3

        # Check lever types
        for lever_name, lever_value in rule.levers.items():
            if not self._is_valid_lever_value(lever_value):
                findings.append(
                    {
                        "severity": "warning",
                        "message": f"Lever '{lever_name}' has unusual value: {lever_value}",
                        "recommendation": "Validate lever type",
                    }
                )
                score -= 0.1

        # Check coherence thresholds are reasonable
        if "threshold" in rule.levers:
            threshold = rule.levers["threshold"]
            if isinstance(threshold, (int, float)):
                if threshold < 0 or threshold > 1:
                    findings.append(
                        {
                            "severity": "error",
                            "message": f"Coherence threshold {threshold} out of range [0, 1]",
                            "recommendation": "Set threshold between 0.0 and 1.0",
                        }
                    )
                    score -= 0.2
                elif threshold != 0.5:
                    findings.append(
                        {
                            "severity": "info",
                            "message": f"Threshold {threshold} deviates from HIHO (0.5)",
                            "recommendation": "Consider if non-0.5 threshold is intentional",
                        }
                    )
                    score -= 0.05

        return ReviewPerspective(
            name="engineer",
            passed=score >= 0.7,
            score=max(0.0, score),
            findings=findings,
            recommendations=[f["recommendation"] for f in findings],
        )

    async def _review_as_tester(self, rule: Rule) -> ReviewPerspective:
        """
        Tester perspective: Test coverage

        Checks:
        - Adversarial tests defined
        - Edge cases covered
        - Integration test paths
        """
        findings = []
        score = 1.0

        # Check adversarial tests exist
        if len(rule.adversarial_tests) == 0:
            findings.append(
                {
                    "severity": "error",
                    "message": "No adversarial tests defined",
                    "recommendation": "Add tests for boundary conditions, edge cases, failure modes",
                }
            )
            score -= 0.3
        elif len(rule.adversarial_tests) < 2:
            findings.append(
                {
                    "severity": "warning",
                    "message": "Only one adversarial test defined",
                    "recommendation": "Add more comprehensive test coverage",
                }
            )
            score -= 0.1

        # Check test naming convention
        for test in rule.adversarial_tests:
            if not test.startswith("test_"):
                findings.append(
                    {
                        "severity": "warning",
                        "message": f"Test '{test}' doesn't follow pytest naming",
                        "recommendation": "Rename to 'test_{description}'",
                    }
                )
                score -= 0.05

        # Check condition complexity
        condition_complexity = self._assess_condition_complexity(rule.condition)
        if condition_complexity > 3:
            findings.append(
                {
                    "severity": "warning",
                    "message": f"Condition complexity {condition_complexity} - may be hard to test",
                    "recommendation": "Simplify condition or add more test cases",
                }
            )
            score -= 0.1

        return ReviewPerspective(
            name="tester",
            passed=score >= 0.7,
            score=max(0.0, score),
            findings=findings,
            recommendations=[f["recommendation"] for f in findings],
        )

    async def _review_as_security(self, rule: Rule) -> ReviewPerspective:
        """
        Security perspective: Safety

        Checks:
        - No injection vulnerabilities
        - No data leakage risks
        - Safe file paths
        """
        findings = []
        score = 1.0

        # Check condition for injection
        dangerous_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"os\.system",
            r"subprocess",
            r"__import__",
            r"__globals__",
            r"__class__",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, rule.condition, re.IGNORECASE):
                findings.append(
                    {
                        "severity": "critical",
                        "message": f"Condition contains dangerous pattern: {pattern}",
                        "recommendation": "Remove dangerous function calls",
                    }
                )
                score -= 0.5

        # Check for path traversal in witness_plate
        if "witness_plate" in rule.levers:
            path = str(rule.levers["witness_plate"])
            if ".." in path or path.startswith("/"):
                findings.append(
                    {
                        "severity": "error",
                        "message": "Witness plate path may be unsafe",
                        "recommendation": "Use vault-relative paths only",
                    }
                )
                score -= 0.3

        # Check for SQL injection in conditions (if querying DB)
        if "SELECT" in rule.condition.upper() or "INSERT" in rule.condition.upper():
            findings.append(
                {
                    "severity": "error",
                    "message": "Condition contains SQL-like syntax",
                    "recommendation": "Conditions should not contain SQL",
                }
            )
            score -= 0.3

        return ReviewPerspective(
            name="security",
            passed=score >= 0.7,
            score=max(0.0, score),
            findings=findings,
            recommendations=[f["recommendation"] for f in findings],
        )

    async def _generate_adversarial_tests(
        self, rule: Rule, perspectives: list[ReviewPerspective]
    ) -> list[str]:
        """Generate additional adversarial tests based on review findings"""
        tests = list(rule.adversarial_tests)

        # Add tests based on findings
        for perspective in perspectives:
            for finding in perspective.findings:
                if finding["severity"] in ["error", "critical"]:
                    test_name = f"test_{rule.id}_{perspective.name}_{finding['severity']}"
                    if test_name not in tests:
                        tests.append(test_name)

        # Add HIHO-specific tests for coherence-related rules
        if "coherence" in rule.condition.lower():
            hiho_tests = [
                f"test_{rule.id}_hiho_boundary_0_49",
                f"test_{rule.id}_hiho_boundary_0_50",
                f"test_{rule.id}_hiho_boundary_0_51",
                f"test_{rule.id}_hiho_convergence_stability",
                f"test_{rule.id}_hiho_divergence_handling",
            ]
            for test in hiho_tests:
                if test not in tests:
                    tests.append(test)

        # Add lever boundary tests
        for lever_name, lever_value in rule.levers.items():
            if isinstance(lever_value, (int, float)):
                test_name = f"test_{rule.id}_lever_{lever_name}_boundary_min"
                if test_name not in tests:
                    tests.append(test_name)
                test_name = f"test_{rule.id}_lever_{lever_name}_boundary_max"
                if test_name not in tests:
                    tests.append(test_name)

        return tests

    async def _query_graph_insights(self, rule: Rule) -> dict[str, Any]:
        """
        Query SurrealDB graph for insights about this rule

        Returns:
            Historical violations, cross-rule connections, learning patterns
        """
        if not self.db:
            return {"error": "SurrealDB not available"}

        try:
            rule_neuron = f"neuron:prefrontal_{rule.id}"

            # Query violations (latent synapses pointing to this rule)
            violation_sql = f"""
                SELECT count() as violation_count
                FROM synapse
                WHERE out = {rule_neuron} AND link_type = 'latent';
            """
            violation_result = self.db.query(violation_sql)
            violation_count = (
                violation_result[0].get("result", [{}])[0].get("violation_count", 0)
                if violation_result
                else 0
            )

            # Query cross-rule connections (dream synapses)
            dream_sql = f"""
                SELECT in, out, resonance
                FROM synapse
                WHERE (in = {rule_neuron} OR out = {rule_neuron}) AND link_type = 'dream';
            """
            dream_result = self.db.query(dream_sql)
            dream_synapses = dream_result[0].get("result", []) if dream_result else []

            # Query affinity patterns
            affinity_sql = f"""
                SELECT dim_agent_affinity
                FROM {rule_neuron};
            """
            affinity_result = self.db.query(affinity_sql)
            affinity = (
                affinity_result[0].get("result", [{}])[0].get("dim_agent_affinity")
                if affinity_result
                else None
            )

            return {
                "violation_count": violation_count,
                "violation_trend": "increasing" if violation_count > 10 else "stable",
                "cross_rule_connections": len(dream_synapses),
                "dream_synapses": [
                    {
                        "rule": s.get("in" if s.get("out") == rule_neuron else "out", ""),
                        "resonance": s.get("resonance", ""),
                    }
                    for s in dream_synapses
                ],
                "affinity_vector": affinity,
                "confidence": "high" if affinity else "low",
            }

        except Exception as e:
            return {"error": str(e)}

    def _validate_condition_safety(self, condition: str) -> bool:
        """Validate condition doesn't contain dangerous patterns"""
        dangerous = ["eval(", "exec(", "os.system", "subprocess", "__import__", "__globals__"]
        return not any(pattern in condition.lower() for pattern in dangerous)

    def _is_valid_lever_value(self, value: Any) -> bool:
        """Check if lever value is valid type"""
        return isinstance(value, (int, float, bool, str))

    def _assess_condition_complexity(self, condition: str) -> int:
        """Assess condition complexity (higher = more complex)"""
        complexity = 0

        # Count logical operators
        complexity += condition.count("AND")
        complexity += condition.count("OR")

        # Count function calls
        complexity += condition.count("(")

        # Count comparison operators
        complexity += len(re.findall(r"[<>=!]+", condition))

        return complexity


class ConsensusVoter:
    """
    Vote on rule changes based on adversarial review

    Requires consensus across all four perspectives for major changes
    """

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def vote_on_change(
        self, rule: Rule, review: AdversarialReviewResult, change_type: str
    ) -> tuple[bool, str]:
        """
        Vote on whether to accept a rule change

        Returns:
            (approved, reason)
        """
        # Critical changes need consensus
        if change_type in ["delete", "action_change", "condition_change"]:
            if not review.consensus_reached:
                return False, "Critical change requires consensus across all perspectives"

        # All changes need minimum score
        if review.overall_score < self.threshold:
            return False, f"Score {review.overall_score:.2f} below threshold {self.threshold}"

        # Security must pass
        security = next((p for p in review.perspectives if p.name == "security"), None)
        if security and not security.passed:
            return False, "Security review failed"

        return True, "Change approved by consensus"
