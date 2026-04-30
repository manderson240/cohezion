"""Request-execution alignment analysis for closed-loop compound engineering.

Analyzes how well task execution aligns with human intent and constraints.
Captures misalignment patterns in vault for experience-guided improvement.

Architecture:
    1. Parse request into structured HumanRequest (intent, constraints, criteria)
    2. Analyze alignment between request and execution result
    3. Score misalignment (composite of intent/constraint/criteria satisfaction)
    4. Log high-misalignment cases to vault as decisions
    5. Query vault for prior alignment patterns to inform future decisions
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from cohezion.compound.models import (
    ConstraintType,
    ConstraintViolation,
    CriterionFailure,
    DriftSignal,
    ExecutionAlignment,
    ExecutionConstraint,
    HumanRequest,
    IntentType,
    SuccessCriterion,
)


if TYPE_CHECKING:
    from cohezion.compound.executor import ExecutionResult
    from cohezion.compound.inflection_detector import AnomalyDetection
    from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


# Intent keywords for fast classification
_INTENT_KEYWORDS = {
    "generate": [
        "generate",
        "create",
        "write",
        "compose",
        "draft",
        "produce",
        "build",
    ],
    "analyze": [
        "analyze",
        "evaluate",
        "assess",
        "examine",
        "review",
        "inspect",
        "verify",
    ],
    "search": [
        "search",
        "find",
        "locate",
        "discover",
        "identify",
        "scan",
        "lookup",
    ],
    "transform": [
        "transform",
        "convert",
        "format",
        "extract",
        "parse",
        "reformat",
    ],
    "persist": [
        "store",
        "save",
        "persist",
        "record",
        "log",
        "archive",
    ],
}

# Pre-compile patterns for constraints
_CONSTRAINT_PATTERNS = {
    ConstraintType.TOKENS: re.compile(
        r"(?:under|within|under|limit.*?to|max|maximum)\s+(\d+)\s*(?:tokens?)?",
        re.IGNORECASE,
    ),
    ConstraintType.LATENCY: re.compile(
        r"(?:under|within|limit.*?to)\s+(\d+)\s*(ms|millisecond|sec|second|min|minute)",
        re.IGNORECASE,
    ),
    ConstraintType.QUALITY: re.compile(r"(high|low|max|min)\s*quality", re.IGNORECASE),
    ConstraintType.SCOPE: re.compile(
        r"(?:only|just|restrict(?:ed)?|limit)\s+to\s+(\w+)", re.IGNORECASE
    ),
}

# Success criterion metric mapping
_CRITERION_METRIC_MAP = {
    "coherent": ("coherence", 0.7),
    "accurate": ("accuracy", 0.8),
    "relevant": ("relevance", 0.7),
    "complete": ("completeness", 0.8),
    "consistent": ("consistency", 0.75),
    "correct": ("correctness", 0.8),
}

# Intent-type success criteria defaults
_INTENT_DEFAULTS = {
    IntentType.GENERATE: [
        SuccessCriterion("Output is coherent", "coherence", 0.7, False),
    ],
    IntentType.ANALYZE: [
        SuccessCriterion("Analysis is correct", "correctness", 0.8, False),
    ],
    IntentType.SEARCH: [
        SuccessCriterion("Results are relevant", "relevance", 0.7, False),
    ],
    IntentType.TRANSFORM: [
        SuccessCriterion("Output format is correct", "format_correctness", 0.8, False),
    ],
}


class RequestAlignmentAnalyzer:
    """Analyze alignment between human requests and task execution.

    Bridges the gap between human intent and compound execution by:
    1. Parsing requests into structured intent/constraints/criteria
    2. Analyzing how well execution matches the request
    3. Scoring misalignment for experience-guided improvement
    4. Persisting alignment patterns to vault
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        intent_confidence_threshold: float = 0.1,
        constraint_tolerance: float = 0.1,
    ):
        """Initialize request alignment analyzer.

        Args:
            mcp_client: Connected MCPClient for vault operations
            intent_confidence_threshold: Minimum confidence for intent classification
            constraint_tolerance: % tolerance for constraint satisfaction
        """
        self.mcp_client = mcp_client
        self.intent_confidence_threshold = intent_confidence_threshold
        self.constraint_tolerance = constraint_tolerance

        # Lazy-loaded semantic encoder
        self._text_encoder = None

    @property
    def text_encoder(self) -> Any | None:
        """Lazy-load text encoder for semantic intent classification.

        Returns:
            SemanticTextEncoder or None if unavailable
        """
        if self._text_encoder is None:
            try:
                from cohezion.cache.text_encoder import get_text_encoder

                self._text_encoder = get_text_encoder()
                logger.debug("Initialized semantic text encoder")
            except Exception as e:
                logger.debug("Failed to load semantic encoder (using keyword fallback): %s", e)
                self._text_encoder = False  # Flag: tried and failed
        return self._text_encoder if self._text_encoder else None

    def parse_request(self, request_text: str) -> HumanRequest:
        """Parse human request into structured HumanRequest.

        Args:
            request_text: Raw human request text

        Returns:
            HumanRequest with parsed intent, constraints, criteria
        """
        request = HumanRequest(raw_text=request_text)

        # Step 1: Classify intent (keywords first, then semantic)
        intent_type, intent_confidence = self._classify_intent(request_text)
        request.intent = intent_type
        request.intent_confidence = intent_confidence
        logger.debug(
            "Classified intent: %s (confidence=%.2f)",
            intent_type.value,
            intent_confidence,
        )

        # Step 2: Extract constraints
        request.constraints = self._extract_constraints(request_text)
        logger.debug("Extracted %d constraints", len(request.constraints))

        # Step 3: Extract success criteria
        request.criteria = self._extract_criteria(request_text, intent_type)
        logger.debug("Extracted %d success criteria", len(request.criteria))

        # Step 4: Extract scope
        request.scope_includes, request.scope_excludes = self._extract_scope(request_text)

        return request

    def analyze_alignment(
        self,
        request: HumanRequest,
        execution_result: ExecutionResult,
        operation_type: str,
        anomaly_analysis: AnomalyDetection | None = None,
    ) -> ExecutionAlignment:
        """Analyze alignment between request and execution result.

        Args:
            request: Parsed HumanRequest
            execution_result: ExecutionResult from compound execution
            operation_type: Type of operation that was executed
            anomaly_analysis: Optional AnomalyDetection from InflectionDetector

        Returns:
            ExecutionAlignment with scores, violations, failures, recommendations
        """
        # Compute intent match score
        intent_match_score = self._compute_intent_match(
            request.intent, operation_type, execution_result
        )

        # Check constraint satisfaction
        violations = self._check_constraints(request.constraints or [], execution_result.metrics)
        constraint_satisfaction = max(0.0, 1.0 - (len(violations) * 0.3))  # Penalty per violation

        # Check success criteria
        failures = self._check_criteria(request.criteria or [], execution_result.metrics)
        criteria_satisfaction = max(0.0, 1.0 - (len(failures) * 0.2))  # Penalty per failure

        # Detect drift signals
        drift_signals = self._detect_drift_signals(execution_result, anomaly_analysis)
        drift_penalty = (
            sum(s.severity for s in drift_signals) / len(drift_signals) if drift_signals else 0.0
        )

        # Compute composite misalignment score
        alignment_score = (
            0.4 * intent_match_score + 0.3 * constraint_satisfaction + 0.3 * criteria_satisfaction
        )
        misalignment_score = (1.0 - alignment_score) + (drift_penalty * 0.2)
        misalignment_score = min(1.0, max(0.0, misalignment_score))

        # Generate issues and recommendations
        issues = self._generate_issues(violations, failures, drift_signals, intent_match_score)
        recommendations = self._generate_recommendations(
            violations, failures, drift_signals, request.intent
        )

        return ExecutionAlignment(
            intent_match_score=intent_match_score,
            constraint_satisfaction=constraint_satisfaction,
            criteria_satisfaction=criteria_satisfaction,
            misalignment_score=misalignment_score,
            violations=violations,
            failures=failures,
            drift_signals=drift_signals,
            issues=issues,
            recommendations=recommendations,
            should_retry=misalignment_score > 0.5,
        )

    def log_alignment_to_vault(
        self, request: HumanRequest, alignment: ExecutionAlignment, project: str
    ) -> str:
        """Log alignment analysis to vault for experience guidance.

        Args:
            request: Original HumanRequest
            alignment: ExecutionAlignment analysis result
            project: Project name for vault scoping

        Returns:
            Vault path where alignment was logged, or empty string on failure
        """
        if alignment.misalignment_score > 0.5:
            # High misalignment: log as decision (ADR)
            return self._log_as_decision(request, alignment, project)
        else:
            # Normal alignment: log as experiment
            return self._log_as_experiment(request, alignment, project)

    def query_alignment_patterns(
        self, task_description: str, project: str = "cohezion"
    ) -> dict[str, Any]:
        """Query vault for prior alignment patterns on similar tasks.

        Args:
            task_description: Description of the task
            project: Project name for scoped search

        Returns:
            Dict with relevant alignment patterns (non-blocking on failure)
        """
        try:
            context = self.mcp_client.vault_find_relevant_context(
                query=f"alignment misalignment {task_description}", project=project
            )
            logger.debug(
                "Found %d alignment patterns for task",
                len(context) if context else 0,
            )
            return {"alignment_patterns": context if context else []}
        except Exception as e:
            logger.warning("Failed to query alignment patterns (non-blocking): %s", e)
            return {"alignment_patterns": [], "error": str(e)}

    # ========================================================================
    # Private methods
    # ========================================================================

    def _classify_intent(self, request_text: str) -> tuple[IntentType, float]:
        """Classify request intent using keywords then semantic fallback.

        Args:
            request_text: Request text to classify

        Returns:
            Tuple of (IntentType, confidence_score)
        """
        # Phase 1: Keyword matching (fast)
        # Score by: matches / total keywords for that intent (normalized)
        scores: dict[str, float] = {}
        lower_text = request_text.lower()

        for intent_str, keywords in _INTENT_KEYWORDS.items():
            matches = 0
            for keyword in keywords:
                if re.search(rf"\b{keyword}\b", lower_text):
                    matches += 1
            # Normalize by number of keywords in this category
            scores[intent_str] = matches / len(keywords) if keywords else 0.0

        # Find best intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        # If we have any match, use it (confidence = normalized score, min 0.5 for any match)
        if best_score > 0:
            confidence = max(best_score, 0.5)
            if confidence >= self.intent_confidence_threshold:
                return (
                    IntentType[best_intent.upper()],
                    confidence,
                )

        # Phase 2: Semantic fallback (if encoder available)
        if self.text_encoder:
            return self._classify_intent_semantic(request_text)

        # Phase 3: Default to UNKNOWN
        logger.debug("Could not classify intent, defaulting to UNKNOWN")
        return IntentType.UNKNOWN, 0.0

    def _classify_intent_semantic(self, request_text: str) -> tuple[IntentType, float]:
        """Semantic intent classification (fallback).

        Args:
            request_text: Request text to classify

        Returns:
            Tuple of (IntentType, confidence_score)
        """
        try:
            import numpy as np

            encoder = self.text_encoder
            if not encoder:
                return IntentType.UNKNOWN, 0.0

            # Encode request
            request_embedding = encoder.encode(request_text)

            # Compute intent prototypes (lazy)
            intent_prototypes = {
                "generate": encoder.encode(
                    "Create, write, compose, draft, and produce new content"
                ),
                "analyze": encoder.encode("Evaluate, assess, review, and analyze existing content"),
                "search": encoder.encode("Find, locate, discover, and search for items"),
                "transform": encoder.encode("Convert, reformat, extract, and transform data"),
                "persist": encoder.encode("Store, save, record, and persist information"),
            }

            # Compute similarities
            best_intent = None
            best_similarity = 0.0

            for intent_str, prototype in intent_prototypes.items():
                similarity = float(
                    np.dot(request_embedding, prototype)
                    / (np.linalg.norm(request_embedding) * np.linalg.norm(prototype))
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_intent = intent_str

            if best_similarity >= 0.3:  # Semantic threshold
                return IntentType[best_intent.upper()], best_similarity

            return IntentType.UNKNOWN, 0.0
        except Exception as e:
            logger.debug("Semantic intent classification failed: %s", e)
            return IntentType.UNKNOWN, 0.0

    def _extract_constraints(self, request_text: str) -> list[ExecutionConstraint]:
        """Extract constraints from request text using regex patterns.

        Args:
            request_text: Request text to extract from

        Returns:
            List of ExecutionConstraints
        """
        constraints = []

        # Check TOKENS constraint
        match = _CONSTRAINT_PATTERNS[ConstraintType.TOKENS].search(request_text)
        if match:
            value = float(match.group(1))
            constraints.append(
                ExecutionConstraint(
                    type=ConstraintType.TOKENS, value=value, unit="tokens", is_hard=True
                )
            )

        # Check LATENCY constraint
        match = _CONSTRAINT_PATTERNS[ConstraintType.LATENCY].search(request_text)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            # Normalize to milliseconds
            multipliers = {
                "ms": 1,
                "millisecond": 1,
                "sec": 1000,
                "second": 1000,
                "min": 60000,
                "minute": 60000,
            }
            value_ms = value * multipliers.get(unit, 1)
            constraints.append(
                ExecutionConstraint(
                    type=ConstraintType.LATENCY, value=value_ms, unit="ms", is_hard=True
                )
            )

        # Check QUALITY constraint
        match = _CONSTRAINT_PATTERNS[ConstraintType.QUALITY].search(request_text)
        if match:
            quality_level = match.group(1).lower()
            quality_map = {"high": 0.7, "max": 0.9, "low": 0.3, "min": 0.1}
            value = quality_map.get(quality_level, 0.5)
            constraints.append(
                ExecutionConstraint(
                    type=ConstraintType.QUALITY,
                    value=value,
                    unit="score",
                    is_hard=False,  # Soft preference
                )
            )

        # Check SCOPE constraint
        match = _CONSTRAINT_PATTERNS[ConstraintType.SCOPE].search(request_text)
        if match:
            scope = match.group(1)
            constraints.append(
                ExecutionConstraint(type=ConstraintType.SCOPE, value=1.0, unit=scope, is_hard=True)
            )

        return constraints

    def _extract_criteria(
        self, request_text: str, intent_type: IntentType
    ) -> list[SuccessCriterion]:
        """Extract success criteria from request text.

        Args:
            request_text: Request text to extract from
            intent_type: Inferred intent type for default criteria

        Returns:
            List of SuccessCriteria
        """
        criteria = []

        # Look for explicit criteria ("must be...", "should be...")
        explicit_pattern = re.compile(r"(?:must|should|needs?)\s+(?:be\s+)?(\w+)", re.IGNORECASE)
        for match in explicit_pattern.finditer(request_text):
            criterion_word = match.group(1).lower()
            if criterion_word in _CRITERION_METRIC_MAP:
                metric_name, threshold = _CRITERION_METRIC_MAP[criterion_word]
                criteria.append(
                    SuccessCriterion(
                        description=f"Output must be {criterion_word}",
                        metric_name=metric_name,
                        threshold=threshold,
                        is_explicit=True,
                    )
                )

        # Add intent-specific default criteria if none extracted
        if not criteria and intent_type in _INTENT_DEFAULTS:
            criteria = _INTENT_DEFAULTS[intent_type].copy()

        return criteria

    def _extract_scope(self, request_text: str) -> tuple[list[str], list[str]]:
        """Extract scope inclusions/exclusions from request.

        Args:
            request_text: Request text to extract from

        Returns:
            Tuple of (scope_includes, scope_excludes)
        """
        includes = []
        excludes = []

        # Look for "only", "just" (inclusions)
        only_pattern = re.compile(r"(?:only|just)\s+(\w+)", re.IGNORECASE)
        for match in only_pattern.finditer(request_text):
            includes.append(match.group(1))

        # Look for "except", "excluding", "not", "without" (exclusions)
        except_pattern = re.compile(r"(?:except|excluding|not|without)\s+(\w+)", re.IGNORECASE)
        for match in except_pattern.finditer(request_text):
            excludes.append(match.group(1))

        return includes, excludes

    def _compute_intent_match(
        self, request_intent: IntentType, operation_type: str, result: ExecutionResult
    ) -> float:
        """Compute how well executed operation matched request intent.

        Args:
            request_intent: Intended operation type
            operation_type: Actual operation type executed
            result: ExecutionResult to analyze

        Returns:
            0.0-1.0 intent match score
        """
        # Direct intent match (compare lowercase name to operation_type string)
        if request_intent.name.lower() == operation_type.lower():
            return 1.0

        # Semantic similarity (if encoder available)
        if self.text_encoder and result.output:
            try:
                import numpy as np

                encoder = self.text_encoder
                intent_prototype = encoder.encode(f"This is a {request_intent.name.lower()} task")
                output_embedding = encoder.encode(result.output[:500])  # First 500 chars

                similarity = float(
                    np.dot(intent_prototype, output_embedding)
                    / (np.linalg.norm(intent_prototype) * np.linalg.norm(output_embedding))
                )
                return max(0.0, min(1.0, similarity))
            except Exception as e:
                logger.debug("Intent alignment computation failed: %s", e)

        # Multi-step request handling
        if request_intent == IntentType.MULTI_STEP:
            return 0.7  # Partial credit

        # Mismatch
        return 0.0

    def _check_constraints(
        self, constraints: list[ExecutionConstraint], metrics: dict[str, Any]
    ) -> list[ConstraintViolation]:
        """Check which constraints were violated.

        Args:
            constraints: Constraints to check
            metrics: Execution metrics dict

        Returns:
            List of ConstraintViolations
        """
        violations = []

        for constraint in constraints:
            if constraint.type == ConstraintType.TOKENS:
                actual = metrics.get("tokens_used", 0)
                allowed = constraint.value * (1 + self.constraint_tolerance)
                if actual > allowed:
                    severity = min(1.0, (actual - allowed) / allowed)
                    violations.append(
                        ConstraintViolation(
                            constraint=constraint,
                            requested_value=constraint.value,
                            actual_value=actual,
                            severity=severity,
                        )
                    )

            elif constraint.type == ConstraintType.LATENCY:
                actual_ms = metrics.get("duration_seconds", 0) * 1000
                allowed_ms = constraint.value * (1 + self.constraint_tolerance)
                if actual_ms > allowed_ms:
                    severity = min(1.0, (actual_ms - allowed_ms) / allowed_ms)
                    violations.append(
                        ConstraintViolation(
                            constraint=constraint,
                            requested_value=constraint.value,
                            actual_value=actual_ms,
                            severity=severity,
                        )
                    )

            elif constraint.type == ConstraintType.QUALITY:
                # Check quality metrics (coherence, accuracy, etc.)
                quality_metrics = ["coherence", "accuracy", "correctness"]
                actual_quality = max((metrics.get(m, 0) for m in quality_metrics), default=0.0)
                if actual_quality < constraint.value:
                    severity = min(1.0, (constraint.value - actual_quality) / constraint.value)
                    violations.append(
                        ConstraintViolation(
                            constraint=constraint,
                            requested_value=constraint.value,
                            actual_value=actual_quality,
                            severity=severity,
                        )
                    )

        return violations

    def _check_criteria(
        self, criteria: list[SuccessCriterion], metrics: dict[str, Any]
    ) -> list[CriterionFailure]:
        """Check which success criteria were not met.

        Args:
            criteria: Success criteria to check
            metrics: Execution metrics dict

        Returns:
            List of CriterionFailures
        """
        failures = []

        for criterion in criteria:
            actual = metrics.get(criterion.metric_name, 0.0)
            if actual < criterion.threshold:
                gap = criterion.threshold - actual
                failures.append(
                    CriterionFailure(
                        criterion=criterion,
                        expected_value=criterion.threshold,
                        actual_value=actual,
                        gap=gap,
                    )
                )

        return failures

    def _detect_drift_signals(
        self, result: ExecutionResult, anomaly: AnomalyDetection | None
    ) -> list[DriftSignal]:
        """Detect signals indicating execution divergence.

        Args:
            result: ExecutionResult to analyze
            anomaly: Optional AnomalyDetection from InflectionDetector

        Returns:
            List of DriftSignals
        """
        signals = []

        # Execution failure
        if not result.success:
            signals.append(
                DriftSignal(
                    signal_type="execution_failed",
                    severity=1.0,
                    description="Task execution failed",
                    metadata={"error": result.metrics.get("error", "unknown")},
                )
            )

        # Anomaly detection signals
        if anomaly:
            if anomaly.severity.value == "critical":
                signals.append(
                    DriftSignal(
                        signal_type="anomaly_critical",
                        severity=0.9,
                        description=f"Critical anomaly detected: {anomaly.issues}",
                        metadata={"anomaly_score": anomaly.score},
                    )
                )
            elif anomaly.severity.value == "warning":
                signals.append(
                    DriftSignal(
                        signal_type="anomaly_warning",
                        severity=0.5,
                        description=f"Anomaly warning: {anomaly.issues}",
                        metadata={"anomaly_score": anomaly.score},
                    )
                )

        # Coherence drop
        if result.metrics.get("coherence", 1.0) < 0.3:
            signals.append(
                DriftSignal(
                    signal_type="coherence_drop",
                    severity=0.7,
                    description="Output coherence below threshold",
                    metadata={"coherence": result.metrics.get("coherence")},
                )
            )

        # Retry signals
        retry_count = result.metrics.get("retry_count", 0)
        if retry_count > 0:
            severity = min(1.0, retry_count * 0.3)
            signals.append(
                DriftSignal(
                    signal_type="retry_required",
                    severity=severity,
                    description=f"Required {retry_count} retries",
                    metadata={"retry_count": retry_count},
                )
            )

        # Cache miss storm
        if result.metrics.get("cache_hit_rate", 1.0) < 0.1:
            signals.append(
                DriftSignal(
                    signal_type="cache_miss_storm",
                    severity=0.5,
                    description="Low cache hit rate",
                    metadata={"cache_hit_rate": result.metrics.get("cache_hit_rate")},
                )
            )

        return signals

    def _generate_issues(
        self,
        violations: list[ConstraintViolation],
        failures: list[CriterionFailure],
        drift_signals: list[DriftSignal],
        intent_match: float,
    ) -> list[str]:
        """Generate human-readable issue descriptions.

        Args:
            violations: List of constraint violations
            failures: List of criterion failures
            drift_signals: List of drift signals
            intent_match: Intent match score

        Returns:
            List of issue descriptions
        """
        issues = []

        if intent_match < 0.5:
            issues.append(f"Execution may not match request intent (match={intent_match:.2f})")

        for violation in violations:
            issues.append(
                f"{violation.constraint.type.name.capitalize()} constraint violated: "
                f"requested {violation.requested_value}, got {violation.actual_value}"
            )

        for failure in failures:
            issues.append(
                f"{failure.criterion.metric_name} criterion not met: "
                f"required {failure.expected_value}, got {failure.actual_value}"
            )

        for signal in drift_signals:
            if signal.severity > 0.5:
                issues.append(signal.description)

        return issues

    def _generate_recommendations(
        self,
        violations: list[ConstraintViolation],
        failures: list[CriterionFailure],
        drift_signals: list[DriftSignal],
        intent_type: IntentType,
    ) -> list[str]:
        """Generate recommended actions based on analysis.

        Args:
            violations: List of constraint violations
            failures: List of criterion failures
            drift_signals: List of drift signals
            intent_type: Type of request

        Returns:
            List of recommendations
        """
        recommendations = []

        for violation in violations:
            if violation.constraint.type == ConstraintType.TOKENS:
                recommendations.append("Reduce token requirements or optimize prompt/execution")
            elif violation.constraint.type == ConstraintType.LATENCY:
                recommendations.append("Optimize execution speed or increase time budget")
            elif violation.constraint.type == ConstraintType.QUALITY:
                recommendations.append("Use higher-quality model or improve prompt")

        for failure in failures:
            recommendations.append(f"Improve {failure.criterion.metric_name} to meet requirements")

        for signal in drift_signals:
            if signal.signal_type == "coherence_drop":
                recommendations.append("Improve prompt clarity or use higher-capability model")
            elif signal.signal_type == "retry_required":
                recommendations.append("Investigate root cause of retries")
            elif signal.signal_type == "cache_miss_storm":
                recommendations.append("Optimize cache or improve input deduplication")

        if not recommendations:
            recommendations.append("Execution aligned with request")

        return recommendations

    def _log_as_decision(
        self, request: HumanRequest, alignment: ExecutionAlignment, project: str
    ) -> str:
        """Log high-misalignment as decision (ADR).

        Args:
            request: Original request
            alignment: Alignment analysis
            project: Project name

        Returns:
            Vault path or empty string on failure
        """
        try:
            title = f"High misalignment in {request.intent.name} task: {request.raw_text[:50]}"
            context = (
                f"Request: {request.raw_text}\n\n"
                f"Intent: {request.intent.name} (confidence={request.intent_confidence:.2f})\n\n"
                f"Constraints: {len(request.constraints or [])}\n"
                f"Criteria: {len(request.criteria or [])}"
            )
            decision = (
                f"Misalignment score: {alignment.misalignment_score:.2f}\n"
                f"Intent match: {alignment.intent_match_score:.2f}\n"
                f"Constraint satisfaction: {alignment.constraint_satisfaction:.2f}\n"
                f"Criteria satisfaction: {alignment.criteria_satisfaction:.2f}\n\n"
                f"Issues: {json.dumps(alignment.issues, indent=2)}"
            )
            rationale = (
                f"High misalignment indicates execution diverged from request. "
                f"Recommendations: {json.dumps(alignment.recommendations, indent=2)}"
            )

            path = self.mcp_client.vault_log_decision(
                project=project,
                title=title,
                context=context,
                decision=decision,
                rationale=rationale,
            )
            logger.info("Logged high-misalignment decision: %s", path)
            return path
        except Exception as e:
            logger.warning("Failed to log misalignment decision (non-blocking): %s", e)
            return ""

    def _log_as_experiment(
        self, request: HumanRequest, alignment: ExecutionAlignment, project: str
    ) -> str:
        """Log normal alignment as experiment.

        Args:
            request: Original request
            alignment: Alignment analysis
            project: Project name

        Returns:
            Vault path or empty string on failure
        """
        try:
            issues = alignment.issues or []
            recommendations = alignment.recommendations or []
            hypothesis = (
                f"Request alignment for {request.intent.name} task: {request.raw_text[:100]}"
            )
            method = f"Analyzed request with intent={request.intent.name}, "(
                f"{len(request.constraints or [])} constraints, {len(request.criteria or [])} "
                f"criteria"
            )
            result = (
                f"Misalignment score: {alignment.misalignment_score:.2f} ({len(issues)} issues)"
            )
            learnings = (
                f"Execution aligned well with request. "
                f"Recommendations: {', '.join(recommendations)}"
                if alignment.misalignment_score <= 0.3
                else f"Moderate misalignment detected. {len(issues)} issues, retry recommended."
            )

            path = self.mcp_client.vault_log_experiment(
                project=project,
                hypothesis=hypothesis,
                method=method,
                result=result,
                learnings=learnings,
            )
            logger.debug("Logged alignment experiment: %s", path)
            return path
        except Exception as e:
            logger.warning("Failed to log alignment experiment (non-blocking): %s", e)
            return ""


# Factory for creating analyzer instances
class RequestAlignmentAnalyzerFactory:
    """Factory for creating RequestAlignmentAnalyzer instances."""

    @staticmethod
    def create(
        mcp_client: MCPClient,
        intent_confidence_threshold: float = 0.5,
        constraint_tolerance: float = 0.1,
    ) -> RequestAlignmentAnalyzer:
        """Create a RequestAlignmentAnalyzer instance.

        Args:
            mcp_client: Connected MCPClient
            intent_confidence_threshold: Minimum confidence for intent classification
            constraint_tolerance: % tolerance for constraint satisfaction

        Returns:
            RequestAlignmentAnalyzer instance
        """
        return RequestAlignmentAnalyzer(
            mcp_client=mcp_client,
            intent_confidence_threshold=intent_confidence_threshold,
            constraint_tolerance=constraint_tolerance,
        )
