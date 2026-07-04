"""Tests for lemonade_recipes.py — structural invariants only.

These tests run without a live Lemonade daemon.
They guard:
  - All LLM BASE_RECIPES have ctx_size > 0 and ≤ 32768 (N3 OOM hazard)
  - Gemma-4-E2B uses llamacpp_backend="rocm" (intentional RDNA 3.5 path)
  - All other llamacpp models use llamacpp_backend="auto"
  - USER_VARIANTS checkpoint paths reference the correct base models
  - user.DeepSeek-Qwen3-8B-Reasoning does NOT accidentally point to the 35B checkpoint
"""

from cohezion.compound.lemonade_recipes import BASE_RECIPES, USER_VARIANTS


class TestBaseRecipeCtxSize:
    def test_all_have_ctx_size(self) -> None:
        for name, opts in BASE_RECIPES.items():
            assert "ctx_size" in opts, f"{name}: missing ctx_size"

    def test_no_ctx_size_zero(self) -> None:
        """ctx_size=0 triggers KV-cache OOM hang on Strix Halo (N3)."""
        for name, opts in BASE_RECIPES.items():
            ctx = opts.get("ctx_size")
            assert ctx != 0, f"{name}: ctx_size=0 is an OOM hazard"

    def test_ctx_size_positive(self) -> None:
        for name, opts in BASE_RECIPES.items():
            ctx = opts.get("ctx_size", 0)
            assert ctx > 0, f"{name}: ctx_size must be > 0"

    def test_ctx_size_bounded(self) -> None:
        """Heavy models must be ≤ 16384; MoE code/reasoning models may use 32768."""
        for name, opts in BASE_RECIPES.items():
            ctx = opts.get("ctx_size", 0)
            assert ctx <= 32768, (
                f"{name}: ctx_size={ctx} exceeds 32768 — likely an OOM risk"
            )

    def test_heavy_dense_models_ctx_le_16384(self) -> None:
        """Dense models ≥26B have full weight activation; 16384 is the safe ceiling."""
        dense_heavy = [
            "Qwen3.6-27B-GGUF",
            "Gemma-4-31B-it-GGUF",
        ]
        for name in dense_heavy:
            if name in BASE_RECIPES:
                ctx = BASE_RECIPES[name].get("ctx_size", 0)
                assert ctx <= 16384, f"{name}: dense heavy model, ctx={ctx} should be ≤16384"


class TestBaseRecipeBackend:
    def test_gemma_e2b_uses_rocm(self) -> None:
        """Gemma-4-E2B uses ROCm intentionally — RDNA 3.5 has better GEMM kernels."""
        opts = BASE_RECIPES["Gemma-4-E2B-it-GGUF"]
        assert opts.get("llamacpp_backend") == "rocm", (
            "Gemma-4-E2B must use llamacpp_backend='rocm'"
        )

    def test_all_other_llms_use_auto_backend(self) -> None:
        """Every model except Gemma-4-E2B should use 'auto' so Lemonade picks vulkan/cpu."""
        for name, opts in BASE_RECIPES.items():
            if name == "Gemma-4-E2B-it-GGUF":
                continue
            backend = opts.get("llamacpp_backend")
            assert backend == "auto", (
                f"{name}: expected llamacpp_backend='auto', got '{backend}'"
            )

    def test_no_hardcoded_vulkan(self) -> None:
        """Hardcoded 'vulkan' bypasses Lemonade's device probe and may fail on CPU fallback."""
        for name, opts in BASE_RECIPES.items():
            assert opts.get("llamacpp_backend") != "vulkan", (
                f"{name}: llamacpp_backend='vulkan' is hardcoded — use 'auto' instead"
            )


class TestBaseRecipeArgs:
    def test_all_have_llamacpp_args(self) -> None:
        for name, opts in BASE_RECIPES.items():
            assert "llamacpp_args" in opts, f"{name}: missing llamacpp_args"

    def test_batch_sizes_present_in_llm_args(self) -> None:
        """LLM models (not embedding) should have -b flag for prefill batch size."""
        embedding_models = {"nomic-embed-text-v2-moe-GGUF", "Qwen3-Embedding-0.6B-GGUF"}
        for name, opts in BASE_RECIPES.items():
            if name in embedding_models:
                continue
            args = opts.get("llamacpp_args", "")
            assert "-b " in args, f"{name}: missing -b batch-size flag in llamacpp_args"

    def test_embedding_models_have_pooling(self) -> None:
        embedding_models = {"nomic-embed-text-v2-moe-GGUF", "Qwen3-Embedding-0.6B-GGUF"}
        for name in embedding_models:
            if name in BASE_RECIPES:
                args = BASE_RECIPES[name].get("llamacpp_args", "")
                assert "--pooling" in args, f"{name}: embedding model missing --pooling"

    def test_thinking_models_have_preserve_thinking(self) -> None:
        """Reasoning models that support <think> mode should preserve their CoT."""
        reasoning_models = {
            "DeepSeek-Qwen3-8B-GGUF",
            "Qwen3.6-35B-A3B-MTP-GGUF",
        }
        for name in reasoning_models:
            if name in BASE_RECIPES:
                args = BASE_RECIPES[name].get("llamacpp_args", "")
                assert "preserve_thinking" in args, (
                    f"{name}: reasoning model should preserve thinking in llamacpp_args"
                )

    def test_no_thinking_base_model_has_disable_thinking(self) -> None:
        """Qwen3.6-35B-A3B-GGUF base defaults to NoThinking — disable to avoid blank outputs."""
        name = "Qwen3.6-35B-A3B-GGUF"
        if name in BASE_RECIPES:
            args = BASE_RECIPES[name].get("llamacpp_args", "")
            assert "enable_thinking" in args, (
                f"{name}: base 35B should have enable_thinking:false to avoid CoT scaffold"
            )


