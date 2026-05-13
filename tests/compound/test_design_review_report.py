"""Tests for Design Review Report (DRR) generator.

Verifies V-Model gate reports are deterministic, hashable, and correct.
"""

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.compound.design_review_report import (
    DRRGenerator,
    Finding,
    FindingSeverity,
    GateLevel,
)


@pytest.fixture
def generator():
    return DRRGenerator()


@pytest.fixture
def left_artifact(tmp_path):
    f = tmp_path / "plan.md"
    f.write_text("# Plan\n\nImplement feature X with tests.")
    return str(f)


@pytest.fixture
def right_artifact(tmp_path):
    f = tmp_path / "test_plan.py"
    f.write_text("def test_feature_x():\n    assert True\n")
    return str(f)


class TestDRRGenerator:
    """Test DRR generation at V-Model gates."""

    @pytest.mark.unit
    def test_generate_passing_drr(self, generator, left_artifact, right_artifact):
        """DRR with valid artifacts should pass."""
        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="test-session",
            left_artifact=left_artifact,
            right_artifact=right_artifact,
        )
        assert report.passed is True
        assert report.critical_count == 0
        assert report.gate == GateLevel.PLAN

    @pytest.mark.unit
    def test_missing_left_artifact_fails(self, generator, right_artifact):
        """Missing left artifact produces critical finding."""
        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="test-session",
            left_artifact="/nonexistent/plan.md",
            right_artifact=right_artifact,
        )
        assert report.passed is False
        assert report.critical_count >= 1
        assert any(f.category == "missing_artifact" for f in report.findings)

    @pytest.mark.unit
    def test_missing_right_artifact_fails(self, generator, left_artifact):
        """Missing right artifact produces critical finding."""
        report = generator.generate(
            gate=GateLevel.IMPLEMENTATION,
            session_id="test-session",
            left_artifact=left_artifact,
            right_artifact="/nonexistent/test.py",
        )
        assert report.passed is False
        assert report.critical_count >= 1

    @pytest.mark.unit
    def test_empty_artifact_high_severity(self, generator, tmp_path):
        """Empty artifact produces high severity finding."""
        left = tmp_path / "empty.md"
        left.write_text("")
        right = tmp_path / "test.py"
        right.write_text("def test_x():\n    assert 1 == 1\n")

        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="test",
            left_artifact=str(left),
            right_artifact=str(right),
        )
        assert any(f.category == "empty_artifact" for f in report.findings)

    @pytest.mark.unit
    def test_drr3_checks_assertions(self, generator, tmp_path):
        """DRR-3 gate checks for assertions in test file."""
        left = tmp_path / "code.py"
        left.write_text("def hello(): return 'world'")
        right = tmp_path / "test_code.py"
        right.write_text("# No tests here\npass\n")

        report = generator.generate(
            gate=GateLevel.IMPLEMENTATION,
            session_id="test",
            left_artifact=str(left),
            right_artifact=str(right),
        )
        assert any(f.category == "no_assertions" for f in report.findings)
        assert any(f.category == "no_test_functions" for f in report.findings)

    @pytest.mark.unit
    def test_report_hash_deterministic(self, generator, left_artifact, right_artifact):
        """Same inputs produce same report hash."""
        r1 = generator.generate(GateLevel.PLAN, "s1", left_artifact, right_artifact)
        r2 = generator.generate(GateLevel.PLAN, "s1", left_artifact, right_artifact)
        assert r1.report_hash == r2.report_hash

    @pytest.mark.unit
    def test_report_hash_changes_with_content(self, generator, tmp_path):
        """Different artifact content produces different report hash."""
        left1 = tmp_path / "v1.md"
        left1.write_text("version 1")
        left2 = tmp_path / "v2.md"
        left2.write_text("version 2")
        right = tmp_path / "test.py"
        right.write_text("def test_x():\n    assert True\n")

        r1 = generator.generate(GateLevel.PLAN, "s1", str(left1), str(right))
        r2 = generator.generate(GateLevel.PLAN, "s1", str(left2), str(right))
        assert r1.report_hash != r2.report_hash

    @pytest.mark.unit
    def test_summary_format(self, generator, left_artifact, right_artifact):
        """Summary is concise and contains gate level."""
        report = generator.generate(GateLevel.PLAN, "s1", left_artifact, right_artifact)
        assert "DRR-1" in report.summary
        assert "PASS" in report.summary or "FAIL" in report.summary

    @pytest.mark.unit
    def test_surql_params(self, generator, left_artifact, right_artifact):
        """SurrealDB params contain all required fields."""
        report = generator.generate(GateLevel.PLAN, "s1", left_artifact, right_artifact)
        params = report.to_surql_params()

        assert params["gate_id"] == "DRR-1"
        assert params["level"] == "plan"
        assert params["session_id"] == "s1"
        assert len(params["artifact_hash"]) == 64  # SHA-256
        assert len(params["test_hash"]) == 64
        assert isinstance(params["passed"], bool)
        assert isinstance(params["findings_json"], list)

    @pytest.mark.unit
    def test_identical_artifacts_detected(self, generator, tmp_path):
        """Identical left and right artifacts produce medium finding."""
        f = tmp_path / "same.py"
        f.write_text("content")

        report = generator.generate(GateLevel.PLAN, "s1", str(f), str(f))
        assert any(f.category == "identical_artifacts" for f in report.findings)


