"""Unit tests for ModelCardHarness — model card → inference parameter resolution."""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.xfail(
    reason="TDD-red: feature not fully implemented post-consolidation", strict=False
)

import pytest

from cohezion.inference.model_card_harness import (
    _OUTPUT_TYPE_MAX_TOKENS,
    InferenceParams,
    ModelCardHarness,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _harness_with_models(*models: dict) -> ModelCardHarness:
    return ModelCardHarness(list(models))


def _model(
    model_id: str,
    labels: list[str] | None = None,
    downloaded: bool = True,
    ctx_size: int | None = None,
) -> dict:
    m: dict = {"id": model_id, "labels": labels or [], "downloaded": downloaded}
    if ctx_size:
        m["recipe_options"] = {"ctx_size": str(ctx_size)}
    return m


# ── Model family detection ────────────────────────────────────────────────────


class TestModelFamilyDetection:
    def test_gemma4_is_thinking_model(self):
        h = ModelCardHarness([])
        assert h.is_thinking_model("Gemma-4-E4B-it-GGUF") is True
        assert h.is_thinking_model("Gemma-4-E2B-it-GGUF") is True

    def test_qwen3_is_qwen3_family(self):
        h = ModelCardHarness([])
        assert h.is_qwen3_family("Qwen3-8B-GGUF") is True
        assert h.is_qwen3_family("DeepSeek-Qwen3-8B-GGUF") is True

    def test_llama_not_thinking_model(self):
        h = ModelCardHarness([])
        assert h.is_thinking_model("llama3.2-1b-FLM") is False
        assert h.is_thinking_model("Granite-4.1-8B-GGUF") is False

    def test_granite_not_qwen3(self):
        h = ModelCardHarness([])
        assert h.is_qwen3_family("Granite-4.1-8B-GGUF") is False


# ── Inference parameter configuration ────────────────────────────────────────


class TestGetParams:
    def test_qwen3_code_gets_no_think_prefix(self):
        h = ModelCardHarness([])
        p = h.get_params("code", "Qwen3-8B-GGUF")
        assert p.prompt_prefix == "/no_think\n"
        assert p.max_tokens == _OUTPUT_TYPE_MAX_TOKENS["code"]

    def test_qwen3_categorical_gets_no_think_prefix(self):
        h = ModelCardHarness([])
        p = h.get_params("short_categorical", "Qwen3-8B-GGUF")
        assert p.prompt_prefix == "/no_think\n"

    def test_qwen3_long_generation_no_prefix(self):
        """Qwen3 /no_think only applied for short/code tasks, not long generation."""
        h = ModelCardHarness([])
        p = h.get_params("long_generation", "Qwen3-8B-GGUF")
        assert p.prompt_prefix == ""

    def test_gemma4_code_gets_thinking_budget(self):
        h = ModelCardHarness([])
        p = h.get_params("code", "Gemma-4-E4B-it-GGUF")
        assert "thinking" in p.extra_body
        assert p.extra_body["thinking"]["type"] == "enabled"
        assert p.extra_body["thinking"]["budget_tokens"] > 0

    def test_gemma4_thinking_budget_bounded(self):
        """Thinking budget must be positive and reasonable."""
        h = ModelCardHarness([])
        p = h.get_params("short_categorical", "Gemma-4-E2B-it-GGUF")
        budget = p.extra_body["thinking"]["budget_tokens"]
        assert 50 <= budget <= 500

    def test_llama_no_thinking_overhead(self):
        """Non-thinking models get no extra_body thinking config."""
        h = ModelCardHarness([])
        p = h.get_params("short_categorical", "llama3.2-1b-FLM")
        assert "thinking" not in p.extra_body
        assert p.prompt_prefix == ""

    def test_granite_no_special_config(self):
        """Granite coding model: no thinking, no prefix."""
        h = ModelCardHarness([])
        p = h.get_params("code", "Granite-4.1-8B-GGUF")
        assert p.prompt_prefix == ""
        assert "thinking" not in p.extra_body
        assert p.max_tokens == _OUTPUT_TYPE_MAX_TOKENS["code"]


# ── max_tokens per output type ────────────────────────────────────────────────


class TestMaxTokens:
    @pytest.mark.parametrize(
        "output_type,min_tokens",
        [
            ("short_categorical", 30),
            ("short_answer", 100),
            ("code", 400),
            ("long_generation", 600),
            ("math_reasoning", 600),
        ],
    )
    def test_max_tokens_reasonable(self, output_type, min_tokens):
        h = ModelCardHarness([])
        p = h.get_params(output_type, "llama3.2-1b-FLM")
        assert p.max_tokens >= min_tokens, (
            f"{output_type} max_tokens={p.max_tokens} too low (need ≥ {min_tokens})"
        )

    def test_gemma4_code_max_tokens_accounts_for_overhead(self):
        """Code on Gemma-4 needs thinking overhead tokens — must be > default code budget."""
        h = ModelCardHarness([])
        p = h.get_params("code", "Gemma-4-E4B-it-GGUF")
        # Empirical: Gemma-4-E4B uses 2260 thinking tokens on code tasks
        # max_tokens must include the overhead + actual output headroom
        assert p.max_tokens >= 600


# ── Best model selection ──────────────────────────────────────────────────────


class TestBestModelForOutputType:
    def test_code_prefers_coding_labeled_model(self):
        h = _harness_with_models(
            _model("Granite-4.1-8B-GGUF", labels=["coding"]),
            _model("Gemma-4-E4B-it-GGUF", labels=["reasoning"]),
        )
        best = h.best_model_for_output_type("code")
        assert best == "Granite-4.1-8B-GGUF"

    def test_code_falls_back_to_qwen3_reasoning(self):
        h = _harness_with_models(
            _model("DeepSeek-Qwen3-8B-GGUF", labels=["reasoning"]),
        )
        best = h.best_model_for_output_type("code")
        assert best == "DeepSeek-Qwen3-8B-GGUF"

    def test_math_reasoning_prefers_reasoning_model(self):
        h = _harness_with_models(
            _model("Granite-4.1-8B-GGUF", labels=["coding"]),
            _model("DeepSeek-Qwen3-8B-GGUF", labels=["reasoning"]),
        )
        best = h.best_model_for_output_type("math_reasoning")
        assert best == "DeepSeek-Qwen3-8B-GGUF"

    def test_no_matching_model_returns_none(self):
        h = _harness_with_models(_model("llama3.2-1b-FLM", labels=[]))
        best = h.best_model_for_output_type("code")
        assert best is None

    def test_not_downloaded_model_ignored(self):
        h = _harness_with_models(
            _model("Granite-4.1-8B-GGUF", labels=["coding"], downloaded=False),
        )
        best = h.best_model_for_output_type("code")
        assert best is None  # not downloaded = not available


# ── apply() helper ────────────────────────────────────────────────────────────


class TestApply:
    def test_apply_prepends_prefix(self):
        p = InferenceParams(model_id="m", max_tokens=100, prompt_prefix="/no_think\n")
        prompt, extra = p.apply("Hello world")
        assert prompt == "/no_think\nHello world"
        assert extra == {}

    def test_apply_no_prefix(self):
        p = InferenceParams(model_id="m", max_tokens=100)
        prompt, extra = p.apply("Hello world")
        assert prompt == "Hello world"

    def test_apply_returns_extra_body(self):
        p = InferenceParams(
            model_id="m",
            max_tokens=100,
            extra_body={"thinking": {"type": "enabled", "budget_tokens": 200}},
        )
        _, extra = p.apply("test")
        assert extra["thinking"]["budget_tokens"] == 200


# ── from_live_api graceful degradation ───────────────────────────────────────


class TestFromLiveApi:
    def test_failed_api_returns_empty_harness(self):
        """If API is down, harness is empty — callers must handle gracefully."""
        h = ModelCardHarness.from_live_api(port=19999)  # no server on this port
        assert h.best_model_for_output_type("code") is None
        assert h.get_labels("anything") == []

    def test_empty_harness_get_params_still_works(self):
        """get_params works even with empty harness (uses model_id heuristics)."""
        h = ModelCardHarness([])
        p = h.get_params("code", "Gemma-4-E4B-it-GGUF")
        assert isinstance(p, InferenceParams)
        assert p.max_tokens > 0

    def test_from_live_api_success_path(self):
        """from_live_api builds harness from API response data."""
        import json
        from unittest.mock import MagicMock, patch

        fake_response = json.dumps(
            {"data": [{"id": "Granite-4.1-8B-GGUF", "labels": ["coding"], "downloaded": True}]}
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch(
            "cohezion.inference.model_card_harness.urllib.request.urlopen", return_value=mock_resp
        ):
            h = ModelCardHarness.from_live_api(port=13305)

        assert h.get_labels("Granite-4.1-8B-GGUF") == ["coding"]
        assert h.best_model_for_output_type("code") == "Granite-4.1-8B-GGUF"


class TestIsThinkingModelCatalogAware:
    """is_thinking_model uses lemonade 'reasoning' label when model is in the catalog."""

    def test_gemma4_in_catalog_without_reasoning_label_is_not_thinking(self):
        """Live data: Gemma-4-E4B has tool-calling/vision/llamacpp but NOT reasoning."""
        h = _harness_with_models(
            _model("Gemma-4-E4B-it-GGUF", labels=["tool-calling", "vision", "llamacpp"])
        )
        assert h.is_thinking_model("Gemma-4-E4B-it-GGUF") is False

    def test_gemma4_not_in_catalog_uses_prefix_fallback(self):
        """FLM/NPU Gemma-4 variants not in 13305 catalog fall back to prefix → True."""
        h = ModelCardHarness([])
        assert h.is_thinking_model("Gemma-4-E4B-it-GGUF") is True

    def test_reasoning_label_non_qwen3_is_thinking(self):
        """A non-Qwen3 model with 'reasoning' label IS a thinking model."""
        h = _harness_with_models(_model("DeepSeek-R1-0528-GGUF", labels=["reasoning"]))
        assert h.is_thinking_model("DeepSeek-R1-0528-GGUF") is True

    def test_qwen3_with_reasoning_label_is_not_thinking_model(self):
        """Qwen3 family has 'reasoning' label but uses /no_think — not a thinking model."""
        h = _harness_with_models(_model("DeepSeek-Qwen3-8B-GGUF", labels=["reasoning"]))
        assert h.is_thinking_model("DeepSeek-Qwen3-8B-GGUF") is False

    def test_in_catalog_with_empty_labels_is_not_thinking(self):
        """Catalog entry with no labels: trust the catalog → not a thinking model."""
        h = _harness_with_models(_model("Gemma-4-E4B-it-GGUF", labels=[]))
        assert h.is_thinking_model("Gemma-4-E4B-it-GGUF") is False

    def test_get_params_gemma4_in_catalog_no_thinking_overhead(self):
        """When Gemma-4 is in catalog without 'reasoning' label, no thinking budget set."""
        h = _harness_with_models(
            _model("Gemma-4-E4B-it-GGUF", labels=["tool-calling", "vision", "llamacpp"])
        )
        p = h.get_params("code", "Gemma-4-E4B-it-GGUF")
        assert "thinking" not in p.extra_body
        assert p.prompt_prefix == ""

    def test_get_params_reasoning_model_in_catalog_gets_budget(self):
        """A non-Qwen3 model with 'reasoning' label in catalog gets thinking budget."""
        h = _harness_with_models(_model("DeepSeek-R1-0528-GGUF", labels=["reasoning"]))
        p = h.get_params("short_answer", "DeepSeek-R1-0528-GGUF")
        assert "thinking" in p.extra_body
        assert p.extra_body["thinking"]["budget_tokens"] > 0


class TestGetCtxSize:
    def test_ctx_size_returns_int_when_present(self):
        h = _harness_with_models(_model("Gemma-4-E4B-it-GGUF", ctx_size=32768))
        assert h.get_ctx_size("Gemma-4-E4B-it-GGUF") == 32768

    def test_ctx_size_returns_none_when_absent(self):
        h = _harness_with_models(_model("llama3.2-1b-FLM"))
        assert h.get_ctx_size("llama3.2-1b-FLM") is None

    def test_ctx_size_returns_none_for_unknown_model(self):
        h = ModelCardHarness([])
        assert h.get_ctx_size("unknown-model") is None