class TestBaseRecipeCount:
    def test_recipe_count(self) -> None:
        """17 LLM models with crafted recipes."""
        assert len(BASE_RECIPES) == 17, (
            f"Expected 17 BASE_RECIPES, got {len(BASE_RECIPES)}. "
            "Update this count if you intentionally add/remove a model."
        )


class TestUserVariants:
    def test_variant_count(self) -> None:
        assert len(USER_VARIANTS) == 5, (
            f"Expected 5 USER_VARIANTS, got {len(USER_VARIANTS)}"
        )

    def test_all_have_model_name(self) -> None:
        for v in USER_VARIANTS:
            assert "model_name" in v, f"USER_VARIANT missing model_name: {v}"

    def test_all_model_names_have_user_prefix(self) -> None:
        for v in USER_VARIANTS:
            name = v.get("model_name", "")
            assert name.startswith("user."), (
                f"{name}: user variant must start with 'user.'"
            )

    def test_all_have_checkpoint_or_checkpoints(self) -> None:
        for v in USER_VARIANTS:
            name = v.get("model_name", "?")
            has_ckpt = "checkpoint" in v or "checkpoints" in v
            assert has_ckpt, f"{name}: must have 'checkpoint' or 'checkpoints'"

    def test_all_have_recipe_options(self) -> None:
        for v in USER_VARIANTS:
            name = v.get("model_name", "?")
            assert "recipe_options" in v, f"{name}: missing recipe_options"
            ro = v.get("recipe_options") or {}
            assert "ctx_size" in ro, f"{name}: recipe_options missing ctx_size"
            ctx = ro.get("ctx_size", 0)
            assert ctx > 0, f"{name}: ctx_size must be > 0"
            assert ctx <= 32768, f"{name}: ctx_size={ctx} exceeds 32768"

    def test_deepseek_8b_checkpoint_is_not_35b(self) -> None:
        """Bug fix guard: user.DeepSeek-Qwen3-8B-Reasoning had the wrong 35B checkpoint."""
        for v in USER_VARIANTS:
            if v.get("model_name") == "user.DeepSeek-Qwen3-8B-Reasoning":
                ckpt = v.get("checkpoint", "")
                assert "35B" not in ckpt, (
                    f"user.DeepSeek-Qwen3-8B-Reasoning checkpoint points to a 35B model: {ckpt!r}. "
                    "This is a regression of the checkpoint-mismatch bug."
                )
                assert "DeepSeek" in ckpt or "deepseek" in ckpt.lower(), (
                    f"user.DeepSeek-Qwen3-8B-Reasoning checkpoint should be a DeepSeek 8B model: {ckpt!r}"
                )
                assert "8B" in ckpt or "8b" in ckpt.lower(), (
                    f"user.DeepSeek-Qwen3-8B-Reasoning checkpoint should be an 8B model: {ckpt!r}"
                )
                return
        names = [v.get("model_name") for v in USER_VARIANTS]
        assert False, f"user.DeepSeek-Qwen3-8B-Reasoning not found in USER_VARIANTS: {names}"

    def test_35b_variants_use_correct_checkpoint(self) -> None:
        """35B variants should point to Qwen3.6-35B, not DeepSeek or another model."""
        for v in USER_VARIANTS:
            name = v.get("model_name", "")
            if "35B" in name:
                ckpt = v.get("checkpoint") or str(v.get("checkpoints", ""))
                assert "Qwen3.6-35B" in ckpt or "Qwen3.6-35B" in str(ckpt), (
                    f"{name}: 35B variant should point to Qwen3.6-35B checkpoint, got: {ckpt!r}"
                )

    def test_gemma_26b_variant_has_ngram_spec(self) -> None:
        """Gemma-4-26B NoThinking variant should retain ngram speculative decoding."""
        for v in USER_VARIANTS:
            if v.get("model_name") == "user.Gemma-4-26B-A4B-NoThinking":
                ro = v.get("recipe_options") or {}
                args = ro.get("llamacpp_args", "")
                assert "spec-type ngram" in args, (
                    "Gemma-4-26B-NoThinking variant should include ngram spec-decode"
                )
                return
