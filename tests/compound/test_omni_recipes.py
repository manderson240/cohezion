"""Tests for LemonadeLoopRecipes — custom Omni model recipe registry.

Verifies:
- Category-aware model selection (lint_fix → Gemma-4-E4B, test_fix → Omni planner)
- Graceful degradation when Lemonade is offline (register_all is non-blocking)
- model_for_category returns (model_name, system_role) — never empty
- N3 compliance: all heavy recipes specify ctx_size=16384
- System role is non-empty for every registered recipe
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _make_registry(base_url: str = "http://localhost:19999"):
    from cohezion.compound.autonomous_loop.omni_recipes import LemonadeLoopRecipes

    return LemonadeLoopRecipes(base_url=base_url)


class TestCategoryAwareSelection:
    def test_lint_fix_routes_to_gemma(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import FAST_FALLBACK_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "lint_fix",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == FAST_FALLBACK_MODEL
        assert role  # non-empty system role

    def test_test_fix_routes_to_omni_planner(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import OMNI_PLANNER_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "test_fix",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == OMNI_PLANNER_MODEL
        assert "test" in role.lower()

    def test_type_fix_routes_to_omni_planner(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import OMNI_PLANNER_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "type_fix",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == OMNI_PLANNER_MODEL

    def test_unknown_category_falls_back_to_omni_planner(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import OMNI_PLANNER_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "exotic_category",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == OMNI_PLANNER_MODEL

    def test_lint_fix_degrades_to_omni_when_gemma_unavailable(self) -> None:
        """If Gemma-4-E4B is not loaded, lint_fix still gets a valid model."""
        from cohezion.compound.autonomous_loop.omni_recipes import OMNI_PLANNER_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "lint_fix",
            available_models=["Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        # Gemma not available → walks to next recipe that IS available
        assert model in (OMNI_PLANNER_MODEL, "Gemma-4-E4B-it-GGUF")
        assert role

    def test_nothing_available_still_returns_valid_model(self) -> None:
        """Even with empty available_models, must return a non-empty tuple."""
        registry = _make_registry()
        model, role = registry.model_for_category("lint_fix", available_models=[])
        assert model
        assert role

    def test_none_available_models_allows_any(self) -> None:
        """available_models=None disables the availability filter."""
        from cohezion.compound.autonomous_loop.omni_recipes import FAST_FALLBACK_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category("lint_fix", available_models=None)
        assert model == FAST_FALLBACK_MODEL


class TestN3Compliance:
    def test_all_heavy_recipes_have_safe_ctx_size(self) -> None:
        """N3: heavy models must never have ctx_size=0 or ctx_size > 16384."""
        from cohezion.compound.autonomous_loop.omni_recipes import (
            ALL_RECIPES,
            SAFE_CTX_SIZE,
        )

        for recipe in ALL_RECIPES:
            if recipe.heavy:
                assert recipe.ctx_size == SAFE_CTX_SIZE, (
                    f"{recipe.model_name} has ctx_size={recipe.ctx_size}, "
                    f"expected {SAFE_CTX_SIZE} (N3 compliance)"
                )

    def test_no_recipe_has_ctx_size_zero(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import ALL_RECIPES

        for recipe in ALL_RECIPES:
            assert recipe.ctx_size > 0, f"{recipe.model_name} has ctx_size=0 — OOM hazard"


class TestSystemRoles:
    def test_all_recipes_have_non_empty_system_role(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import ALL_RECIPES

        for recipe in ALL_RECIPES:
            assert recipe.system_role.strip(), (
                f"{recipe.model_name} has empty system_role — BMAD scaffolding missing"
            )

    def test_system_roles_are_distinct_per_category(self) -> None:
        """Different task types must get different personas — not the same generic prompt."""
        from cohezion.compound.autonomous_loop.omni_recipes import (
            FAST_LINTER,
            OMNI_PLANNER,
            TEST_SPECIALIST,
        )

        roles = {FAST_LINTER.system_role, TEST_SPECIALIST.system_role, OMNI_PLANNER.system_role}
        assert len(roles) == 3, "Recipes share a system role — personas are not distinct"


class TestRegistration:
    def test_register_all_non_blocking_when_offline(self) -> None:
        """register_all() must not raise even if Lemonade is unreachable."""
        registry = _make_registry()
        result = registry.register_all()  # Lemonade at :19999 is not running
        assert isinstance(result, int)
        assert result == 0  # nothing registered — server offline

    def test_register_all_returns_count_on_success(self) -> None:
        """When Lemonade accepts the POST, count should equal unique model names."""
        from cohezion.compound.autonomous_loop.omni_recipes import ALL_RECIPES

        registry = _make_registry()
        unique_models = len({r.model_name for r in ALL_RECIPES})

        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({"status": "ok"}).encode()

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = registry.register_all()

        assert result == unique_models

    def test_register_payload_includes_save_options_true(self) -> None:
        """N3: every POST to /api/v1/load must include save_options=true."""

        registry = _make_registry()
        captured_payloads: list[dict] = []

        def fake_urlopen(req, timeout=None):
            payload = json.loads(req.data)
            captured_payloads.append(payload)
            mock = MagicMock()
            mock.__enter__ = MagicMock(return_value=mock)
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = json.dumps({"status": "ok"}).encode()
            return mock

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            registry.register_all()

        for payload in captured_payloads:
            assert payload.get("save_options") is True, (
                f"Payload missing save_options=True: {payload}"
            )
            assert payload.get("ctx_size", 0) > 0, f"Payload has ctx_size=0 — OOM hazard: {payload}"


class TestQwopusCoder:
    """Qwopus3.6-27B-Coder preferred over 35B Omni for test_fix + type_fix when loaded.

    Qwopus3.6-27B-Coder (Jackrong/Qwopus3.6-27B-Coder, 67% SWE-bench Verified at
    Q5_K_M): smaller RAM footprint than Qwen3.6-35B-MTP, coding-specialized training.
    The recipe degrades gracefully to the 35B fallback when not loaded.
    """

    def test_qwopus_preferred_over_35b_for_test_fix_when_loaded(self) -> None:
        """Discriminating: if Qwopus IS in available_models, it wins over the 35B model."""
        from cohezion.compound.autonomous_loop.omni_recipes import QWOPUS_CODER

        registry = _make_registry()
        model, role = registry.model_for_category(
            "test_fix",
            available_models=[
                "Gemma-4-E4B-it-GGUF",
                "Qwopus3.6-27B-Coder-Q5_K_M",
                "Qwen3.6-35B-A3B-MTP-GGUF",
            ],
        )
        assert model == QWOPUS_CODER.model_name
        assert "coding" in role.lower() or "surgical" in role.lower()

    def test_qwopus_preferred_over_35b_for_type_fix_when_loaded(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import QWOPUS_CODER

        registry = _make_registry()
        model, _role = registry.model_for_category(
            "type_fix",
            available_models=["Qwopus3.6-27B-Coder-Q5_K_M", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == QWOPUS_CODER.model_name

    def test_qwopus_falls_back_to_35b_for_test_fix_when_absent(self) -> None:
        """If Qwopus is not loaded, test_fix degrades to Qwen3.6-35B-MTP (TEST_SPECIALIST)."""
        from cohezion.compound.autonomous_loop.omni_recipes import OMNI_PLANNER_MODEL

        registry = _make_registry()
        model, role = registry.model_for_category(
            "test_fix",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwen3.6-35B-A3B-MTP-GGUF"],
        )
        assert model == OMNI_PLANNER_MODEL
        assert "test" in role.lower()

    def test_qwopus_not_selected_for_lint_fix(self) -> None:
        """Qwopus recipe does not cover lint_fix — fast Gemma wins there."""
        from cohezion.compound.autonomous_loop.omni_recipes import FAST_FALLBACK_MODEL

        registry = _make_registry()
        model, _role = registry.model_for_category(
            "lint_fix",
            available_models=["Gemma-4-E4B-it-GGUF", "Qwopus3.6-27B-Coder-Q5_K_M"],
        )
        assert model == FAST_FALLBACK_MODEL

    def test_qwopus_recipe_has_safe_ctx_size(self) -> None:
        """N3 compliance: Qwopus is a 27B heavy model, must use SAFE_CTX_SIZE."""
        from cohezion.compound.autonomous_loop.omni_recipes import QWOPUS_CODER, SAFE_CTX_SIZE

        assert QWOPUS_CODER.heavy is True
        assert QWOPUS_CODER.ctx_size == SAFE_CTX_SIZE

    def test_qwopus_recipe_is_in_all_recipes(self) -> None:
        from cohezion.compound.autonomous_loop.omni_recipes import ALL_RECIPES, QWOPUS_CODER

        assert QWOPUS_CODER in ALL_RECIPES

    def test_qwopus_appears_before_test_specialist_in_all_recipes(self) -> None:
        """Priority: Qwopus must appear before TEST_SPECIALIST so it wins when loaded."""
        from cohezion.compound.autonomous_loop.omni_recipes import (
            ALL_RECIPES,
            QWOPUS_CODER,
            TEST_SPECIALIST,
        )

        names = [r.model_name for r in ALL_RECIPES]
        qwopus_idx = next(
            i for i, r in enumerate(ALL_RECIPES) if r.model_name == QWOPUS_CODER.model_name
        )
        specialist_idx = next(i for i, r in enumerate(ALL_RECIPES) if r is TEST_SPECIALIST)
        assert qwopus_idx < specialist_idx, (
            f"QWOPUS_CODER at index {qwopus_idx} must precede TEST_SPECIALIST "
            f"at index {specialist_idx} in ALL_RECIPES; got {names}"
        )
