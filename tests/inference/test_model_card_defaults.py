"""Tests for model-card-aligned sampling defaults."""

from __future__ import annotations


from cohezion.inference.model_card_defaults import (
    apply_model_card_defaults,
    get_sampling_defaults,
)


class TestGetSamplingDefaults:
    def test_gemma4_returns_temp_and_topk(self):
        params = get_sampling_defaults("Gemma-4-E4B-it-GGUF")
        assert params["temperature"] == 1.0
        assert params["top_k"] == 64
        assert params["top_p"] == 0.95

    def test_qwen3_nonthinking_returns_low_temp(self):
        params = get_sampling_defaults("Qwen3.6-35B-A3B-GGUF")
        assert params["temperature"] == 0.7
        assert params["top_p"] == 0.8
        assert params["top_k"] == 20
        assert params["min_p"] == 0.0

    def test_qwen3_thinking_returns_thinking_params(self):
        params = get_sampling_defaults("Qwen3.6-35B-A3B-ThinkingCoder")
        # Thinking mode uses lower temp for more deterministic chain-of-thought
        assert params["temperature"] == 0.6
        assert params["top_k"] == 30

    def test_npu_model_returns_low_temp(self):
        params = get_sampling_defaults("llama3.2-1b-FLM")
        assert params["temperature"] == 0.3

    def test_unknown_model_returns_empty(self):
        params = get_sampling_defaults("some-unknown-model-xyz")
        assert params == {}

    def test_returns_copy_not_original(self):
        """Mutation of returned dict must not affect the registry."""
        params = get_sampling_defaults("Gemma-4-E4B-it-GGUF")
        params["temperature"] = 999.0
        params2 = get_sampling_defaults("Gemma-4-E4B-it-GGUF")
        assert params2["temperature"] == 1.0  # original unchanged


class TestApplyModelCardDefaults:
    def test_fills_missing_sampling_params(self):
        payload = {"model": "Gemma-4-E4B-it-GGUF", "messages": [], "max_tokens": 100}
        result = apply_model_card_defaults(payload)
        assert result["temperature"] == 1.0
        assert result["top_k"] == 64

    def test_does_not_override_explicit_temperature(self):
        """Caller-set temperature takes precedence over model card default."""
        payload = {
            "model": "Gemma-4-E4B-it-GGUF",
            "messages": [],
            "temperature": 0.0,  # caller wants deterministic
        }
        result = apply_model_card_defaults(payload)
        assert result["temperature"] == 0.0  # must not be overridden to 1.0

    def test_unknown_model_payload_unchanged(self):
        payload = {"model": "mystery-model", "messages": [], "max_tokens": 50}
        result = apply_model_card_defaults(payload)
        assert set(result.keys()) == {"model", "messages", "max_tokens"}

    def test_mutates_payload_in_place(self):
        payload = {"model": "Qwen3.6-35B-A3B-GGUF", "messages": []}
        result = apply_model_card_defaults(payload)
        assert result is payload  # same object

    def test_qwen3_all_sampling_params_applied(self):
        payload = {"model": "Qwen3.6-35B-A3B-NoThinking", "messages": []}
        apply_model_card_defaults(payload)
        assert payload["temperature"] == 0.7
        assert payload["top_p"] == 0.8
        assert payload["top_k"] == 20
        assert payload["min_p"] == 0.0
