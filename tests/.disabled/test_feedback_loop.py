"""Tests for compound feedback loop, models, and persistence."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from cohezion.compound.executor import CompoundExecutionResult, CompoundExecutor
from cohezion.compound.feedback_loop import CompoundFeedbackLoop
from cohezion.compound.models import CompoundCycleReport, CompoundCycleResult
from cohezion.compound.persistence import CompoundPersistence

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Mock token client
# ---------------------------------------------------------------------------


class _MockTokenClient:
    """Mock TokenEfficientClient that returns canned responses."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return "mock output"

    def get_metrics(self) -> dict[str, Any]:
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_hit_rate": 0.0,
            "tokens_saved": 0,
            "total_calls": 0,
            "model_usage": {},
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_executor() -> CompoundExecutor:
    """Return a CompoundExecutor wired to a mock token client."""
    return CompoundExecutor(token_client=_MockTokenClient())


@pytest.fixture()
def tmp_persistence(tmp_path: Path) -> CompoundPersistence:
    """Return a CompoundPersistence backed by a temporary JSONL directory."""
    return CompoundPersistence(jsonl_dir=tmp_path / "cycles")


@pytest.fixture()
def _reset_metrics() -> None:
    """Reset the metrics singleton before and after each test."""
    from cohezion.compound.metrics import reset_collector

    reset_collector()
    yield  # type: ignore[misc]
    reset_collector()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    """Tests for Pydantic models."""

    def test_cycle_result_defaults(self) -> None:
        result = CompoundCycleResult(skill_name="test_skill", input_text="hello")
        assert result.skill_name == "test_skill"
        assert result.input_text == "hello"
        assert result.execution_output == ""
        assert result.execution_tokens == 0
        assert result.compound_score_delta == 0.0
        assert result.patterns == []
        assert result.refinements_applied == 0
        assert result.model_usage == {}

    def test_cycle_result_full(self) -> None:
        result = CompoundCycleResult(
            skill_name="skill_a",
            input_text="input",
            execution_output="output",
            execution_tokens=100,
            execution_duration_ms=50.5,
            compound_score_delta=0.75,
            patterns=["pattern1"],
            refinements_applied=2,
            version_before="1.0",
            version_after="1.1",
            model_usage={"phi3:mini": 3},
        )
        assert result.execution_tokens == 100
        assert result.model_usage["phi3:mini"] == 3

    def test_cycle_result_serialization(self) -> None:
        result = CompoundCycleResult(skill_name="s", input_text="i", patterns=["p1", "p2"])
        data = result.model_dump()
        assert data["skill_name"] == "s"
        assert len(data["patterns"]) == 2
        roundtrip = CompoundCycleResult.model_validate(data)
        assert roundtrip == result

    def test_cycle_report_defaults(self) -> None:
        report = CompoundCycleReport(skill_name="test_skill")
        assert report.total_cycles == 0
        assert report.cycles == []
        assert report.final_compound_score_delta == 0.0

    def test_cycle_report_with_cycles(self) -> None:
        c1 = CompoundCycleResult(skill_name="s", input_text="i", execution_tokens=10)
        c2 = CompoundCycleResult(skill_name="s", input_text="i2", execution_tokens=20)
        report = CompoundCycleReport(
            skill_name="s",
            cycles=[c1, c2],
            total_cycles=2,
            total_tokens=30,
        )
        assert report.total_cycles == 2
        assert report.total_tokens == 30


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for JSONL persistence."""

    @pytest.mark.asyncio()
    async def test_persistence_jsonl_save_and_load(self, tmp_path: Path) -> None:
        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        # Force JSONL by setting surreal unavailable
        persistence._surreal_available = False

        record_id = await persistence.save_cycle("test_skill", {"tokens": 42, "output": "hello"})
        assert record_id.startswith("jsonl:test_skill:")

        history = await persistence.load_history("test_skill", limit=5)
        assert len(history) == 1
        assert history[0]["tokens"] == 42
        assert history[0]["skill_name"] == "test_skill"

    @pytest.mark.asyncio()
    async def test_persistence_jsonl_multiple_records(self, tmp_path: Path) -> None:
        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        for i in range(5):
            await persistence.save_cycle("skill_a", {"index": i})

        history = await persistence.load_history("skill_a", limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0]["index"] == 4
        assert history[2]["index"] == 2

    @pytest.mark.asyncio()
    async def test_persistence_load_empty(self, tmp_path: Path) -> None:
        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        history = await persistence.load_history("nonexistent", limit=5)
        assert history == []

    @pytest.mark.asyncio()
    async def test_persistence_special_characters(self, tmp_path: Path) -> None:
        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        await persistence.save_cycle("my/skill name", {"data": 1})
        history = await persistence.load_history("my/skill name", limit=5)
        assert len(history) == 1


# ---------------------------------------------------------------------------
# Feedback loop tests
# ---------------------------------------------------------------------------


def _make_mock_exec_result(
    skill_name: str = "test_skill",
    output: str = "generated output",
    tokens: int = 50,
    duration_ms: float = 100.0,
) -> CompoundExecutionResult:
    """Build a CompoundExecutionResult with sensible defaults."""
    return CompoundExecutionResult(
        skill_name=skill_name,
        final_output=output,
        steps=[
            {
                "step_index": 0,
                "operation": "generate",
                "description": "Generate code",
                "output": output,
                "tokens_used": tokens,
                "duration_ms": duration_ms,
                "model": "phi3:mini",
            }
        ],
        total_tokens=tokens,
        total_duration_ms=duration_ms,
        model_usage={"phi3:mini": 1},
    )


class TestFeedbackLoop:
    """Tests for CompoundFeedbackLoop."""

    @pytest.mark.asyncio()
    async def test_single_cycle(self, mock_executor: CompoundExecutor, tmp_path: Path) -> None:
        exec_result = _make_mock_exec_result()
        mock_executor.execute_skill = AsyncMock(return_value=exec_result)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        result = await loop.run_cycle("test_skill", "analyze this code")

        assert isinstance(result, CompoundCycleResult)
        assert result.skill_name == "test_skill"
        assert result.input_text == "analyze this code"
        assert result.execution_output == "generated output"
        assert result.execution_tokens == 50
        assert result.compound_score_delta > 0.0
        mock_executor.execute_skill.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_multi_cycle(self, mock_executor: CompoundExecutor, tmp_path: Path) -> None:
        exec_result = _make_mock_exec_result()
        mock_executor.execute_skill = AsyncMock(return_value=exec_result)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        report = await loop.run_multi_cycle("test_skill", "initial input", cycles=3)

        assert isinstance(report, CompoundCycleReport)
        assert report.total_cycles == 3
        assert len(report.cycles) == 3
        assert report.total_tokens == 150  # 50 * 3
        assert report.skill_name == "test_skill"
        assert mock_executor.execute_skill.await_count == 3

    @pytest.mark.asyncio()
    async def test_no_refinements_case(
        self, mock_executor: CompoundExecutor, tmp_path: Path
    ) -> None:
        """When all tasks succeed and no patterns trigger refinements."""
        exec_result = _make_mock_exec_result(tokens=50)
        mock_executor.execute_skill = AsyncMock(return_value=exec_result)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        result = await loop.run_cycle("test_skill", "input")

        # With tokens > 0 and all tasks completed, the "All tasks succeeded"
        # pattern fires but does not trigger any refinement suggestions
        # (no "failed" or "zero tokens" in that pattern text).
        assert result.refinements_applied == 0

    @pytest.mark.asyncio()
    @pytest.mark.usefixtures("_reset_metrics")
    async def test_feedback_loop_with_metrics(
        self, mock_executor: CompoundExecutor, tmp_path: Path
    ) -> None:
        """Verify that metrics collector gets called during a cycle."""
        exec_result = _make_mock_exec_result()
        mock_executor.execute_skill = AsyncMock(return_value=exec_result)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        await loop.run_cycle("test_skill", "input")

        from cohezion.compound.metrics import get_collector

        collector = get_collector()
        assert collector.total_executions == 1
        assert collector.total_cycles == 1
        assert collector.total_tokens() == 50

    @pytest.mark.asyncio()
    async def test_cycle_persists_to_jsonl(
        self, mock_executor: CompoundExecutor, tmp_path: Path
    ) -> None:
        """Verify that cycle results are persisted to JSONL."""
        exec_result = _make_mock_exec_result()
        mock_executor.execute_skill = AsyncMock(return_value=exec_result)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        await loop.run_cycle("test_skill", "input")

        history = await persistence.load_history("test_skill", limit=5)
        assert len(history) == 1
        assert history[0]["skill_name"] == "test_skill"
        assert history[0]["execution_tokens"] == 50

    @pytest.mark.asyncio()
    async def test_multi_cycle_feeds_output_forward(
        self, mock_executor: CompoundExecutor, tmp_path: Path
    ) -> None:
        """Verify that each cycle's output becomes the next cycle's input."""
        call_count = 0

        async def _varying_execute(
            skill_name: str, input_text: str, model: str | None = None
        ) -> CompoundExecutionResult:
            nonlocal call_count
            call_count += 1
            return _make_mock_exec_result(output=f"output_{call_count}")

        mock_executor.execute_skill = AsyncMock(side_effect=_varying_execute)

        persistence = CompoundPersistence(jsonl_dir=tmp_path / "cycles")
        persistence._surreal_available = False

        loop = CompoundFeedbackLoop(
            executor=mock_executor,
            persistence=persistence,
        )

        report = await loop.run_multi_cycle("test_skill", "initial", cycles=3)

        # Each cycle should have received the previous output
        calls = mock_executor.execute_skill.call_args_list
        assert calls[0].args[1] == "initial"
        assert calls[1].args[1] == "output_1"
        assert calls[2].args[1] == "output_2"
        assert report.cycles[-1].execution_output == "output_3"
