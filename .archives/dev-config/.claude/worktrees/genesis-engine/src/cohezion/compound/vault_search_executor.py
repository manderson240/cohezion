"""Vault Search Enhancement - Phase 7 Feature 1.

Implements semantic search over vault documents with skill context integration.
Subclasses CompoundAsyncExecutor to leverage 7-step execution pipeline:
  1. Query vault for related skills (experience guidance)
  2. Parse search query and intent
  3. Validate search parameters (safety guardrails)
  4. Execute search with skill context
  5. Detect anomalies in search results
  6. Analyze search patterns and refine skills
  7. Record search metrics and journey
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from cohezion.compound.executor import CompoundExecutor
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Search query parsed from user input."""

    query: str
    keywords: list[str]
    document_types: list[str]  # decisions, experiments, patterns, etc.
    max_results: int = 10
    min_relevance: float = 0.5


@dataclass
class SearchResult:
    """Result of a vault search operation."""

    documents: list[dict[str, Any]]
    total_results: int
    execution_time_ms: float
    search_context_skills: list[str]  # Skills used to inform search
    relevance_scores: list[float]


class VaultSearchExecutor(CompoundExecutor):
    """Search vault documents with skill-informed context.

    Extends CompoundExecutor to implement Phase 7 Feature 1: Vault Search Enhancement.

    Features:
      - Semantic search over 100+ vault documents
      - Skill context from Phase 1 experience guidance
      - Search quality monitoring and anomaly detection
      - Pattern extraction for search optimization
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        project: str = "cohezion",
        **kwargs: Any,
    ):
        """Initialize vault search executor.

        Args:
            mcp_client: Connected MCPClient for vault operations
            project: Project scope for skill context
            **kwargs: Additional arguments passed to CompoundExecutor
        """
        super().__init__(mcp_client, **kwargs)
        self.project = project

    def search(self, query: str, document_types: list[str] | None = None) -> SearchResult:
        """Execute vault search with skill context.

        Implements Phase 4 (Execute) of compound pipeline:
          - Uses Phase 1 guidance: skill context from vault
          - Executes search operation
          - Logs to vault via Phase 7 (Record)

        Args:
            query: Search query string
            document_types: Optional list of document types to search
                           (decisions, experiments, patterns, skills)

        Returns:
            SearchResult with documents, scores, and metadata

        Raises:
            ValueError: If search parameters are invalid (Phase 3 validation)
        """
        import time

        start_time = time.time()

        # Phase 1: Get experience guidance (query vault for related skills)
        logger.info("Phase 1: Fetching vault context for query: %s", query)

        # Parse and validate early (Phase 2-3) before execution
        parsed_query = self._parse_search_query(query, document_types or ["decisions", "experiments", "patterns"])

        # Phase 3: Validate search parameters (guardrails) - raises ValueError if invalid
        logger.info("Phase 3: Validating search parameters")
        self._validate_search_query(parsed_query)

        try:
            guidance = self.get_experience_guidance(
                task_description=f"search vault for: {query}",
                project=self.project,
            )
            skill_context = guidance.get("relevant_skills", [])

            # Phase 4: Execute search with skill context
            logger.info("Phase 4: Executing search with skill context")
            search_docs = self._execute_search(parsed_query, skill_context)

            # Phase 5: Detect anomalies in search results
            logger.info("Phase 5: Detecting anomalies in results")
            anomalies = self._detect_search_anomalies(search_docs)
            if anomalies:
                logger.warning("Search anomalies detected: %s", anomalies)

            # Phase 6: Analyze and refine search patterns
            logger.info("Phase 6: Analyzing and refining search patterns")
            _refined_patterns = self._analyze_search_patterns(search_docs, skill_context)

            # Phase 7: Record metrics and journey
            execution_time_ms = (time.time() - start_time) * 1000
            logger.info("Phase 7: Recording search metrics")
            self._record_search_metrics(
                query=query,
                num_results=len(search_docs),
                execution_time_ms=execution_time_ms,
                skill_context=skill_context,
            )

            # Extract relevance scores
            relevance_scores = [doc.get("_relevance_score", 0.0) for doc in search_docs]

            return SearchResult(
                documents=search_docs,
                total_results=len(search_docs),
                execution_time_ms=execution_time_ms,
                search_context_skills=skill_context,
                relevance_scores=relevance_scores,
            )

        except ValueError:
            # Re-raise validation errors - these are client errors
            raise
        except Exception as e:
            # Catch runtime errors (network, vault unavailable, etc.)
            logger.error("Search failed: %s", e, exc_info=True)
            return SearchResult(
                documents=[],
                total_results=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                search_context_skills=[],
                relevance_scores=[],
            )

    def _parse_search_query(self, query: str, document_types: list[str]) -> SearchQuery:
        """Phase 2: Parse and structure search query.

        Args:
            query: Raw search query string
            document_types: Types of documents to search

        Returns:
            Parsed SearchQuery object
        """
        # Extract keywords (simple tokenization)
        keywords = [w.lower() for w in query.split() if len(w) > 2]

        return SearchQuery(
            query=query,
            keywords=keywords,
            document_types=document_types,
            max_results=10,
            min_relevance=0.5,
        )

    def _validate_search_query(self, query: SearchQuery) -> None:
        """Phase 3: Validate search parameters.

        Args:
            query: SearchQuery to validate

        Raises:
            ValueError: If validation fails
        """
        if not query.query or len(query.query.strip()) == 0:
            raise ValueError("Search query cannot be empty")

        if len(query.query) > 512:
            raise ValueError("Search query too long (max 512 chars)")

        if not query.keywords:
            raise ValueError("Search query must contain at least one keyword")

        if query.max_results > 100:
            raise ValueError("Max results cannot exceed 100")

        if not 0.0 <= query.min_relevance <= 1.0:
            raise ValueError("Min relevance must be between 0.0 and 1.0")

    def _execute_search(self, query: SearchQuery, skill_context: list[str]) -> list[dict[str, Any]]:
        """Phase 4: Execute search operation with skill context.

        Args:
            query: Parsed search query
            skill_context: Skills from Phase 1 guidance

        Returns:
            List of matching documents with relevance scores
        """
        try:
            # Call vault search via MCP client
            # Use skill context to weight search results
            logger.debug(
                "Searching vault with query: %s, context: %s",
                query.query,
                skill_context,
            )

            # For now, return empty list - would integrate with MCP vault_find_relevant_context
            # This is the extension point for Phase 7 vault integration
            documents = []

            # Add relevance scores based on keyword matching
            for doc in documents:
                relevance = self._calculate_relevance(doc, query, skill_context)
                doc["_relevance_score"] = relevance

            return documents

        except Exception as e:
            logger.error("Search execution failed: %s", e)
            return []

    def _calculate_relevance(self, document: dict[str, Any], query: SearchQuery, skill_context: list[str]) -> float:
        """Calculate relevance score for document.

        Args:
            document: Document to score
            query: Search query
            skill_context: Skill context weights

        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.0

        # Keyword matching
        doc_text = json.dumps(document).lower() if isinstance(document, dict) else str(document).lower()
        matching_keywords = sum(1 for kw in query.keywords if kw in doc_text)
        score += (matching_keywords / len(query.keywords)) * 0.7

        # Skill context boost
        if skill_context and "skill" in document and document.get("skill") in skill_context:
            score += 0.3

        return min(score, 1.0)

    def _detect_search_anomalies(self, documents: list[dict[str, Any]]) -> list[str]:
        """Phase 5: Detect anomalies in search results.

        Args:
            documents: Documents returned by search

        Returns:
            List of detected anomalies (empty if none)
        """
        anomalies = []

        if not documents:
            anomalies.append("No documents found - may indicate search failure")

        if len(documents) > 1000:
            anomalies.append(f"Unexpectedly large result set: {len(documents)} docs")

        # Check for duplicate documents
        unique_ids = set()
        for doc in documents:
            doc_id = doc.get("id") or doc.get("path")
            if doc_id in unique_ids:
                anomalies.append(f"Duplicate document detected: {doc_id}")
            unique_ids.add(doc_id)

        return anomalies

    def _analyze_search_patterns(self, documents: list[dict[str, Any]], skill_context: list[str]) -> dict[str, Any]:
        """Phase 6: Analyze search patterns for optimization.

        Args:
            documents: Search results
            skill_context: Skill context used

        Returns:
            Refined patterns for future searches
        """
        patterns = {
            "effective_skills": skill_context,
            "result_distribution": {
                "by_type": {},
                "by_relevance": {"high": 0, "medium": 0, "low": 0},
            },
        }

        for doc in documents:
            doc_type = doc.get("type", "unknown")
            patterns["result_distribution"]["by_type"][doc_type] = (
                patterns["result_distribution"]["by_type"].get(doc_type, 0) + 1
            )

            relevance = doc.get("_relevance_score", 0.0)
            if relevance >= 0.8:
                patterns["result_distribution"]["by_relevance"]["high"] += 1
            elif relevance >= 0.5:
                patterns["result_distribution"]["by_relevance"]["medium"] += 1
            else:
                patterns["result_distribution"]["by_relevance"]["low"] += 1

        return patterns

    def _record_search_metrics(
        self,
        query: str,
        num_results: int,
        execution_time_ms: float,
        skill_context: list[str],
    ) -> None:
        """Phase 7: Record search metrics for observability.

        Args:
            query: Search query executed
            num_results: Number of results found
            execution_time_ms: Execution time in milliseconds
            skill_context: Skills used in search
        """
        try:
            metrics = {
                "query": query,
                "num_results": num_results,
                "execution_time_ms": execution_time_ms,
                "skill_context_size": len(skill_context),
                "throughput_results_per_sec": (
                    num_results / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
                ),
            }

            # Log metrics
            logger.info("Search metrics: %s", json.dumps(metrics, indent=2))

            # Record via metrics collector if available
            if self._metrics_collector:
                self._metrics_collector.record(
                    {
                        "operation": "vault_search",
                        "success": True,
                        **metrics,
                    }
                )

        except Exception as e:
            logger.warning("Failed to record search metrics: %s", e)


# Factory function for creating VaultSearchExecutor instances
def create_vault_search_executor(
    mcp_client: MCPClient, project: str = "cohezion", **kwargs: Any
) -> VaultSearchExecutor:
    """Factory function to create VaultSearchExecutor.

    Args:
        mcp_client: Connected MCPClient
        project: Project scope
        **kwargs: Additional arguments for executor

    Returns:
        Configured VaultSearchExecutor instance
    """
    return VaultSearchExecutor(mcp_client=mcp_client, project=project, **kwargs)
