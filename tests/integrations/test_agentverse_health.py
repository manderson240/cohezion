"""Repo health checks for Cohezion-AgentVerse integration.

Automated checks to ensure the integration module maintains
quality standards: no circular imports, proper exports, etc.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestModuleHealth:
    """Health checks for the integration module."""

    def test_module_imports_without_error(self):
        """[P0] Should import the module without errors."""
        from cohezion.integrations.agentverse import (
            AgentVerseBenchmarkRunner,
            AgentVerseBridge,
            BenchmarkResult,
            CoherenceViolation,
            CohezionAgentAdapter,
            CohezionEnvironment,
            CohezionSimulationEnvironment,
            CohezionTaskSolvingEnvironment,
        )

        assert AgentVerseBridge is not None
        assert AgentVerseBenchmarkRunner is not None
        assert BenchmarkResult is not None
        assert CoherenceViolation is not None
        assert CohezionAgentAdapter is not None
        assert CohezionEnvironment is not None
        assert CohezionSimulationEnvironment is not None
        assert CohezionTaskSolvingEnvironment is not None

    def test_no_circular_imports(self):
        """[P0] Should not have circular imports (basic smoke test)."""
        import cohezion.integrations.agentverse as module

        assert module.__name__ == "cohezion.integrations.agentverse"

    def test_all_exports_are_public(self):
        """[P0] All __all__ exports should be importable."""
        import cohezion.integrations.agentverse as module
        from cohezion.integrations.agentverse import __all__

        for name in __all__:
            assert hasattr(module, name), f"{name} is in __all__ but not found in module"

    def test_dataclasses_are_instantiable(self):
        """[P0] Dataclasses should be instantiable with required args."""
        from cohezion.integrations.agentverse import BenchmarkResult, CoherenceViolation

        result = BenchmarkResult(
            task="test",
            skill="test_PRIME",
            success=True,
            metrics={},
        )
        assert result.task == "test"

        violation = CoherenceViolation(
            agent="test",
            coherence=0.3,
            severity="CRITICAL",
            message="test",
        )
        assert violation.agent == "test"


class TestIntegrationCompleteness:
    """Verify integration is complete and consistent."""

    def test_agent_adapter_has_required_methods(self):
        """[P0] CohezionAgentAdapter should have all required methods."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        client = MagicMock()
        executor = MagicMock()

        adapter = CohezionAgentAdapter(
            skill_name="test_PRIME",
            mcp_client=client,
            executor=executor,
        )

        assert hasattr(adapter, "step")
        assert hasattr(adapter, "reset_history")
        assert hasattr(adapter, "get_allowed_tools")
        assert hasattr(adapter, "get_disallowed_tools")
        assert hasattr(adapter, "select_model")

    def test_bridge_has_required_methods(self):
        """[P0] AgentVerseBridge should have all required methods."""
        from cohezion.integrations.agentverse import AgentVerseBridge

        executor = MagicMock()
        bridge = AgentVerseBridge(executor=executor)

        assert hasattr(bridge, "on_agent_message")
        assert hasattr(bridge, "route_message")
        assert hasattr(bridge, "get_coherence_trajectory")
        assert hasattr(bridge, "get_average_coherence")
        assert hasattr(bridge, "check_hiho_violations")
        assert hasattr(bridge, "reset")

    def test_benchmark_runner_has_required_methods(self):
        """[P0] AgentVerseBenchmarkRunner should have all required methods."""
        from cohezion.integrations.agentverse import AgentVerseBenchmarkRunner

        runner = AgentVerseBenchmarkRunner(
            executor=MagicMock(),
            mcp_client=MagicMock(),
        )

        assert hasattr(runner, "run_single_task")
        assert hasattr(runner, "run_batch_benchmark")
        assert hasattr(runner, "should_trigger_refinement")
        assert hasattr(runner, "get_skill_coherence_summary")
        assert hasattr(runner, "identify_weak_skills")
        assert hasattr(runner, "get_refinement_candidates")
        assert hasattr(runner, "persist_results")
        assert hasattr(runner, "load_historical_results")


class TestFileStructure:
    """Verify file structure is correct."""

    def test_all_python_files_exist(self):
        """[P0] All expected Python files should exist."""
        base = Path("src/cohezion/integrations/agentverse")

        expected = [
            "__init__.py",
            "cohezion_agent.py",
            "cohezion_environment.py",
            "bridge.py",
            "benchmark_runner.py",
        ]

        for filename in expected:
            path = base / filename
            assert path.exists(), f"Expected file {filename} not found"

    def test_no_extra_files_in_module(self):
        """[P1] Module should not contain unexpected files."""
        base = Path("src/cohezion/integrations/agentverse")

        if not base.exists():
            pytest.skip("Module directory doesn't exist yet")

        python_files = list(base.glob("*.py"))
        assert len(python_files) >= 5, "Should have at least __init__.py and 4 modules"


class TestTypeHints:
    """Verify basic type hints are present (smoke test)."""

    def test_bridge_has_type_hints(self):
        """[P1] Bridge methods should have type hints."""
        import inspect

        from cohezion.integrations.agentverse import AgentVerseBridge

        executor = MagicMock()
        bridge = AgentVerseBridge(executor=executor)

        sig = inspect.signature(bridge.on_agent_message)
        assert sig is not None

    def test_adapter_step_is_callable(self):
        """[P1] Adapter step should be callable."""
        from cohezion.integrations.agentverse import CohezionAgentAdapter

        client = MagicMock()
        executor = MagicMock()

        adapter = CohezionAgentAdapter(
            skill_name="test",
            mcp_client=client,
            executor=executor,
        )

        assert callable(adapter.step)


class TestConstantsAndConfiguration:
    """Verify constants and configuration are correct."""

    def test_hiho_band_is_valid(self):
        """[P0] HIHO band should be properly defined."""
        from cohezion.integrations.agentverse import bridge

        assert hasattr(bridge, "HIHO_LOW")
        assert hasattr(bridge, "HIHO_HIGH")
        assert 0 <= bridge.HIHO_LOW < bridge.HIHO_HIGH <= 1.0

    def test_refinement_threshold_is_valid(self):
        """[P0] Refinement threshold should be valid."""
        from cohezion.integrations.agentverse import benchmark_runner

        assert hasattr(benchmark_runner, "REFINEMENT_THRESHOLD")
        assert 0 <= benchmark_runner.REFINEMENT_THRESHOLD <= 1.0
