"""Tests for research pipeline core orchestrator."""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@pytest.fixture
def mock_findings():
    """Mock findings data for testing."""
    # Import after pipeline is created
    from research.pipeline import Finding
    return [
        Finding(
            title="Test Finding 1",
            url="https://example.com/1",
            source="web_search",
            snippet="This is a test snippet about AI",
            category="compound_engineering",
            raw_score=0.0
        ),
        Finding(
            title="Test Finding 2",
            url="https://example.com/2",
            source="github_recent",
            snippet="Another test about tokens",
            category="token_efficiency",
            raw_score=0.0
        )
    ]


def test_finding_dataclass_creation():
    """Test Finding dataclass can be created with all required fields."""
    from research.pipeline import Finding

    finding = Finding(
        title="Test Finding",
        url="https://example.com/test",
        source="web_search",
        snippet="Test snippet",
        category="compound_engineering",
        raw_score=0.0
    )

    assert finding.title == "Test Finding"
    assert finding.url == "https://example.com/test"
    assert finding.source == "web_search"
    assert finding.snippet == "Test snippet"
    assert finding.category == "compound_engineering"
    assert finding.raw_score == 0.0


def test_research_report_dataclass_creation():
    """Test ResearchReport dataclass can be created with all required fields."""
    from research.pipeline import ResearchReport, Finding

    findings = [
        Finding(
            title="Test",
            url="https://example.com",
            source="test",
            snippet="snippet",
            category="test",
            raw_score=0.0
        )
    ]

    report = ResearchReport(
        findings=findings,
        scores={},
        metadata={"test": "value"},
        timestamp=datetime.now()
    )

    assert len(report.findings) == 1
    assert report.scores == {}
    assert report.metadata == {"test": "value"}
    assert isinstance(report.timestamp, datetime)


def test_pipeline_run_orchestrates_stages(mock_findings):
    """Test Pipeline.run() calls harvest, score, publish in sequence."""
    from research.pipeline import Pipeline, ResearchReport

    # Mock config
    config = {"test": "config"}

    # Create pipeline with mocked stages
    pipeline = Pipeline(config)

    # Track which methods were called
    calls = []

    async def mock_harvest(config):
        calls.append("harvest")
        return mock_findings

    async def mock_score(findings, config):
        calls.append("score")
        return findings, {}

    async def mock_publish(findings, scores, config):
        calls.append("publish")
        return {"published": len(findings)}

    # Replace pipeline methods with mocks
    pipeline.harvest = mock_harvest
    pipeline.score = mock_score
    pipeline.publish = mock_publish

    # Run pipeline
    import asyncio
    result = asyncio.run(pipeline.run())

    # Verify stages were called in order
    assert calls == ["harvest", "score", "publish"]
    assert isinstance(result, ResearchReport)
    assert len(result.findings) > 0


def test_pipeline_handles_partial_harvest_failure(mock_findings):
    """Test pipeline continues when one harvest source fails."""
    from research.pipeline import Pipeline

    config = {"test": "config"}
    pipeline = Pipeline(config)

    # Mock harvest that partially fails
    async def mock_harvest_with_failure(config):
        # Simulate partial failure by logging an error but returning some findings
        return mock_findings[:1]  # Only return 1 finding instead of 2

    pipeline.harvest = mock_harvest_with_failure

    # Mock other stages
    async def mock_score(findings, config):
        return findings, {}

    async def mock_publish(findings, scores, config):
        return {"published": len(findings)}

    pipeline.score = mock_score
    pipeline.publish = mock_publish

    # Run should succeed even with partial failure
    import asyncio
    result = asyncio.run(pipeline.run())

    assert len(result.findings) == 1  # Still got some findings
    assert result.metadata.get("published") == 1
