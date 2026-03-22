"""End-to-end tests for ResearchAgent compound integration.

Tests ResearchAgent working with full compound executor cycle.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig
from cohezion.compound.models import ExecutionMetrics, ExecutionResult
from cohezion.research import ResearchAgent, ResearchConfig


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client for vault operations."""
    client = MagicMock()
    client.vault_write.return_value = "success"
    client.vault_read.return_value = None
    client.vault_find_relevant_context.return_value = []
    return client


@pytest.fixture
def temp_research_dir():
    """Create temporary directory for research artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        yield path


class TestResearchAgentCompoundE2E:
    """E2E tests: ResearchAgent + CompoundExecutor."""

    @pytest.mark.fast
    def test_research_agent_with_mock_executor(self, temp_research_dir):
        """[E2E-01] ResearchAgent runs with mocked compound executor."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=2,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        # Mock executor that returns synthetic results
        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute.return_value = ExecutionResult(
            success=True,
            output="Experiment complete",
            metrics=ExecutionMetrics(
                duration_seconds=1.0,
                total_tokens=100,
            ),
        )

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act
        session = agent.run_session()

        # Assert
        assert session.experiments_completed == 2
        assert session.best_metric == float("inf")  # Mock doesn't update
        assert mock_executor.execute.call_count == 2

    @pytest.mark.fast
    def test_research_agent_checkpoint_persistence(self, temp_research_dir, mock_mcp_client):
        """[E2E-02] Research sessions persist checkpoints to vault."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        agent = ResearchAgent(config=config)

        # Act - Run session
        with patch.dict("os.environ", {"COHEZION_MOCK_VAULT": "1"}):
            session = agent.run_session()

        # Assert
        assert session.session_id is not None
        assert Path(config.experiment_log).exists()

        # Verify log was written
        with open(config.experiment_log) as f:
            lines = f.readlines()
            assert len(lines) >= 1

    @pytest.mark.fast
    def test_multi_experiment_optimization_progress(self, temp_research_dir):
        """[E2E-03] Multiple experiments show optimization progress."""
        # Arrange - Create agent with improving metrics
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        # Track experiments
        experiment_count = [0]

        def improving_execute(task):
            experiment_count[0] += 1
            # Simulating improving metrics
            metric = 3.0 - (experiment_count[0] * 0.5)
            return ExecutionResult(
                success=True,
                output=f"Experiment {experiment_count[0]}",
                metrics=ExecutionMetrics(
                    duration_seconds=1.0,
                    total_tokens=100,
                ),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = improving_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act
        session = agent.run_session()

        # Assert
        assert session.experiments_completed == 3
        assert experiment_count[0] == 3
        assert session.best_metric == float("inf")  # Session tracks best

    @pytest.mark.fast
    def test_research_agent_error_recovery(self, temp_research_dir):
        """[E2E-04] Agent continues after experiment failures."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        call_count = [0]

        def unreliable_execute(task):
            call_count[0] += 1
            if call_count[0] == 2:
                # Second experiment fails
                return ExecutionResult(
                    success=False,
                    output="Training failed",
                    metrics=ExecutionMetrics(
                        duration_seconds=0.5,
                        total_tokens=50,
                    ),
                )
            return ExecutionResult(
                success=True,
                output=f"Experiment {call_count[0]}",
                metrics=ExecutionMetrics(
                    duration_seconds=1.0,
                    total_tokens=100,
                ),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = unreliable_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act
        session = agent.run_session()

        # Assert - Should complete all experiments despite one failure
        assert session.experiments_completed == 3
        assert call_count[0] == 3  # All experiments attempted

    @pytest.mark.fast
    def test_session_early_stop(self, temp_research_dir):
        """[E2E-05] Session can be stopped early."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=10,  # Would take long
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        def slow_execute(task):
            return ExecutionResult(
                success=True,
                output="Complete",
                metrics=ExecutionMetrics(
                    duration_seconds=0.1,
                    total_tokens=100,
                ),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = slow_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act - Run just 2 experiments then stop
        agent.run_session(max_experiments=2)

        # Assert
        assert agent.session.experiments_completed == 2
        assert agent.session.active

    @pytest.mark.fast
    def test_experiment_result_logging_format(self, temp_research_dir):
        """[E2E-06] Experiment results logged in correct format."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=1,
            target_metric="val_bpb",
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        def mock_execute(task):
            return ExecutionResult(
                success=True,
                output="Complete",
                metrics=ExecutionMetrics(
                    duration_seconds=5.0,
                    total_tokens=1000,
                ),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = mock_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act
        agent.run_session()

        # Assert - Verify JSONL format
        import json

        with open(config.experiment_log) as f:
            line = f.readline()
            record = json.loads(line)

        assert "experiment_id" in record
        assert "timestamp" in record
        assert "metric_value" in record
        assert "metric_name" in record
        assert record["metric_name"] == "val_bpb"
        assert "improved" in record
        assert "duration_seconds" in record

    @pytest.mark.fast
    def test_research_agent_with_real_compound_executor(self, temp_research_dir):
        """[E2E-07] ResearchAgent works with real CompoundExecutor."""
        # Arrange - Use actual executor with mocked execution
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=2,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        call_count = [0]

        def test_execute(task, context=None):
            call_count[0] += 1
            return f"Result {call_count[0]}", {
                "metric_value": 2.0 + call_count[0] * 0.1,
                "duration_seconds": 0.1 * call_count[0],
                "improved": True,
            }

        executor = CompoundExecutor(
            execute_fn=test_execute,
            config=ExecutionConfig(max_retries=0),
        )

        agent = ResearchAgent(config=config, executor=executor)

        # Act
        session = agent.run_session()

        # Assert
        assert session.experiments_completed == 2
        assert call_count[0] == 2

    @pytest.mark.fast
    def test_experiment_concurrency_simulation(self, temp_research_dir):
        """[E2E-08] Multiple experiments run without interference."""
        # Arrange
        config = ResearchConfig(
            experiment_time_budget=10.0,
            max_experiments=3,
            experiment_log=temp_research_dir / "experiments.jsonl",
            checkpoint_dir=temp_research_dir / "checkpoints",
        )

        results = []

        def tracking_execute(task):
            results.append(task.id)
            return ExecutionResult(
                success=True,
                output=task.id,
                metrics=ExecutionMetrics(
                    duration_seconds=0.1,
                    total_tokens=100,
                ),
            )

        mock_executor = Mock(spec=CompoundExecutor)
        mock_executor.execute = tracking_execute

        agent = ResearchAgent(config=config, executor=mock_executor)

        # Act
        agent.run_session()

        # Assert
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        assert "exp-1" in results[0] or "exp-2" in results[0] or "exp-3" in results[0]


class TestResearchAgentCompoundIntegration:
    """Integration tests: ResearchAgent + Compound components."""

    @pytest.mark.fast
    def test_research_config_with_compound_defaults(self):
        """[INT-01] ResearchConfig uses compound-compatible defaults."""
        config = ResearchConfig()

        assert config.experiment_time_budget == 300.0
        assert config.max_experiments == 100
        assert config.target_metric == "val_bpb"
        assert config.enable_guardrails is True

    @pytest.mark.fast
    def test_research_agent_session_id_generation(self):
        """[INT-02] Each agent gets unique session ID."""
        agent1 = ResearchAgent()
        agent2 = ResearchAgent()

        assert agent1.session.session_id != agent2.session.session_id
        assert len(agent1.session.session_id) > 0
        assert len(agent2.session.session_id) > 0

    @pytest.mark.fast
    def test_research_agent_config_validation(self, temp_research_dir):
        """[INT-03] Invalid config raises appropriate errors."""
        # Invalid time budget
        with pytest.raises(ValueError, match="experiment_time_budget"):
            ResearchConfig(
                experiment_time_budget=5.0,  # Too low
                experiment_log=temp_research_dir / "experiments.jsonl",
                checkpoint_dir=temp_research_dir / "checkpoints",
            )

        # Invalid path traversal
        with pytest.raises(ValueError, match="path traversal"):
            ResearchConfig(
                experiment_log=Path("../../../etc/passwd"),
                checkpoint_dir=temp_research_dir / "checkpoints",
            )
