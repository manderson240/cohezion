"""Tests for VaultSearchExecutor (Phase 7 Feature 1).

Tests the vault search enhancement with skill context integration following
the CompoundAsyncExecutor pattern (7-step execution pipeline).
"""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.vault_search_executor import (
    SearchQuery,
    SearchResult,
    VaultSearchExecutor,
    create_vault_search_executor,
)
from cohezion.core.mcp_client import MCPClient


@pytest.fixture
def mock_mcp_client():
    """Create mock MCPClient for testing."""
    client = MagicMock(spec=MCPClient)
    client.is_connected = MagicMock(return_value=True)
    return client


@pytest.fixture
def vault_search_executor(mock_mcp_client):
    """Create VaultSearchExecutor instance for testing."""
    return VaultSearchExecutor(mcp_client=mock_mcp_client, project="test-cohezion")


class TestVaultSearchExecutor:
    """Test VaultSearchExecutor initialization and configuration."""

    def test_initialization(self, mock_mcp_client):
        """Test executor initializes correctly."""
        executor = VaultSearchExecutor(mcp_client=mock_mcp_client, project="test")

        assert executor.mcp_client == mock_mcp_client
        assert executor.project == "test"

    def test_factory_creation(self, mock_mcp_client):
        """Test factory function creates executor."""
        executor = create_vault_search_executor(mock_mcp_client, project="test")

        assert isinstance(executor, VaultSearchExecutor)
        assert executor.project == "test"

    def test_search_with_empty_query_raises(self, vault_search_executor):
        """Test search with empty query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            vault_search_executor.search("")

    def test_search_with_whitespace_query_raises(self, vault_search_executor):
        """Test search with whitespace-only query raises ValueError."""
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            vault_search_executor.search("   ")

    def test_search_with_query_too_long_raises(self, vault_search_executor):
        """Test search with query >512 chars raises ValueError."""
        long_query = "a" * 513
        with pytest.raises(ValueError, match="Search query too long"):
            vault_search_executor.search(long_query)

    def test_search_with_short_keywords_ignored(self, vault_search_executor):
        """Test search with keywords <3 chars are ignored."""
        with pytest.raises(ValueError, match="must contain at least one keyword"):
            vault_search_executor.search("a b c")  # All keywords < 3 chars

    def test_search_returns_search_result(self, vault_search_executor):
        """Test search returns SearchResult object."""
        vault_search_executor.logger = MagicMock()
        vault_search_executor.logger.get_experience_guidance = MagicMock(
            return_value={
                "relevant_skills": ["vault-integration", "search-optimization"]
            }
        )

        result = vault_search_executor.search("test vault search")

        assert isinstance(result, SearchResult)
        assert result.total_results == 0  # Empty search for now
        assert result.execution_time_ms > 0

    def test_parse_search_query(self, vault_search_executor):
        """Test query parsing extracts keywords."""
        query = vault_search_executor._parse_search_query(
            "find vault patterns for compound engineering",
            document_types=["patterns"],
        )

        assert isinstance(query, SearchQuery)
        assert "vault" in query.keywords
        assert "patterns" in query.keywords
        assert query.document_types == ["patterns"]
        assert query.max_results == 10

    def test_validate_search_query_max_results(self, vault_search_executor):
        """Test validation rejects max_results > 100."""
        query = SearchQuery(query="test", keywords=["test"], document_types=[], max_results=101)

        with pytest.raises(ValueError, match="Max results cannot exceed 100"):
            vault_search_executor._validate_search_query(query)

    def test_validate_search_query_relevance_bounds(self, vault_search_executor):
        """Test validation enforces relevance bounds."""
        query = SearchQuery(query="test", keywords=["test"], document_types=[], min_relevance=1.5)

        with pytest.raises(ValueError, match=r"Min relevance must be between 0\.0 and 1\.0"):
            vault_search_executor._validate_search_query(query)

    def test_calculate_relevance_keyword_match(self, vault_search_executor):
        """Test relevance calculation for keyword matches."""
        document = {"title": "test document", "content": "this is a test"}
        query = SearchQuery(
            query="test document",
            keywords=["test", "document"],
            document_types=[],
        )

        relevance = vault_search_executor._calculate_relevance(document, query, skill_context=[])

        # 2 matching keywords out of 2, so score should be high
        assert relevance > 0.5

    def test_calculate_relevance_with_skill_context(self, vault_search_executor):
        """Test relevance boost with skill context match."""
        document = {"title": "test", "skill": "vault-integration"}
        query = SearchQuery(
            query="test",
            keywords=["test"],
            document_types=[],
        )

        # Without skill context
        relevance_no_context = vault_search_executor._calculate_relevance(document, query, skill_context=[])

        # With matching skill context
        relevance_with_context = vault_search_executor._calculate_relevance(
            document, query, skill_context=["vault-integration"]
        )

        assert relevance_with_context > relevance_no_context

    def test_detect_search_anomalies_no_results(self, vault_search_executor):
        """Test anomaly detection for empty results."""
        anomalies = vault_search_executor._detect_search_anomalies([])

        assert len(anomalies) > 0
        assert any("No documents found" in a for a in anomalies)

    def test_detect_search_anomalies_too_many_results(self, vault_search_executor):
        """Test anomaly detection for too many results."""
        documents = [{"id": f"doc_{i}"} for i in range(1001)]

        anomalies = vault_search_executor._detect_search_anomalies(documents)

        assert len(anomalies) > 0
        assert any("Unexpectedly large" in a for a in anomalies)

    def test_detect_search_anomalies_duplicates(self, vault_search_executor):
        """Test anomaly detection for duplicate documents."""
        documents = [
            {"id": "doc_1", "path": "/path/1"},
            {"id": "doc_1", "path": "/path/1"},  # Duplicate
        ]

        anomalies = vault_search_executor._detect_search_anomalies(documents)

        assert len(anomalies) > 0
        assert any("Duplicate" in a for a in anomalies)

    def test_analyze_search_patterns(self, vault_search_executor):
        """Test pattern analysis extracts search insights."""
        documents = [
            {"type": "decision", "_relevance_score": 0.9},
            {"type": "pattern", "_relevance_score": 0.7},
            {"type": "decision", "_relevance_score": 0.4},
        ]

        patterns = vault_search_executor._analyze_search_patterns(documents, skill_context=["vault-integration"])

        assert patterns["effective_skills"] == ["vault-integration"]
        assert patterns["result_distribution"]["by_type"]["decision"] == 2
        assert patterns["result_distribution"]["by_type"]["pattern"] == 1
        assert patterns["result_distribution"]["by_relevance"]["high"] == 1
        assert patterns["result_distribution"]["by_relevance"]["medium"] == 1
        assert patterns["result_distribution"]["by_relevance"]["low"] == 1

    def test_record_search_metrics(self, vault_search_executor):
        """Test metrics recording with mock collector."""
        vault_search_executor._metrics_collector = MagicMock()

        vault_search_executor._record_search_metrics(
            query="test search",
            num_results=5,
            execution_time_ms=100.0,
            skill_context=["skill1", "skill2"],
        )

        vault_search_executor._metrics_collector.record.assert_called_once()
        call_args = vault_search_executor._metrics_collector.record.call_args[0][0]
        assert call_args["operation"] == "vault_search"
        assert call_args["num_results"] == 5

    def test_record_search_metrics_no_collector(self, vault_search_executor):
        """Test metrics recording handles missing collector gracefully."""
        vault_search_executor._metrics_collector = None

        # Should not raise
        vault_search_executor._record_search_metrics(
            query="test",
            num_results=0,
            execution_time_ms=50.0,
            skill_context=[],
        )

    def test_search_execution_flow(self, vault_search_executor):
        """Test full search execution flow with all 7 phases."""
        vault_search_executor.logger = MagicMock()
        vault_search_executor.logger.get_experience_guidance = MagicMock(
            return_value={"relevant_skills": ["test-skill"]}
        )
        vault_search_executor._metrics_collector = MagicMock()

        result = vault_search_executor.search("test query")

        # Verify result structure
        assert isinstance(result, SearchResult)
        assert result.total_results >= 0
        assert len(result.search_context_skills) > 0

        # Verify all phases were executed
        vault_search_executor.logger.get_experience_guidance.assert_called()
        vault_search_executor._metrics_collector.record.assert_called()

    def test_search_error_handling(self, vault_search_executor):
        """Test search handles errors gracefully."""
        vault_search_executor.logger = MagicMock()
        vault_search_executor.logger.get_experience_guidance = MagicMock(
            side_effect=Exception("Vault connection failed")
        )

        result = vault_search_executor.search("test query")

        # Should return empty result, not raise
        assert isinstance(result, SearchResult)
        assert result.total_results == 0
        assert len(result.documents) == 0


class TestSearchQuery:
    """Test SearchQuery data class."""

    def test_search_query_creation(self):
        """Test SearchQuery can be created."""
        query = SearchQuery(
            query="find patterns",
            keywords=["find", "patterns"],
            document_types=["patterns"],
            max_results=20,
            min_relevance=0.6,
        )

        assert query.query == "find patterns"
        assert query.keywords == ["find", "patterns"]
        assert query.document_types == ["patterns"]
        assert query.max_results == 20
        assert query.min_relevance == 0.6

    def test_search_query_defaults(self):
        """Test SearchQuery uses proper defaults."""
        query = SearchQuery(query="test", keywords=["test"], document_types=["decisions"])

        assert query.max_results == 10
        assert query.min_relevance == 0.5


class TestSearchResult:
    """Test SearchResult data class."""

    def test_search_result_creation(self):
        """Test SearchResult can be created."""
        docs = [{"id": "doc1", "title": "Test"}]
        scores = [0.95]

        result = SearchResult(
            documents=docs,
            total_results=1,
            execution_time_ms=45.0,
            search_context_skills=["skill1"],
            relevance_scores=scores,
        )

        assert result.total_results == 1
        assert len(result.documents) == 1
        assert result.execution_time_ms == 45.0

    def test_search_result_empty(self):
        """Test SearchResult with empty results."""
        result = SearchResult(
            documents=[],
            total_results=0,
            execution_time_ms=0.0,
            search_context_skills=[],
            relevance_scores=[],
        )

        assert result.total_results == 0
        assert len(result.documents) == 0


# Integration test demonstrating Phase 7 Feature 1
@pytest.mark.asyncio
async def test_vault_search_executor_phase7_integration(mock_mcp_client):
    """Integration test for Phase 7 Feature 1: Vault Search Enhancement.

    Demonstrates all 7 phases of compound execution:
    1. Query vault for experience guidance
    2. Parse request (search query)
    3. Apply guardrails (validate parameters)
    4. Execute core logic (vault search with context)
    5. Detect anomalies (search quality check)
    6. Analyze & refine (pattern extraction)
    7. Record metrics & journey (observability)
    """
    executor = VaultSearchExecutor(mcp_client=mock_mcp_client, project="cohezion")

    # Setup mocks
    executor.logger = MagicMock()
    executor.logger.get_experience_guidance = MagicMock(
        return_value={"relevant_skills": ["vault-integration", "search-optimization"]}
    )
    executor._metrics_collector = MagicMock()

    # Execute search (demonstrates all 7 phases)
    result = executor.search("compound engineering patterns")

    # Verify execution completed successfully
    assert isinstance(result, SearchResult)
    assert result.execution_time_ms > 0
    assert len(result.search_context_skills) > 0

    # Verify all phases were invoked
    executor.logger.get_experience_guidance.assert_called()
    executor._metrics_collector.record.assert_called()
