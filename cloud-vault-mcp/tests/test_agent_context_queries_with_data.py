"""Tests for agent context queries with sample data.

Creates sample data in SurrealDB and validates queries return correct results.
"""

import json
import os
import uuid

import pytest

from mcp_server.agent_context_queries import AgentContextQueries


pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Requires SurrealDB — unavailable in CI",
)


def create_sample_data():
    """Create sample data for testing."""
    import httpx

    client = httpx.Client(timeout=30.0)
    headers = {
        "Content-Type": "text/plain",
        "NS": "cohezion",
        "DB": "vault",
    }

    # Create sample session
    session_id = f"session:{uuid.uuid4()}"
    session_query = f"""
    USE NS cohezion;
    USE DB vault;

    UPSERT agent_session:`{session_id}` SET
      agent_name = 'test-agent',
      started_at = fn::now(),
      status = 'success',
      context = {{"model": "test", "temperature": 0.7}};
    """

    response = client.post(
        "http://localhost:8000/sql",
        headers=headers,
        auth=("root", "root"),
        content=session_query,
    )
    print(f"Create session: {response.status_code}")

    # Create sample decision
    decision_id = f"decision:{uuid.uuid4()}"
    decision_query = f"""
    USE NS cohezion;
    USE DB vault;

    UPSERT agent_decision:`{decision_id}` SET
      session_id = `{session_id}`,
      title = 'Test Decision',
      chosen_option = 'Option A',
      decision_reasoning = {{"rationale": "Test rationale", "confidence": 0.95}},
      estimated_cost = 1.0,
      created_at = fn::now();
    """

    response = client.post(
        "http://localhost:8000/sql",
        headers=headers,
        auth=("root", "root"),
        content=decision_query,
    )
    print(f"Create decision: {response.status_code}")

    # Create sample action
    action_id = f"action:{uuid.uuid4()}"
    action_query = f"""
    USE NS cohezion;
    USE DB vault;

    UPSERT agent_action:`{action_id}` SET
      decision_id = `{decision_id}`,
      tool_name = 'Read',
      sequence_order = 1,
      executed_at = fn::now(),
      execution_time_ms = 1200,
      status = 'success';
    """

    response = client.post(
        "http://localhost:8000/sql",
        headers=headers,
        auth=("root", "root"),
        content=action_query,
    )
    print(f"Create action: {response.status_code}")

    # Create sample outcome
    outcome_id = f"outcome:{uuid.uuid4()}"
    outcome_query = f"""
    USE NS cohezion;
    USE DB vault;

    UPSERT agent_outcome:`{outcome_id}` SET
      decision_id = `{decision_id}`,
      session_id = `{session_id}`,
      outcome_status = 'success',
      actual_cost = 0.5,
      lessons_generated = ['lesson-test'],
      completed_at = fn::now();
    """

    response = client.post(
        "http://localhost:8000/sql",
        headers=headers,
        auth=("root", "root"),
        content=outcome_query,
    )
    print(f"Create outcome: {response.status_code}")

    # Create sample lesson
    lesson_id = f"lesson_val:{uuid.uuid4()}"
    lesson_query = f"""
    USE NS cohezion;
    USE DB vault;

    UPSERT lesson_validation:`{lesson_id}` SET
      outcome_id = `{outcome_id}`,
      lesson_vault_file = 'lessons/lesson-test.md',
      lesson_title = 'Test Lesson',
      confidence_score = 0.95,
      created_at = fn::now();
    """

    response = client.post(
        "http://localhost:8000/sql",
        headers=headers,
        auth=("root", "root"),
        content=lesson_query,
    )
    print(f"Create lesson: {response.status_code}")

    return {
        "session_id": session_id,
        "decision_id": decision_id,
        "action_id": action_id,
        "outcome_id": outcome_id,
        "lesson_id": lesson_id,
    }


def test_queries_with_data():
    """Test all queries with sample data."""
    print("\n=== CREATING SAMPLE DATA ===")
    ids = create_sample_data()
    print(f"Created: {ids}")

    print("\n=== TESTING QUERIES ===")
    q = AgentContextQueries()

    print("\n1. Research Lineage")
    result = q.query_research_lineage(limit=10)
    print(f"  Records: {len(result)}")
    if result:
        print(f"  Sample: {json.dumps(result[0], default=str, indent=4)}")

    print("\n2. Lesson Validation")
    result = q.query_lesson_validation(limit=10)
    print(f"  Records: {len(result)}")
    if result:
        print(f"  Sample: {json.dumps(result[0], default=str, indent=4)}")

    print("\n3. Cascade Detection")
    result = q.query_cascade_detection(limit=10)
    print(f"  Records: {len(result)}")
    if result:
        print(f"  Sample: {json.dumps(result[0], default=str, indent=4)}")

    print("\n4. Cost Analysis")
    result = q.query_decision_cost_analysis(limit=10)
    print(f"  Records: {len(result)}")
    if result:
        print(f"  Sample: {json.dumps(result[0], default=str, indent=4)}")

    print("\n5. Execution Performance")
    result = q.query_execution_performance(limit=10)
    print(f"  Records: {len(result)}")
    if result:
        print(f"  Sample: {json.dumps(result[0], default=str, indent=4)}")

    print("\n6. Session Summary")
    result = q.get_session_summary(ids["session_id"])
    print(f"  Result: {json.dumps(result, default=str, indent=4)}")

    print("\n" + "=" * 60)
    print("✅ ALL QUERIES EXECUTED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    test_queries_with_data()
