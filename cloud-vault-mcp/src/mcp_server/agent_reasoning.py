"""Agent reasoning operations for Phase 2 SurrealDB integration.

Tracks agent reasoning chains, decision challenges, and decision cascades
to enable root cause analysis, contradiction detection, and impact propagation.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger(__name__)


class AgentReasoningOps:
    """Operations for tracking reasoning chains, challenges, and cascades in SurrealDB."""

    def __init__(self, surrealdb_sync):
        """Initialize with SurrealDBSync instance.

        Args:
            surrealdb_sync: SurrealDBSync instance for database operations
        """
        self.db = surrealdb_sync

    def record_reasoning(
        self,
        decision_id: str,
        reasoning_type: str,
        reasoning_chain: list[str],
        confidence_score: float = 0.7,
        assumptions: list[str] | None = None,
        alternatives_rejected: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Create a reasoning node that explains WHY a decision was made.

        Args:
            decision_id: ID of the decision being reasoned about
            reasoning_type: Type of reasoning (research|pattern|intuition|convention|hybrid)
            reasoning_chain: Step-by-step chain of thought (list of reasoning steps)
            confidence_score: Confidence level (0.0-1.0)
            assumptions: List of assumptions made (default: empty)
            alternatives_rejected: List of dicts with rejected options and reasons

        Returns:
            Dict with reasoning_id, decision_id, confidence_score, status
        """
        try:
            reasoning_id = f"agent_reasoning:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()
            assumptions = assumptions or []
            alternatives_rejected = alternatives_rejected or []

            # Validate decision exists
            decision_check = self.db._execute_query(
                f"SELECT id FROM {decision_id} LIMIT 1"
            )
            if not decision_check or len(decision_check) == 0:
                return {
                    "success": False,
                    "error": f"Decision not found: {decision_id}",
                }

            # Validate reasoning_type
            valid_types = ["research", "pattern", "intuition", "convention", "hybrid"]
            if reasoning_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Invalid reasoning_type: {reasoning_type}. Must be one of {valid_types}",
                }

            # Validate confidence_score
            if not (0.0 <= confidence_score <= 1.0):
                return {
                    "success": False,
                    "error": f"confidence_score must be between 0.0 and 1.0, got {confidence_score}",
                }

            # Create reasoning node
            query = f"""
                CREATE agent_reasoning SET
                    reasoning_id = '{reasoning_id}',
                    decision_id = '{decision_id}',
                    reasoning_type = '{reasoning_type}',
                    reasoning_chain = {json.dumps(reasoning_chain)},
                    confidence_score = {confidence_score},
                    assumptions = {json.dumps(assumptions)},
                    alternatives_rejected = {json.dumps(alternatives_rejected)},
                    created_at = '{now}',
                    updated_at = '{now}'
                RETURN id, reasoning_id, decision_id, reasoning_type, confidence_score
            """

            result = self.db._execute_query(query)
            if not result or len(result) == 0:
                return {
                    "success": False,
                    "error": "Failed to create reasoning node",
                }

            # Create informs_reasoning edge
            try:
                edge_query = f"""
                    RELATE {decision_id} -> informs_reasoning -> {reasoning_id} SET
                        created_at = '{now}'
                    RETURN id
                """
                edge_result = self.db._execute_query(edge_query)
                if not edge_result or len(edge_result) == 0:
                    logger.warning(
                        f"Failed to create informs_reasoning edge for {reasoning_id}"
                    )

            except Exception as e:
                logger.warning(f"Error creating informs_reasoning edge: {e}")

            logger.info(
                f"Created reasoning node: {reasoning_id} for decision {decision_id}"
            )

            return {
                "success": True,
                "reasoning_id": reasoning_id,
                "decision_id": decision_id,
                "reasoning_type": reasoning_type,
                "confidence_score": confidence_score,
                "chain_length": len(reasoning_chain),
                "timestamp": now,
            }

        except Exception as e:
            logger.error(f"Error recording reasoning: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def record_challenge(
        self,
        decision_id: str,
        lesson_id: str,
        challenge_type: str,
        severity: str = "minor",
        notes: str = "",
    ) -> dict[str, Any]:
        """Record when a decision challenges or refines an existing lesson.

        Args:
            decision_id: ID of the decision challenging the lesson
            lesson_id: ID of the lesson being challenged
            challenge_type: Type of challenge (contradicts|limits|refines|extends)
            severity: Severity level (major|minor|clarification, default: minor)
            notes: Human-readable explanation of the challenge

        Returns:
            Dict with edge_id, decision_id, lesson_id, challenge_type, severity
        """
        try:
            edge_id = f"challenges_lesson:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()

            # Validate decision exists
            decision_check = self.db._execute_query(
                f"SELECT id FROM {decision_id} LIMIT 1"
            )
            if not decision_check or len(decision_check) == 0:
                return {
                    "success": False,
                    "error": f"Decision not found: {decision_id}",
                }

            # Validate lesson exists
            lesson_check = self.db._execute_query(
                f"SELECT id FROM lesson:{lesson_id} LIMIT 1"
            )
            if not lesson_check or len(lesson_check) == 0:
                return {
                    "success": False,
                    "error": f"Lesson not found: {lesson_id}",
                }

            # Validate challenge_type
            valid_types = ["contradicts", "limits", "refines", "extends"]
            if challenge_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Invalid challenge_type: {challenge_type}. Must be one of {valid_types}",
                }

            # Validate severity
            valid_severities = ["major", "minor", "clarification"]
            if severity not in valid_severities:
                return {
                    "success": False,
                    "error": f"Invalid severity: {severity}. Must be one of {valid_severities}",
                }

            # Create challenges_lesson edge
            edge_query = f"""
                RELATE {decision_id} -> challenges_lesson -> lesson:{lesson_id} SET
                    challenge_type = '{challenge_type}',
                    severity = '{severity}',
                    notes = {json.dumps(notes)},
                    created_at = '{now}'
                RETURN id
            """

            edge_result = self.db._execute_query(edge_query)
            if not edge_result or len(edge_result) == 0:
                return {
                    "success": False,
                    "error": "Failed to create challenges_lesson edge",
                }

            logger.info(
                f"Created challenge edge: {decision_id} -{challenge_type}-> lesson:{lesson_id} (severity: {severity})"
            )

            return {
                "success": True,
                "edge_id": edge_id,
                "decision_id": decision_id,
                "lesson_id": lesson_id,
                "challenge_type": challenge_type,
                "severity": severity,
                "timestamp": now,
            }

        except Exception as e:
            logger.error(f"Error recording challenge: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def record_cascade(
        self,
        source_decision_id: str,
        dependent_decision_id: str,
        dependency_type: str,
        impact_level: str = "minor",
        notes: str = "",
    ) -> dict[str, Any]:
        """Record how one decision impacts downstream decisions (cascade tracking).

        Args:
            source_decision_id: ID of the source decision
            dependent_decision_id: ID of the dependent decision
            dependency_type: Type of dependency (blocks|enables|refines|contradicts)
            impact_level: Impact severity (critical|significant|minor, default: minor)
            notes: Explanation of the dependency

        Returns:
            Dict with edge_id, source_decision_id, dependent_decision_id, dependency_type, impact_level
        """
        try:
            edge_id = f"relates_to_decision:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()

            # Validate source decision exists
            source_check = self.db._execute_query(
                f"SELECT id FROM {source_decision_id} LIMIT 1"
            )
            if not source_check or len(source_check) == 0:
                return {
                    "success": False,
                    "error": f"Source decision not found: {source_decision_id}",
                }

            # Validate dependent decision exists
            dependent_check = self.db._execute_query(
                f"SELECT id FROM {dependent_decision_id} LIMIT 1"
            )
            if not dependent_check or len(dependent_check) == 0:
                return {
                    "success": False,
                    "error": f"Dependent decision not found: {dependent_decision_id}",
                }

            # Validate dependency_type
            valid_types = ["blocks", "enables", "refines", "contradicts"]
            if dependency_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Invalid dependency_type: {dependency_type}. Must be one of {valid_types}",
                }

            # Validate impact_level
            valid_impacts = ["critical", "significant", "minor"]
            if impact_level not in valid_impacts:
                return {
                    "success": False,
                    "error": f"Invalid impact_level: {impact_level}. Must be one of {valid_impacts}",
                }

            # Create relates_to_decision edge
            edge_query = f"""
                RELATE {source_decision_id} -> relates_to_decision -> {dependent_decision_id} SET
                    dependency_type = '{dependency_type}',
                    impact_level = '{impact_level}',
                    notes = {json.dumps(notes)},
                    created_at = '{now}'
                RETURN id
            """

            edge_result = self.db._execute_query(edge_query)
            if not edge_result or len(edge_result) == 0:
                return {
                    "success": False,
                    "error": "Failed to create relates_to_decision edge",
                }

            logger.info(
                f"Created cascade edge: {source_decision_id} -{dependency_type}-> "
                f"{dependent_decision_id} (impact: {impact_level})"
            )

            return {
                "success": True,
                "edge_id": edge_id,
                "source_decision_id": source_decision_id,
                "dependent_decision_id": dependent_decision_id,
                "dependency_type": dependency_type,
                "impact_level": impact_level,
                "timestamp": now,
            }

        except Exception as e:
            logger.error(f"Error recording cascade: {e}")
            return {
                "success": False,
                "error": str(e),
            }
