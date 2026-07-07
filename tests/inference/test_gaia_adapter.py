"""Unit tests for gaia_adapter — GAIA SDK adapter and AMD-optimization tier selection."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.gaia_adapter import (
    GaiaAgentTier,
    _GaiaLLMClientShim,
    amd_optimized_hierarchy,
    build_gaia_llm_tier,
    build_gaia_native_tier,
    rank_models_by_amd_optimization,
)


# ── GaiaAgentTier.run ─────────────────────────────────────────────────────────


class TestGaiaAgentTierRun:
    @pytest.mark.asyncio
    async def test_run_with_prompt_method(self):
        """Agent.prompt() method is called and result wrapped in OrchestrationResult."""
        mock_agent = MagicMock()
        mock_agent.prompt = MagicMock(return_value="test response")
        tier = GaiaAgentTier(agent=mock_agent, label="test-model")

        result = await tier.run("Hello")

        assert result.text == "test response"
        assert result.error is None
        assert result.primary_model == "test-model"
        assert result.final_model == "test-model"

    @pytest.mark.asyncio
    async def test_run_with_run_method_fallback(self):
        """Falls back to .run() if .prompt() is absent."""
        mock_agent = SimpleNamespace(run=MagicMock(return_value="run response"))
        tier = GaiaAgentTier(agent=mock_agent, label="test")

        result = await tier.run("Hello")

        assert result.text == "run response"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_with_no_method_returns_error(self):
        """Agent with no prompt/run/chat method returns error gracefully."""
        mock_agent = object()  # no methods
        tier = GaiaAgentTier(agent=mock_agent, label="broken")

        result = await tier.run("Hello")

        assert result.error is not None
        assert "no prompt/run/chat method" in result.error

    @pytest.mark.asyncio
    async def test_run_exception_returns_error_not_raise(self):
        """If agent.prompt() raises, the error is captured (not propagated)."""
        mock_agent = MagicMock()
        mock_agent.prompt.side_effect = RuntimeError("model crashed")
        tier = GaiaAgentTier(agent=mock_agent, label="failing-model")

        result = await tier.run("Hello")

        assert result.error is not None
        assert "RuntimeError" in result.error
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_run_result_has_latency(self):
        """OrchestrationResult includes latency_ms."""
        mock_agent = MagicMock()
        mock_agent.prompt = MagicMock(return_value="ok")
        tier = GaiaAgentTier(agent=mock_agent, label="test")

        result = await tier.run("Hello")

        assert result.latency_ms >= 0.0


# ── rank_models_by_amd_optimization ──────────────────────────────────────────


class TestRankModelsByAmdOptimization:
    def test_npu_ranked_before_cloud(self):
        """NPU (FLM) models rank ahead of cloud models."""
        from cohezion.inference.gaia_adapter import _AMD_PATH_RANK
        from cohezion.inference.registry import Lane

        # Verify the rank table has the expected ordering
        assert _AMD_PATH_RANK[Lane.NPU] < _AMD_PATH_RANK[Lane.CLOUD_CLAUDE]
        assert _AMD_PATH_RANK[Lane.IGPU_ROCWMMA] < _AMD_PATH_RANK[Lane.CLOUD_OLLAMA]

    def test_unknown_models_ranked_last(self):
        """Models not in registry get rank=99 and are sorted to end."""
        result = rank_models_by_amd_optimization(["unknown-model-xyz"])
        assert result == ["unknown-model-xyz"]  # single item stays

    def test_empty_list_returns_empty(self):
        result = rank_models_by_amd_optimization([])
        assert result == []

    def test_rank_preserves_all_models(self):
        """All input models are present in output (no filtering)."""
        models = ["model-a", "model-b", "model-c"]
        result = rank_models_by_amd_optimization(models)
        assert sorted(result) == sorted(models)


# ── build_gaia_native_tier ────────────────────────────────────────────────────


class TestBuildGaiaNativeTier:
    def test_raises_when_gaia_not_installed(self):
        """RuntimeError raised if amd-gaia is not installed."""
        with patch.dict(
            sys.modules,
            {
                "gaia": None,
                "gaia.agents": None,
                "gaia.agents.chat": None,
                "gaia.agents.chat.agent": None,
            },
        ):
            # When GAIA module is missing entirely, import fails
            with pytest.raises((RuntimeError, ImportError)):
                build_gaia_native_tier()

    def test_returns_gaia_agent_tier_with_label(self):
        """Successful build returns GaiaAgentTier with correct label."""
        mock_agent_instance = MagicMock()
        mock_chat_agent_cls = MagicMock(return_value=mock_agent_instance)
        mock_config_cls = MagicMock()

        mock_gaia_module = MagicMock()
        mock_gaia_module.ChatAgent = mock_chat_agent_cls
        mock_gaia_module.ChatAgentConfig = mock_config_cls

        with patch.dict(sys.modules, {"gaia.agents.chat.agent": mock_gaia_module}):
            tier = build_gaia_native_tier(
                model_id="llama3.2-1b-FLM", base_url="http://localhost:13306/v1"
            )

        assert isinstance(tier, GaiaAgentTier)
        assert "llama3.2-1b-FLM" in tier.label

    def test_default_model_id(self):
        """Default model_id is Gemma-4-E2B-it-GGUF."""
        mock_gaia_module = MagicMock()
        mock_gaia_module.ChatAgent = MagicMock(return_value=MagicMock())
        mock_gaia_module.ChatAgentConfig = MagicMock()

        with patch.dict(sys.modules, {"gaia.agents.chat.agent": mock_gaia_module}):
            tier = build_gaia_native_tier()

        assert "Gemma-4-E2B-it-GGUF" in tier.label


# ── amd_optimized_hierarchy ───────────────────────────────────────────────────


class TestAmdOptimizedHierarchy:
    def test_hierarchy_structure_with_cloud(self):
        """With include_cloud=True, hierarchy includes cloud tiers."""
        orch = amd_optimized_hierarchy(include_cloud=True, max_cost_usd=0.10)
        assert len(orch.tiers) == 6
        assert orch.max_cost_usd == 0.10

    def test_hierarchy_structure_without_cloud(self):
        """With include_cloud=False, only local AMD tiers."""
        orch = amd_optimized_hierarchy(include_cloud=False)
        assert len(orch.tiers) == 4

    def test_tier0_is_cheapest_local(self):
        """Tier 0 is the cheapest/fastest local model (Gemma-4-E2B)."""
        orch = amd_optimized_hierarchy(include_cloud=False)
        tier0_target = orch.tiers[0][0]
        assert "E2B" in tier0_target or "e2b" in tier0_target.lower()

    def test_trust_tier_is_last(self):
        """The terminal tier uses QualityGate.TRUST (always passes)."""
        orch = amd_optimized_hierarchy(include_cloud=True)
        last_gate = orch.tiers[-1][1]
        from cohezion.inference.orchestrator import QualityGate

        assert last_gate is QualityGate.TRUST  # type: ignore[attr-defined]


# ── build_gaia_llm_tier / _GaiaLLMClientShim (LemonadeClient path, 0.19.0+) ───


class TestGaiaLLMClientTier:
    """The supported GAIA path: LemonadeClient wrapped as a tier (no RAG deps)."""

    @staticmethod
    def _fake_client(content: str = "Paris"):
        client = MagicMock()
        client.chat_completions.return_value = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}]
        }
        return client

    def test_shim_prompt_extracts_content(self):
        """Shim adapts chat_completions -> .prompt(text) -> str."""
        shim = _GaiaLLMClientShim(
            self._fake_client("Paris"),
            "Granite-4.1-8B-GGUF",
            max_tokens=16,
            temperature=0.0,
        )
        assert shim.prompt("capital of France?") == "Paris"

    def test_shim_passes_model_and_params(self):
        """Shim forwards model id + sampling params to chat_completions."""
        client = self._fake_client()
        shim = _GaiaLLMClientShim(client, "M", max_tokens=42, temperature=0.3)
        shim.prompt("hi")
        kwargs = client.chat_completions.call_args.kwargs
        assert kwargs["model"] == "M"
        assert kwargs["max_tokens"] == 42
        assert kwargs["temperature"] == 0.3
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]

    def test_build_llm_tier_defaults_to_fleet_router(self):
        """Factory points LemonadeClient at the existing fleet router :13305 (OOM-safe)."""
        with patch("gaia.llm.lemonade_client.LemonadeClient") as MockClient:
            tier = build_gaia_llm_tier("Granite-4.1-8B-GGUF")
        assert isinstance(tier, GaiaAgentTier)
        assert tier.label == "gaia-llm:Granite-4.1-8B-GGUF"
        assert "13305" in MockClient.call_args.kwargs["base_url"]

    @pytest.mark.asyncio
    async def test_tier_run_returns_text_no_error(self):
        """End-to-end through GaiaAgentTier.run with a mocked client."""
        with patch(
            "gaia.llm.lemonade_client.LemonadeClient", return_value=self._fake_client("Paris")
        ):
            tier = build_gaia_llm_tier("Granite-4.1-8B-GGUF")
        result = await tier.run("capital of France?")
        assert result.text == "Paris"
        assert result.error is None


# ── recipe-aware sampling defaults (2026-07-07 goal: right recipe per model) ──


class TestGaiaLLMTierRecipeAwareDefaults:
    """build_gaia_llm_tier used to hardcode temperature=0.0 for every model
    regardless of family, silently overriding any server-side recipe tuning
    on every request. It must now resolve the model's family default instead,
    while still respecting an explicit caller override."""

    @staticmethod
    def _fake_client(content: str = "ok"):
        client = MagicMock()
        client.chat_completions.return_value = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}]
        }
        return client

    def test_qwen3_model_gets_family_temperature_not_zero(self):
        client = self._fake_client()
        with patch("gaia.llm.lemonade_client.LemonadeClient", return_value=client):
            tier = build_gaia_llm_tier("DeepSeek-Qwen3-8B-GGUF")
        tier.agent.prompt("hi")
        kwargs = client.chat_completions.call_args.kwargs
        assert kwargs["temperature"] == 0.6
        assert kwargs["top_k"] == 20
        assert kwargs["top_p"] == 0.95

    def test_gemma4_model_gets_family_temperature(self):
        client = self._fake_client()
        with patch("gaia.llm.lemonade_client.LemonadeClient", return_value=client):
            tier = build_gaia_llm_tier("Gemma-4-E4B-it-GGUF")
        tier.agent.prompt("hi")
        kwargs = client.chat_completions.call_args.kwargs
        assert kwargs["temperature"] == 1.0
        assert kwargs["top_k"] == 64

    def test_unknown_model_falls_back_to_generic_default_not_zero(self):
        client = self._fake_client()
        with patch("gaia.llm.lemonade_client.LemonadeClient", return_value=client):
            tier = build_gaia_llm_tier("Granite-4.1-8B-GGUF")
        tier.agent.prompt("hi")
        kwargs = client.chat_completions.call_args.kwargs
        assert kwargs["temperature"] != 0.0
        assert "top_k" not in kwargs  # no family match -> no sampling extras sent

    def test_explicit_temperature_override_still_wins(self):
        """Caller-supplied temperature must not be clobbered by the family default."""
        client = self._fake_client()
        with patch("gaia.llm.lemonade_client.LemonadeClient", return_value=client):
            tier = build_gaia_llm_tier("DeepSeek-Qwen3-8B-GGUF", temperature=0.2)
        tier.agent.prompt("hi")
        kwargs = client.chat_completions.call_args.kwargs
        assert kwargs["temperature"] == 0.2
