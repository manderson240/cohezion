"""Unit tests for entire.io commit parsing (entire_ops.py)."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "mcp_server"))

from entire_ops import CommitData, EntireOps, ParsingError


@pytest.fixture
def entire_ops():
    """Create EntireOps instance."""
    return EntireOps("/tmp/vault")


class TestParseTimestamp:
    """Test timestamp parsing."""

    def test_parse_iso_format(self, entire_ops):
        """Test ISO 8601 format timestamps."""
        ts = entire_ops._parse_timestamp("2026-02-12T14:30:00+00:00")
        assert ts.year == 2026
        assert ts.month == 2
        assert ts.day == 12

    def test_parse_iso_z_format(self, entire_ops):
        """Test ISO 8601 format with Z suffix."""
        ts = entire_ops._parse_timestamp("2026-02-12T14:30:00Z")
        assert ts.year == 2026

    def test_invalid_format_raises_error(self, entire_ops):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError):
            entire_ops._parse_timestamp("not-a-date")


class TestExtractAgentId:
    """Test agent ID extraction."""

    def test_extract_from_name(self, entire_ops):
        """Test extracting agent ID from name."""
        agent_id = entire_ops._extract_agent_id(
            "data-graph-specialist <data@example.com>"
        )
        assert agent_id == "data-graph-specialist"

    def test_convert_spaces_to_dashes(self, entire_ops):
        """Test that spaces are converted to dashes."""
        agent_id = entire_ops._extract_agent_id("Claude Code Agent <code@example.com>")
        assert agent_id == "claude-code-agent"

    def test_lowercase_conversion(self, entire_ops):
        """Test that names are converted to lowercase."""
        agent_id = entire_ops._extract_agent_id(
            "Data-Graph-Specialist <data@example.com>"
        )
        assert agent_id == "data-graph-specialist"

    def test_fallback_to_unknown(self, entire_ops):
        """Test fallback when no valid name found."""
        agent_id = entire_ops._extract_agent_id("")
        assert agent_id == "unknown"


class TestExtractOutcomes:
    """Test outcome bullet extraction."""

    def test_extract_session_summary(self, entire_ops):
        """Test extracting outcomes from Session Summary section."""
        body = """Session Summary (2026-02-12):
✅ Completed schema design
✅ Created 12 indexes
- Performance validation

## Next Section"""
        outcomes = entire_ops._extract_outcomes(body)
        assert len(outcomes) >= 2
        assert "Completed schema design" in outcomes
        assert "Created 12 indexes" in outcomes

    def test_extract_outcomes_section(self, entire_ops):
        """Test extracting from Outcomes section."""
        body = """Outcomes:
- Item 1
- Item 2

## Next"""
        outcomes = entire_ops._extract_outcomes(body)
        assert "Item 1" in outcomes
        assert "Item 2" in outcomes

    def test_strip_emoji(self, entire_ops):
        """Test that emoji are stripped."""
        body = "Outcomes:\n✅ Completed work\n❌ Failed task"
        outcomes = entire_ops._extract_outcomes(body)
        assert any("Completed work" in o for o in outcomes)
        # Emoji should be stripped
        assert not any(o.startswith("✅") for o in outcomes)

    def test_empty_section(self, entire_ops):
        """Test handling empty outcomes section."""
        body = "Session Summary:\n\n## Next"
        outcomes = entire_ops._extract_outcomes(body)
        assert outcomes == []


class TestExtractMetrics:
    """Test metric extraction."""

    def test_extract_coverage_metrics(self, entire_ops):
        """Test extracting coverage metrics."""
        body = """Vault Metrics:
- Papers: 87% (73/84)
- Decisions: 88% (15/17)"""
        metrics = entire_ops._extract_metrics(body)

        assert "papers_coverage" in metrics
        assert metrics["papers_coverage"] == 0.87
        assert metrics["papers_current"] == 73.0
        assert metrics["papers_total"] == 84.0
        assert metrics["decisions_coverage"] == 0.88

    def test_extract_multiple_metrics(self, entire_ops):
        """Test extracting multiple metric lines."""
        body = """Metrics:
- Schema: 100% (5/5)
- Tests: 96% (50/52)"""
        metrics = entire_ops._extract_metrics(body)

        assert metrics["schema_coverage"] == 1.0
        assert metrics["tests_coverage"] == 0.96

    def test_empty_metrics(self, entire_ops):
        """Test handling empty metrics section."""
        body = "Metrics:\n\n## Next"
        metrics = entire_ops._extract_metrics(body)
        assert metrics == {}

    def test_malformed_metrics(self, entire_ops):
        """Test handling malformed metric lines."""
        body = """Metrics:
- Invalid format
- Another: invalid"""
        metrics = entire_ops._extract_metrics(body)
        # Should return empty dict rather than raising error
        assert isinstance(metrics, dict)


