"""SurrealDB Proactive Repository - Track suggestion acceptances and feedback.

Implements Phase 5 Learning System:
- Track suggestion acceptance rates
- Store user feedback
- Enable confidence adjustment
- Pattern effectiveness reports
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from cohezion.core.persistence.repositories.base import BaseRepository, RepositoryMetrics
from cohezion.core.persistence.surreal_client import SurrealClient


logger = structlog.get_logger(__name__)


@dataclass
class SuggestionAcceptance:
    """Record of a suggestion being accepted or rejected."""

    suggestion_id: str
    pattern_id: str
    accepted: bool
    timestamp: str = field(default_factory=lambda: "")
    execution_time_ms: float | None = None
    feedback: str | None = None
    user_id: str = "default"
    project_root: str = ""
    confidence_at_decision: float = 0.0

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PatternEffectiveness:
    """Effectiveness metrics for a detection pattern."""

    pattern_id: str
    pattern_name: str
    total_suggestions: int = 0
    accepted: int = 0
    rejected: int = 0
    avg_confidence: float = 0.0
    avg_execution_time_ms: float | None = None
    last_updated: str = field(default_factory=lambda: "")

    @property
    def acceptance_rate(self) -> float:
        """Calculate acceptance rate as percentage."""
        if self.total_suggestions == 0:
            return 0.0
        return self.accepted / self.total_suggestions

    @property
    def effectiveness_score(self) -> float:
        """Calculate effectiveness score (0.0-1.0)."""
        # Weighted combination of acceptance rate and confidence
        acceptance_weight = 0.7
        confidence_weight = 0.3
        return (self.acceptance_rate * acceptance_weight) + (self.avg_confidence * confidence_weight)


class SurrealProactiveRepository(BaseRepository[SuggestionAcceptance, dict[str, Any]]):
    """Repository for proactive suggestion tracking and learning."""

    TABLE_NAME = "proactive_suggestion_acceptances"

    def __init__(self, client: SurrealClient) -> None:
        """Initialize the proactive repository.

        Args:
            client: SurrealDB client instance
        """
        BaseRepository.__init__(self, table_name=self.TABLE_NAME)
        self._client = client
        self._table = self.TABLE_NAME
        self._metrics: list[RepositoryMetrics] = []

    async def _ensure_table(self) -> None:
        """Ensure the table exists in SurrealDB."""
        try:
            query = f"""
            DEFINE TABLE IF NOT EXISTS {self._table} SCHEMAFULL;
            DEFINE FIELD suggestion_id ON {self._table} TYPE string;
            DEFINE FIELD pattern_id ON {self._table} TYPE string;
            DEFINE FIELD accepted ON {self._table} TYPE bool;
            DEFINE FIELD timestamp ON {self._table} TYPE datetime;
            DEFINE FIELD execution_time_ms ON {self._table} TYPE option<float>;
            DEFINE FIELD feedback ON {self._table} TYPE option<string>;
            DEFINE FIELD user_id ON {self._table} TYPE string DEFAULT 'default';
            DEFINE FIELD project_root ON {self._table} TYPE string;
            DEFINE FIELD confidence_at_decision ON {self._table} TYPE float;
            """
            await self._client.query(query)
            logger.debug("proactive_table_ensured")
        except Exception as e:
            logger.error("proactive_table_creation_failed", error=str(e))
            raise

    async def record_acceptance(self, acceptance: SuggestionAcceptance) -> SuggestionAcceptance:
        """Record a suggestion acceptance or rejection.

        Args:
            acceptance: The acceptance record to store

        Returns:
            The stored acceptance record with ID
        """
        start_time = datetime.now()
        try:
            await self._ensure_table()

            query = f"""
            CREATE {self.TABLE_NAME} CONTENT {{
                suggestion_id: $suggestion_id,
                pattern_id: $pattern_id,
                accepted: $accepted,
                timestamp: $timestamp,
                execution_time_ms: $execution_time_ms,
                feedback: $feedback,
                user_id: $user_id,
                project_root: $project_root,
                confidence_at_decision: $confidence_at_decision
            }}
            """

            result = await self._client.query(
                query,
                {
                    "suggestion_id": acceptance.suggestion_id,
                    "pattern_id": acceptance.pattern_id,
                    "accepted": acceptance.accepted,
                    "timestamp": acceptance.timestamp,
                    "execution_time_ms": acceptance.execution_time_ms,
                    "feedback": acceptance.feedback,
                    "user_id": acceptance.user_id,
                    "project_root": acceptance.project_root,
                    "confidence_at_decision": acceptance.confidence_at_decision,
                },
            )

            if result and len(result) > 0:
                stored = result[0]
                logger.info(
                    "acceptance_recorded",
                    suggestion_id=acceptance.suggestion_id,
                    accepted=acceptance.accepted,
                )
                return acceptance

            raise ValueError("Failed to store acceptance - no result returned")

        except Exception as e:
            logger.error("acceptance_recording_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="record_acceptance",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise

    async def get_pattern_effectiveness(self, pattern_id: str) -> PatternEffectiveness:
        """Get effectiveness metrics for a pattern.

        Args:
            pattern_id: The pattern ID to analyze

        Returns:
            PatternEffectiveness with aggregated metrics
        """
        start_time = datetime.now()
        try:
            query = f"""
            SELECT
                pattern_id,
                COUNT() as total_suggestions,
                COUNTIF(accepted == true) as accepted,
                COUNTIF(accepted == false) as rejected,
                math::mean(confidence_at_decision) as avg_confidence,
                math::mean(execution_time_ms) as avg_execution_time_ms
            FROM {self.TABLE_NAME}
            WHERE pattern_id = $pattern_id
            GROUP ALL
            """

            result = await self._client.query(query, {"pattern_id": pattern_id})

            if result and len(result) > 0:
                row = result[0]
                effectiveness = PatternEffectiveness(
                    pattern_id=pattern_id,
                    pattern_name=pattern_id,  # Could be enhanced with pattern registry
                    total_suggestions=row.get("total_suggestions", 0),
                    accepted=row.get("accepted", 0),
                    rejected=row.get("rejected", 0),
                    avg_confidence=row.get("avg_confidence", 0.0) or 0.0,
                    avg_execution_time_ms=row.get("avg_execution_time_ms"),
                    last_updated=datetime.now().isoformat(),
                )
                logger.debug(
                    "pattern_effectiveness_calculated",
                    pattern_id=pattern_id,
                    acceptance_rate=effectiveness.acceptance_rate,
                )
                return effectiveness

            # No data yet - return empty metrics
            return PatternEffectiveness(
                pattern_id=pattern_id,
                pattern_name=pattern_id,
                last_updated=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error("pattern_effectiveness_calculation_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="get_pattern_effectiveness",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise

    async def get_all_pattern_effectiveness(self) -> list[PatternEffectiveness]:
        """Get effectiveness metrics for all patterns.

        Returns:
            List of PatternEffectiveness for all patterns
        """
        start_time = datetime.now()
        try:
            query = f"""
            SELECT
                pattern_id,
                COUNT() as total_suggestions,
                COUNTIF(accepted == true) as accepted,
                COUNTIF(accepted == false) as rejected,
                math::mean(confidence_at_decision) as avg_confidence,
                math::mean(execution_time_ms) as avg_execution_time_ms
            FROM {self.TABLE_NAME}
            GROUP BY pattern_id
            """

            result = await self._client.query(query)

            effectiveness_list = []
            if result:
                for row in result:
                    effectiveness = PatternEffectiveness(
                        pattern_id=row.get("pattern_id", "unknown"),
                        pattern_name=row.get("pattern_id", "unknown"),
                        total_suggestions=row.get("total_suggestions", 0),
                        accepted=row.get("accepted", 0),
                        rejected=row.get("rejected", 0),
                        avg_confidence=row.get("avg_confidence", 0.0) or 0.0,
                        avg_execution_time_ms=row.get("avg_execution_time_ms"),
                        last_updated=datetime.now().isoformat(),
                    )
                    effectiveness_list.append(effectiveness)

            logger.debug(
                "all_pattern_effectiveness_calculated",
                patterns_count=len(effectiveness_list),
            )
            return effectiveness_list

        except Exception as e:
            logger.error("all_pattern_effectiveness_calculation_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="get_all_pattern_effectiveness",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise

    async def get_suggestion_history(self, suggestion_id: str, limit: int = 100) -> list[SuggestionAcceptance]:
        """Get acceptance history for a specific suggestion.

        Args:
            suggestion_id: The suggestion ID
            limit: Maximum number of records to return

        Returns:
            List of SuggestionAcceptance records
        """
        start_time = datetime.now()
        try:
            query = f"""
            SELECT * FROM {self.TABLE_NAME}
            WHERE suggestion_id = $suggestion_id
            ORDER BY timestamp DESC
            LIMIT $limit
            """

            result = await self._client.query(query, {"suggestion_id": suggestion_id, "limit": limit})

            history = []
            if result:
                for row in result:
                    acceptance = SuggestionAcceptance(
                        suggestion_id=row.get("suggestion_id", ""),
                        pattern_id=row.get("pattern_id", ""),
                        accepted=row.get("accepted", False),
                        timestamp=row.get("timestamp", ""),
                        execution_time_ms=row.get("execution_time_ms"),
                        feedback=row.get("feedback"),
                        user_id=row.get("user_id", "default"),
                        project_root=row.get("project_root", ""),
                        confidence_at_decision=row.get("confidence_at_decision", 0.0),
                    )
                    history.append(acceptance)

            logger.debug(
                "suggestion_history_retrieved",
                suggestion_id=suggestion_id,
                records_count=len(history),
            )
            return history

        except Exception as e:
            logger.error("suggestion_history_retrieval_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="get_suggestion_history",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise

    async def get_recent_acceptances(self, limit: int = 100) -> list[SuggestionAcceptance]:
        """Get recent acceptance records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent SuggestionAcceptance records
        """
        start_time = datetime.now()
        try:
            query = f"""
            SELECT * FROM {self.TABLE_NAME}
            ORDER BY timestamp DESC
            LIMIT $limit
            """

            result = await self._client.query(query, {"limit": limit})

            acceptances = []
            if result:
                for row in result:
                    acceptance = SuggestionAcceptance(
                        suggestion_id=row.get("suggestion_id", ""),
                        pattern_id=row.get("pattern_id", ""),
                        accepted=row.get("accepted", False),
                        timestamp=row.get("timestamp", ""),
                        execution_time_ms=row.get("execution_time_ms"),
                        feedback=row.get("feedback"),
                        user_id=row.get("user_id", "default"),
                        project_root=row.get("project_root", ""),
                        confidence_at_decision=row.get("confidence_at_decision", 0.0),
                    )
                    acceptances.append(acceptance)

            logger.debug(
                "recent_acceptances_retrieved",
                records_count=len(acceptances),
            )
            return acceptances

        except Exception as e:
            logger.error("recent_acceptances_retrieval_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="get_recent_acceptances",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise

    async def delete_old_records(self, days_old: int = 90) -> int:
        """Delete old acceptance records.

        Args:
            days_old: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        start_time = datetime.now()
        try:
            cutoff_date = datetime.now()
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old).isoformat()

            query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE timestamp < d::time($cutoff_date)
            RETURN COUNT()
            """

            result = await self._client.query(query, {"cutoff_date": cutoff_date})

            deleted_count = result[0] if result and len(result) > 0 else 0

            logger.info(
                "old_records_deleted",
                deleted_count=deleted_count,
                days_old=days_old,
            )
            return deleted_count

        except Exception as e:
            logger.error("old_records_deletion_failed", error=str(e))
            metrics = RepositoryMetrics.from_operation(
                operation="delete_old_records",
                start_time=start_time.timestamp(),
                success=False,
                error=e,
            )
            self._metrics.append(metrics)
            raise
