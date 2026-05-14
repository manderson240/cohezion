"""Coverage batch Z25: tool_flux, mycelium/observer, manifold_bridge, agentskills_bridge, swarm/providers."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: flux/providers/tool_flux.py
# ---------------------------------------------------------------------------


class TestToolFlux:
    def _make_cap(self, name="my_skill", description="does stuff", score=0.8, cap_type="skill"):
        cap = MagicMock()
        cap.name = name
        cap.description = description
        cap.score = score
        cap.type = cap_type
        return cap

    def test_get_context_returns_flux_blocks(self):
        from cohezion.flux.providers.tool_flux import ToolFlux
        from cohezion.flux.types import FluxBlock

        cap = self._make_cap()
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("summarize"))
        assert len(blocks) == 1
        assert isinstance(blocks[0], FluxBlock)

    def test_get_context_block_content_format(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        cap = self._make_cap(name="summarizer", description="summarize text")
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("summarize"))
        assert blocks[0].content == "summarizer: summarize text"

    def test_get_context_block_uses_tool_source(self):
        from cohezion.flux.providers.tool_flux import ToolFlux
        from cohezion.flux.types import FluxSource

        cap = self._make_cap()
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks[0].source == FluxSource.TOOL

    def test_get_context_block_relevance_score(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        cap = self._make_cap(score=0.95)
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks[0].relevance_score == pytest.approx(0.95)

    def test_get_context_block_metadata(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        cap = self._make_cap(name="analyzer", cap_type="agent")
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("analyze"))
        assert blocks[0].metadata == {"type": "agent", "name": "analyzer"}

    def test_get_context_exception_returns_empty(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        registry = MagicMock()
        registry.find.side_effect = RuntimeError("registry unavailable")
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks == []

    def test_get_context_empty_results_returns_empty(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        registry = MagicMock()
        registry.find.return_value = []
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks == []

    def test_get_context_none_results_returns_empty(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        registry = MagicMock()
        registry.find.return_value = None
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks == []

    def test_get_context_passes_top_k_to_registry(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        registry = MagicMock()
        registry.find.return_value = []
        tf = ToolFlux(registry)
        asyncio.run(tf.get_context("test", top_k=3))
        registry.find.assert_called_once_with("test", top_k=3)

    def test_get_context_no_score_attribute_defaults_to_half(self):
        from cohezion.flux.providers.tool_flux import ToolFlux

        cap = MagicMock(spec=["name", "description"])
        cap.name = "minimal_cap"
        cap.description = "no score"
        del cap.score  # spec restricts attrs — no score attribute
        registry = MagicMock()
        registry.find.return_value = [cap]
        tf = ToolFlux(registry)
        blocks = asyncio.run(tf.get_context("test"))
        assert blocks[0].relevance_score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Module 2: mycelium/observer.py
# ---------------------------------------------------------------------------


class TestChangeObserver:
    def test_detect_modified_files_returns_py_files(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.return_value = b"src/cohezion/foo.py\nsrc/cohezion/bar.py\n"
            obs = ChangeObserver(".")
            files = obs.detect_modified_files()
        assert files == ["src/cohezion/foo.py", "src/cohezion/bar.py"]

    def test_detect_modified_files_filters_non_py(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.return_value = b"src/cohezion/foo.py\nREADME.md\nsetup.cfg\n"
            obs = ChangeObserver(".")
            files = obs.detect_modified_files()
        assert files == ["src/cohezion/foo.py"]

    def test_detect_modified_files_error_returns_empty(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.side_effect = subprocess.CalledProcessError(1, "git")
            obs = ChangeObserver(".")
            files = obs.detect_modified_files()
        assert files == []

    def test_extract_diff_context_returns_diff(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.return_value = b"@@ -1,3 +1,4 @@\n+new_line\n"
            obs = ChangeObserver(".")
            diff = obs.extract_diff_context("src/cohezion/foo.py")
        assert "@@ -1,3 +1,4 @@" in diff

    def test_extract_diff_context_error_returns_empty_string(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.side_effect = subprocess.CalledProcessError(128, "git")
            obs = ChangeObserver(".")
            diff = obs.extract_diff_context("src/cohezion/foo.py")
        assert diff == ""

    def test_custom_root_dir_passed_to_subprocess(self):
        from cohezion.mycelium.observer import ChangeObserver

        with patch("cohezion.mycelium.observer.subprocess.check_output") as mock_co:
            mock_co.return_value = b""
            obs = ChangeObserver("/custom/root")
            obs.detect_modified_files()
        _args, kwargs = mock_co.call_args
        assert kwargs.get("cwd") == "/custom/root"


# ---------------------------------------------------------------------------
# Module 3: core/routing/manifold_bridge.py
# ---------------------------------------------------------------------------


class TestManifoldBridge:
    @pytest.fixture(autouse=True)
    def _patch_router(self):
        with patch("cohezion.core.routing.manifold_bridge.LOCAL_ROUTER", MagicMock()):
            yield

    def test_map_to_archetype_returns_constant(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mb = ManifoldBridge()
        arch = mb._map_to_archetype([0.1, 0.5, 0.9])
        assert arch == "self_optimizing_kernel_synthesis"

    def test_map_to_archetype_ignores_embedding_value(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mb = ManifoldBridge()
        assert mb._map_to_archetype([0.0] * 512) == mb._map_to_archetype([1.0] * 512)

    def test_build_transcendence_prompt_contains_archetype(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mb = ManifoldBridge()
        latent = MagicMock()
        latent.semantic_intent = "write better code"
        prompt = mb._build_transcendence_prompt(latent, "self_optimizing_kernel_synthesis")
        assert "self_optimizing_kernel_synthesis" in prompt

    def test_build_transcendence_prompt_contains_intent(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mb = ManifoldBridge()
        latent = MagicMock()
        latent.semantic_intent = "optimize memory usage"
        prompt = mb._build_transcendence_prompt(latent, "some_arch")
        assert "optimize memory usage" in prompt

    def test_local_manifold_bridge_singleton_exists(self):
        from cohezion.core.routing.manifold_bridge import LOCAL_MANIFOLD_BRIDGE, ManifoldBridge

        assert isinstance(LOCAL_MANIFOLD_BRIDGE, ManifoldBridge)

    def test_manifold_bridge_instantiation(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mb = ManifoldBridge()
        assert mb.router is not None

    def test_precipitate_intent_returns_result_dict(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mock_router = MagicMock()
        mock_router.route_task = AsyncMock(return_value="Generated output from model")
        with patch("cohezion.core.routing.manifold_bridge.LOCAL_ROUTER", mock_router):
            mb = ManifoldBridge()
            mb.router = mock_router

            latent = MagicMock()
            latent.semantic_intent = "optimize the system"
            latent.embedding = [0.1, 0.2, 0.3]

            journey = MagicMock()
            result = asyncio.run(mb.precipitate_intent(journey, latent))

        assert "archetype" in result
        assert "result_summary" in result
        assert "raw_result" in result
        assert result["phi_est"] == pytest.approx(0.85)

    def test_precipitate_intent_uses_reasoning_task_type(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        mock_router = MagicMock()
        mock_router.route_task = AsyncMock(return_value="x" * 300)
        with patch("cohezion.core.routing.manifold_bridge.LOCAL_ROUTER", mock_router):
            mb = ManifoldBridge()
            mb.router = mock_router

            latent = MagicMock()
            latent.semantic_intent = "explain the concept"
            latent.embedding = [0.0]

            asyncio.run(mb.precipitate_intent(MagicMock(), latent))

        call_kwargs = mock_router.route_task.call_args.kwargs
        # archetype is "self_optimizing_kernel_synthesis" — no "code" in it → reasoning
        assert call_kwargs.get("task_type") == "reasoning"

    def test_precipitate_intent_result_summary_truncated(self):
        from cohezion.core.routing.manifold_bridge import ManifoldBridge

        long_result = "A" * 500
        mock_router = MagicMock()
        mock_router.route_task = AsyncMock(return_value=long_result)
        with patch("cohezion.core.routing.manifold_bridge.LOCAL_ROUTER", mock_router):
            mb = ManifoldBridge()
            mb.router = mock_router

            latent = MagicMock()
            latent.semantic_intent = "test"
            latent.embedding = [0.0]

            result = asyncio.run(mb.precipitate_intent(MagicMock(), latent))

        # result_summary is first 200 chars + "..."
        assert result["result_summary"] == "A" * 200 + "..."


# ---------------------------------------------------------------------------
# Module 4: mcp/agentskills_bridge.py
# ---------------------------------------------------------------------------


class TestAgentskillsBridge:
    def test_execute_success_when_governance_passes(self):
        from cohezion.mcp.agentskills_bridge import agentskills_execute

        with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_eng_cls:
            mock_eng = MagicMock()
            mock_eng.can_perform.return_value = True
            mock_eng_cls.return_value = mock_eng
            result = asyncio.run(agentskills_execute("agent-1", "summarize", {"text": "hello"}))
        assert result["success"] is True

    def test_execute_returns_skill_name_on_success(self):
        from cohezion.mcp.agentskills_bridge import agentskills_execute

        with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_eng_cls:
            mock_eng = MagicMock()
            mock_eng.can_perform.return_value = True
            mock_eng_cls.return_value = mock_eng
            result = asyncio.run(agentskills_execute("agent-1", "my_skill", {}))
        assert result["skill"] == "my_skill"

    def test_execute_governance_violation_when_tier_insufficient(self):
        from cohezion.mcp.agentskills_bridge import agentskills_execute

        with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_eng_cls:
            mock_eng = MagicMock()
            mock_eng.can_perform.return_value = False
            mock_eng_cls.return_value = mock_eng
            result = asyncio.run(agentskills_execute("agent-1", "forbidden_skill", {}))
        assert result["success"] is False
        assert "Governance Violation" in result["error"]

    def test_execute_creates_new_autonomy_engine_per_call(self):
        from cohezion.mcp.agentskills_bridge import agentskills_execute

        with patch("cohezion.mcp.agentskills_bridge.AutonomyEngine") as mock_eng_cls:
            mock_eng = MagicMock()
            mock_eng.can_perform.return_value = True
            mock_eng_cls.return_value = mock_eng
            asyncio.run(agentskills_execute("a1", "s1", {}))
            asyncio.run(agentskills_execute("a2", "s2", {}))
        assert mock_eng_cls.call_count == 2


# ---------------------------------------------------------------------------
# Module 5: swarm/providers/__init__.py
# ---------------------------------------------------------------------------


class TestSwarmProvidersInit:
    def test_model_provider_importable(self):
        from cohezion.swarm.providers import ModelProvider

        assert ModelProvider is not None

    def test_get_model_provider_importable(self):
        from cohezion.swarm.providers import get_model_provider

        assert callable(get_model_provider)

    def test_register_model_provider_importable(self):
        from cohezion.swarm.providers import register_model_provider

        assert callable(register_model_provider)

    def test_get_model_provider_raises_for_unknown(self):
        from cohezion.swarm.providers import get_model_provider

        with pytest.raises(ValueError, match="not registered"):
            get_model_provider("definitely_not_a_real_provider_xyz123")

    def test_register_and_retrieve_model_provider(self):
        from cohezion.swarm.providers import ModelProvider, get_model_provider, register_model_provider

        class DummyProvider(ModelProvider):
            async def generate(self, model, prompt, **kwargs):
                return MagicMock(response="dummy")

            async def list_models(self):
                return []

            async def health_check(self):
                return True

            async def close(self):
                pass

        unique_name = "test_dummy_provider_z25"
        register_model_provider(unique_name, DummyProvider)
        provider = get_model_provider(unique_name)
        assert isinstance(provider, DummyProvider)