class TestExtractTeamStatus:
    """Test team status extraction."""

    def test_extract_team_status(self, entire_ops):
        """Test extracting team status."""
        body = "Team: Ready for Phase 2 launch\nOther info"
        status = entire_ops._extract_team_status(body)
        assert "Ready for Phase 2" in status

    def test_extract_status_label(self, entire_ops):
        """Test extracting Status label."""
        body = "Status: All systems operational"
        status = entire_ops._extract_team_status(body)
        assert "All systems operational" in status

    def test_no_status_found(self, entire_ops):
        """Test default when no status found."""
        body = "Some random content"
        status = entire_ops._extract_team_status(body)
        assert status == "No status recorded"


class TestExtractNextActions:
    """Test next action extraction."""

    def test_extract_next_actions(self, entire_ops):
        """Test extracting next actions."""
        body = """Next Actions:
- Complete Track B implementation
- Deploy to production
- Monitor for issues"""
        actions = entire_ops._extract_next_actions(body)
        assert len(actions) >= 2
        assert "Complete Track B" in actions[0]

    def test_extract_next_steps(self, entire_ops):
        """Test extracting from 'Next Steps' label."""
        body = """Next Steps:
- Step 1
- Step 2"""
        actions = entire_ops._extract_next_actions(body)
        assert "Step 1" in actions

    def test_empty_actions(self, entire_ops):
        """Test empty actions section."""
        body = "Next:\n\n## Done"
        actions = entire_ops._extract_next_actions(body)
        assert actions == []


class TestParseCommitMetadata:
    """Test full commit metadata parsing."""

    def test_parse_valid_commit(self, entire_ops):
        """Test parsing a valid entire.io commit."""
        body = """Session Summary (2026-02-12):
✅ Completed schema design
✅ Created indexes

Vault Metrics:
- Papers: 87% (73/84)
- Decisions: 88% (15/17)

Team: Ready for Phase 2

Next Actions:
- Deploy to production"""

        data = entire_ops.parse_commit_metadata(
            commit_hash="abc123def456",
            commit_author="data-graph-specialist <data@example.com>",
            commit_date="2026-02-12T14:30:00+00:00",
            commit_body=body,
        )

        assert isinstance(data, CommitData)
        assert data.commit_hash == "abc123def456"
        assert data.agent_id == "data-graph-specialist"
        assert len(data.outcomes) >= 1
        assert len(data.metrics) >= 2
        assert "Ready for Phase 2" in data.team_status
        assert len(data.next_actions) >= 1

    def test_minimal_commit(self, entire_ops):
        """Test parsing minimal commit (minimal data)."""
        body = "Simple commit message"

        data = entire_ops.parse_commit_metadata(
            commit_hash="abc123",
            commit_author="test-agent <test@example.com>",
            commit_date="2026-02-12T14:30:00+00:00",
            commit_body=body,
        )

        assert data.commit_hash == "abc123"
        assert data.agent_id == "test-agent"
        # Should not raise error even with minimal data
        assert isinstance(data.outcomes, list)
        assert isinstance(data.metrics, dict)

    def test_invalid_timestamp_raises_error(self, entire_ops):
        """Test that invalid timestamp raises ParsingError."""
        with pytest.raises(ParsingError):
            entire_ops.parse_commit_metadata(
                commit_hash="abc123",
                commit_author="agent <agent@example.com>",
                commit_date="not-a-date",
                commit_body="body",
            )


class TestCommitDataclass:
    """Test CommitData dataclass."""

    def test_commit_data_creation(self):
        """Test creating CommitData instance."""
        data = CommitData(
            commit_hash="abc123",
            timestamp=datetime(2026, 2, 12, 14, 30, tzinfo=UTC),
            agent_id="test-agent",
            outcomes=["outcome1", "outcome2"],
            metrics={"coverage": 0.87},
            team_status="ready",
            next_actions=["action1"],
        )

        assert data.commit_hash == "abc123"
        assert data.agent_id == "test-agent"
        assert len(data.outcomes) == 2
