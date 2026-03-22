"""Agent context operations for SurrealDB integration.

Handles tracking agent execution context including sessions, decisions, actions,
outcomes, and lessons extracted during agent work.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx


logger = logging.getLogger(__name__)


class AgentContextOps:
    """Operations for managing agent execution context in SurrealDB."""

    def __init__(
        self,
        surrealdb_url: str = "http://localhost:8000",
        namespace: str = "cohezion",
        database: str = "vault",
        username: str = "root",
        password: str = "root",
    ):
        """Initialize agent context operations.

        Args:
            surrealdb_url: SurrealDB HTTP endpoint
            namespace: SurrealDB namespace
            database: SurrealDB database name
            username: Auth username
            password: Auth password
        """
        self.surrealdb_url = surrealdb_url.rstrip("/")
        self.namespace = namespace
        self.database = database
        self.auth = (username, password)
        self.client = httpx.Client(timeout=30.0)

        logger.info(
            f"Initialized AgentContextOps: {surrealdb_url}/{namespace}/{database}"
        )

    def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute SurrealDB SQL query.

        Args:
            query: SurrealQL query string

        Returns:
            List of result objects from SurrealDB
        """
        headers = {
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "NS": self.namespace,
            "DB": self.database,
        }

        response = self.client.post(
            f"{self.surrealdb_url}/sql",
            headers=headers,
            auth=self.auth,
            content=query,
        )
        response.raise_for_status()
        return response.json()

    def track_session(
        self,
        agent_names: list[str],
        duration_ms: int,
        status: str,
        model_used: str = "haiku",
        total_turns: int = 0,
        total_functions: int = 0,
        error_message: str | None = None,
    ) -> str:
        """Track a new agent execution session.

        Args:
            agent_names: List of agent names participating in session
            duration_ms: Session duration in milliseconds
            status: Session status (running | completed | error)
            model_used: Primary model used (haiku | sonnet | opus)
            total_turns: Total conversation turns
            total_functions: Total function calls
            error_message: Error message if status=error

        Returns:
            Session ID created
        """
        session_id = f"session:{str(uuid4())[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        error_clause = (
            f", error_message = {json.dumps(error_message)}" if error_message else ""
        )

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        CREATE session:{session_id[:10]}... SET
            id = {json.dumps(session_id)},
            timestamp = <datetime> {json.dumps(timestamp)},
            duration_ms = {duration_ms},
            agent_names = {json.dumps(agent_names)},
            status = {json.dumps(status)},
            model_used = {json.dumps(model_used)},
            total_turns = {total_turns},
            total_functions = {total_functions},
            created_at = time::now(),
            updated_at = time::now()
            {error_clause};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Created session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def record_decision(
        self,
        session_id: str,
        title: str,
        context: str,
        reasoning: str,
        alternatives: list[str],
        chosen_path: str,
        confidence: float = 0.8,
        reversible: bool = True,
    ) -> str:
        """Record a critical decision during agent execution.

        Args:
            session_id: Parent session ID
            title: Decision title
            context: Why was this decision needed?
            reasoning: How was decision made?
            alternatives: List of alternative paths considered
            chosen_path: Which path was chosen?
            confidence: Confidence level (0.0 - 1.0)
            reversible: Can this decision be undone?

        Returns:
            Decision ID created
        """
        decision_id = f"decision:{str(uuid4())[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        CREATE {decision_id} SET
            id = {json.dumps(decision_id)},
            session_id = {json.dumps(session_id)},
            timestamp = <datetime> {json.dumps(timestamp)},
            title = {json.dumps(title)},
            context = {json.dumps(context)},
            reasoning = {json.dumps(reasoning)},
            alternatives = {json.dumps(alternatives)},
            chosen_path = {json.dumps(chosen_path)},
            confidence = {confidence},
            reversible = {reversible},
            created_at = time::now();

        -- Link to session
        RELATE {session_id}->has_decisions->{decision_id} SET count = 1;
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Created decision: {decision_id} in session {session_id}")
            return decision_id
        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
            raise

    def record_action(
        self,
        session_id: str,
        tool_name: str,
        input_params: dict,
        output: str,
        duration_ms: int,
        status: str = "success",
        error_details: str | None = None,
    ) -> str:
        """Record a tool action/function call during execution.

        Args:
            session_id: Parent session ID
            tool_name: Name of tool invoked (read, write, bash, etc)
            input_params: Sanitized input parameters
            output: Action output (truncated to ~5000 chars)
            duration_ms: Execution duration
            status: Action status (success | error | timeout)
            error_details: Error details if status=error

        Returns:
            Action ID created
        """
        action_id = f"action:{str(uuid4())[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"
        output_truncated = output[:5000] if output else ""

        error_clause = (
            f", error_details = {json.dumps(error_details)}" if error_details else ""
        )

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        CREATE {action_id} SET
            id = {json.dumps(action_id)},
            session_id = {json.dumps(session_id)},
            timestamp = <datetime> {json.dumps(timestamp)},
            tool_name = {json.dumps(tool_name)},
            input_params = {json.dumps(input_params)},
            output = {json.dumps(output_truncated)},
            duration_ms = {duration_ms},
            status = {json.dumps(status)},
            created_at = time::now()
            {error_clause};

        -- Link to session
        RELATE {session_id}->has_actions->{action_id} SET count = 1;
        """

        try:
            result = self._execute_query(query)
            logger.info(
                f"Created action: {action_id} ({tool_name}) in session {session_id}"
            )
            return action_id
        except Exception as e:
            logger.error(f"Failed to record action: {e}")
            raise

    def record_outcome(
        self,
        session_id: str,
        status: str,
        summary: str,
        metrics: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        vault_notes_created: list[str] | None = None,
    ) -> str:
        """Record final outcome of a session.

        Args:
            session_id: Parent session ID
            status: Outcome status (success | partial | failed)
            summary: Human-readable result summary
            metrics: Execution metrics (turns, functions, errors, etc)
            artifacts: Files/artifacts created
            vault_notes_created: Vault notes created during session

        Returns:
            Outcome ID created
        """
        outcome_id = f"outcome:{str(uuid4())[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"
        metrics = metrics or {}
        artifacts = artifacts or []
        vault_notes_created = vault_notes_created or []

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        CREATE {outcome_id} SET
            id = {json.dumps(outcome_id)},
            session_id = {json.dumps(session_id)},
            timestamp = <datetime> {json.dumps(timestamp)},
            status = {json.dumps(status)},
            summary = {json.dumps(summary)},
            metrics = {json.dumps(metrics)},
            artifacts = {json.dumps(artifacts)},
            vault_notes_created = {json.dumps(vault_notes_created)},
            created_at = time::now();

        -- Link to session
        RELATE {session_id}->has_outcomes->{outcome_id};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Created outcome: {outcome_id} for session {session_id}")
            return outcome_id
        except Exception as e:
            logger.error(f"Failed to record outcome: {e}")
            raise

    def record_lesson(
        self,
        session_id: str,
        title: str,
        severity: str,
        description: str,
        linked_lesson_path: str | None = None,
        auto_extracted: bool = True,
    ) -> str:
        """Record a lesson extracted from session.

        Args:
            session_id: Parent session ID
            title: Lesson title
            severity: Severity level (CRITICAL | HIGH | MEDIUM | LOW)
            description: Lesson description
            linked_lesson_path: Path to vault note (lessons/2026-02-11-*.md)
            auto_extracted: Was this auto-generated or human-curated?

        Returns:
            Lesson ID created
        """
        lesson_id = f"lesson:{str(uuid4())[:8]}"

        linked_clause = (
            f", linked_lesson_path = {json.dumps(linked_lesson_path)}"
            if linked_lesson_path
            else ""
        )

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        CREATE {lesson_id} SET
            id = {json.dumps(lesson_id)},
            session_id = {json.dumps(session_id)},
            title = {json.dumps(title)},
            severity = {json.dumps(severity)},
            description = {json.dumps(description)},
            auto_extracted = {str(auto_extracted).lower()},
            created_at = time::now()
            {linked_clause};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Created lesson: {lesson_id} for session {session_id}")
            return lesson_id
        except Exception as e:
            logger.error(f"Failed to record lesson: {e}")
            raise

    def query_research_lineage(self, session_id: str) -> list[dict[str, Any]]:
        """Query: Find all papers that informed decisions in a session.

        Args:
            session_id: Session to analyze

        Returns:
            List of papers with decision context
        """
        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        -- Get all decisions from session
        LET $decisions = (
            SELECT out FROM has_decisions WHERE in = {json.dumps(session_id)}
        );

        -- Find papers that informed those decisions
        SELECT DISTINCT
            paper,
            decision:title,
            derives_from_research:source_type
        FROM $decisions -> derives_from_research -> paper;
        """

        try:
            result = self._execute_query(query)
            logger.info(
                f"Research lineage query for {session_id}: {len(result)} papers"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to query research lineage: {e}")
            return []

    def query_lesson_validation(self, session_id: str) -> list[dict[str, Any]]:
        """Query: Find lessons validated by session outcomes.

        Args:
            session_id: Session to analyze

        Returns:
            List of lessons with validation context
        """
        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        -- Get outcomes from session
        LET $outcomes = (
            SELECT out FROM has_outcomes WHERE in = {json.dumps(session_id)}
        );

        -- Find lessons validated by those outcomes
        SELECT DISTINCT
            lesson,
            outcome:status,
            lesson:severity,
            lesson:linked_lesson_path
        FROM $outcomes -> validates_lesson -> lesson;
        """

        try:
            result = self._execute_query(query)
            logger.info(
                f"Lesson validation query for {session_id}: {len(result)} lessons"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to query lesson validation: {e}")
            return []

    def query_cascading_impact(self, decision_id: str) -> dict[str, Any]:
        """Query: Trace how a decision impacts actions and outcomes.

        Args:
            decision_id: Decision to trace

        Returns:
            Dictionary with decision, actions, and outcomes
        """
        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        -- Get decision details
        SELECT
            id, title, reasoning, chosen_path,
            (SELECT out FROM informs_actions WHERE in = <thing>{json.dumps(decision_id)}) AS informed_actions
        FROM {json.dumps(decision_id)};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Cascading impact query for {decision_id}")
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"Failed to query cascading impact: {e}")
            return {}

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()