class TestDRRPersist:
    """Test DRRGenerator.persist() method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_persist_with_mock_client(self, generator, left_artifact, right_artifact):
        """persist() calls surreal_client.query with correct params."""
        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="session-persist-test",
            left_artifact=left_artifact,
            right_artifact=right_artifact,
        )
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(return_value=[{}])

        result = await generator.persist(report, surreal_client=mock_client)

        assert result is True
        mock_client.query.assert_awaited_once()
        call_args = mock_client.query.call_args
        # First positional arg is the query string
        query_str = call_args[0][0]
        assert "vmodel_gate" in query_str
        assert "CREATE" in query_str
        # Second positional arg is the params dict
        params = call_args[0][1]
        assert params["gate_id"] == "DRR-1"
        assert params["session_id"] == "session-persist-test"
        assert isinstance(params["passed"], bool)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_persist_graceful_failure(self, generator, left_artifact, right_artifact):
        """persist() returns False when client raises an exception."""
        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="session-fail-test",
            left_artifact=left_artifact,
            right_artifact=right_artifact,
        )
        mock_client = AsyncMock()
        mock_client.query = AsyncMock(side_effect=RuntimeError("connection refused"))

        result = await generator.persist(report, surreal_client=mock_client)

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_persist_no_client_available(self, generator, left_artifact, right_artifact):
        """persist() returns False when no client provided and import fails."""
        import sys

        report = generator.generate(
            gate=GateLevel.PLAN,
            session_id="session-no-client",
            left_artifact=left_artifact,
            right_artifact=right_artifact,
        )
        # Remove the surreal_client module from sys.modules so the lazy import
        # inside persist() triggers an ImportError, exercising the fallback path.
        module_key = "cohezion.persistence.surreal_client"
        original = sys.modules.pop(module_key, None)
        try:
            with patch("builtins.__import__", side_effect=ImportError("surreal_client unavailable")):
                result = await generator.persist(report, surreal_client=None)
        finally:
            if original is not None:
                sys.modules[module_key] = original

        assert result is False


class TestFinding:
    """Test Finding dataclass."""

    @pytest.mark.unit
    def test_finding_is_frozen(self):
        """Findings are immutable."""
        f = Finding(FindingSeverity.HIGH, "test", "desc")
        with pytest.raises(AttributeError):
            f.severity = FindingSeverity.LOW  # type: ignore[misc]


class TestGateLevel:
    """Test gate level enum."""

    @pytest.mark.unit
    def test_all_gates_defined(self):
        assert GateLevel.INTENT.value == "DRR-0"
        assert GateLevel.PLAN.value == "DRR-1"
        assert GateLevel.ARCHITECTURE.value == "DRR-2"
        assert GateLevel.IMPLEMENTATION.value == "DRR-3"
