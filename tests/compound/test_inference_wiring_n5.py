"""Structural tests: inference_provider wiring into compound improvement arm."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestInferenceProviderParams:
    """Verify all three compound components accept inference_provider."""

    def test_retrospection_engine_accepts_inference_provider(self):
        import inspect

        from cohezion.core.compound.retrospection import RetrospectionEngine

        params = inspect.signature(RetrospectionEngine.__init__).parameters
        assert "inference_provider" in params

    def test_skill_consensus_voter_accepts_inference_provider(self):
        import inspect

        from cohezion.compound.skill_consensus_voter import SkillConsensusVoter

        params = inspect.signature(SkillConsensusVoter.__init__).parameters
        assert "inference_provider" in params

    def test_compound_executor_accepts_inference_provider(self):
        import inspect

        from cohezion.compound.executor import CompoundExecutor

        params = inspect.signature(CompoundExecutor.__init__).parameters
        assert "inference_provider" in params

    def test_retrospection_engine_stores_provider(self):
        from cohezion.core.compound.retrospection import RetrospectionEngine

        provider = MagicMock()
        engine = RetrospectionEngine(inference_provider=provider)
        assert engine._inference_provider is provider

    def test_skill_consensus_voter_stores_provider(self):
        from cohezion.compound.skill_consensus_voter import SkillConsensusVoter

        mcp_client = MagicMock()
        provider = MagicMock()
        voter = SkillConsensusVoter(mcp_client, inference_provider=provider)
        assert voter._inference_provider is provider

    def test_compound_executor_stores_provider(self):
        from cohezion.compound.executor import CompoundExecutor

        mcp_client = MagicMock()
        provider = MagicMock()
        executor = CompoundExecutor(mcp_client, inference_provider=provider)
        assert executor._inference_provider is provider

    def test_compound_executor_none_provider_is_safe(self):
        from cohezion.compound.executor import CompoundExecutor

        mcp_client = MagicMock()
        executor = CompoundExecutor(mcp_client, inference_provider=None)
        assert executor._inference_provider is None


class TestN5ProductionPath:
    """N5: production improvement path uses BBQ (thinking at full depth)."""

    def test_make_executor_wires_exec_provider(self):
        """make_executor() must pass exec_provider as inference_provider to CompoundExecutor."""
        import inspect

        from cohezion.compound import make_executor

        src = inspect.getsource(make_executor)
        assert "inference_provider" in src, "make_executor must wire inference_provider"
        assert "exec_provider" in src, "make_executor must build exec_provider"

    def test_executor_factory_wires_retrospection_with_provider(self):
        """ExecutorFactory.create() must pass inference_provider to RetrospectionEngine."""
        import inspect

        from cohezion.compound.executor_factory import ExecutorFactory

        src = inspect.getsource(ExecutorFactory.create)
        assert "RetrospectionEngine" in src
        assert "inference_provider" in src or "_retro_provider" in src
