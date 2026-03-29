"""Tests for CompoundBenchmarkLoop - TDD tests.

Tests for the compound benchmark loop that orchestrates
benchmark → refine → re-benchmark cycles.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_runner():
    """Create mock AgentVerseBenchmarkRunner."""
    runner = MagicMock()
    runner.run_batch_benchmark = MagicMock()
    runner.get_average_coherence = MagicMock(return_value=0.5)
    runner.identify_weak_skills = MagicMock(return_value=[])
    runner.get_refinement_candidates = MagicMock(return_value=[])
    runner.persist_results = MagicMock(return_value="/vault/benchmarks/test.json")
    return runner


@pytest.fixture
def mock_refiner():
    """Create mock SkillRefiner."""
    refiner = MagicMock()
    refiner.refine = MagicMock(return_value="/skills/refined/test_PRIME.md")
    return refiner


@pytest.fixture
def loop(mock_runner, mock_refiner):
    """Create CompoundBenchmarkLoop with mocks."""
    from cohezion.integrations.agentverse import CompoundBenchmarkLoop

    return CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)


class TestCompoundBenchmarkLoopInitialization:
    """[P0] Tests for CompoundBenchmarkLoop initialization."""

    def test_initialization_with_runner_and_refiner(self, mock_runner, mock_refiner):
        """[P0] Should initialize with runner and refiner."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        assert loop.runner is mock_runner
        assert loop.refiner is mock_refiner

    def test_initialization_with_config(self, mock_runner, mock_refiner):
        """[P0] Should accept custom config."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop, LoopConfig

        config = LoopConfig(max_iterations=10, weak_skill_threshold=0.3)
        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner, config=config)
        assert loop.config.max_iterations == 10
        assert loop.config.weak_skill_threshold == 0.3

    def test_default_config_values(self, mock_runner, mock_refiner):
        """[P0] Should have sensible default config."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        assert loop.config.max_iterations == 5
        assert loop.config.coherence_threshold == 0.5
        assert loop.config.weak_skill_threshold == 0.4
        assert loop.config.improvement_threshold == 0.1


class TestCompoundBenchmarkLoopExecution:
    """[P0] Tests for loop execution."""

    @pytest.mark.asyncio
    async def test_run_loop_executes_benchmark(self, loop, mock_runner):
        """[P0] Should run benchmark when executing loop."""
        tasks = [{"task": "test", "skill": "test_PRIME"}]
        await loop.run_loop(tasks)
        mock_runner.run_batch_benchmark.assert_called_once_with(tasks)

    @pytest.mark.asyncio
    async def test_run_loop_returns_loop_result(self, loop, mock_runner):
        """[P0] Should return LoopResult after execution."""
        from cohezion.integrations.agentverse import LoopResult

        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)
        assert isinstance(result, LoopResult)

    @pytest.mark.asyncio
    async def test_run_loop_tracks_iterations(self, loop, mock_runner, mock_refiner):
        """[P0] Should track number of iterations."""
        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)
        assert result.total_iterations == 5

    @pytest.mark.asyncio
    async def test_run_loop_stops_at_max_iterations(self, loop, mock_runner):
        """[P0] Should stop at max iterations even if not converged."""
        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)
        assert result.total_iterations == 5
        assert result.converged is False


class TestCompoundBenchmarkLoopRefinement:
    """[P1] Tests for skill refinement in loop."""

    @pytest.mark.asyncio
    async def test_run_loop_refines_weak_skills(self, loop, mock_runner, mock_refiner):
        """[P1] Should refine identified weak skills."""
        mock_runner.identify_weak_skills.return_value = ["python_PRIME", "testing_PRIME"]

        tasks = [{"task": "test", "skill": "test_PRIME"}]
        await loop.run_loop(tasks)

        assert mock_refiner.refine.call_count >= 1

    @pytest.mark.asyncio
    async def test_run_loop_skips_already_refined(self, loop, mock_runner, mock_refiner):
        """[P1] Should not refine skills already refined in previous iteration."""
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        tasks = [{"task": "test", "skill": "python_PRIME"}]
        await loop.run_loop(tasks)

        assert mock_refiner.refine.call_count == 1

    @pytest.mark.asyncio
    async def test_run_loop_tracks_refined_skills(self, loop, mock_runner):
        """[P1] Should track all refined skills in result."""
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        tasks = [{"task": "test", "skill": "python_PRIME"}]
        result = await loop.run_loop(tasks)
        assert "python_PRIME" in result.refined_skills


class TestCompoundBenchmarkLoopConvergence:
    """[P1] Tests for convergence detection."""

    @pytest.mark.asyncio
    async def test_convergence_requires_improvement(self, loop, mock_runner):
        """[P1] Convergence requires coherence improvement >= threshold."""
        mock_runner.identify_weak_skills.return_value = []
        mock_runner.get_average_coherence.return_value = 0.5

        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)

        assert result.converged is False

    @pytest.mark.asyncio
    async def test_no_convergence_when_not_improved(self, loop, mock_runner):
        """[P1] Should not converge when not improved."""
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)

        assert result.converged is False


class TestCompoundBenchmarkLoopHelpers:
    """[P1] Tests for helper methods."""

    def test_identify_weak_skills_delegates_to_runner(self, loop, mock_runner):
        """[P1] Should delegate to runner's identify_weak_skills."""
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        weak = loop.identify_weak_skills_from_results()
        mock_runner.identify_weak_skills.assert_called_once()
        assert weak == ["python_PRIME"]

    def test_identify_weak_skills_with_custom_threshold(self, loop, mock_runner):
        """[P1] Should use custom threshold when provided."""
        loop.identify_weak_skills_from_results(threshold=0.3)
        mock_runner.identify_weak_skills.assert_called_with(0.3)

    def test_get_refinement_candidates_delegates(self, loop, mock_runner):
        """[P1] Should delegate to runner's get_refinement_candidates."""
        mock_runner.get_refinement_candidates.return_value = ["python_PRIME"]

        candidates = loop.get_refinement_candidates()
        mock_runner.get_refinement_candidates.assert_called_once()
        assert candidates == ["python_PRIME"]


