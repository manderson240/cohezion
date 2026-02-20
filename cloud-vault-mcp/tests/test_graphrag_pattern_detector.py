"""
Tests for GraphRAG Pattern Auto-Detection

Tests pattern usage analysis, similarity-based suggestions,
and impact summary statistics.
"""

from unittest.mock import patch

import pytest

from mcp_server.graphrag_pattern_detector import (
    PatternDetector,
    PatternSuggestion,
    PatternUsage,
)


@pytest.fixture
def pattern_detector(tmp_path):
    """Pattern detector instance"""
    return PatternDetector(vault_path=tmp_path)


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_detect_patterns_success(mock_execute, pattern_detector):
    """Test successful pattern detection"""
    # Mock query response
    mock_execute.return_value = [
        {
            "result": [
                {
                    "id": "vault_memory:pattern1",
                    "title": "Token Efficient Workflow",
                    "path": "patterns/token-efficient.md",
                    "content": "Implement → test → document pattern",
                    "used_in_count": 5,
                    "informed_by_count": 2,
                    "led_to_count": 1,
                    "used_in_docs": ["vault_memory:dec1", "vault_memory:dec2"],
                    "informed_by_docs": ["vault_memory:exp1"],
                    "led_to_docs": ["vault_memory:dec3"],
                },
                {
                    "id": "vault_memory:pattern2",
                    "title": "Test Isolation",
                    "path": "patterns/test-isolation.md",
                    "content": "Reset singletons in conftest.py",
                    "used_in_count": 3,
                    "informed_by_count": 1,
                    "led_to_count": 0,
                    "used_in_docs": ["vault_memory:dec4"],
                    "informed_by_docs": [],
                    "led_to_docs": [],
                },
            ]
        }
    ]

    patterns = await pattern_detector.detect_patterns(min_usage=3)

    assert len(patterns) == 2
    assert patterns[0].pattern_id == "vault_memory:pattern1"
    assert patterns[0].title == "Token Efficient Workflow"
    assert patterns[0].total_impact == 8  # 5 + 2 + 1
    assert patterns[1].total_impact == 4  # 3 + 1 + 0


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_detect_patterns_filters_low_usage(mock_execute, pattern_detector):
    """Test that patterns below min_usage threshold are filtered"""
    mock_execute.return_value = [
        {
            "result": [
                {
                    "id": "vault_memory:pattern1",
                    "title": "High Usage Pattern",
                    "path": "patterns/high.md",
                    "content": "Used many times",
                    "used_in_count": 5,
                    "informed_by_count": 0,
                    "led_to_count": 0,
                    "used_in_docs": [],
                    "informed_by_docs": [],
                    "led_to_docs": [],
                },
                {
                    "id": "vault_memory:pattern2",
                    "title": "Low Usage Pattern",
                    "path": "patterns/low.md",
                    "content": "Rarely used",
                    "used_in_count": 1,
                    "informed_by_count": 0,
                    "led_to_count": 0,
                    "used_in_docs": [],
                    "informed_by_docs": [],
                    "led_to_docs": [],
                },
            ]
        }
    ]

    patterns = await pattern_detector.detect_patterns(min_usage=3)

    assert len(patterns) == 1  # Only high usage pattern
    assert patterns[0].pattern_id == "vault_memory:pattern1"


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_detect_patterns_empty_result(mock_execute, pattern_detector):
    """Test handling of empty query results"""
    mock_execute.return_value = [{"result": []}]

    patterns = await pattern_detector.detect_patterns()

    assert len(patterns) == 0


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_suggest_patterns_finds_similar_docs(mock_execute, pattern_detector):
    """Test pattern suggestion from similar documents"""
    # Mock embedding vectors (normalized, high similarity)
    vec1 = [0.9, 0.1, 0.1] + [0.0] * 765  # 768D vector
    vec2 = [0.85, 0.15, 0.1] + [0.0] * 765  # Similar to vec1

    mock_execute.return_value = [
        {
            "result": [
                {
                    "id": "vault_memory:dec1",
                    "title": "Decision 1",
                    "type": "decision",
                    "content": "Used pattern X successfully",
                    "embedding": vec1,
                    "tags": ["testing", "isolation"],
                },
                {
                    "id": "vault_memory:dec2",
                    "title": "Decision 2",
                    "type": "decision",
                    "content": "Applied pattern X again",
                    "embedding": vec2,
                    "tags": ["testing", "mocking"],
                },
            ]
        }
    ]

    suggestions = await pattern_detector.suggest_patterns(min_similarity=0.7)

    assert len(suggestions) > 0
    assert (
        "testing" in suggestions[0].common_themes
        or "isolation" in suggestions[0].common_themes
    )


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_suggest_patterns_requires_group_size_2(mock_execute, pattern_detector):
    """Test that suggestions require at least 2 similar documents"""
    vec1 = [1.0] + [0.0] * 767

    mock_execute.return_value = [
        {
            "result": [
                {
                    "id": "vault_memory:dec1",
                    "title": "Single Decision",
                    "type": "decision",
                    "content": "Standalone decision",
                    "embedding": vec1,
                    "tags": ["unique"],
                }
            ]
        }
    ]

    suggestions = await pattern_detector.suggest_patterns()

    assert len(suggestions) == 0  # No suggestions for single doc


@pytest.mark.asyncio
@patch("mcp_server.graphrag_pattern_detector.execute_surreal_async")
async def test_get_pattern_impact_summary(mock_execute, pattern_detector):
    """Test pattern impact summary statistics"""
    # Mock summary query
    mock_execute.side_effect = [
        # First call: aggregate stats
        [
            {
                "result": [
                    {
                        "total_patterns": 10,
                        "total_used_in": 25,
                        "total_informed_by": 15,
                        "max_usage": 8,
                    }
                ]
            }
        ],
        # Second call: high-impact patterns (for detect_patterns)
        [{"result": []}],
        # Third call: unused patterns
        [{"result": [{"unused": 2}]}],
    ]

    summary = await pattern_detector.get_pattern_impact_summary()

    assert summary["total_patterns"] == 10
    assert summary["avg_usage"] == 4.0  # (25 + 15) / 10
    assert summary["max_usage"] == 8
    assert summary["unused_patterns"] == 2


@pytest.mark.asyncio
async def test_pattern_usage_dataclass():
    """Test PatternUsage dataclass construction"""
    pattern = PatternUsage(
        pattern_id="vault_memory:test",
        title="Test Pattern",
        path="patterns/test.md",
        content="Test content",
        usage_count=5,
        referenced_by=["doc1", "doc2"],
        used_in=["doc3"],
        informed_by=["doc4"],
        total_impact=10,
    )

    assert pattern.pattern_id == "vault_memory:test"
    assert pattern.usage_count == 5
    assert len(pattern.referenced_by) == 2


@pytest.mark.asyncio
async def test_pattern_suggestion_dataclass():
    """Test PatternSuggestion dataclass construction"""
    suggestion = PatternSuggestion(
        suggested_title="New Pattern",
        similarity_score=0.85,
        source_docs=["doc1", "doc2", "doc3"],
        common_themes=["testing", "isolation"],
        rationale="Found 3 similar decisions",
    )

    assert suggestion.suggested_title == "New Pattern"
    assert suggestion.similarity_score == 0.85
    assert len(suggestion.source_docs) == 3
    assert "testing" in suggestion.common_themes
