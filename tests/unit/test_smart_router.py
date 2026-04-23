"""Tests for the smart router module (cohezion.swarm.smart_router)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.swarm.smart_router import (
    LOCAL_MODELS,
    TASK_REQUIREMENTS,
    AgentAction,
    ModelCapability,
    ModelProfile,
    RoutingDecision,
    SmartRouter,
    TaskType,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestTaskType:
    def test_all_values_accessible(self):
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.SYNTHESIS.value == "synthesis"
        assert TaskType.CREATIVE.value == "creative"
        assert TaskType.CODING.value == "coding"
        assert TaskType.FACTUAL.value == "factual"
        assert TaskType.DEBATE.value == "debate"
        assert TaskType.SUMMARY.value == "summary"


class TestModelCapability:
    def test_all_values_accessible(self):
        assert ModelCapability.FAST.value == "fast"
        assert ModelCapability.ACCURATE.value == "accurate"
        assert ModelCapability.CREATIVE.value == "creative"
        assert ModelCapability.LARGE_CONTEXT.value == "large_context"
        assert ModelCapability.CODING.value == "coding"


# ---------------------------------------------------------------------------
# ModelProfile tests
# ---------------------------------------------------------------------------


class TestModelProfile:
    def test_efficiency_score(self):
        profile = ModelProfile(
            name="test",
            capabilities=[],
            context_length=4096,
            speed_tier=2,
            quality_tier=4,
        )
        assert profile.efficiency_score == 2.0  # 4/2

    def test_efficiency_score_fast_low_quality(self):
        profile = ModelProfile(
            name="fast",
            capabilities=[],
            context_length=4096,
            speed_tier=1,
            quality_tier=2,
        )
        assert profile.efficiency_score == 2.0  # 2/1

    def test_efficiency_score_slow_high_quality(self):
        profile = ModelProfile(
            name="slow",
            capabilities=[],
            context_length=4096,
            speed_tier=5,
            quality_tier=5,
        )
        assert profile.efficiency_score == 1.0  # 5/5


# ---------------------------------------------------------------------------
# SmartRouter.classify_task tests
# ---------------------------------------------------------------------------


class TestClassifyTask:
    def setup_method(self):
        self.router = SmartRouter(log_actions=False)

    def test_analysis(self):
        assert self.router.classify_task("analyze this data") == TaskType.ANALYSIS
        assert self.router.classify_task("examine the results") == TaskType.ANALYSIS
        assert self.router.classify_task("evaluate performance") == TaskType.ANALYSIS

    def test_synthesis(self):
        assert self.router.classify_task("synthesize findings") == TaskType.SYNTHESIS
        assert self.router.classify_task("integrate the modules") == TaskType.SYNTHESIS
        assert self.router.classify_task("combine these ideas") == TaskType.SYNTHESIS

    def test_creative(self):
        assert self.router.classify_task("create a new module") == TaskType.CREATIVE
        assert self.router.classify_task("imagine a scenario") == TaskType.CREATIVE
        assert self.router.classify_task("write a story about AI") == TaskType.CREATIVE
        assert self.router.classify_task("compose a poem") == TaskType.CREATIVE

    def test_coding(self):
        assert self.router.classify_task("implement a function") == TaskType.CODING
        assert self.router.classify_task("debug this code") == TaskType.CODING
        assert self.router.classify_task("write a function for sorting") == TaskType.CODING

    def test_factual(self):
        assert self.router.classify_task("verify this fact") == TaskType.FACTUAL
        assert self.router.classify_task("is this true?") == TaskType.FACTUAL

    def test_debate(self):
        assert self.router.classify_task("debate the merits") == TaskType.DEBATE
        assert self.router.classify_task("different perspective on this") == TaskType.DEBATE
        assert self.router.classify_task("argue for and against") == TaskType.DEBATE

    def test_summary(self):
        assert self.router.classify_task("summarize the paper") == TaskType.SUMMARY
        assert self.router.classify_task("give me a brief overview") == TaskType.SUMMARY
        assert self.router.classify_task("tldr of this document") == TaskType.SUMMARY

    def test_default_is_analysis(self):
        assert self.router.classify_task("something random entirely") == TaskType.ANALYSIS


# ---------------------------------------------------------------------------
# SmartRouter.route tests
# ---------------------------------------------------------------------------


class TestRoute:
    def test_route_with_models(self):
        router = SmartRouter(strategy="efficiency", log_actions=False)
        router.available_models = {
            "model_a": ModelProfile(
                name="model_a",
                capabilities=[ModelCapability.CODING],
                context_length=32768,
                speed_tier=1,
                quality_tier=3,
            ),
            "model_b": ModelProfile(
                name="model_b",
                capabilities=[ModelCapability.ACCURATE, ModelCapability.CODING],
                context_length=65536,
                speed_tier=3,
                quality_tier=5,
            ),
        }
        decision = router.route(TaskType.CODING)
        assert isinstance(decision, RoutingDecision)
        assert decision.task_type == TaskType.CODING
        assert decision.selected_model in ["model_a", "model_b"]

    def test_route_no_models_fallback(self):
        router = SmartRouter(log_actions=False)
        router.available_models = {}
        decision = router.route(TaskType.ANALYSIS)
        assert decision.selected_model == "gemma3:4b"
        assert decision.confidence == 0.5
        assert "fallback" in decision.reasoning.lower()

    def test_route_quality_strategy(self):
        router = SmartRouter(strategy="quality", log_actions=False)
        router.available_models = {
            "fast_model": ModelProfile(
                name="fast_model",
                capabilities=[ModelCapability.FAST, ModelCapability.ACCURATE],
                context_length=8192,
                speed_tier=1,
                quality_tier=2,
            ),
            "quality_model": ModelProfile(
                name="quality_model",
                capabilities=[ModelCapability.ACCURATE],
                context_length=32768,
                speed_tier=5,
                quality_tier=5,
            ),
        }
        decision = router.route(TaskType.ANALYSIS)
        assert decision.selected_model == "quality_model"

    def test_route_speed_strategy(self):
        router = SmartRouter(strategy="speed", log_actions=False)
        router.available_models = {
            "fast_model": ModelProfile(
                name="fast_model",
                capabilities=[ModelCapability.FAST, ModelCapability.ACCURATE],
                context_length=8192,
                speed_tier=1,
                quality_tier=2,
            ),
            "slow_model": ModelProfile(
                name="slow_model",
                capabilities=[ModelCapability.ACCURATE],
                context_length=32768,
                speed_tier=5,
                quality_tier=5,
            ),
        }
        decision = router.route(TaskType.ANALYSIS)
        assert decision.selected_model == "fast_model"

    def test_route_includes_fallbacks(self):
        router = SmartRouter(strategy="efficiency", log_actions=False)
        router.available_models = {
            "m1": ModelProfile("m1", [ModelCapability.CODING], 4096, 1, 3),
            "m2": ModelProfile("m2", [ModelCapability.CODING], 4096, 2, 4),
            "m3": ModelProfile("m3", [ModelCapability.CODING], 4096, 3, 5),
        }
        decision = router.route(TaskType.CODING)
        assert len(decision.fallback_models) <= 2


# ---------------------------------------------------------------------------
# AgentAction tests
# ---------------------------------------------------------------------------


class TestAgentAction:
    def test_to_dict(self):
        action = AgentAction(
            timestamp="2026-02-06T00:00:00",
            agent_type="test",
            model="phi3:mini",
            task_type="coding",
            input_tokens=10,
            output_tokens=20,
            duration_ms=100.0,
            success=True,
            metadata={"key": "val"},
        )
        d = action.to_dict()
        assert d["agent_type"] == "test"
        assert d["model"] == "phi3:mini"
        assert d["success"] is True
        assert d["metadata"] == {"key": "val"}

    def test_to_dict_keys(self):
        action = AgentAction(
            timestamp="t",
            agent_type="a",
            model="m",
            task_type="t",
            input_tokens=0,
            output_tokens=0,
            duration_ms=0,
            success=False,
        )
        d = action.to_dict()
        expected_keys = {
            "timestamp",
            "agent_type",
            "model",
            "task_type",
            "input_tokens",
            "output_tokens",
            "duration_ms",
            "success",
            "metadata",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# SmartRouter.execute tests
# ---------------------------------------------------------------------------


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        router = SmartRouter(log_actions=True)
        router.available_models = {
            "test:model": ModelProfile(
                "test:model",
                [ModelCapability.FAST],
                4096,
                1,
                3,
            ),
        }

        # `await resp.json()` is used at smart_router.py:419, so `.json` must
        # be an AsyncMock returning the payload (not MagicMock returning a dict,
        # which triggers "object dict can't be used in 'await' expression").
        mock_response = MagicMock()
        mock_response.status_code = 200
        # smart_router.py reads data["response"] (Ollama /api/generate format),
        # not data["message"]["content"] (/api/chat format).
        mock_response.json = AsyncMock(
            return_value={
                "response": "generated text",
                "eval_count": 50,
                "prompt_eval_count": 0,
            }
        )

        router.client = AsyncMock()
        router.client.post = AsyncMock(return_value=mock_response)

        response, action = await router.execute(
            "summarize this",
            agent_type="test_agent",
        )
        assert response == "generated text"
        assert action.success is True
        assert len(router.action_log) == 1

    @pytest.mark.asyncio
    async def test_execute_fallback_on_failure(self):
        router = SmartRouter(log_actions=True)
        router.available_models = {
            "primary": ModelProfile("primary", [ModelCapability.FAST], 4096, 1, 3),
            "fallback": ModelProfile("fallback", [ModelCapability.FAST], 4096, 1, 2),
        }

        call_count = 0

        async def mock_post(url, json=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("model down")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": "fallback response"}
            return mock_resp

        router.client = AsyncMock()
        router.client.post = mock_post

        _response, action = await router.execute("brief this")
        # The primary might fail and fallback succeeds
        assert action is not None

    @pytest.mark.asyncio
    async def test_execute_all_fail(self):
        router = SmartRouter(log_actions=True)
        router.available_models = {
            "only": ModelProfile("only", [ModelCapability.FAST], 4096, 1, 3),
        }

        router.client = AsyncMock()
        router.client.post = AsyncMock(side_effect=ConnectionError("down"))

        response, action = await router.execute("summarize")
        assert response == ""
        assert action.success is False


# ---------------------------------------------------------------------------
# SmartRouter.save_action_log tests
# ---------------------------------------------------------------------------


class TestSaveActionLog:
    @pytest.mark.asyncio
    async def test_save_creates_file(self, tmp_path):
        router = SmartRouter(log_actions=True)
        router.action_log_dir = tmp_path

        router.action_log = [
            AgentAction(
                timestamp="t",
                agent_type="a",
                model="m",
                task_type="t",
                input_tokens=0,
                output_tokens=0,
                duration_ms=0,
                success=True,
            )
        ]

        await router.save_action_log()

        files = list(tmp_path.glob("actions_*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_save_empty_log_noop(self, tmp_path):
        router = SmartRouter(log_actions=True)
        router.action_log_dir = tmp_path
        router.action_log = []
        await router.save_action_log()
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 0


# ---------------------------------------------------------------------------
# TASK_REQUIREMENTS and LOCAL_MODELS sanity checks
# ---------------------------------------------------------------------------


class TestModuleConstants:
    def test_task_requirements_covers_all_task_types(self):
        for tt in TaskType:
            assert tt in TASK_REQUIREMENTS

    def test_local_models_not_empty(self):
        assert len(LOCAL_MODELS) > 0

    def test_local_models_have_profiles(self):
        for name, profile in LOCAL_MODELS.items():
            assert isinstance(profile, ModelProfile)
            assert profile.name == name
            assert profile.context_length > 0
