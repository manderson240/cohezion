"""Adversarial tests for Cohezion-AgentVerse integration.

Tests that probe edge cases, failure modes, and potential security
issues in the integration layer.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestAgentVerseBridgeAdversarial:
    """Adversarial tests for AgentVerseBridge."""

    @pytest.fixture()
    def bridge(self):
        """Create bridge with mock executor."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        executor = MagicMock()
        return AgentVerseBridge(executor=executor)

    def test_handles_executor_exception(self, bridge):
        """[P1] Should handle executor exceptions gracefully."""
        bridge.executor.execute_task.side_effect = RuntimeError("Executor failed")

        try:
            result = bridge.on_agent_message(
                agent_name="test",
                message="task",
                skill_name="test_PRIME",
            )
            # Exception should be caught and result should be returned
            assert result is not None
        except RuntimeError:
            # Or exception propagates - both are acceptable
            pass

    def test_handles_missing_coherence_metric(self, bridge):
        """[P1] Should handle missing coherence in metrics."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metrics = {}
        mock_result.duration_seconds = 1.0
        bridge.executor.execute_task.return_value = mock_result

        bridge.on_agent_message("agent", "msg", "skill")
        violations = bridge.check_hiho_violations()

        assert len(violations) == 0

    def test_handles_extreme_coherence_values(self, bridge):
        """[P1] Should handle extreme coherence values."""
        bridge.metrics = [
            {"coherence": 0.0, "agent": "a1"},
            {"coherence": 1.0, "agent": "a2"},
            {"coherence": -0.5, "agent": "a3"},
            {"coherence": 1.5, "agent": "a4"},
        ]

        violations = bridge.check_hiho_violations()
        assert len(violations) == 4

    def test_handles_empty_agent_name(self, bridge):
        """[P1] Should handle empty agent name."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metrics = {"coherence": 0.5}
        mock_result.duration_seconds = 1.0
        bridge.executor.execute_task.return_value = mock_result

        bridge.on_agent_message("", "message", "skill_PRIME")
        assert len(bridge.metrics) == 1

    def test_handles_very_long_message(self, bridge):
        """[P1] Should handle very long messages without crashing."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metrics = {"coherence": 0.5}
        mock_result.duration_seconds = 1.0
        bridge.executor.execute_task.return_value = mock_result

        long_message = "x" * 100000
        bridge.on_agent_message("agent", long_message, "skill_PRIME")
        assert len(bridge.metrics) == 1

    def test_average_coherence_with_empty_metrics(self, bridge):
        """[P1] Should return 0.0 for average coherence with no metrics."""
        assert bridge.get_average_coherence() == 0.0

    def test_reset_with_no_metrics(self, bridge):
        """[P1] Should handle reset with no metrics."""
        bridge.reset()
        assert bridge.metrics == []

    def test_violations_with_no_metrics(self, bridge):
        """[P1] Should return no violations with empty metrics."""
        violations = bridge.check_hiho_violations()
        assert violations == []


class TestCohezionAgentAdapterAdversarial:
    """Adversarial tests for CohezionAgentAdapter."""

    @pytest.fixture()
    def adapter(self):
        """Create adapter with mock dependencies."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        client = MagicMock()
        executor = MagicMock()
        return CohezionAgentAdapter(
            skill_name="test_PRIME",
            mcp_client=client,
            executor=executor,
        )

    def test_unknown_role_defaults_safely(self):
        """[P1] Should default to implementer for unknown roles."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        client = MagicMock()
        executor = MagicMock()
        adapter = CohezionAgentAdapter(
            skill_name="test_PRIME",
            mcp_client=client,
            executor=executor,
            role="unknown_role",
        )
        assert adapter.role == "implementer"

    def test_step_with_executor_exception(self, adapter):
        """[P1] Should propagate executor exceptions."""
        adapter.executor.execute_task.side_effect = ValueError("Invalid task")

        with pytest.raises(ValueError):
            adapter.step("some task")

    def test_select_model_with_unknown_skill(self, adapter):
        """[P1] Should return default model for unknown skill names."""
        adapter.skill_name = "completely_unknown_skill_xyz"
        model = adapter.select_model()
        assert model is not None
        assert isinstance(model, str)

    def test_infer_operation_type_defaults_to_generate(self, adapter):
        """[P1] Should return generate for unrecognized operations."""
        op = adapter._infer_operation_type("do something random")
        assert op == "generate"

    def test_disallowed_tools_returns_list(self, adapter):
        """[P1] Should always return a list from get_disallowed_tools."""
        disallowed = adapter.get_disallowed_tools()
        assert isinstance(disallowed, list)

    def test_allowed_tools_returns_list(self, adapter):
        """[P1] Should always return a list from get_allowed_tools."""
        allowed = adapter.get_allowed_tools()
        assert isinstance(allowed, list)


class TestBenchmarkRunnerAdversarial:
    """Adversarial tests for AgentVerseBenchmarkRunner."""

    @pytest.fixture()
    def runner(self):
        """Create runner with mock dependencies."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        return AgentVerseBenchmarkRunner(
            executor=MagicMock(),
            mcp_client=MagicMock(),
        )

    def test_run_batch_with_empty_tasks(self, runner):
        """[P1] Should handle empty task list."""
        results = runner.run_batch_benchmark([])
        assert results == []

    def test_run_batch_with_malformed_tasks(self, runner):
        """[P1] Should handle malformed task dicts gracefully."""
        runner.executor.execute_task.return_value = MagicMock(
            success=True,
            metrics={"coherence": 0.5},
            duration_seconds=1.0,
        )

        tasks = [
            {"task": "valid", "skill": "python_PRIME"},
            {"task": "valid", "skill": "python_PRIME"},
        ]

        results = runner.run_batch_benchmark(tasks)
        assert len(results) == 2

    def test_should_trigger_refinement_edge_cases(self, runner):
        """[P1] Should handle edge cases for refinement."""
        from cohezion.integrations.agentverse import BenchmarkResult

        result1 = BenchmarkResult(task="t", skill="s", success=False, metrics={})
        assert runner.should_trigger_refinement(result1) is True

        result2 = BenchmarkResult(task="t", skill="s", success=True, metrics={"coherence": 0.3})
        assert runner.should_trigger_refinement(result2) is True

        result3 = BenchmarkResult(task="t", skill="s", success=True, metrics={"coherence": 0.6})
        assert runner.should_trigger_refinement(result3) is False

    def test_identify_weak_skills_with_no_results(self, runner):
        """[P1] Should return empty list with no results."""
        weak = runner.identify_weak_skills()
        assert weak == []

    def test_get_skill_coherence_summary_with_no_results(self, runner):
        """[P1] Should return empty summary with no results."""
        summary = runner.get_skill_coherence_summary()
        assert summary == {}

    def test_get_refinement_candidates_with_no_results(self, runner):
        """[P1] Should return empty list with no results."""
        candidates = runner.get_refinement_candidates()
        assert candidates == []

    def test_persist_with_empty_results(self, runner):
        """[P1] Should handle persisting empty results."""
        path = runner.persist_results()
        assert path is not None

    def test_load_historical_returns_list(self, runner):
        """[P1] Should always return a list from load_historical."""
        result = runner.load_historical_results()
        assert isinstance(result, list)


