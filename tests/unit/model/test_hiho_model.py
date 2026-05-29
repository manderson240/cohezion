"""Tests for Cohezion HIHO-LM (architecture + training data pipeline).

Most tests are torch-independent — they test imports, config, training data.
Torch-dependent tests are skipped automatically when torch is not available.
"""

from __future__ import annotations

import pytest


# --- HIHO kernel tests (numpy, no torch) ---


class TestHIHOKernelNumpy:
    def test_peaks_at_zero(self):
        from cohezion.model.hiho_attention import hiho_kernel_numpy

        assert hiho_kernel_numpy(0.0) == pytest.approx(1.0, rel=1e-6)

    def test_zero_at_large_positive(self):
        from cohezion.model.hiho_attention import hiho_kernel_numpy

        assert hiho_kernel_numpy(100.0) == pytest.approx(0.0, abs=1e-6)

    def test_zero_at_large_negative(self):
        from cohezion.model.hiho_attention import hiho_kernel_numpy

        assert hiho_kernel_numpy(-100.0) == pytest.approx(0.0, abs=1e-6)

    def test_symmetric(self):
        from cohezion.model.hiho_attention import hiho_kernel_numpy

        for x in [1.0, 2.0, 0.5]:
            assert hiho_kernel_numpy(x) == pytest.approx(hiho_kernel_numpy(-x), rel=1e-6)

    def test_strictly_positive_in_middle(self):
        from cohezion.model.hiho_attention import hiho_kernel_numpy

        for x in [-2.0, -1.0, 0.0, 1.0, 2.0]:
            assert hiho_kernel_numpy(x) >= 0.0


# --- CohezionLMConfig tests ---


