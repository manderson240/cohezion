"""Comprehensive tests for ResearchAgent.

P0 coverage for research module.
Generated following elegant simplification patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.research import (
    CodeChange,
    ExperimentResult,
    MultiAgentResearchConfig,
    ResearchAgent,
    ResearchConfig,
    ResearchSecurityGuardrails,
    SimpleMultiAgent,
)


class TestResearchConfig:
    """[P0] Tests for ResearchConfig."""

    def test_default_values(self):
        """[P0] Should have sensible defaults."""
        config = ResearchConfig()

        assert config.experiment_time_budget == 300.0
        assert config.max_experiments == 100
        assert config.model_depth == 8
        assert config.vocab_size == 8192

    def test_custom_config(self):
        """[P0] Should accept custom values."""
        config = ResearchConfig(
            experiment_time_budget=600.0,
            max_experiments=50,
            model_depth=16,
        )

        assert config.experiment_time_budget == 600.0
        assert config.max_experiments == 50
        assert config.model_depth == 16

    def test_experiment_result_to_dict(self):
        """[P0] Should convert ExperimentResult to dict."""
        result = ExperimentResult(
            experiment_id="exp-1",
            timestamp="2026-03-09T00:00:00",
            metric_value=2.5,
            metric_name="val_bpb",
            improved=True,
            code_changes=["line1", "line2"],
            duration_seconds=300.0,
        )

        data = result.to_dict()

        assert data["experiment_id"] == "exp-1"
        assert data["metric_value"] == 2.5
        assert data["improved"] is True


class TestResearchAgent:
    """[P0] Tests for ResearchAgent."""

    def test_initializes_with_defaults(self):
        """[P0] Should initialize with defaults."""
        agent = ResearchAgent()

        assert agent.config is not None
        assert agent.session is not None
        assert agent.executor is not None

    def test_initializes_with_custom_config(self, data_temp_dir):
        """[P0] Should accept custom config."""
        config = ResearchConfig(
            experiment_log=data_temp_dir / "experiments.jsonl",
            max_experiments=10,
        )
        agent = ResearchAgent(config=config)

        assert agent.config.max_experiments == 10

    def test_get_best_result_empty(self):
        """[P0] Should return None when no experiments."""
        agent = ResearchAgent()

        result = agent.get_best_result()

        assert result is None

    def test_get_best_result_with_data(self):
        """[P0] Should return best result."""
        agent = ResearchAgent()
        agent.session.best_metric = 2.5
        agent.session.experiments_completed = 10

        result = agent.get_best_result()

        assert result is not None
        assert result["metric"] == 2.5
        assert result["experiments"] == 10

    def test_stop_session(self):
        """[P0] Should stop session gracefully."""
        agent = ResearchAgent()

        agent.stop()

        assert agent.session.active is False


class TestResearchSecurityGuardrails:
    """[P0] Tests for security guardrails."""

    def test_validates_safe_code(self):
        """[P0] Should validate safe code."""
        guardrails = ResearchSecurityGuardrails()

        safe_code = """
def train(model, data):
    loss = model(data)
    return loss
"""
        change = CodeChange(
            file_path=Path("train.py"),
            old_code="",
            new_code=safe_code,
            change_type="modify",
        )

        result = guardrails.validate_change(change)

        assert result.is_valid is True
        assert result.risk_level == "low"

    def test_detects_forbidden_pattern(self):
        """[P0] Should detect forbidden patterns."""
        guardrails = ResearchSecurityGuardrails()

        dangerous_code = """
import os
os.system("rm -rf /")
"""
        change = CodeChange(
            file_path=Path("train.py"),
            old_code="",
            new_code=dangerous_code,
            change_type="modify",
        )

        result = guardrails.validate_change(change)

        assert result.is_valid is False
        # Guardrail detects 'os' as a forbidden import (which subsumes os.system)
        assert any("os" in issue for issue in result.issues)

    def test_detects_invalid_ast(self):
        """[P0] Should detect invalid Python."""
        guardrails = ResearchSecurityGuardrails()

        invalid_code = "def train(:\n  pass"

        change = CodeChange(
            file_path=Path("train.py"),
            old_code="",
            new_code=invalid_code,
            change_type="modify",
        )

        result = guardrails.validate_change(change)

        assert result.is_valid is False
        assert "Invalid Python syntax" in result.issues

    def test_detects_dangerous_operations(self):
        """[P0] Should detect dangerous operations."""
        guardrails = ResearchSecurityGuardrails()

        dangerous_code = """
import socket
sock = socket.socket()
sock.connect(("localhost", 8080))
"""
        change = CodeChange(
            file_path=Path("train.py"),
            old_code="",
            new_code=dangerous_code,
            change_type="modify",
        )

        result = guardrails.validate_change(change)

        assert "Network operations" in str(result.issues)


class TestMultiAgentResearch:
    """[P0] Tests for multi-agent research."""

    def test_multi_agent_config_defaults(self):
        """[P0] Should have default config."""
        config = MultiAgentResearchConfig()

        assert config.num_agents == 3
        assert config.experiments_per_agent == 33
        assert config.agent_diversity == "high"

    def test_multi_agent_result_structure(self):
        """[P0] Should track multi-agent results."""
        from cohezion.research import MultiAgentResult

        result = MultiAgentResult(
            experiments_completed=100,
            best_metric=2.5,
        )

        assert result.experiments_completed == 100
        assert result.best_metric == 2.5


class TestSimpleMultiAgent:
    """[P0] Tests for SimpleMultiAgent."""

    @pytest.mark.asyncio()
    async def test_runs_tasks_across_agents(self):
        """[P0] Should distribute tasks across agents."""
        multi = SimpleMultiAgent(num_agents=2)

        # Mock agents
        executed = []

        async def mock_executor(task):
            executed.append(task.id)
            return {"success": True}

        multi.add_agent("agent-1", mock_executor)
        multi.add_agent("agent-2", mock_executor)

        from cohezion.compound.models import Task

        tasks = [
            Task(id="t1", description="", skill_name="", operation_type=""),
            Task(id="t2", description="", skill_name="", operation_type=""),
        ]

        results = await multi.run(tasks)

        assert len(results) == 2
        assert "t1" in executed
        assert "t2" in executed


class TestResearchIntegration:
    """[P0] Integration tests."""

    def test_full_research_workflow_mocked(self, data_temp_dir):
        """[P0] Should complete research workflow."""
        config = ResearchConfig(
            experiment_log=data_temp_dir / "experiments.jsonl",
            max_experiments=2,
            experiment_time_budget=10.0,  # Minimum valid value (10s–24h)
        )

        agent = ResearchAgent(config=config)

        # Mock training execution to be fast
        def fast_train(task, context):
            return ("done", {"metric": 2.0, "duration": 1.0})

        agent.executor.execute_fn = fast_train

        # Run session (synchronous method)
        session = agent.run_session(max_experiments=2)

        assert session.experiments_completed == 2


# Test coverage summary
# Total tests: 16
# P0: 16
# Expected pass rate: 100%
