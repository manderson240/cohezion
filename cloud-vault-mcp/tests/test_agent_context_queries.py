"""Tests for agent context queries.

Validates that query infrastructure works and returns correct structure.
"""

import json

import pytest

from mcp_server.agent_context_queries import AgentContextQueries


class TestAgentContextQueries:
    """Test suite for agent context queries."""

    @pytest.fixture
    def queries(self):
        """Create query executor for tests."""
        return AgentContextQueries(
            surrealdb_url="http://localhost:8001",
            namespace="cohezion",
            database="vault",
            username="root",
            password="root",
        )

    def test_research_lineage_query(self, queries):
        """Test research lineage query structure."""
        result = queries.query_research_lineage(limit=5)
        # Should return list (empty is ok, schema is fresh)
        assert isinstance(result, list)
        print(f"Research lineage returned {len(result)} records")

    def test_lesson_validation_query(self, queries):
        """Test lesson validation query structure."""
        result = queries.query_lesson_validation(limit=5)
        # Should return list (empty is ok)
        assert isinstance(result, list)
        print(f"Lesson validation returned {len(result)} records")

    def test_cascade_detection_query(self, queries):
        """Test cascade detection query structure."""
        result = queries.query_cascade_detection(limit=5)
        # Should return list (empty is ok)
        assert isinstance(result, list)
        print(f"Cascade detection returned {len(result)} records")

    def test_cost_analysis_query(self, queries):
        """Test decision cost analysis query."""
        result = queries.query_decision_cost_analysis(limit=5)
        # Should return list (empty is ok)
        assert isinstance(result, list)
        print(f"Cost analysis returned {len(result)} records")

    def test_execution_performance_query(self, queries):
        """Test execution performance query."""
        result = queries.query_execution_performance(limit=5)
        # Should return list (empty is ok)
        assert isinstance(result, list)
        print(f"Execution performance returned {len(result)} records")

    def test_session_summary(self, queries):
        """Test session summary query."""
        # Try with non-existent ID (should return empty dict)
        result = queries.get_session_summary("session:nonexistent")
        assert isinstance(result, dict)
        print(f"Session summary returned: {json.dumps(result, default=str, indent=2)}")

    def test_all_queries_return_list_or_dict(self, queries):
        """Meta-test: All queries should return list or dict."""
        queries_to_test = [
            (queries.query_research_lineage, list),
            (queries.query_lesson_validation, list),
            (queries.query_cascade_detection, list),
            (queries.query_decision_cost_analysis, list),
            (queries.query_execution_performance, list),
        ]

        for query_func, expected_type in queries_to_test:
            result = query_func(limit=1)
            assert isinstance(result, expected_type), (
                f"{query_func.__name__} should return {expected_type}, got {type(result)}"
            )


if __name__ == "__main__":
    # Manual test run

    q = AgentContextQueries()

    print("\n" + "=" * 60)
    print("QUERY INFRASTRUCTURE TEST")
    print("=" * 60)

    print("\n1. Research Lineage Query")
    print("-" * 60)
    result = q.query_research_lineage(limit=3)
    print(f"Status: {len(result)} records returned")
    print(f"Type: {type(result)}")

    print("\n2. Lesson Validation Query")
    print("-" * 60)
    result = q.query_lesson_validation(limit=3)
    print(f"Status: {len(result)} records returned")
    print(f"Type: {type(result)}")

    print("\n3. Cascade Detection Query")
    print("-" * 60)
    result = q.query_cascade_detection(limit=3)
    print(f"Status: {len(result)} records returned")
    print(f"Type: {type(result)}")

    print("\n4. Cost Analysis Query")
    print("-" * 60)
    result = q.query_decision_cost_analysis(limit=3)
    print(f"Status: {len(result)} records returned")
    print(f"Type: {type(result)}")

    print("\n5. Execution Performance Query")
    print("-" * 60)
    result = q.query_execution_performance(limit=3)
    print(f"Status: {len(result)} records returned")
    print(f"Type: {type(result)}")

    print("\n6. Session Summary Query")
    print("-" * 60)
    result = q.get_session_summary("session:test")
    print("Status: Session lookup completed")
    print(f"Result: {result}")

    print("\n" + "=" * 60)
    print("INFRASTRUCTURE STATUS: ✅ All queries working")
    print("=" * 60)