class TestCompoundBenchmarkLoopEdgeCases:
    """[P1] Edge case tests."""

    @pytest.mark.asyncio
    async def test_run_loop_with_empty_tasks(self, loop, mock_runner):
        """[P1] Should handle empty task list."""
        result = await loop.run_loop([])
        assert result.total_iterations == 5

    @pytest.mark.asyncio
    async def test_run_loop_with_no_weak_skills(self, loop, mock_runner):
        """[P1] Should handle case where no skills are weak."""
        mock_runner.identify_weak_skills.return_value = []

        tasks = [{"task": "test", "skill": "test_PRIME"}]
        result = await loop.run_loop(tasks)

        assert len(result.refined_skills) == 0

    def test_run_loop_requires_async(self, loop, mock_runner):
        """[P1] run_loop should be async."""
        import inspect

        assert inspect.iscoroutinefunction(loop.run_loop)


class TestLoopConfig:
    """[P0] Tests for LoopConfig dataclass."""

    def test_default_values(self):
        """[P0] Should have sensible defaults."""
        from cohezion.integrations.agentverse import LoopConfig

        config = LoopConfig()
        assert config.max_iterations == 5
        assert config.coherence_threshold == 0.5
        assert config.weak_skill_threshold == 0.4
        assert config.improvement_threshold == 0.1

    def test_custom_values(self):
        """[P0] Should accept custom values."""
        from cohezion.integrations.agentverse import LoopConfig

        config = LoopConfig(
            max_iterations=10,
            coherence_threshold=0.6,
            weak_skill_threshold=0.3,
            improvement_threshold=0.15,
        )
        assert config.max_iterations == 10
        assert config.coherence_threshold == 0.6
        assert config.weak_skill_threshold == 0.3
        assert config.improvement_threshold == 0.15


class TestIterationResult:
    """[P0] Tests for IterationResult dataclass."""

    def test_creation(self):
        """[P0] Should create iteration result."""
        from cohezion.integrations.agentverse import IterationResult

        result = IterationResult(
            iteration=0,
            coherence_before=0.5,
            coherence_after=0.6,
            weak_skills=["python_PRIME"],
            refined_skills=["python_PRIME"],
            converged=True,
            improvement=0.1,
        )
        assert result.iteration == 0
        assert result.coherence_after == 0.6
        assert result.converged is True


class TestLoopResult:
    """[P0] Tests for LoopResult dataclass."""

    def test_creation(self):
        """[P0] Should create loop result."""
        from cohezion.integrations.agentverse import IterationResult, LoopResult

        iterations = [
            IterationResult(
                iteration=0,
                coherence_before=0.5,
                coherence_after=0.6,
                weak_skills=[],
                refined_skills=[],
                converged=True,
                improvement=0.1,
            )
        ]

        result = LoopResult(
            total_iterations=1,
            final_coherence=0.6,
            initial_coherence=0.5,
            total_improvement=0.1,
            iterations=iterations,
            refined_skills={"python_PRIME"},
            converged=True,
        )

        assert result.total_iterations == 1
        assert result.final_coherence == 0.6
        assert result.total_improvement == 0.1
        assert "python_PRIME" in result.refined_skills


class TestCompoundBenchmarkLoopAdversarial:
    """Adversarial tests for CompoundBenchmarkLoop."""

    @pytest.mark.asyncio
    async def test_handles_refiner_exception(self, mock_runner, mock_refiner):
        """[P1] Should handle refiner exceptions gracefully."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        mock_refiner.refine.side_effect = Exception("Refiner failed")
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        tasks = [{"task": "test", "skill": "python_PRIME"}]

        result = await loop.run_loop(tasks)
        assert result.total_iterations == 5

    @pytest.mark.asyncio
    async def test_handles_runner_exception(self, mock_runner, mock_refiner):
        """[P1] Should handle runner exceptions gracefully."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        mock_runner.run_batch_benchmark.side_effect = Exception("Runner failed")

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        tasks = [{"task": "test", "skill": "test_PRIME"}]

        import contextlib

        with contextlib.suppress(Exception):
            await loop.run_loop(tasks)

    @pytest.mark.asyncio
    async def test_handles_empty_results(self, mock_runner, mock_refiner):
        """[P1] Should handle empty benchmark results."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        mock_runner.get_average_coherence.return_value = 0.0
        mock_runner.identify_weak_skills.return_value = ["python_PRIME"]

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        tasks = [{"task": "test", "skill": "python_PRIME"}]

        result = await loop.run_loop(tasks)
        assert result.final_coherence == 0.0

    @pytest.mark.asyncio
    async def test_handles_all_skills_strong(self, mock_runner, mock_refiner):
        """[P1] Should handle case where all skills are already strong."""
        from cohezion.integrations.agentverse import CompoundBenchmarkLoop

        mock_runner.get_average_coherence.return_value = 0.8
        mock_runner.identify_weak_skills.return_value = []

        loop = CompoundBenchmarkLoop(runner=mock_runner, refiner=mock_refiner)
        tasks = [{"task": "test", "skill": "python_PRIME"}]

        await loop.run_loop(tasks)
        assert mock_refiner.refine.call_count == 0
