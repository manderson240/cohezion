"""Discriminating tests for the deepseek-r1 / bonsai model-card entries (2026-07-28).

Both families previously matched NOTHING in `_MODEL_DEFAULTS` and fell through to `{}`.
For FLM (NPU) models that is the ONLY sampling surface they have -- FastFlowLM rejects sampling
flags in `flm_args` (verified: `flm_args flag is not allowed: --temp`), so a request-layer miss
means genuinely bare defaults.

The ORDERING test is the important one: DeepSeek-R1 distills contain both "deepseek-r1" and
"qwen3", and `_match_model` returns the FIRST substring hit in insertion order. Put the generic
qwen3 key first and the distills silently pick up `top_k=20`, which R1's card does not specify.
"""

from __future__ import annotations

from cohezion.inference.model_card_defaults import get_sampling_defaults


class TestDeepSeekR1:
    def test_flm_build_is_no_longer_unmatched(self):
        """DISCRIMINATING: this returned {} before the fix, i.e. bare defaults on the NPU."""
        d = get_sampling_defaults("deepseek-r1-0528-8b-FLM")
        assert d, "deepseek-r1 FLM must match a card entry, not fall through to {}"
        assert d["temperature"] == 0.6
        assert d["top_p"] == 0.95

    def test_r1_precedes_generic_qwen3_for_distills(self):
        """DISCRIMINATING: ordering.

        A DeepSeek-R1-Qwen3 distill matches BOTH keys. R1's card omits top_k; the generic qwen3
        entry sets top_k=20. If the generic key wins, this assertion fails -- which is exactly
        the silent misconfiguration the ordering comment exists to prevent.
        """
        d = get_sampling_defaults("DeepSeek-R1-0528-Qwen3-8B-GGUF")
        assert "top_k" not in d, f"generic qwen3 entry won the match: {d}"
        assert d["temperature"] == 0.6

    def test_plain_qwen3_still_gets_top_k(self):
        """The ordering fix must not strip top_k from genuine Qwen3 models."""
        d = get_sampling_defaults("Qwen3-8B-GGUF")
        assert d["top_k"] == 20


class TestBonsai:
    def test_bonsai_matches_registry_values(self):
        """DISCRIMINATING: returned {} before the fix.

        Values are lemonade's own, unanimous across all five shipped Bonsai entries.
        """
        d = get_sampling_defaults("Ternary-Bonsai-27B-gguf-PQ2_0")
        assert d == {"temperature": 0.7, "top_p": 0.9, "top_k": 40}

    def test_bonsai_case_insensitive(self):
        assert get_sampling_defaults("BONSAI-8B-GGUF")["top_k"] == 40


class TestNoRegression:
    def test_gemma4_unchanged(self):
        d = get_sampling_defaults("Gemma-4-E4B-it-GGUF")
        assert d == {"temperature": 1.0, "top_k": 64, "top_p": 0.95}

    def test_qwen36_specific_still_precedes_generic(self):
        d = get_sampling_defaults("Qwen3.6-35B-A3B-GGUF")
        assert d["top_p"] == 0.8, "qwen3.6-specific entry must still win over generic qwen3"

    def test_unknown_model_still_returns_empty(self):
        """Do NOT invent defaults for models whose card we have not grounded.

        Verified 2026-07-28 against primary sources: Llama-3.2-3B-Instruct's card specifies NO
        sampling parameters, and Mistral-Medium-3.5 is gated (401) with its quant mirror
        carrying none either. Both are therefore deliberately absent, not overlooked.
        """
        assert get_sampling_defaults("Ornith-1.0-35B-GGUF-Q4_K_M") == {}
        assert get_sampling_defaults("Soofi-S-Instruct-Preview-GGUF-Q4_K_M") == {}
        assert get_sampling_defaults("mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS") == {}


class TestNemotron:
    def test_nemotron_uses_tool_calling_regime(self):
        """DISCRIMINATING: the card gives TWO regimes and they differ.

        reasoning -> temp 1.0 / top_p 1.0 ; tool calling -> temp 0.6 / top_p 0.95.
        We take tool-calling (how lemonade labels this model). An implementation that grabbed
        the reasoning pair, or averaged them, fails here.
        """
        d = get_sampling_defaults("Nemotron-3-Nano-30B-A3B-GGUF")
        assert d == {"temperature": 0.6, "top_p": 0.95}

    def test_nemotron_has_no_invented_top_k(self):
        """The card specifies no top_k; adding one would be a guess."""
        assert "top_k" not in get_sampling_defaults("Nemotron-3-Nano-30B-A3B-GGUF")