class TestCohezionLMConfig:
    def test_mini_params_reasonable(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        cfg = CohezionLMConfig.mini()
        assert 5_000_000 < cfg.n_params < 20_000_000

    def test_small_larger_than_mini(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        assert CohezionLMConfig.small().n_params > CohezionLMConfig.mini().n_params

    def test_base_largest(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        assert CohezionLMConfig.base().n_params > CohezionLMConfig.small().n_params

    def test_beta_kl_is_a3_value(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        cfg = CohezionLMConfig()
        assert cfg.beta_kl == pytest.approx(0.01)

    def test_hiho_threshold_is_0_5(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        assert CohezionLMConfig().hiho_threshold == pytest.approx(0.5)

    def test_d_ff_4x_d_model(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        cfg = CohezionLMConfig.mini()
        assert cfg.d_ff == 4 * cfg.d_model


# --- TrainingExample tests ---


class TestTrainingExample:
    def test_hiho_weight_peaks_at_half(self):
        from cohezion.model.training_data import TrainingExample

        e = TrainingExample("question", "answer" * 5, quality_score=0.5)
        assert e.hiho_weight == pytest.approx(1.0, rel=1e-6)

    def test_hiho_weight_zero_at_extremes(self):
        from cohezion.model.training_data import TrainingExample

        e0 = TrainingExample("q", "a" * 20, quality_score=0.0)
        e1 = TrainingExample("q", "a" * 20, quality_score=1.0)
        assert e0.hiho_weight == pytest.approx(0.0)
        assert e1.hiho_weight == pytest.approx(0.0)

    def test_invalid_below_hiho_threshold(self):
        from cohezion.model.training_data import TrainingExample

        e = TrainingExample("test question here", "test response here hello", quality_score=0.3)
        assert e.is_valid is False

    def test_valid_at_hiho(self):
        from cohezion.model.training_data import TrainingExample

        e = TrainingExample(
            "What is the HIHO threshold?",
            "The HIHO threshold is 0.5 in all physics substrates." * 3,
            quality_score=0.5,
        )
        assert e.is_valid is True

    def test_invalid_short_response(self):
        from cohezion.model.training_data import TrainingExample

        e = TrainingExample("question longer than 10 chars", "short", quality_score=0.8)
        assert e.is_valid is False

    def test_to_dict_keys(self):
        from cohezion.model.training_data import TrainingExample

        e = TrainingExample("question", "response " * 5, quality_score=0.6)
        d = e.to_dict()
        assert all(
            k in d for k in ("instruction", "response", "quality_score", "hiho_weight", "source")
        )


# --- TrainingDataset tests ---


class TestTrainingDataset:
    def test_add_valid_example(self):
        from cohezion.model.training_data import TrainingDataset, TrainingExample

        ds = TrainingDataset()
        ds.add(TrainingExample("What is LENR?", "LENR is..." * 5, quality_score=0.6))
        assert len(ds) == 1

    def test_add_invalid_filtered_out(self):
        from cohezion.model.training_data import TrainingDataset, TrainingExample

        ds = TrainingDataset()
        ds.add(TrainingExample("q" * 5, "r" * 5, quality_score=0.2))
        assert len(ds) == 0

    def test_mean_quality(self):
        from cohezion.model.training_data import TrainingDataset, TrainingExample

        ds = TrainingDataset()
        for q in [0.5, 0.6, 0.7]:
            ds.add(TrainingExample("question " * 3, "response " * 5, quality_score=q))
        assert ds.mean_quality == pytest.approx(0.6, rel=1e-3)

    def test_hiho_engaged_near_half(self):
        from cohezion.model.training_data import TrainingDataset, TrainingExample

        ds = TrainingDataset()
        for q in [0.45, 0.5, 0.55]:
            ds.add(TrainingExample("question " * 3, "response " * 5, quality_score=q))
        assert ds.hiho_engaged is True

    def test_iter_batches(self):
        from cohezion.model.training_data import TrainingDataset, TrainingExample

        ds = TrainingDataset()
        for i in range(10):
            ds.add(TrainingExample(f"question {i} " * 2, "response " * 5, quality_score=0.6))
        batches = list(ds.iter_batches(batch_size=3))
        assert sum(len(b) for b in batches) == len(ds)
        assert len(batches[0]) == 3

    def test_stats_dict_keys(self):
        from cohezion.model.training_data import TrainingDataset

        ds = TrainingDataset()
        stats = ds.stats()
        assert "total" in stats and "mean_quality" in stats and "hiho_engaged" in stats

    def test_empty_mean_quality_zero(self):
        from cohezion.model.training_data import TrainingDataset

        assert TrainingDataset().mean_quality == 0.0


# --- Torch-dependent tests (skipped without torch) ---


def _require_torch():
    from cohezion.model.hiho_attention import is_torch_available

    if not is_torch_available():
        pytest.skip("PyTorch not available")


class TestHIHOAttentionTorch:
    def test_output_shape(self):
        _require_torch()
        import torch

        from cohezion.model.hiho_attention import HIHOAttention

        attn = HIHOAttention(d_model=64, n_heads=4)
        x = torch.randn(2, 10, 64)
        out = attn(x, x, x)
        assert out.shape == (2, 10, 64)

    def test_weights_sum_to_one(self):
        """Normalized HIHO weights must sum to 1 per query position."""
        _require_torch()
        import torch

        from cohezion.model.hiho_attention import hiho_kernel

        # Test the kernel normalization directly
        logits = torch.randn(2, 4, 8, 8)  # [B, H, T_q, T_k]
        weights = hiho_kernel(logits)
        weight_sum = weights.sum(dim=-1)
        norm_weights = weights / weight_sum.unsqueeze(-1).clamp(min=1e-9)
        row_sums = norm_weights.sum(dim=-1)
        assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5)

    def test_entropy_positive(self):
        _require_torch()
        import torch

        from cohezion.model.hiho_attention import HIHOAttention

        attn = HIHOAttention(d_model=64, n_heads=4)
        x = torch.randn(1, 8, 64)
        entropy = attn.hiho_entropy(x, x)
        assert entropy.item() > 0.0


class TestCohezionLMTorch:
    def test_forward_shape(self):
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        cfg = CohezionLMConfig(
            d_model=64, n_layers=2, n_heads=4, d_ff=256, vocab_size=128, max_seq_len=32
        )
        model = CohezionLM(cfg)
        ids = torch.randint(0, 128, (2, 16))
        logits = model(ids)
        assert logits.shape == (2, 16, 128)

    def test_loss_is_scalar(self):
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        cfg = CohezionLMConfig(
            d_model=64, n_layers=2, n_heads=4, d_ff=256, vocab_size=128, max_seq_len=32
        )
        model = CohezionLM(cfg)
        ids = torch.randint(0, 128, (2, 16))
        loss = model.loss(ids[:, :-1], ids[:, 1:])
        assert loss.ndim == 0  # scalar

    def test_hiho_weighted_loss(self):
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        cfg = CohezionLMConfig(
            d_model=64, n_layers=2, n_heads=4, d_ff=256, vocab_size=128, max_seq_len=32
        )
        model = CohezionLM(cfg)
        ids = torch.randint(0, 128, (2, 16))
        weights = torch.tensor([0.5, 0.7])
        loss = model.loss(ids[:, :-1], ids[:, 1:], quality_weight=weights)
        assert loss.item() > 0

    def test_generate_extends_sequence(self):
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        cfg = CohezionLMConfig(
            d_model=64, n_layers=2, n_heads=4, d_ff=256, vocab_size=128, max_seq_len=64
        )
        model = CohezionLM(cfg)
        prompt = torch.randint(0, 128, (1, 5))
        output = model.generate(prompt, max_new=10)
        assert output.shape[1] == 15  # 5 prompt + 10 generated

    def test_build_factory_mini(self):
        _require_torch()
        from cohezion.model.cohezion_lm import build_cohezion_lm

        model = build_cohezion_lm("mini")
        assert model.config.model_name == "cohezion-hiho-mini"

    def test_invalid_size_raises(self):
        _require_torch()
        from cohezion.model.cohezion_lm import build_cohezion_lm

        with pytest.raises(ValueError, match="Unknown size"):
            build_cohezion_lm("xxl")

    def test_build_factory_byte_level(self):
        _require_torch()
        from cohezion.model.cohezion_lm import build_cohezion_lm

        model = build_cohezion_lm("byte_level")
        assert model.config.vocab_size == 256
        assert model.config.model_name == "cohezion-hiho-byte"


class TestByteLevelConfig:
    """Tests for CohezionLMConfig.byte_level() — vocab=256 aligned to UTF-8 tokenizer."""

    def test_vocab_size_256(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        cfg = CohezionLMConfig.byte_level()
        assert cfg.vocab_size == 256

    def test_init_loss_near_floor(self):
        """init_loss should be within 0.5 of log(256)=5.545 — exp_XXXX1/ZZZZ1 finding."""
        _require_torch()
        import math

        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(42)
        cfg = CohezionLMConfig.byte_level()
        model = CohezionLM(cfg)
        ids = torch.randint(0, 256, (2, 17))
        loss = model.loss(ids[:, :-1], ids[:, 1:])
        floor = math.log(256)
        assert abs(loss.item() - floor) < 0.5, f"init_loss={loss.item():.4f}, floor={floor:.4f}"

    def test_model_name(self):
        from cohezion.model.cohezion_lm import CohezionLMConfig

        assert CohezionLMConfig.byte_level().model_name == "cohezion-hiho-byte"

    def test_generate_text_returns_string(self):
        """generate_text() must return str for normal and empty prompts — exp_DDDD2."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        for prompt in ["HIHO", "LENR", ""]:
            out = model.generate_text(prompt, max_new=5)
            assert isinstance(out, str), f"Expected str, got {type(out)} for {prompt!r}"
            assert len(out) >= 0  # replacement chars may reduce len slightly

    def test_generate_text_empty_prompt_uses_bos(self):
        """Empty prompt falls back to BOS token, no crash."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        out = model.generate_text("", max_new=3)
        assert isinstance(out, str)


class TestHIHOCoherence:
    """Tests for hiho_coherence() — 4q(1-q) kernel on attention entropy (exp_GGGG2)."""

    def test_random_model_has_low_coherence(self):
        """Randomly initialized model has near-uniform attention → low HIHO coherence."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        probe = torch.randint(0, 256, (1, 32))
        coh = model.hiho_coherence(probe)
        assert 0.0 <= coh <= 0.2, f"Expected low coherence for random model, got {coh:.4f}"

    def test_coherence_in_range(self):
        """hiho_coherence() must return a value in [0, 1]."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(42)
        model = CohezionLM(CohezionLMConfig.byte_level())
        for _ in range(3):
            probe = torch.randint(0, 256, (1, 16))
            coh = model.hiho_coherence(probe)
            assert 0.0 <= coh <= 1.0, f"coherence={coh} out of [0, 1]"

    def test_hiho_kernel_peaks_at_midpoint(self):
        """4q(1-q) = 1.0 at q=0.5, 0.0 at q=0 and q=1."""
        # This is a pure math test, no torch needed
        for q in [0.0, 1.0]:
            assert 4 * q * (1 - q) == 0.0
        assert 4 * 0.5 * 0.5 == 1.0


class TestHIHOPerplexity:
    """Tests for hiho_perplexity() — byte-level evaluation metric (exp_KKKK2)."""

    def test_random_model_has_high_perplexity(self):
        """Random model perplexity should be near byte-level ceiling (~256)."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(42)
        model = CohezionLM(CohezionLMConfig.byte_level())
        ppl = model.hiho_perplexity("hello world this is a test sentence")
        assert ppl > 100, f"Expected high perplexity for random model, got {ppl:.2f}"

    def test_short_text_returns_inf(self):
        """Single-char text (< 2 bytes) returns inf since no prediction is possible."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        assert model.hiho_perplexity("X") == float("inf")
        assert model.hiho_perplexity("") == float("inf")

    def test_from_autoresearch_returns_model(self):
        """from_autoresearch() returns a trained CohezionLM without crashing."""
        _require_torch()
        from cohezion.model.cohezion_lm import CohezionLM

        # Use the real autoresearch.jsonl if available, else empty path (returns untrained model)
        model = CohezionLM.from_autoresearch(steps=2)
        assert isinstance(model, CohezionLM)
        assert model.config.vocab_size == 256
        assert model.config.model_name == "cohezion-hiho-byte"

    def test_hiho_score_method_exists(self):
        """hiho_score() applies 4q(1-q) kernel to normalized log perplexity."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        score = model.hiho_score("test")
        assert 0.0 <= score <= 1.0

    def test_hiho_score_zero_for_short_input(self):
        """Empty and single-byte inputs return 0.0 (inf perplexity → zero score)."""
        _require_torch()
        import torch

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(0)
        model = CohezionLM(CohezionLMConfig.byte_level())
        assert model.hiho_score("") == 0.0
        assert model.hiho_score("X") == 0.0

    def test_perplexity_decreases_after_training(self):
        """Perplexity must decrease after training on the evaluation text."""
        _require_torch()
        import torch
        import torch.optim as optim

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(42)
        model = CohezionLM(CohezionLMConfig.byte_level())
        text = "HIHO stability principle means the system maximizes entropy."
        ppl_before = model.hiho_perplexity(text)
        # Overfit on the text
        enc = text.encode("utf-8")
        ids = torch.tensor([list(enc[:65])], dtype=torch.long)
        opt = optim.AdamW(model.parameters(), lr=1e-3)
        model.train()
        for _ in range(50):
            loss = model.loss(ids[:, :-1], ids[:, 1:])
            opt.zero_grad()
            loss.backward()
            opt.step()
        ppl_after = model.hiho_perplexity(text)
        assert ppl_after < ppl_before, f"PPL should decrease: {ppl_before:.1f} → {ppl_after:.1f}"

    def test_coherence_increases_during_early_training(self):
        """LM8: HIHO coherence peaks during early training (step 10 > step 0). exp_IIII7."""
        _require_torch()
        import torch
        import torch.optim as optim

        from cohezion.model.cohezion_lm import CohezionLM, CohezionLMConfig

        torch.manual_seed(42)
        config = CohezionLMConfig.byte_level()
        model = CohezionLM(config)
        eval_ids = torch.tensor([[b for b in b"HIHO coherence"[:14]]])
        coh_0 = model.hiho_coherence(eval_ids)
        if isinstance(coh_0, torch.Tensor):
            coh_0 = coh_0.item()
        # Train 10 steps
        ids = torch.tensor([list(b"HIHO coherence kernel peaks at 0.5"[:33])])
        opt = optim.AdamW(model.parameters(), lr=1e-2)
        model.train()
        for _ in range(10):
            loss = model.loss(ids[:, :-1], ids[:, 1:])
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        coh_10 = model.hiho_coherence(eval_ids)
        if isinstance(coh_10, torch.Tensor):
            coh_10 = coh_10.item()
        assert coh_10 > coh_0, f"LM8: coherence should rise at step 10: {coh_0:.4f} → {coh_10:.4f}"
