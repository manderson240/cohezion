"""Strategic queries for agent context schema.

Implements 3 key queries:
1. Research Lineage: Papers → Decisions → Lessons
2. Lesson Validation: Outcomes generating lessons
3. Cascade Detection: Lessons preventing future errors
"""

import json
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class AgentContextQueries:
    """Execute strategic queries on agent context schema."""

    def __init__(
        self,
        surrealdb_url: str = "http://localhost:8001",
        namespace: str = "cohezion",
        database: str = "vault",
        username: str = "root",
        password: str = "root",
    ):
        """Initialize query executor.

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

    def query_research_lineage(
        self, limit: int = 10, paper_path_filter: str = "%papers%"
    ) -> list[dict[str, Any]]:
        """Query 1: Research Lineage (Papers → Decisions → Lessons).

        Traces how research (papers) influences architectural decisions,
        which then generate operational lessons.

        Args:
            limit: Max results to return
            paper_path_filter: Filter papers by path (SQL LIKE pattern)

        Returns:
            List of lineage records with paper → decision → lesson chains
        """
        logger.info("Executing research lineage query...")

        # Simplified query for testing (papers may not be linked to decisions yet)
        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          decision.id,
          decision.title,
          decision.chosen_option
        FROM agent_decision as decision
        LIMIT {limit};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Research lineage query returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Research lineage query failed: {e}")
            return []

    def query_lesson_validation(
        self, min_confidence: float = 0.5, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Query 2: Lesson Validation (Outcomes that generated lessons).

        Shows which outcomes produced lessons and at what confidence level.
        Helps identify high-value outcomes (outcomes that teach the most).

        Args:
            min_confidence: Minimum confidence score to include
            limit: Max results to return

        Returns:
            List of outcome records with lesson generation stats
        """
        logger.info("Executing lesson validation query...")

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          outcome.id,
          outcome.outcome_status,
          outcome.actual_cost
        FROM agent_outcome as outcome
        LIMIT {limit};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Lesson validation query returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Lesson validation query failed: {e}")
            return []

    def query_cascade_detection(self, limit: int = 10) -> list[dict[str, Any]]:
        """Query 3: Cascade Detection (Lessons preventing future errors).

        Shows if lessons learned from one outcome prevented errors in
        subsequent decisions. Measures lesson impact on future decision quality.

        Args:
            limit: Max results to return

        Returns:
            List of lesson impact records
        """
        logger.info("Executing cascade detection query...")

        # Simplified query for testing
        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          lesson.id,
          lesson.lesson_title,
          lesson.confidence_score
        FROM lesson_validation as lesson
        LIMIT {limit};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Cascade detection query returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Cascade detection query failed: {e}")
            return []

    def query_decision_cost_analysis(self, limit: int = 10) -> list[dict[str, Any]]:
        """Supplementary Query: Decision Cost Analysis.

        Analyzes cost efficiency of decisions (estimated vs actual).
        Helps identify decisions that were significantly more/less expensive than planned.

        Args:
            limit: Max results to return

        Returns:
            List of cost analysis records
        """
        logger.info("Executing decision cost analysis query...")

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          decision.id,
          decision.title,
          decision.estimated_cost
        FROM agent_decision as decision
        LIMIT {limit};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Decision cost analysis query returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Decision cost analysis query failed: {e}")
            return []

    def query_execution_performance(self, limit: int = 10) -> list[dict[str, Any]]:
        """Supplementary Query: Execution Performance Analysis.

        Analyzes tool execution patterns (which tools take longest, which fail most).
        Helps optimize decision execution chains.

        Args:
            limit: Max results to return

        Returns:
            List of tool performance records
        """
        logger.info("Executing execution performance query...")

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          tool_name,
          execution_time_ms,
          status
        FROM agent_action
        LIMIT {limit};
        """

        try:
            result = self._execute_query(query)
            logger.info(f"Execution performance query returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Execution performance query failed: {e}")
            return []

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get comprehensive summary of a single session.

        Args:
            session_id: Session ID to summarize

        Returns:
            Dictionary with session summary
        """
        logger.info(f"Fetching session summary: {session_id}")

        query = f"""
        USE NS {self.namespace};
        USE DB {self.database};

        SELECT
          id,
          agent_name,
          started_at,
          ended_at,
          status,
          decision_id,
          context
        FROM agent_session WHERE id = `{session_id}` LIMIT 1;
        """

        try:
            result = self._execute_query(query)
            if result and len(result) > 0:
                return result[0]
            else:
                logger.warning(f"Session not found: {session_id}")
                return {}
        except Exception as e:
            logger.error(f"Session summary query failed: {e}")
            return {}


if __name__ == "__main__":
    # Test queries
    q = AgentContextQueries()

    print("\n=== RESEARCH LINEAGE ===")
    lineage = q.query_research_lineage(limit=5)
    print(json.dumps(lineage, indent=2, default=str))

    print("\n=== LESSON VALIDATION ===")
    lessons = q.query_lesson_validation(limit=5)
    print(json.dumps(lessons, indent=2, default=str))

    print("\n=== CASCADE DETECTION ===")
    cascade = q.query_cascade_detection(limit=5)
    print(json.dumps(cascade, indent=2, default=str))

    print("\n=== DECISION COST ANALYSIS ===")
    costs = q.query_decision_cost_analysis(limit=5)
    print(json.dumps(costs, indent=2, default=str))

    print("\n=== EXECUTION PERFORMANCE ===")
    perf = q.query_execution_performance(limit=5)
    print(json.dumps(perf, indent=2, default=str))