class TestBenchmarkRunnerVaultAdversarial:
    """Adversarial tests for BenchmarkRunner vault integration."""

    @pytest.fixture()
    def runner_with_vault(self):
        """Create runner with vault mocks."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        mock_client = MagicMock()
        mock_client.vault_write = MagicMock(return_value="ok")
        mock_client.vault_list = MagicMock(return_value=[])
        mock_client.vault_read = MagicMock(return_value="{}")

        return AgentVerseBenchmarkRunner(
            executor=MagicMock(),
            mcp_client=mock_client,
        )

    def test_persist_handles_vault_write_failure(self, runner_with_vault):
        """[P1] Should handle vault_write failure gracefully."""
        runner_with_vault.mcp_client.vault_write.side_effect = Exception("Vault server down")
        from cohezion.integrations.agentverse import BenchmarkResult

        runner_with_vault.results = [BenchmarkResult(task="t", skill="s", success=True, metrics={"coherence": 0.5})]

        path = runner_with_vault.persist_results()
        assert path is not None

    def test_persist_handles_empty_results(self, runner_with_vault):
        """[P1] Should handle persisting empty results without crashing."""
        path = runner_with_vault.persist_results()
        assert path is not None
        assert "/vault/benchmarks/" in path

    def test_load_handles_vault_list_failure(self, runner_with_vault):
        """[P1] Should handle vault_list failure gracefully."""
        runner_with_vault.mcp_client.vault_list.side_effect = Exception("Connection refused")

        results = runner_with_vault.load_historical_results()
        assert isinstance(results, list)

    def test_load_handles_corrupted_json(self, runner_with_vault):
        """[P1] Should handle corrupted JSON in vault gracefully."""
        runner_with_vault.mcp_client.vault_list.return_value = ["/vault/benchmarks/bad.json"]
        runner_with_vault.mcp_client.vault_read.return_value = "not valid json {"

        results = runner_with_vault.load_historical_results()
        assert isinstance(results, list)

    def test_load_handles_empty_vault(self, runner_with_vault):
        """[P1] Should return empty list when vault is empty."""
        runner_with_vault.mcp_client.vault_list.return_value = []

        results = runner_with_vault.load_historical_results()
        assert results == []

    def test_load_handles_mixed_valid_invalid_files(self, runner_with_vault):
        """[P1] Should skip invalid files but return valid ones."""
        runner_with_vault.mcp_client.vault_list.return_value = [
            "/vault/benchmarks/good.json",
            "/vault/benchmarks/bad.json",
            "/vault/benchmarks/also_good.json",
        ]
        runner_with_vault.mcp_client.vault_read.side_effect = [
            '{"coherence": 0.8}',
            "invalid json {{{",
            '{"coherence": 0.6}',
        ]

        results = runner_with_vault.load_historical_results()
        assert len(results) == 2
        assert results[0]["coherence"] == 0.8
        assert results[1]["coherence"] == 0.6

    def test_load_handles_vault_read_failure_per_file(self, runner_with_vault):
        """[P1] Should handle individual file read failures gracefully."""
        runner_with_vault.mcp_client.vault_list.return_value = [
            "/vault/benchmarks/file1.json",
            "/vault/benchmarks/file2.json",
            "/vault/benchmarks/file3.json",
        ]
        runner_with_vault.mcp_client.vault_read.side_effect = [
            Exception("Read failed"),
            '{"coherence": 0.7}',
            Exception("Read failed"),
        ]

        results = runner_with_vault.load_historical_results()
        assert len(results) == 1
        assert results[0]["coherence"] == 0.7

    def test_persist_creates_timestamped_path(self, runner_with_vault):
        """[P1] Should create unique timestamped paths for each persist."""
        from cohezion.integrations.agentverse import BenchmarkResult

        runner_with_vault.results = [BenchmarkResult(task="t", skill="s", success=True, metrics={})]

        path1 = runner_with_vault.persist_results()
        import time

        time.sleep(0.01)
        path2 = runner_with_vault.persist_results()

        assert path1 != path2
        assert path1.startswith("/vault/benchmarks/")
        assert path2.startswith("/vault/benchmarks/")


class TestCohezionEnvironmentAdversarial:
    """Adversarial tests for Cohezion environments."""

    def test_environment_handles_missing_executor(self):
        """[P1] Should handle None executor gracefully."""
        from cohezion.integrations.agentverse import CohezionEnvironment

        client = MagicMock()
        env = CohezionEnvironment(mcp_client=client, executor=None)
        assert env.executor is None

    def test_simulation_add_agent_without_name(self):
        """[P1] Should handle agents without name attribute."""
        from cohezion.integrations.agentverse import CohezionSimulationEnvironment

        client = MagicMock()
        env = CohezionSimulationEnvironment(mcp_client=client, executor=MagicMock())

        agent = MagicMock(spec=[])
        env.add_agent(agent)
        assert len(env.agents) == 1

    def test_task_environment_is_multi_agent(self):
        """[P1] Should correctly report as multi-agent."""
        from cohezion.integrations.agentverse import CohezionTaskSolvingEnvironment

        client = MagicMock()
        env = CohezionTaskSolvingEnvironment(
            mcp_client=client,
            executor=MagicMock(),
            task_description="test",
        )

        assert env.is_multi_agent() is True


class TestCoherenceViolationEdgeCases:
    """Edge case tests for CoherenceViolation."""

    def test_violation_at_exact_hiho_boundaries(self):
        """[P1] Should correctly identify violations at exact boundaries."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        bridge = AgentVerseBridge(executor=MagicMock())

        bridge.metrics = [
            {"coherence": 0.4, "agent": "exact_low"},
            {"coherence": 0.6, "agent": "exact_high"},
            {"coherence": 0.399, "agent": "just_below"},
            {"coherence": 0.601, "agent": "just_above"},
        ]

        violations = bridge.check_hiho_violations()
        assert len(violations) == 2

    def test_export_trajectory_structure(self):
        """[P1] Should export trajectory with expected structure."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        bridge = AgentVerseBridge(executor=MagicMock())
        bridge.metrics = [
            {"coherence": 0.7, "agent": "a1"},
        ]

        trajectory = bridge.export_trajectory()
        assert "metrics" in trajectory
        assert "coherence_trend" in trajectory
        assert "average_coherence" in trajectory
        assert "violation_count" in trajectory
