"""Agent context operations for Phase 1 SurrealDB integration.

Tracks agent sessions, decisions, and outcomes to enable research lineage queries.
"""

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger(__name__)

_SURREAL_ID_RE = re.compile(r"^[a-zA-Z_][\w]*:[a-zA-Z0-9_\-]+$")


def _validate_record_id(rid: str) -> str:
    """Validate a SurrealDB record ID to prevent query injection."""
    if not _SURREAL_ID_RE.match(rid):
        raise ValueError(f"Invalid SurrealDB record ID: {rid!r}")
    return rid


class AgentContextOps:
    """Operations for tracking agent sessions, decisions, and outcomes in SurrealDB."""

    def __init__(self, surrealdb_sync):
        """Initialize with SurrealDBSync instance.

        Args:
            surrealdb_sync: SurrealDBSync instance for database operations
        """
        self.db = surrealdb_sync

    def track_session(
        self,
        agent_id: str,
        goals: list[str],
        model_used: str = "claude-haiku-4-5",
        phase: str = "research",
    ) -> dict[str, Any]:
        """Create a new agent session node.

        Args:
            agent_id: Unique agent identifier (e.g., 'integration-engineer')
            goals: List of goals for the session
            model_used: Model name (default: claude-haiku-4-5)
            phase: Session phase (research, decision, implementation, validation)

        Returns:
            Dict with session_id, status, timestamp
        """
        try:
            session_id = f"agent_session:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()

            query = f"""
                CREATE agent_session SET
                    agent_id = '{agent_id}',
                    session_id = '{session_id}',
                    start_time = '{now}',
                    end_time = null,
                    model_used = '{model_used}',
                    total_tokens = 0,
                    cost_usd = 0.0,
                    phase = '{phase}',
                    status = 'in_progress',
                    goals = {json.dumps(goals)},
                    outcome_summary = null
                RETURN id, agent_id, session_id, start_time, status
            """

            result = self.db._execute_query(query)
            if result and len(result) > 0:
                record = result[0]
                logger.info(f"Created agent session: {session_id}")
                return {
                    "success": True,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "status": "in_progress",
                    "timestamp": now,
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create session in SurrealDB",
                }

        except Exception as e:
            logger.error(f"Error creating agent session: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def record_decision(
        self,
        session_id: str,
        decision_type: str,
        reasoning: str,
        papers_applied: list[str],
        confidence_score: float = 0.7,
    ) -> dict[str, Any]:
        """Record a decision and link it to research papers.

        Args:
            session_id: Session ID from track_session
            decision_type: Type of decision (architecture, feature, refactor, bugfix, data)
            reasoning: Explanation of the decision
            papers_applied: List of paper IDs that informed the decision
            confidence_score: Confidence level (0-1)

        Returns:
            Dict with decision_id, links_created, validation warnings
        """
        try:
            decision_id = f"agent_decision:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()

            # Validate session exists
            _validate_record_id(session_id)
            session_check = self.db._execute_query(
                f"SELECT id FROM {session_id} LIMIT 1"
            )
            if not session_check or len(session_check) == 0:
                return {
                    "success": False,
                    "error": f"Session not found: {session_id}",
                }

            # Create decision node
            query = f"""
                CREATE agent_decision SET
                    decision_id = '{decision_id}',
                    session_id = '{session_id}',
                    decision_type = '{decision_type}',
                    timestamp = '{now}',
                    reasoning = {json.dumps(reasoning)},
                    confidence_score = {confidence_score},
                    validation_status = 'pending',
                    implementation_status = 'proposed',
                    metadata = null
                RETURN id, decision_id, session_id, decision_type, confidence_score
            """

            result = self.db._execute_query(query)
            if not result or len(result) == 0:
                return {
                    "success": False,
                    "error": "Failed to create decision node",
                }

            # Link to papers
            links_created = 0
            paper_errors = []

            for paper_id in papers_applied:
                try:
                    # Normalize paper ID if needed
                    if not paper_id.startswith("paper:"):
                        paper_id = f"paper:{paper_id}"

                    # Check if paper exists
                    _validate_record_id(paper_id)
                    paper_check = self.db._execute_query(
                        f"SELECT id FROM {paper_id} LIMIT 1"
                    )
                    if not paper_check or len(paper_check) == 0:
                        paper_errors.append(f"Paper not found: {paper_id}")
                        continue

                    # Create APPLIED_RESEARCH edge
                    edge_query = f"""
                        RELATE {decision_id} -> applied_research -> {paper_id} SET
                            relevance_score = 0.8,
                            applied_at = '{now}'
                        RETURN id
                    """

                    edge_result = self.db._execute_query(edge_query)
                    if edge_result and len(edge_result) > 0:
                        links_created += 1
                    else:
                        paper_errors.append(f"Failed to link paper: {paper_id}")

                except Exception as e:
                    paper_errors.append(f"Error linking {paper_id}: {e!s}")

            # Update session token count
            try:
                self.db._execute_query(f"UPDATE {session_id} SET total_tokens += 500")
            except Exception as e:
                logger.warning(f"Failed to update session tokens: {e}")

            logger.info(
                f"Created decision {decision_id} with {links_created} paper links"
            )

            result_dict = {
                "success": True,
                "decision_id": decision_id,
                "session_id": session_id,
                "decision_type": decision_type,
                "confidence_score": confidence_score,
                "links_created": links_created,
                "total_papers": len(papers_applied),
                "timestamp": now,
            }

            if paper_errors:
                result_dict["validation_warnings"] = paper_errors

            return result_dict

        except Exception as e:
            logger.error(f"Error recording decision: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def record_outcome(
        self,
        session_id: str,
        outcome_type: str,
        lessons_learned: list[str],
        metrics: dict = None,
    ) -> dict[str, Any]:
        """Record session outcome and link to lessons.

        Args:
            session_id: Session ID from track_session
            outcome_type: Type of outcome (success, partial, failed)
            lessons_learned: List of lesson note IDs from vault
            metrics: Dict of outcome metrics (session_duration_min, token_efficiency_ratio, etc)

        Returns:
            Dict with outcome_id, validated_lessons, validation errors
        """
        try:
            outcome_id = f"agent_outcome:{uuid.uuid4()!s}"
            now = datetime.now(UTC).isoformat()
            metrics = metrics or {}

            # Validate session exists
            _validate_record_id(session_id)
            session_check = self.db._execute_query(
                f"SELECT id FROM {session_id} LIMIT 1"
            )
            if not session_check or len(session_check) == 0:
                return {
                    "success": False,
                    "error": f"Session not found: {session_id}",
                }

            # Create outcome node
            query = f"""
                CREATE agent_outcome SET
                    outcome_id = '{outcome_id}',
                    session_id = '{session_id}',
                    outcome_type = '{outcome_type}',
                    timestamp = '{now}',
                    lessons_learned = {json.dumps(lessons_learned)},
                    metrics = {json.dumps(metrics)},
                    validated_by = null
                RETURN id, outcome_id, session_id, outcome_type
            """

            result = self.db._execute_query(query)
            if not result or len(result) == 0:
                return {
                    "success": False,
                    "error": "Failed to create outcome node",
                }

            # Link to lessons
            validated_lessons = 0
            validation_errors = []

            for lesson_id in lessons_learned:
                try:
                    # Check if lesson exists
                    _validate_record_id(f"lesson:{lesson_id}")
                    lesson_check = self.db._execute_query(
                        f"SELECT id FROM lesson:{lesson_id} LIMIT 1"
                    )
                    if not lesson_check or len(lesson_check) == 0:
                        validation_errors.append(f"Lesson not found: {lesson_id}")
                        continue

                    # Create VALIDATES_LESSON edge
                    edge_query = f"""
                        RELATE {outcome_id} -> validates_lesson -> lesson:{lesson_id} SET
                            alignment_score = 0.85,
                            validation_type = 'confirms'
                        RETURN id
                    """

                    edge_result = self.db._execute_query(edge_query)
                    if edge_result and len(edge_result) > 0:
                        validated_lessons += 1
                    else:
                        validation_errors.append(
                            f"Failed to validate lesson: {lesson_id}"
                        )

                except Exception as e:
                    validation_errors.append(f"Error validating {lesson_id}: {e!s}")

            # Update session to mark completion
            try:
                now_str = datetime.now(UTC).isoformat()
                self.db._execute_query(
                    f"""UPDATE {session_id} SET
                        status = 'completed',
                        end_time = '{now_str}',
                        outcome_summary = '{outcome_type}'
                    """
                )
            except Exception as e:
                logger.warning(f"Failed to update session completion: {e}")

            logger.info(
                f"Created outcome {outcome_id} with {validated_lessons} lesson validations"
            )

            result_dict = {
                "success": True,
                "outcome_id": outcome_id,
                "session_id": session_id,
                "outcome_type": outcome_type,
                "validated_lessons": validated_lessons,
                "total_lessons": len(lessons_learned),
                "timestamp": now,
            }

            if validation_errors:
                result_dict["validation_errors"] = validation_errors

            return result_dict

        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
            return {
                "success": False,
                "error": str(e),
            }
