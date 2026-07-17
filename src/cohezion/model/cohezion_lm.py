"""Cohezion Language Model — HIHO-structured transformer for compound loop guidance.

Architecture:
  - Embedding: BPE tokenizer + positional encoding
  - Layers: N × HIHOTransformerLayer (HIHO attention + HIHO feed-forward)
  - Output: LM head with weight tying
  - Target task: predict high-quality compound loop guidance from task descriptions

Training data source:
  - autoresearch.jsonl: 80,000+ (task, guidance, output, quality_score) tuples
  - stealthskater corpus: 50+ physics concept descriptions
  - compound loop history: SurrealDB autodqa_results table

Hardware target (AMD Strix Halo):
  - Training: iGPU (Radeon 8060S, ROCm) + CPU (AVX-512, 16-core)
  - Inference: NPU (XDNA2) via GGUF export through llama.cpp ROCm

Model sizes (parameter count):
  - HIHO-Mini:  d=256, layers=4, heads=4, vocab=8192   ≈ 10M params (NPU target)
  - HIHO-Small: d=512, layers=8, heads=8, vocab=16384  ≈ 45M params (iGPU target)
  - HIHO-Base:  d=768, layers=12, heads=12, vocab=32768 ≈ 110M params (CPU target)

Design principles:
  - FLUME-First: all generated guidance passes through FLUME VAE encode → decode
  - HIHO gate: outputs with quality_score < 0.45 excluded from training data
  - Bi-temporal: model version tracked in SurrealDB with valid_from/valid_to
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CohezionLMConfig:
    """Configuration for the Cohezion Language Model.

    Parameters
    ----------
    d_model : int
        Hidden dimension size.
    n_layers : int
        Number of transformer layers.
    n_heads : int
        Number of attention heads.
    d_ff : int
        Feed-forward inner dimension (usually 4×d_model).
    vocab_size : int
        Vocabulary size.
    max_seq_len : int
        Maximum sequence length.
    dropout : float
        Dropout probability during training.
    model_name : str
        Human-readable model name (used for GGUF export).
    """

    d_model: int = 256
    n_layers: int = 4
    n_heads: int = 4
    d_ff: int = 1024
    vocab_size: int = 8192
    max_seq_len: int = 512
    dropout: float = 0.1
    model_name: str = "cohezion-hiho-mini"

    # Physics parameters embedded into the model
    hiho_threshold: float = 0.5
    beta_kl: float = 0.01  # A3 invariant: FLUME VAE regularization
    ffn_scale: float = 1.0  # HIHO FFN activation scale (exp_FFFF4: 8.0 optimal for byte_level)
    # exp_PPPP8: logit_shift prevents gradient vanishing at HIHO peak (x=0).
    # Use 0.5 for n_seeds=1 (prevents 100x divergence). Use 0.0 for n_seeds=3
    # (multi-seed selection already avoids diverging seeds, shift slightly hurts).
    logit_shift: float = 0.0

    @property
    def n_params(self) -> int:
        """Approximate parameter count."""
        embed = self.vocab_size * self.d_model
        per_layer = (
            4 * self.d_model * self.d_model  # Q, K, V, O projections
            + 2 * self.d_model * self.d_ff  # FF up + down
            + 4 * self.d_model  # LayerNorm params
        )
        # lm_head is weight-tied to token_embed — does not add extra params
        return embed + self.n_layers * per_layer

    @classmethod
    def mini(cls) -> CohezionLMConfig:
        """HIHO-Mini: ~10M params, NPU target (llama3.2-1b replacement)."""
        return cls(
            d_model=256,
            n_layers=4,
            n_heads=4,
            d_ff=1024,
            vocab_size=8192,
            model_name="cohezion-hiho-mini",
        )

    @classmethod
    def small(cls) -> CohezionLMConfig:
        """HIHO-Small: ~45M params, iGPU target."""
        return cls(
            d_model=512,
            n_layers=8,
            n_heads=8,
            d_ff=2048,
            vocab_size=16384,
            model_name="cohezion-hiho-small",
        )

    @classmethod
    def base(cls) -> CohezionLMConfig:
        """HIHO-Base: ~110M params, CPU (AVX-512) target."""
        return cls(
            d_model=768,
            n_layers=12,
            n_heads=12,
            d_ff=3072,
            vocab_size=32768,
            model_name="cohezion-hiho-base",
        )

    @classmethod
    def byte_level(cls) -> CohezionLMConfig:
        """Byte-level mini: vocab=256, aligned to UTF-8 byte tokenizer.

        exp_XXXX1: vocab=256 starts at loss≈log(256)=5.545 (vs 9.01 for vocab=8192).
        Use when training with the simple byte-level tokenizer in train.py.
        """
        return cls(
            d_model=256,
            n_layers=4,
            n_heads=4,
            d_ff=1024,
            vocab_size=256,
            model_name="cohezion-hiho-byte",
            ffn_scale=1.0,
        )


try:
    import torch
    import torch.nn as nn

    from cohezion.model.hiho_attention import HIHOTransformerLayer

    class CohezionLM(nn.Module):
        """Cohezion Language Model with HIHO-structured attention.

        Usage:
          config = CohezionLMConfig.mini()
          model = CohezionLM(config)
          logits = model(input_ids)

          # Training (next-token prediction)
          loss = model.loss(input_ids, target_ids)

          # Generation
          output = model.generate(prompt_ids, max_new=50)
        """

        def __init__(self, config: CohezionLMConfig):
            super().__init__()
            self.config = config

            self.token_embed = nn.Embedding(config.vocab_size, config.d_model)
            self.pos_embed = nn.Embedding(config.max_seq_len, config.d_model)
            self.dropout = nn.Dropout(config.dropout)

            self.layers = nn.ModuleList(
                [
                    HIHOTransformerLayer(
                        d_model=config.d_model,
                        n_heads=config.n_heads,
                        d_ff=config.d_ff,
                        dropout=config.dropout,
                        ffn_scale=config.ffn_scale,
                        logit_shift=config.logit_shift,
                    )
                    for _ in range(config.n_layers)
                ]
            )

            self.norm = nn.LayerNorm(config.d_model)
            # Weight-tied LM head (shares weights with token embedding)
            self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)
            self.lm_head.weight = self.token_embed.weight

            # Initialize weights
            self.apply(self._init_weights)
            logger.info(
                "CohezionLM initialized: %s | ~%dM params",
                config.model_name,
                config.n_params // 1_000_000,
            )

        def _init_weights(self, module: nn.Module) -> None:
            if isinstance(module, (nn.Linear, nn.Embedding)):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if isinstance(module, nn.Linear) and module.bias is not None:
                nn.init.zeros_(module.bias)

        def _causal_mask(self, seq_len: int, device: torch.device) -> torch.Tensor:
            """Generate causal (autoregressive) attention mask."""
            mask = torch.triu(
                torch.ones(seq_len, seq_len, dtype=torch.bool, device=device), diagonal=1
            )
            return mask.unsqueeze(0).unsqueeze(0)  # [1, 1, T, T]

        def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
            """Forward pass — returns logits [B, T, vocab_size]."""
            B, T = input_ids.shape
            assert self.config.max_seq_len >= T, (
                f"Sequence too long: {T} > {self.config.max_seq_len}"
            )

            device = input_ids.device
            positions = torch.arange(T, device=device).unsqueeze(0)  # [1, T]

            x = self.dropout(self.token_embed(input_ids) + self.pos_embed(positions))

            mask = self._causal_mask(T, device)
            for layer in self.layers:
                x = layer(x, mask=mask)

            x = self.norm(x)
            return self.lm_head(x)  # [B, T, vocab_size]

        def loss(
            self,
            input_ids: torch.Tensor,
            target_ids: torch.Tensor,
            quality_weight: torch.Tensor | None = None,
        ) -> torch.Tensor:
            """Next-token prediction loss with optional HIHO quality weighting.

            Parameters
            ----------
            input_ids : [B, T]
            target_ids : [B, T] (shifted by 1 from input)
            quality_weight : [B] optional quality score weights.
                High quality_score (near HIHO) = higher weight = more learning.
                Weight = γ(quality_score) = 4 × q × (1-q)
            """
            logits = self.forward(input_ids)  # [B, T, V]
            B, T, V = logits.shape

            loss = (
                torch.nn.functional.cross_entropy(
                    logits.reshape(B * T, V),
                    target_ids.reshape(B * T),
                    reduction="none",
                )
                .reshape(B, T)
                .mean(dim=1)
            )  # [B] per-sample loss

            if quality_weight is not None:
                # HIHO weighting: 4q(1-q) — maximum learning at q=0.5
                hiho_w = 4.0 * quality_weight * (1.0 - quality_weight)
                loss = (loss * hiho_w).mean()
            else:
                loss = loss.mean()

            return loss

        @torch.no_grad()
        def generate(
            self,
            prompt_ids: torch.Tensor,
            max_new: int = 128,
            temperature: float = 0.8,
            top_k: int = 50,
        ) -> torch.Tensor:
            """Autoregressive generation with temperature and top-k sampling."""
            self.eval()
            ids = prompt_ids.clone()
            for _ in range(max_new):
                # Crop to max_seq_len
                ids_cond = ids[:, -self.config.max_seq_len :]
                logits = self.forward(ids_cond)[:, -1, :]  # last token logits [B, V]
                logits = logits / temperature
                if top_k > 0:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = float("-inf")
                probs = torch.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, num_samples=1)  # [B, 1]
                ids = torch.cat([ids, next_id], dim=1)
            return ids

        def generate_text(
            self,
            prompt: str,
            max_new: int = 64,
            temperature: float = 0.8,
            top_k: int = 50,
        ) -> str:
            """Convenience: generate text from a string prompt using byte-level tokenization.

            Encodes prompt to UTF-8 bytes, runs generate(), decodes output back to string.
            Designed for CohezionLMConfig.byte_level() models (vocab_size=256).
            """
            import torch

            prompt_bytes = prompt.encode("utf-8")
            # Use BOS token (0) as seed for empty prompts to avoid empty-input crash
            byte_ids = list(prompt_bytes) if prompt_bytes else [0]
            prompt_ids = torch.tensor([byte_ids], dtype=torch.long)
            output_ids = self.generate(
                prompt_ids, max_new=max_new, temperature=temperature, top_k=top_k
            )
            new_ids = output_ids[0, len(byte_ids) :].tolist()
            return bytes(new_ids).decode("utf-8", errors="replace")

        def hiho_coherence(self, input_ids: torch.Tensor) -> float:
            """Measure model's HIHO coherence using the 4q(1-q) kernel on attention entropy.

            Applies the HIHO kernel to normalized attention entropy per layer:
              q = entropy / max_entropy  (normalized to [0, 1])
              hiho_weight = 4 * q * (1 - q)  (peaks at q=0.5 — selective attention)

            Returns:
              ~0.0 for random (near-uniform, q≈1) or overfitted (peaked, q≈0) models
              ~1.0 for HIHO-aligned models with selective-but-balanced attention
            """
            self.eval()
            with torch.no_grad():
                B, T = input_ids.shape
                positions = torch.arange(T, device=input_ids.device).unsqueeze(0)
                x = self.token_embed(input_ids) + self.pos_embed(positions)
                mask = self._causal_mask(T, input_ids.device)
                entropies = []
                for layer in self.layers:
                    q_norm = layer.norm1(x)
                    ent = layer.attn.hiho_entropy(q_norm, q_norm).item()
                    entropies.append(ent)
                    x = layer(x, mask=mask)
                max_entropy = math.log(T + 1) if T > 0 else 1.0
                # Apply HIHO kernel: peaks at q=0.5 (selective attention), 0 at extremes
                hiho_weights = [
                    4.0 * min(e / max_entropy, 1.0) * max(0.0, 1.0 - e / max_entropy)
                    for e in entropies
                ]
                return sum(hiho_weights) / max(1, len(hiho_weights))

        def hiho_score(self, text: str) -> float:
            """Compute HIHO score: 4q(1-q) where q = log(PPL) / log(vocab_size).

            Applies the HIHO coherence kernel to normalized perplexity.
            - q near 0 (very low PPL): model is very familiar with text → hiho_score→0
            - q near 0.5 (moderate PPL): HIHO midpoint → hiho_score=1.0
            - q near 1 (PPL near vocab_size): model finds text near-random → hiho_score→0

            exp_AAAA5 finding: sycophantic exclamation text has low hiho_score (0.008)
            because model (trained on technical text) finds it unusual.
            """
            ppl = self.hiho_perplexity(text)
            if not math.isfinite(ppl) or ppl <= 1.0:
                return 0.0
            floor = math.log(max(2, self.config.vocab_size))
            q = math.log(ppl) / floor
            q = max(0.0, min(1.0, q))
            return 4.0 * q * (1.0 - q)

        def hiho_perplexity(self, text: str, chunk_size: int = 64) -> float:
            """Compute byte-level perplexity on evaluation text.

            Splits text into chunks, computes mean cross-entropy loss, returns exp(loss).
            Lower perplexity = better model. Random baseline ≈ 256 (for byte-level vocab).
            """
            import torch

            encoded = text.encode("utf-8")
            if len(encoded) < 2:
                return float("inf")

            total_loss = 0.0
            count = 0
            self.eval()
            with torch.no_grad():
                for start in range(0, len(encoded) - 1, chunk_size):
                    chunk = list(encoded[start : start + chunk_size + 1])
                    if len(chunk) < 2:
                        continue
                    ids = torch.tensor([chunk], dtype=torch.long)
                    loss = self.loss(ids[:, :-1], ids[:, 1:])
                    total_loss += loss.item()
                    count += 1

            if count == 0:
                return float("inf")
            return math.exp(total_loss / count)

        @classmethod
        def from_autoresearch(
            cls,
            autoresearch_path: Path | None = None,
            steps: int = 80,
            lr: float | None = None,
            batch_size: int = 8,
            seq_len: int = 128,
            n_seeds: int = 3,
            config_override: CohezionLMConfig | None = None,
            freeze_deep_layers: bool = False,
            smart_seed: bool = False,
            lr_schedule: str = "cosine",
            optimizer: str = "rmsprop",
            seeds: list[int] | None = None,
            include_code: bool = True,
            sgdr_t0: int | None = None,
            n_code: int = 20,
            code_sample_weight: float = 1.0,
        ) -> CohezionLM:
            """Build and train a byte_level HIHO-LM on autoresearch winner history.

            Trains n_seeds models with different random seeds, returns the best one
            (lowest perplexity on a held-out eval set). exp_QQQQ5: seed variance is huge
            (PPL 28-252 across seeds) — multi-seed selection is essential.

            smart_seed=True: exp_WWWW9 — select best seed by initial embedding spread
            (<1ms) instead of training all n_seeds. Embedding spread (std of norms)
            correlates r=-0.661 with final PPL; highest spread = best convergence.

            freeze_deep_layers: exp_OOOO6 — freeze layers 2+ to eliminate backprop noise
            from zero-gradient layers. Improves PPL by ~7% at 2x speedup.

            lr_schedule: exp_BBBB0 — 'cosine' (default) gives 10.2% PPL improvement over
            constant LR. CosineAnnealingLR from lr to lr*0.01 over training steps.
            Use 'constant' to disable. Warmup adds no benefit for short runs (80 steps).

            optimizer: exp_EEEE0/FFFF0 — 'rmsprop' (default) gives 6.8-11.2% PPL improvement
            over AdamW. RMSprop auto-amplifies near-zero gradient updates in Layers 2-4
            (HIHO gradient vanishing fix). Default lr for rmsprop=5e-4 (exp_PPPP1: -7.6%
            vs 1e-3 on held-out NL — flatter minima generalize better); adamw=1e-2.

            Self-improving: each new autoresearch run adds to training data.
            """
            from pathlib import Path as _Path

            import torch
            import torch.optim as optim

            from cohezion.model.training_data import build_balanced_training_dataset

            path = _Path(autoresearch_path) if autoresearch_path else _Path("autoresearch.jsonl")
            config = (
                config_override if config_override is not None else CohezionLMConfig.byte_level()
            )

            # Train n_seeds models and return the best one
            # exp_GGGG1b: held-out eval phrase (verified not in autoresearch.jsonl)
            # Domain phrase that generalizes — NOT a training-data substring.
            _eval_text = "Compound engineering orchestrates multi-agent systems through coherent feedback loops"
            _all_seeds = seeds if seeds is not None else [42, 99, 1337, 7, 0]

            if smart_seed:
                # exp_WWWW9: select best seed by initial embedding spread (r=-0.661 with PPL)
                # Highest std(embedding norms) → best convergence. <1ms measurement.
                spreads = []
                for s in _all_seeds:
                    torch.manual_seed(s)
                    _m = cls(config)
                    with torch.no_grad():
                        spread = _m.token_embed.weight.norm(dim=1).std().item()
                    spreads.append((spread, s))
                # Pick the top seed (highest spread)
                _seed_candidates = [sorted(spreads, reverse=True)[0][1]]
                logger.info(
                    "smart_seed: selected seed=%d (spread=%.6f)",
                    _seed_candidates[0],
                    sorted(spreads, reverse=True)[0][0],
                )
            else:
                _seed_candidates = _all_seeds[:n_seeds]
            best_model = None
            best_ppl = float("inf")

            dataset = build_balanced_training_dataset(
                path, include_code=include_code, n_code=n_code
            )

            if not dataset.examples:
                logger.warning("from_autoresearch: no training examples found at %s", path)
                return cls(config)

            def _tokenize(text: str) -> torch.Tensor:
                enc = text.encode("utf-8")[: seq_len + 1]
                ids = list(enc) + [0] * max(0, seq_len + 1 - len(enc))
                return torch.tensor(ids[: seq_len + 1], dtype=torch.long)

            # exp_PPPP2: weighted pool construction — code examples sampled at code_sample_weight
            # fraction of domain rate. Prevents high n_code from starving domain gradient
            # (exp_OOOO2: 40 unweighted snippets → 12.7% code fraction → NL_mean +14.6%).
            base_mult = max(1, (steps * batch_size) // len(dataset.examples) + 2)
            if code_sample_weight != 1.0:
                pool = []
                for ex in dataset.examples:
                    mult = max(
                        1,
                        round(
                            base_mult * (code_sample_weight if ex.source == "code_corpus" else 1.0)
                        ),
                    )
                    pool.extend([ex] * mult)
            else:
                pool = dataset.examples * base_mult

            for seed in _seed_candidates:
                torch.manual_seed(seed)
                model = cls(config)
                if freeze_deep_layers and len(model.layers) > 1:
                    for layer in model.layers[1:]:
                        for p in layer.parameters():
                            p.requires_grad_(False)
                trainable = [p for p in model.parameters() if p.requires_grad]
                # exp_EEEE0/FFFF0: RMSprop (+6.8-11.2%) compensates HIHO gradient vanishing
                # exp_BBBB1: momentum=0.5, alpha=0.95 gives additional -18.2% PPL improvement
                # Momentum accumulates gradient history to push near-zero layers 2-4.
                # Default lr: rmsprop=1e-3, adamw=1e-2 (different optimal learning rates)
                # exp_PPPP1: lr=5e-4 gives -7.6% on held-out NL vs lr=1e-3 (flatter minima)
                _lr = lr if lr is not None else (5e-4 if optimizer == "rmsprop" else 1e-2)
                if optimizer == "rmsprop":
                    _opt = optim.RMSprop(trainable, lr=_lr, alpha=0.95, momentum=0.5)
                else:
                    _opt = optim.AdamW(trainable, lr=_lr, weight_decay=0.01)
                # exp_BBBB0: cosine decay gives 10.2% PPL improvement over constant LR
                # exp_PPPP0: 'sgdr' (CosineWarmRestarts T0=steps/4) gives -5.5% for steps>160
                if lr_schedule == "cosine":
                    scheduler: optim.lr_scheduler.LRScheduler | None = (
                        optim.lr_scheduler.CosineAnnealingLR(
                            _opt, T_max=max(1, steps), eta_min=_lr * 0.01
                        )
                    )
                elif lr_schedule == "sgdr":
                    _T0 = sgdr_t0 if sgdr_t0 is not None else max(20, steps // 4)
                    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
                        _opt, T_0=_T0, eta_min=_lr * 0.01
                    )
                else:
                    scheduler = None
                model.train()
                import random as _random

                _rng = _random.Random(seed)  # exp_SSSS0: shuffled sampling gives -4.3% PPL
                for _step in range(steps):
                    batch = _rng.sample(pool, batch_size)
                    ids_list = [_tokenize(f"{ex.instruction} {ex.response}") for ex in batch]
                    weights = torch.tensor([ex.hiho_weight for ex in batch], dtype=torch.float32)
                    ids_batch = torch.stack(ids_list)
                    loss = model.loss(ids_batch[:, :-1], ids_batch[:, 1:])
                    (loss * weights.mean()).clamp(min=1e-8).backward()
                    # exp_TTTT1: clip=0.5 gives -3.1% on held-out NL vs clip=1.0 (confirmed across 2 exps)
                    torch.nn.utils.clip_grad_norm_(trainable, 0.5)
                    _opt.step()
                    _opt.zero_grad()
                    if scheduler is not None:
                        scheduler.step()
                # Evaluate this candidate
                ppl = model.hiho_perplexity(_eval_text)
                if ppl < best_ppl:
                    best_ppl = ppl
                    best_model = model

            logger.info(
                "from_autoresearch: best of %d seeds | steps=%d | best_ppl=%.2f | examples=%d",
                n_seeds,
                steps,
                best_ppl,
                len(dataset),
            )
            return best_model

    _TORCH_AVAILABLE = True

except ImportError:
    _TORCH_AVAILABLE = False
    logger.info("PyTorch not available — CohezionLM stub only")

    class CohezionLM:  # type: ignore[no-redef]
        """Stub: PyTorch not installed."""

        def __init__(self, config: CohezionLMConfig):
            self.config = config
            logger.warning("CohezionLM: PyTorch not available — stub only")


def build_cohezion_lm(size: str = "mini") -> CohezionLM:
    """Factory function returning a CohezionLM of the specified size.

    Parameters
    ----------
    size : str
        'mini' (NPU, ~10M), 'small' (iGPU, ~45M), or 'base' (CPU, ~110M).
    """
    configs = {
        "mini": CohezionLMConfig.mini,
        "small": CohezionLMConfig.small,
        "base": CohezionLMConfig.base,
        "byte_level": CohezionLMConfig.byte_level,
    }
    if size not in configs:
        raise ValueError(f"Unknown size: {size!r}. Choose from: {list(configs)}")
    return CohezionLM(configs[size]())
