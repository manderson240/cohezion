"""Unit tests for lemonade_recipes — model recipe registry and parameter resolver.

All external I/O is mocked at source level so these tests pass without a live
Lemonade server.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.lemonade_recipes import (
    LEMONADE_RECIPES,
    CapabilityProfile,
    ModelRecipe,
    _budgets,
    _cap,
    _metrics,
    _prompts,
    _register,
    _tasks,
    best_model_for_task,
    discover_from_live_models,
    get_inference_params,
    get_recipe,
    probe_live_models,
    register_recipe,
)
from cohezion.inference.registry import Lane, Task


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolate_registry():
    """Back up the global registry, run the test, then restore it.

    Recipes are stored in a module-level dict; tests that register or discover
    recipes must not pollute other tests.
    """
    snapshot = dict(LEMONADE_RECIPES)
    yield
    LEMONADE_RECIPES.clear()
    LEMONADE_RECIPES.update(snapshot)


# ── Recipe dataclass constructors ───────────────────────────────────────────────


class TestRecipeConstructors:
    def test_capability_profile_defaults(self):
        c = CapabilityProfile()
        assert c.reasoning == c.coding == c.creativity == 0.5

    def test_helper_cap_builds_profile(self):
        c = _cap(reasoning=0.9, coding=0.8)
        assert c.reasoning == 0.9
        assert c.coding == 0.8
        assert c.creativity == 0.5

    def test_helper_tasks_filters_unknown_keys(self):
        scores = _tasks(code_gen=0.9, unknown_task=0.5)
        assert Task.CODE_GEN in scores
        assert scores[Task.CODE_GEN] == 0.9
        assert "unknown_task" not in scores

    def test_helper_prompts_defaults(self):
        p = _prompts()
        assert p.default == "You are a helpful assistant."
        assert p.reasoning is None

    def test_helper_budgets_defaults(self):
        b = _budgets()
        assert b.code == 600
        assert b.short_categorical == 50

    def test_helper_metrics_defaults(self):
        m = _metrics()
        assert m.estimated is True
        assert m.ttft_ms is None


# ── Registry lookups ──────────────────────────────────────────────────────────


class TestGetRecipe:
    def test_get_recipe_known_model(self):
        recipe = get_recipe("llama3.2-1b-FLM")
        assert recipe is not None
        assert recipe.model_id == "llama3.2-1b-FLM"
        assert recipe.lane == Lane.NPU

    def test_get_recipe_unknown_model(self):
        assert get_recipe("totally-unknown-model-xyz") is None

    def test_all_recipes_have_valid_capabilities(self):
        for recipe in LEMONADE_RECIPES.values():
            for field_name in (
                "reasoning",
                "coding",
                "creativity",
                "instruction_following",
                "long_context",
                "multilingual",
            ):
                value = getattr(recipe.capabilities, field_name)
                assert 0.0 <= value <= 1.0, f"{recipe.model_id}.{field_name}={value} out of [0,1]"


class TestRegisterRecipe:
    def test_register_recipe_adds_entry(self):
        new = ModelRecipe(
            model_id="custom-test-recipe",
            family="test",
            variant="7b",
            lane=Lane.CPU,
        )
        register_recipe(new)
        assert get_recipe("custom-test-recipe") is new


# ── Task selection ────────────────────────────────────────────────────────────


class TestBestModelForTask:
    def test_best_for_code_gen(self):
        winner = best_model_for_task(Task.CODE_GEN)
        assert winner is not None
        recipe = get_recipe(winner)
        assert recipe is not None
        assert recipe.score_for_task(Task.CODE_GEN) == max(
            r.score_for_task(Task.CODE_GEN) for r in LEMONADE_RECIPES.values()
        )

    def test_best_for_task_lane_filter(self):
        winner = best_model_for_task(Task.SENSING, lane=Lane.NPU)
        assert winner is not None
        assert get_recipe(winner).lane == Lane.NPU

    def test_best_for_task_downloaded_filter(self):
        winner = best_model_for_task(
            Task.CODE_GEN,
            prefer_downloaded={"llama3.2-1b-FLM"},
        )
        assert winner == "llama3.2-1b-FLM"

    def test_best_for_task_no_candidates_returns_none(self):
        assert best_model_for_task(Task.CODE_GEN, prefer_downloaded=set()) is None

    def test_best_for_task_string_input(self):
        winner = best_model_for_task("sensing")
        assert winner is not None
        assert get_recipe(winner) is not None

    def test_best_for_task_invalid_string_raises(self):
        with pytest.raises(ValueError):
            best_model_for_task("not_a_real_task")


# ── Inference parameter resolution ────────────────────────────────────────────


class TestGetInferenceParams:
    def test_thinking_model_adds_budget(self):
        params = get_inference_params("Gemma-4-E4B-it-GGUF", output_type="code")
        assert params["model"] == "Gemma-4-E4B-it-GGUF"
        assert params["temperature"] == 0.7
        assert "thinking" in params["extra_body"]
        assert params["extra_body"]["thinking"]["budget_tokens"] > 0
        # 2260 overhead + 500 code headroom from the recipe
        assert params["max_tokens"] >= 500

    def test_non_thinking_model_no_extra_body(self):
        params = get_inference_params("llama3.2-1b-FLM", output_type="short_answer")
        assert "thinking" not in params["extra_body"]
        assert params["max_tokens"] > 0

    def test_qwen3_reasoning_not_treated_as_thinking_api(self):
        params = get_inference_params("Qwen3-8B-GGUF", output_type="code")
        # Qwen3 supports reasoning but not the Gemma-style thinking budget API.
        assert params["model"] == "Qwen3-8B-GGUF"
        assert "thinking" not in params["extra_body"]

    def test_unknown_model_fallback(self):
        params = get_inference_params("unknown-model", output_type="code")
        assert params["model"] == "unknown-model"
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 512
        assert params["extra_body"] == {}

    def test_system_prompt_per_task_type(self):
        params = get_inference_params(
            "DeepSeek-Qwen3-8B-GGUF", output_type="code", task_type="coding"
        )
        assert "coding" in params["system"].lower()


# ── Live discovery ────────────────────────────────────────────────────────────


class TestProbeLiveModels:
    def test_probe_live_models_success(self):
        fake = json.dumps({"data": [{"id": "Gemma-4-E4B-it-GGUF", "downloaded": True}]}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch(
            "cohezion.inference.lemonade_recipes.urllib.request.urlopen",
            return_value=mock_resp,
        ):
            models = probe_live_models(port=13305)

        assert models == [{"id": "Gemma-4-E4B-it-GGUF", "downloaded": True}]

    def test_probe_live_models_failure_returns_empty(self):
        with patch(
            "cohezion.inference.lemonade_recipes.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("no server"),
        ):
            models = probe_live_models(port=19999)
        assert models == []


class TestDiscoverFromLiveModels:
    def test_discovers_unknown_downloaded_model(self):
        new_models = [
            {
                "id": "Granite-4.1-8B-GGUF",
                "downloaded": True,
                "labels": ["coding"],
                "max_context_window": 32768,
            }
        ]
        added = discover_from_live_models(new_models)
        assert added == ["Granite-4.1-8B-GGUF"]
        recipe = get_recipe("Granite-4.1-8B-GGUF")
        assert recipe is not None
        assert recipe.family == "granite"
        assert recipe.context_window == 32768

    def test_skips_non_downloaded_models(self):
        new_models = [
            {
                "id": "Some-Huge-Model-GGUF",
                "downloaded": False,
                "labels": [],
                "max_context_window": 131072,
            }
        ]
        added = discover_from_live_models(new_models)
        assert added == []

    def test_does_not_overwrite_existing_recipe(self):
        existing = get_recipe("llama3.2-1b-FLM")
        new_models = [
            {
                "id": "llama3.2-1b-FLM",
                "downloaded": True,
                "labels": [],
                "max_context_window": 9999,
            }
        ]
        added = discover_from_live_models(new_models)
        assert added == []
        assert get_recipe("llama3.2-1b-FLM") is existing


# ── Recipe mutability helpers ─────────────────────────────────────────────────


class TestRegisterHelper:
    def test_register_adds_to_global_dict(self, isolate_registry):
        # The autouse fixture already backs up the registry; this test just
        # verifies the helper writes to the module dict.
        recipe = ModelRecipe(
            model_id="tmp-register-model",
            family="tmp",
            variant="1b",
            lane=Lane.CPU,
        )
        _register(recipe)
        assert LEMONADE_RECIPES["tmp-register-model"] is recipe
