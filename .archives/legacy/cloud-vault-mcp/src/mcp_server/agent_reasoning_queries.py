"""Query patterns for Phase 2 agent reasoning analysis.

Implements 4 key query patterns for reasoning analysis:
1. Root cause analysis - Find reasoning chains that led to decisions
2. Contradiction detection - Find lessons that contradict decisions
3. Cascade impact - Trace how decisions affect downstream decisions
4. High-confidence reasoning - Find well-justified decisions for reuse
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class AgentReasoningQueries:
    """Query patterns for agent reasoning analysis."""

    def __init__(self, surrealdb_sync):
        """Initialize with SurrealDBSync instance.

        Args:
            surrealdb_sync: SurrealDBSync instance for database operations
        """
        self.db = surrealdb_sync

    def root_cause_analysis(self, decision_id: str) -> dict[str, Any]:
        """Find the reasoning chain that led to a decision.

        Query Pattern: decision -> informs_reasoning -> agent_reasoning
        Goal: Understand WHY a decision was made

        Args:
            decision_id: ID of the decision to analyze

        Returns:
            Dict with decision_id, reasoning_chains (list), total_chains, status
        """
        try:
            # Query: Find all reasoning nodes for this decision
            query = f"""
                SELECT * FROM agent_reasoning
                WHERE decision_id = '{decision_id}'
                ORDER BY confidence_score DESC
            """

            result = self.db._execute_query(query)
            if not result:
                return {
                    "success": False,
                    "error": f"Decision not found: {decision_id}",
                }

            reasoning_chains = []
            for reasoning in result:
                reasoning_chains.append(
                    {
                        "reasoning_id": reasoning.get("id"),
                        "reasoning_type": reasoning.get("reasoning_type"),
                        "confidence_score": reasoning.get("confidence_score"),
                        "chain_length": len(reasoning.get("reasoning_chain", [])),
                        "reasoning_chain": reasoning.get("reasoning_chain", []),
                        "assumptions": reasoning.get("assumptions", []),
                        "alternatives_rejected": reasoning.get(
                            "alternatives_rejected", []
                        ),
                        "created_at": reasoning.get("created_at"),
                    }
                )

            logger.info(
                f"Root cause analysis for {decision_id}: found {len(reasoning_chains)} reasoning chains"
            )

            return {
                "success": True,
                "decision_id": decision_id,
                "reasoning_chains": reasoning_chains,
                "total_chains": len(reasoning_chains),
                "highest_confidence": max(
                    [r["confidence_score"] for r in reasoning_chains], default=0.0
                ),
            }

        except Exception as e:
            logger.error(f"Error in root_cause_analysis: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def contradiction_detection(
        self, severity_filter: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Find lessons that contradict recent decisions.

        Query Pattern: decision -> challenges_lesson -> lesson
        Goal: Identify when operational evidence contradicts reasoning

        Args:
            severity_filter: Filter by severity (major|minor|clarification, default: all)
            limit: Maximum number of results to return (default: 50)

        Returns:
            Dict with contradictions (list), total_count, status
        """
        try:
            # Build query with optional severity filter
            where_clause = ""
            if severity_filter:
                valid_severities = ["major", "minor", "clarification"]
                if severity_filter not in valid_severities:
                    return {
                        "success": False,
                        "error": f"Invalid severity: {severity_filter}. Must be one of {valid_severities}",
                    }
                where_clause = f"WHERE severity = '{severity_filter}'"

            query = f"""
                SELECT
                    in as decision_id,
                    out as lesson_id,
                    challenge_type,
                    severity,
                    notes,
                    created_at
                FROM challenges_lesson
                {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
            """

            result = self.db._execute_query(query)
            if not result:
                return {
                    "success": True,
                    "contradictions": [],
                    "total_count": 0,
                    "severity_filter": severity_filter,
                }

            contradictions = []
            for challenge in result:
                contradictions.append(
                    {
                        "decision_id": challenge.get("decision_id"),
                        "lesson_id": challenge.get("lesson_id"),
                        "challenge_type": challenge.get("challenge_type"),
                        "severity": challenge.get("severity"),
                        "notes": challenge.get("notes"),
                        "created_at": challenge.get("created_at"),
                    }
                )

            logger.info(
                f"Contradiction detection: found {len(contradictions)} contradictions"
                + (f" (severity: {severity_filter})" if severity_filter else "")
            )

            return {
                "success": True,
                "contradictions": contradictions,
                "total_count": len(contradictions),
                "severity_filter": severity_filter,
                "major_count": sum(
                    1 for c in contradictions if c["severity"] == "major"
                ),
            }

        except Exception as e:
            logger.error(f"Error in contradiction_detection: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def cascade_impact(self, source_decision_id: str, depth: int = 3) -> dict[str, Any]:
        """Trace how one decision affects downstream decisions.

        Query Pattern: decision -> relates_to_decision -> decision (recursive)
        Goal: Understand impact propagation when a critical decision changes

        Args:
            source_decision_id: ID of the source decision
            depth: Maximum cascade depth to trace (default: 3)

        Returns:
            Dict with cascades (list of edges), total_critical, total_significant, total_minor
        """
        try:
            # Query: Find all cascade edges from this decision
            # Note: This implements breadth-first search for cascade impact
            query = f"""
                SELECT
                    in as source_decision,
                    out as dependent_decision,
                    dependency_type,
                    impact_level,
                    notes,
                    created_at
                FROM relates_to_decision
                WHERE in = '{source_decision_id}'
                ORDER BY impact_level, created_at DESC
            """

            result = self.db._execute_query(query)
            if not result:
                return {
                    "success": True,
                    "cascades": [],
                    "source_decision": source_decision_id,
                    "total_cascades": 0,
                    "depth_limit": depth,
                    "critical_count": 0,
                    "significant_count": 0,
                    "minor_count": 0,
                }

            cascades = []
            critical_count = 0
            significant_count = 0
            minor_count = 0

            for cascade in result:
                impact = cascade.get("impact_level", "minor")
                if impact == "critical":
                    critical_count += 1
                elif impact == "significant":
                    significant_count += 1
                else:
                    minor_count += 1

                cascades.append(
                    {
                        "source_decision": cascade.get("source_decision"),
                        "dependent_decision": cascade.get("dependent_decision"),
                        "dependency_type": cascade.get("dependency_type"),
                        "impact_level": impact,
                        "notes": cascade.get("notes"),
                        "created_at": cascade.get("created_at"),
                    }
                )

            logger.info(
                f"Cascade impact for {source_decision_id}: found {len(cascades)} cascades "
                f"({critical_count} critical, {significant_count} significant, {minor_count} minor)"
            )

            return {
                "success": True,
                "cascades": cascades,
                "source_decision": source_decision_id,
                "total_cascades": len(cascades),
                "critical_count": critical_count,
                "significant_count": significant_count,
                "minor_count": minor_count,
                "depth_limit": depth,
            }

        except Exception as e:
            logger.error(f"Error in cascade_impact: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def high_confidence_reasoning(
        self, confidence_threshold: float = 0.8, limit: int = 50
    ) -> dict[str, Any]:
        """Find decisions made with high confidence and strong reasoning.

        Query Pattern: agent_reasoning with confidence_score >= threshold
        Goal: Identify stable, well-justified decisions for reuse in similar contexts

        Args:
            confidence_threshold: Minimum confidence score (0.0-1.0, default: 0.8)
            limit: Maximum number of results to return (default: 50)

        Returns:
            Dict with reasoning (list), total_count, avg_confidence, reasoning_types
        """
        try:
            # Validate threshold
            if not (0.0 <= confidence_threshold <= 1.0):
                return {
                    "success": False,
                    "error": f"confidence_threshold must be between 0.0 and 1.0, got {confidence_threshold}",
                }

            # Query: Find all reasoning above confidence threshold
            query = f"""
                SELECT
                    id as reasoning_id,
                    decision_id,
                    reasoning_type,
                    confidence_score,
                    reasoning_chain,
                    assumptions,
                    created_at
                FROM agent_reasoning
                WHERE confidence_score >= {confidence_threshold}
                ORDER BY confidence_score DESC, created_at DESC
                LIMIT {limit}
            """

            result = self.db._execute_query(query)
            if not result:
                return {
                    "success": True,
                    "reasoning": [],
                    "total_count": 0,
                    "confidence_threshold": confidence_threshold,
                    "avg_confidence": 0.0,
                }

            reasoning_list = []
            confidence_scores = []
            reasoning_types = {}

            for reasoning in result:
                confidence = reasoning.get("confidence_score", 0.0)
                reasoning_type = reasoning.get("reasoning_type", "unknown")
                confidence_scores.append(confidence)

                if reasoning_type not in reasoning_types:
                    reasoning_types[reasoning_type] = 0
                reasoning_types[reasoning_type] += 1

                reasoning_list.append(
                    {
                        "reasoning_id": reasoning.get("id"),
                        "decision_id": reasoning.get("decision_id"),
                        "reasoning_type": reasoning_type,
                        "confidence_score": confidence,
                        "chain_length": len(reasoning.get("reasoning_chain", [])),
                        "assumption_count": len(reasoning.get("assumptions", [])),
                        "created_at": reasoning.get("created_at"),
                    }
                )

            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )

            logger.info(
                f"High-confidence reasoning search: found {len(reasoning_list)} results "
                f"(threshold: {confidence_threshold}, avg confidence: {avg_confidence:.3f})"
            )

            return {
                "success": True,
                "reasoning": reasoning_list,
                "total_count": len(reasoning_list),
                "confidence_threshold": confidence_threshold,
                "avg_confidence": round(avg_confidence, 3),
                "min_confidence": round(min(confidence_scores), 3)
                if confidence_scores
                else 0.0,
                "max_confidence": round(max(confidence_scores), 3)
                if confidence_scores
                else 0.0,
                "reasoning_types": reasoning_types,
            }

        except Exception as e:
            logger.error(f"Error in high_confidence_reasoning: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def reasoning_by_type(self, reasoning_type: str, limit: int = 50) -> dict[str, Any]:
        """Find all reasoning of a specific type (helper query).

        Args:
            reasoning_type: Type to filter (research|pattern|intuition|convention|hybrid)
            limit: Maximum number of results (default: 50)

        Returns:
            Dict with reasoning (list), total_count, avg_confidence
        """
        try:
            valid_types = ["research", "pattern", "intuition", "convention", "hybrid"]
            if reasoning_type not in valid_types:
                return {
                    "success": False,
                    "error": f"Invalid reasoning_type: {reasoning_type}. Must be one of {valid_types}",
                }

            query = f"""
                SELECT
                    id as reasoning_id,
                    decision_id,
                    reasoning_type,
                    confidence_score,
                    created_at
                FROM agent_reasoning
                WHERE reasoning_type = '{reasoning_type}'
                ORDER BY confidence_score DESC
                LIMIT {limit}
            """

            result = self.db._execute_query(query)
            if not result:
                return {
                    "success": True,
                    "reasoning": [],
                    "reasoning_type": reasoning_type,
                    "total_count": 0,
                    "avg_confidence": 0.0,
                }

            reasoning_list = []
            confidence_scores = []

            for reasoning in result:
                confidence = reasoning.get("confidence_score", 0.0)
                confidence_scores.append(confidence)

                reasoning_list.append(
                    {
                        "reasoning_id": reasoning.get("id"),
                        "decision_id": reasoning.get("decision_id"),
                        "confidence_score": confidence,
                        "created_at": reasoning.get("created_at"),
                    }
                )

            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )

            logger.info(
                f"Reasoning by type '{reasoning_type}': found {len(reasoning_list)} results "
                f"(avg confidence: {avg_confidence:.3f})"
            )

            return {
                "success": True,
                "reasoning": reasoning_list,
                "reasoning_type": reasoning_type,
                "total_count": len(reasoning_list),
                "avg_confidence": round(avg_confidence, 3),
            }

        except Exception as e:
            logger.error(f"Error in reasoning_by_type: {e}")
            return {
                "success": False,
                "error": str(e),
            }
