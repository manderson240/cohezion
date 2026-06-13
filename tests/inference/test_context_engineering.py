"""Unit tests for context_engineering — ModelCardRegistry exact-match and coverage."""

from __future__ import annotations

import pytest

from cohezion.inference.context_engineering import ModelCard, ModelCardRegistry


# ── ModelCardRegistry — exact match invariants ────────────────────────────────

# All 12 live models should return EXACT cards (no fuzzy match)
LIVE_MODELS_WITH_EXPECTED_CTX = [
    ("DeepSeek-R1-0528-Qwen3-8B-Q4_1", 32768),
    ("Gemma-4-26B-A4B-it-GGUF", 256000),
    ("Gemma-4-31B-it-GGUF", 32768),
    ("Gemma-4-E4B-it-GGUF", 32768),
    ("Gemma-4-E2B-it-GGUF", 32768),
    ("Qwen3-0.6B-GGUF", 2048),
    ("Qwen3-8B-GGUF", 4096),
    ("Qwen3.5-35B-A3B-GGUF", 32768),
    ("DeepSeek-Qwen3-8B-GGUF", 32768),
    ("gemma3-4b-FLM", 8192),
    ("gemma4-it-e2b-FLM", 4096),
    ("llama3.2-1b-FLM", 4096),
    ("qwen3.5-4b-FLM", 4096),
]


class TestModelCardRegistryExactMatch:
    @pytest.fixture
    def registry(self):
        return ModelCardRegistry()

    @pytest.mark.parametrize("model_id,expected_ctx", LIVE_MODELS_WITH_EXPECTED_CTX)
    def test_exact_match_returns_correct_card(self, registry, model_id, expected_ctx):
        """Each live model must return its OWN card (not a fuzzy-matched card)."""
        card = registry.get_card(model_id)
        assert card is not None, f"No card found for {model_id}"
        assert card.model_id == model_id, (
            f"Fuzzy match: {model_id} returned card for {card.model_id}"
        )
        assert card.context_window == expected_ctx, (
            f"{model_id}: context_window={card.context_window}, expected {expected_ctx}"
        )

    def test_no_gemma4b_gets_26b_context_window(self, registry):
        """Critical: 4B/2B models must NOT get 256K context window via fuzzy match."""
        for model_id in ("Gemma-4-E4B-it-GGUF", "Gemma-4-E2B-it-GGUF"):
            card = registry.get_card(model_id)
            assert card is not None
            assert card.context_window < 100000, (
                f"{model_id} got ctx={card.context_window} — likely got 26B card via fuzzy match"
            )

    def test_no_flm_model_gets_26b_card(self, registry):
        """FLM (NPU) models must not fuzzy-match to the 26B card (wrong family)."""
        for model_id in ("gemma3-4b-FLM", "gemma4-it-e2b-FLM", "qwen3.5-4b-FLM"):
            card = registry.get_card(model_id)
            assert card is not None
            assert card.model_id == model_id, f"{model_id} fuzzy-matched to {card.model_id}"
            assert card.context_window <= 8192, (
                f"FLM model {model_id} got unexpectedly large ctx={card.context_window}"
            )

    def test_llama_flm_has_npu_suitable_defaults(self, registry):
        """llama3.2-1b-FLM is the primary NPU model — verify NPU-appropriate settings."""
        card = registry.get_card("llama3.2-1b-FLM")
        assert card is not None
        assert card.context_window <= 4096, "1B NPU model should have small context window"
        assert card.max_tokens_default <= 100, "NPU short-answer model should have small max_tokens"
        assert card.family == "llama"

    def test_unknown_model_returns_none(self, registry):
        """get_card returns None for completely unknown model families."""
        card = registry.get_card("totally-unknown-model-xyz-9000")
        assert card is None

    def test_register_card_adds_to_registry(self, registry):
        """Custom model cards can be registered at runtime."""
        new_card = ModelCard(
            model_id="custom-test-model",
            family="test",
            variant="7b",
            context_window=16384,
        )
        registry.register_card(new_card)
        retrieved = registry.get_card("custom-test-model")
        assert retrieved is not None
        assert retrieved.model_id == "custom-test-model"
        assert retrieved.context_window == 16384

    def test_update_from_live_api_unavailable_returns_zero(self, registry):
        """When Lemonade is unavailable, returns 0 without raising."""
        result = registry.update_from_live_api(port=19999)  # no server
        assert result == 0
        # Original cards must still be present
        assert registry.get_card("llama3.2-1b-FLM") is not None

    def test_update_from_live_api_live_server(self, registry):
        """Live Lemonade server should update cards with real ctx_size.

        Skips where no Lemonade server is reachable (e.g. CI); asserts the card
        contract when one is present.
        """
        result = registry.update_from_live_api(port=13305)
        if result == 0:
            pytest.skip("Lemonade server not reachable on :13305 — live infra unavailable")
        # Context windows should remain correct after update
        e4b = registry.get_card("Gemma-4-E4B-it-GGUF")
        assert e4b is not None
        assert e4b.context_window > 0


# ── Capability scores sanity ──────────────────────────────────────────────────


class TestCapabilityScores:
    @pytest.fixture
    def registry(self):
        return ModelCardRegistry()

    def test_deepseek_has_higher_reasoning_than_qwen3_base(self, registry):
        """DeepSeek-Qwen3-8B should have higher reasoning than plain Qwen3-8B."""
        ds = registry.get_card("DeepSeek-Qwen3-8B-GGUF")
        q3 = registry.get_card("Qwen3-8B-GGUF")
        assert ds is not None and q3 is not None
        assert ds.capabilities.reasoning >= q3.capabilities.reasoning

    def test_large_models_have_higher_reasoning(self, registry):
        """Larger models should generally have higher reasoning scores."""
        small = registry.get_card("llama3.2-1b-FLM")
        large = registry.get_card("DeepSeek-Qwen3-8B-GGUF")
        assert small is not None and large is not None
        assert large.capabilities.reasoning > small.capabilities.reasoning

    def test_all_capability_scores_in_range(self, registry):
        """All capability scores must be in [0, 1]."""
        for model_id, _ in LIVE_MODELS_WITH_EXPECTED_CTX:
            card = registry.get_card(model_id)
            assert card is not None
            for field_name in (
                "reasoning",
                "coding",
                "creativity",
                "instruction_following",
                "long_context",
                "multilingual",
            ):
                val = getattr(card.capabilities, field_name)
                assert 0.0 <= val <= 1.0, f"{model_id}.{field_name}={val} out of range [0,1]"
