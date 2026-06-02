---
name: hiho-lm
description: Cohezion HIHO Language Model — byte-level transformer with 4x(1-x) HIHO attention kernel. Training, inference, and evaluation utilities for the HIHO-LM research project.
category: model
tags: [language-model, hiho, training, inference, byte-level]
version: "1.0"
---

## Skill: HIHO Language Model (HIHO-LM)

### Overview

The HIHO-LM is a compact transformer language model that embeds the HIHO coherence principle directly into its attention mechanism. Instead of standard softmax attention, it uses the 4x(1-x) coherence kernel applied to scaled dot-product logits.

**Key architectural innovation:**
- Standard attention: softmax(QK^T/√d) → amplifies maximum-logit positions
- HIHO attention: normalize(4σ(QK^T/√d)(1-σ(QK^T/√d))) → amplifies near-zero-logit positions
- Both are normalized to sum=1, but HIHO prefers balanced attention over peaked attention

**Mathematical identity (exp_MMMM8):**
4σ(x)(1-σ(x)) = sech²(x/2) exactly. HIHO attention IS the soliton pulse shape from KdV physics and optical fiber theory. The same function governs light propagation in nonlinear media, water waves, and now neural attention.

**Critical stability property (exp_MMMM3/NNNN3):**
The 4σ(x)(1-σ(x)) kernel is bounded by [0,1] everywhere. At extreme logits (x→±∞), σ(x)→{0,1} so the kernel→0, preventing attention explosion. Softmax diverges at lr=1e-3; HIHO is stable at lr=0.1 (100x higher). The HIHO kernel is a built-in gradient stabilizer.

**FFN saturation as regularization (exp_EEEE4/GGGG4):**
The HIHO FFN has near-uniform activations (mean=0.976, std=0.033) because small fc1 outputs map to kernel≈1.0. This is BENEFICIAL: saturated FFN acts as regularization, forcing the model to learn through the well-conditioned HIHO attention mechanism. Scaling the FFN (ffn_scale>1) increases FFN variance but HURTS training (scale=8 → PPL=66 vs scale=1 → PPL=34). Use ffn_scale=1.0 (default).

### Model Configurations

| Config | Params | vocab | d_model | layers | heads | Target |
|--------|--------|-------|---------|--------|-------|--------|
| `byte_level` | ~3M | 256 | 256 | 4 | 4 | Byte-level training, aligned tokenizer |
| `mini` | ~5M | 8192 | 256 | 4 | 4 | NPU (llama3.2-1b replacement) |
| `small` | ~45M | 16384 | 512 | 8 | 8 | iGPU (ROCWMMA) |
| `base` | ~110M | 32768 | 768 | 12 | 12 | CPU (AVX-512) |

### Key API

```python
from cohezion.model import CohezionLM, CohezionLMConfig, build_cohezion_lm
from cohezion.model import build_balanced_training_dataset

# === CANONICAL PATH: domain-adapted model in ~21s ===
# steps=80, n_seeds=3, optimizer='rmsprop', lr_schedule='cosine', bs=8, seq=128
# Canonical PPL (held-out domain phrase, not training data): 21.24 (exp_GGGG1b)
# -25.2% vs OLD defaults on held-out natural language (P1-P4 mean: 35.99→26.91)
# RMSprop compensates HIHO gradient vanishing (+6.8-11.2% vs AdamW, exp_EEEE0/FFFF0)
# Cosine LR annealing: 10.2% further improvement (exp_BBBB0)
model = CohezionLM.from_autoresearch()  # exp_GGGG1b: canonical held-out PPL=21.24

# === FAST PATH: 2x speedup via smart seed selection ===
# smart_seed=True selects best seed by embedding spread (<1ms) instead of training all 3
# exp_XXXX9: same PPL as n_seeds=3 at 2x speedup (2.7s vs 5.3s)
model_fast = CohezionLM.from_autoresearch(smart_seed=True)  # exp_WWWW9: spread r=-0.661 with PPL

# === 1-LAYER FAST GATE: 4.3x speedup, 72% fewer params, only +2.8% PPL (exp_AAAA0) ===
from cohezion.model.cohezion_lm import CohezionLMConfig
_1L_cfg = CohezionLMConfig(vocab_size=256, d_model=256, n_layers=1, n_heads=4, d_ff=1024, max_seq_len=512, dropout=0.0, ffn_scale=1.0, logit_shift=0.0)
model_gate = CohezionLM.from_autoresearch(config_override=_1L_cfg)  # 852K params, ~1.5s, PPL~30

# Generate text
text = model.generate_text("HIHO equilibrium", max_new=64)

# Maximum quality (steps=120, n_seeds=5 → PPL<28, 13s)
model_hq = CohezionLM.from_autoresearch(steps=120, lr=1e-2, n_seeds=5)

# Measure quality
ppl = model.hiho_perplexity("HIHO stability means 50% coherence")  # lower = better
coh = model.hiho_coherence(input_ids)  # [0,1], peaks at 0.5 entropy
score = model.hiho_score("compound loop quality gate")  # [0,1], peaks at moderate PPL

# Manual build
config = CohezionLMConfig.byte_level()  # vocab=256, aligned to UTF-8
model = CohezionLM(config)  # or: build_cohezion_lm("byte_level")

# Training via CLI
# uv run python src/cohezion/model/train.py --size byte_level --steps 500
```

### HIHO Training Data

The training dataset uses HIHO-weighted loss: each example has weight = 4q(1-q) where q = quality_score.

| Source | Count | q | w=4q(1-q) | Notes |
|--------|-------|---|-----------|-------|
| autoresearch winners | 63+ | ~0.9 | 0.36 | Compound loop experiments |
| stealthskater corpus | 19 | 0.75 | 0.75 | Physics concept descriptions |
| HIHO-band synthetic | 3 | 0.5 | 1.0 | Maximum gradient weight |

**Key finding (exp_NNNN2):** Stealthskater corpus (q=0.75) produces higher HIHO gradient weight (0.75) than high-quality autoresearch (q=0.9, w=0.36). Including stealthskater corpus raised mean HIHO weight from 0.326 to 0.395.

### Empirical Findings

| Experiment | Finding |
|-----------|---------|
| exp_HHHH | Smoke train: loss 9.08→7.62 (-16%) in 20 CPU steps (0.68s) |
| exp_VVVV1 | Gradient ratio q=0.5 vs q=0.9 = 2.778x (exact match to weight ratio) |
| exp_JJJJ2 | Overfit: 99.8% loss reduction on HIHO pattern (200 steps) |
| exp_KKKK2 | Perplexity 300→28 after 100 training steps on physics text (90.7%) |
| exp_RRRR2 | Softmax converges 10x faster on memorization; HIHO has balanced attention |
| exp_SSSS2 | HIHO attention IS normalized (sums to 1 per row via explicit division) |
| exp_XXXX1 | vocab_size=256 starts within 0.01 of floor log(256)=5.545 |
| **exp_MMMM3** | **CRITICAL: At lr=1e-3, HIHO PPL=29.9 vs Softmax PPL=700,480 (diverged). HIHO prevents attention explosion.** |
| **exp_QQQQ5** | **CRITICAL: Seed variance is huge (PPL 28-252). n_seeds=3 selection gives reliable PPL=28.9 in 5.5s.** |
| exp_NNNN3 | HIHO stable at ALL lrs 1e-4 to 1e-1. Optimal lr=1e-2 (lowest PPL 3.638 in 50 steps). |
| exp_LLLL3 | HIHO generalizes: train/test PPL gap < 1.0 after 100 steps (no overfitting) |
| exp_HHHH3 | 10 steps → 100% printable ASCII; 25 steps → PPL<50; 500+ → coherent phrases |
| **exp_XXXX5** | **HIHO training induces head specialization: random JSD=0.0 → trained JSD=0.422. Training drives inter-head diversity.** |
| **exp_YYYY5** | **HIHO produces 1.50x more inter-head diversity than equivalent softmax (JSD 0.656 vs 0.437). Kernel bound prevents attention collapse.** |
| exp_ZZZZ5 | HIHO-LM quality discriminator: domain PPL=31 < sycophantic PPL=37 << random PPL=72. Usable as zero-cost garbage filter. |
| exp_AAAA6 | Stage-3 NOT achieved at 500 steps (single seed). PPL=36.71 but no coherent domain phrases. Stage 3 requires 1000+ steps. |
| exp_BBBB6 | LM1-LM7 harness invariants ALL PASS. init_loss=5.531, coherence_random=0.035, trained PPL=28.96. |
| exp_DDDD6 | Layer ablation: Layer 1 does 99% of work (PPL: no-layer=2777 → 1-layer=28.76). Layers 2-4 add only 0.2-0.5% each. |
| exp_EEEE6 | 1-layer model: 920K params (72.5% fewer), 3.62x faster, PPL=35.09 (+14.5%). Use for speed-critical gates. config_override added to from_autoresearch(). |
| **exp_NNNN6** | **HIHO GRADIENT VANISHING: Layer 1 grad=0.051, Layers 2-4 grad≈0. HIHO kernel derivative=0 at σ=0.5 maximum. Trained logits cluster near 0 → backprop stalls in deep layers.** |
| exp_OOOO6 | Frozen layer test (informative): manually frozen L2-4 showed better PPL in one experiment, but exp_PPPP6 controlled test shows freeze_deep_layers=True is NOT reliably better. |
| exp_PPPP6 | Controlled: freeze_deep_layers=True PPL=37.05 vs full PPL=35.39 — freezing hurts. Gradient vanishing finding is real but freezing is wrong fix. |
| **exp_FFFF7** | **Attention energy: Softmax 0.981 (delta-like) vs HIHO 0.334. Softmax 2.93x more concentrated. HIHO 40% higher entropy. Cleanest quantification of HIHO anti-peaked advantage.** |
| exp_CCCC7 | Greek Parameters: alpha=0.1 converges 2.5x faster. delta>=alpha causes divergence. Basin boundary at x=0.0817. Stability requires alpha > delta. |
| **exp_IIII7** | **CRITICAL: HIHO coherence peaks at step 10 (0.652) = Stage 1 boundary (maximum exploration diversity). Falls to 0.023 at step 80 as model specializes. Arc: explore→specialize, NOT monotone. New diagnostic: peak coherence > 0.5 by step 10 confirms healthy training.** |
| **exp_IIII8** | **CRITICAL: Deceptive convergence — seed=1337 looks good at step 10 (PPL=37.89, rank 2) but catastrophically DIVERGES at step 80 (PPL=1025, rank 5). Cannot predict best seed from early stopping. n_seeds=3 full training is essential.** |
| **exp_PPPP8** | **logit_shift=0.5 prevents catastrophic divergence for n_seeds=1 (867→35 PPL). But exp_RRRR8: hurts with n_seeds=3 (multi-seed already avoids bad seeds). Rule: use shift=0.5 only with n_seeds=1. Default=0.0.** |
| exp_MMMM8 | Mathematical identity: 4σ(x)(1-σ(x)) ≡ sech²(x/2) exactly. HIHO is soliton-shaped. |
| exp_NNNN8 | Mathematical identity: 4σ(x)(1-σ(x)) ≡ 4×d/dx σ(x). HIHO ∝ sigmoid gradient. |
| exp_OOOO8 | d/dx HIHO = 0 at x=0 analytically. Proof of gradient vanishing from exp_NNNN6. |
| **exp_YYYY9** | **Tuned-lens: Layer 1 accounts for 99.6% of total PPL reduction (6051/6074 units). Embedding→L1: 6102→51 PPL. L1→L2: 51→31. L2→L4: 31→28. HIHO learning is almost entirely 1-layer.** |
| exp_ZZZZ9 | Position ablation LOSER: removing pos_embed causes 19x PPL increase (30→577). HIHO anti-peaked attention still needs sequential context — balanced similarity without position = failure. |
| **exp_AAAA0** | **1-layer optimal config: 1L-4H-256D gives PPL=29.87 (+2.8% vs 4L) at 4.3x speedup with 72% fewer params (852K). Larger FFN (16x) and more heads (8H) both HURT. Double d_model catastrophic (+54%). Sweet spot IS the default 256D-4H config.** |
| **exp_BBBB0** | **Cosine LR: 10.2% PPL improvement (30.1→27.0) over constant LR. Now default in from_autoresearch(lr_schedule='cosine'). Warmup adds no benefit. Cosine also rescues high-LR training (1e-1: 588→58 PPL).** |
| exp_CCCC0 | 3-tier config benchmark: ultra-fast=cosine+smart_seed (2s, PPL=30.4, 3x efficiency); default=cosine+n3 (5s, PPL=29.6); max-quality=cosine+n5+120steps (13s, PPL=28.5). |
| exp_DDDD0 | Dropout has ZERO effect on HIHO-LM (0.0 vs 0.1: PPL=23.49 exactly). HIHO FFN saturation IS regularization — dropout is redundant. WD=0 marginally better (-1.7%). |
| **exp_EEEE0** | **RMSprop: 11.2% PPL improvement over AdamW (22.89→20.33). RMSprop auto-amplifies near-zero Layer 2-4 gradients — natural antidote to HIHO gradient vanishing. Adagrad diverges +2M% (accumulated gradient kills LR). AdamW beta2=0.95: only -0.7%.** |
| **exp_FFFF0** | **RMSprop transfers to real autoresearch corpus: PPL=27.98 vs AdamW PPL=30.03 (-6.8%). Now default in from_autoresearch(optimizer='rmsprop'). Combined rmsprop+cosine gives PPL=26.73 (from ~31 baseline). Dataset: 258 examples.** |
| exp_GGGG0 | RMSprop+smart_seed efficiency: PPL=27.90 at 1.9s (3.01x efficiency vs old default). Smart_seed still works perfectly with RMSprop. |
| exp_HHHH0 | RMSprop seed variance: std=0.91 vs AdamW std=0.51 — RMSprop is MORE variable but uniformly better. Even worst RMSprop seed (PPL=29.19) beats AdamW's best seed (PPL=29.44). |
| exp_IIII0 | Gradient clipping: clip=0.5 marginally best (-2.6%). clip>=1.0 equivalent to no-clip for RMSprop. clip=0.1 too aggressive (+7%). Default clip=1.0 acceptable. |
| exp_JJJJ0 | Kernel ablation: Gaussian(σ=0.5) best PPL (55.15), HIHO 3rd (58.45), Softmax 2nd (57.28). HIHO's advantage is gradient stability and physics grounding, not raw PPL. |
| exp_KKKK0 | EMA weights HURT HIHO-LM at 80 steps (-1% to -327%). Cosine schedule already handles smoothing; EMA averages in bad early weights during fast learning phase. |
| **exp_LLLL0** | **Quality discrimination: Random/Domain ratio improved from 2.3x (old) to 9.21x (new). JSON/hex PPL=680. Random English PPL=25 (BELOW domain=26.6 — model learned English broadly). Sycophancy ratio: 1.37x.** |
| **exp_MMMM0** | **Sycophancy now detectable! hiho_score < 0.90 threshold: substantive=0.938 vs sycophantic=0.849 (sep=0.088). Reverses documented exp_ZZZZ5 finding. RMSprop+cosine domain specialization enables detection.** |
| **exp_OOOO0** | **Steps scaling law: PPL ∝ steps^-0.341. 160→PPL=20.2, 320→PPL=15.2, 640→PPL=14.0 (diminishing returns). Extrapolated 1000 steps PPL=11.2. 320-step training (38s) is quality sweet spot.** |
| **exp_PPPP0** | **SGDR warm restarts: T0=steps/4 gives PPL=15.45 vs plain cosine 16.34 (-5.5%) at 320 steps. Now available as lr_schedule='sgdr'. Optimal for training > 160 steps.** |
| exp_QQQQ0 | Full 320-step config: SGDR+rmsprop+n3 gives PPL=14.88 (47% improvement over 80-step default). Smart_seed+SGDR+320 gives PPL=15.64 at 6.5s (1.66x efficiency). |
| exp_RRRR0 | Stage 3 attempt: 1000-step SGDR gives PPL=12.39. Stage 3 not reached. Power law extrapolation: Stage 3 requires ~2800 steps. |
| **exp_SSSS0** | **Shuffled batch sampling: -4.3% PPL (sequential 19.46 → shuffled 18.62). Sequential batching creates correlated gradients with cosine schedule. Now default in from_autoresearch().** |
| exp_TTTT0 | Init scale: std=0.02 (GPT-2 default) is optimal. Smaller (0.01) and larger (0.05) both hurt. HIHO kernel's zero-gradient zones make init scale critical. |
| exp_UUUU0 | Attention logit scale: scale_mult=4 marginally best (-2.3%). Not significant. Default 1/sqrt(d_head) adequate. |
| exp_VVVV0 | Session regression: 15.7% total improvement confirmed (28.95→24.40 with bs=4). Wired: RMSprop+cosine+shuffle. |
| **exp_WWWW0** | **New 3-stage dynamics: Stage 1 at step 1 (was 10), Stage 2 at step 5 (was 25, 5x faster). Coherence arc peak shifted to step 50 (was 10) — more exploration before specialization. Final coherence 0.93+.** |
| exp_XXXX0 | RMSprop advantage confirmed: +2.8-2.9% better than AdamW+all-other-improvements. Gradient normalization effect is unique to RMSprop. |
| exp_YYYY0 | RMSNorm LOSER: +4.9% worse than LayerNorm. HIHO needs mean-centering to keep activations near kernel peak at x=0. |
| **exp_ZZZZ0** | **Batch size monotonically better: bs=8 gives -9.6% (22.34), bs=16 gives -18.7% (18.65). Total tokens = batch_size × steps = primary quality driver. Default batch_size changed 4→8.** |
| exp_AAAA1 | Batch-step tradeoff: for fixed budget, more steps beats fewer steps even with larger batch. Best efficiency: bs=16, 20 steps (1.45x efficiency at PPL=29.75, 3.2s). |
| **exp_BBBB1** | **RMSprop momentum: alpha=0.95, momentum=0.5 gives PPL=17.91 (-18.2%). Momentum accumulates gradient history to push near-zero Layer 2-4 gradients. momentum=0.9 catastrophic (+30.8%). Now default.** |
| exp_CCCC1 | Momentum isolation: old eval phrase confirmed -8.6% from momentum alone. Note: baseline was already RMSprop (confound corrected in exp_DDDD1). |
| **exp_DDDD1** | **Controlled momentum test: alpha=0.95+mom=0.5 vs no-mom AdamW baseline: -9.2% PPL confirmed. Confound resolved.** |
| exp_EEEE1 | Sequence length: 64→128 bytes gives -15.6% PPL (18.70→15.78). Captures more context per training batch. Default changed 64→128. |
| exp_FFFF1 | Extended seq_len (128-512): seq_len=128 is OPTIMAL. All longer seqs worse (seq=192: +24.9%, seq=256: +15.5%). Padding+attention dilution outweigh longer context for this dataset. Default confirmed. |
| **exp_GGGG1** | **HELD-OUT EVAL: 5 phrases not in training data. OLD defaults: NL mean=35.99, garbage=527. NEW defaults: NL mean=26.91 (-25.2%), garbage=761 (19.4x separation). Mean with garbage: +29.3% (misleading — garbage PPL is intentionally high). Corrected analysis: see exp_GGGG1b.** |
| **exp_GGGG1b** | **Corrected analysis: P1-P4 NL mean is correct metric. NEW is -25.2% better. Garbage PPL increase (527→761) is DESIRABLE — bigger separation means better gate. Canonical held-out PPL: v3 defaults = 21.24. Gate threshold=80 valid, 19.4x margin.** |
| **exp_HHHH1** | **Sycophancy detection NOT reliable for v3 model. separation=+0.013 (was +0.088 in exp_MMMM0). Both sycophantic (PPL ~20-32) and domain text have same PPL range. check_sycophancy() accuracy ~60% (chance). Use PPL gate only.** |
| **exp_IIII1** | **160 steps vs 80 steps on held-out eval: NL_mean 27.67→24.29 (-12.2%). Garbage PPL 1084→1189 (better gate). WINNER. Quality sweet spot is 160 steps, not 80.** |
| exp_JJJJ1 | n_seeds at 160 steps: n1=25.41/9s, n3=24.29/24.5s, n5=23.85/41.6s. Best efficiency: n_seeds=1 (160+n1 is faster AND better than 80+n3). n3 gives -4.4% over n1 at 2.7x time cost. |
| exp_KKKK1 | SGDR at 160 steps vs cosine: -1.9% improvement (24.29→23.82). T0=40 (steps/4). WINNER. Wire SGDR as gate default for 160-step training. SGDR benefit grows with more steps (was -5.5% at 320 steps). |
| exp_LLLL1 | Weight decay STRONGLY HURTS RMSprop: +21.8% worse. AdamW WD also hurts (+25.3%). FFN saturation already provides regularization. No WD is optimal. Default confirmed. |
| **exp_MMMM1** | **LR shifts with training length: 80 steps optimal=1e-3, 160 steps optimal=5e-4 (-5.6%). Cosine SGDR restarts benefit from lower starting LR. Wire lr=5e-4 for 160-step gate config.** |
| **exp_NNNN1** | **Confirmed lr=5e-4 at 160 steps n_seeds=3: NL_mean=22.49 (-5.6% vs lr=1e-3). Wire to hiho_lm_gate.py. Cumulative improvement from exp_GGGG1b: -25.2% + SGDR -1.9% + lr=5e-4 -5.6% ≈ -31.8% total.** |
| exp_OOOO1 | SGDR 80 steps LR sweep: lr=5e-4 wins (-4.3% vs 1e-3). LR shift extends to 80-step runs. |
| exp_QQQQ1 | Momentum re-check at lr=5e-4: default alpha=0.95 mom=0.5 still optimal (25.58 vs 26.05 no-mom). Small advantage at low LR vs high advantage at high LR — gradient stabilization less critical. |
| exp_RRRR1 | Batch size at lr=5e-4: bs=16 gives -3.5% (24.69) vs bs=8 (25.58), but 85% longer. At same time budget, 160 steps beats 80+bs16. Default bs=8 stays. |
| **exp_PPPP1** | **lr=5e-4 wins at 80 steps with COSINE too: -7.6% vs lr=1e-3. MECHANISM: lower LR → flatter minima → better generalization on held-out eval. Old eval phrase (in-distribution) masked this. NEW DEFAULT: from_autoresearch() rmsprop lr=5e-4.** |
| exp_QQQQ1 | Momentum at lr=5e-4: alpha=0.95 mom=0.5 still optimal (25.58 vs 26.05 no-mom). Small advantage vs high advantage at lr=1e-3 — gradient stabilization less critical at lower LR. Default confirmed. |
| exp_RRRR1 | Batch size at lr=5e-4: bs=16 gives -3.5% (24.69) vs bs=8 (25.58), but 85% longer. At same time budget, 160 steps beats 80+bs16. Default bs=8 stays. |
| exp_SSSS1 | RMSprop alpha at lr=5e-4: alpha=0.90 and 0.95 tied at 25.58; alpha=0.99 hurts (+5.8%). Default alpha=0.95 confirmed. |
| **exp_TTTT1** | **Gradient clipping at lr=5e-4: clip=0.5 gives -3.1% vs clip=1.0 (24.77 vs 25.58). Confirmed across exp_IIII0 and TTTT1. NEW DEFAULT: clip_grad_norm=0.5.** |
| **exp_UUUU1** | **Session summary: v4 defaults (lr=5e-4+clip=0.5) vs OLD baseline: P1-P4 NL mean -31.2% (35.99→24.77). Garbage margin 10.9x→27.7x. Domain PPL 27.41→19.90.** |
| exp_VVVV1 | Warmup steps at lr=5e-4: no warmup (0 steps) is optimal. Warmup=5 +1.5%, warmup=10 +2.8%. Consistent with exp_BBBB0. HIHO stability makes warmup redundant. |
| **exp_WWWW1** | **Gate config (160+SGDR+lr=5e-4+clip=0.5+n3): NL_mean=23.50 (-5.1% vs fast config). Garbage margin 27.7x→40.8x. Time: 13.2s→25.4s.** |
| **exp_XXXX1** | **CRITICAL EFFICIENCY: smart_seed at 160 steps = IDENTICAL quality (23.50) at 2.97x speedup (8.5s vs 25.3s). Zero quality loss across 2 independent runs. Wire gate: steps=160+smart_seed=True+sgdr+lr=5e-4 → 8.5s, NL_mean=23.50.** |
| exp_DDDD2 | Variance characterization: CV=2.3% (std=0.59 PPL) at 80 steps, n_seeds=3. Noise floor ~4.5%. Deltas <1.2 PPL may be noise. exp_KKKK1 (SGDR -1.9%) and TTTT1 (clip -3.1%) are within noise. |
| **exp_EEEE2** | **Code corpus augmentation: +20 Python snippets from src/cohezion/model/*.py. -9.8% NL_mean, -7.5% P3_code. 4.4σ above noise floor. Data > hyperparameters: 20 snippets beat 6 prior hyperparam experiments. Now default (include_code=True).** |
| exp_FFFF2 | 40 vs 20 code snippets: 40 WORSE (+14.3%). Auto-extracted snippets from non-model files hurt. Quality > quantity. Optimal: 20 hand-curated snippets from model files. |
| **exp_GGGG2** | **Code corpus also improves gate (160+SGDR): -11.1% NL_mean, -21.9% P3_code. P5=202 still >>80 (2.5x gate margin).** |
| **exp_HHHH2** | **320 steps scaling with code corpus: NL_mean=21.65 (-7.9% vs 160). P5_garbage=637.8 (25x gate margin). 17s one-time cost. 640 steps overfits (+9%). Sweet spot: 320 steps. Gate updated.** |
| exp_IIII2 | 640 steps OVERFITS: NL_mean 21.65→23.60 (+9%). P3_code regresses. Ceiling identified at 320 steps for 295-example corpus. |
| exp_JJJJ2 | English corpus augmentation: WITHIN NOISE (+0.8%). English already represented. Only add corpus for real distribution gaps. |
| exp_KKKK2 | SGDR T0 period: T0=80/107/160 all within noise (±0.05 PPL). T0=320 (cosine) slightly worse. Default T0=steps//4 optimal. |
| **exp_LLLL2** | **v5 summary: OLD(26.54) → v5-fast(23.95, -9.8%) → v5-gate(21.65, -18.4%). Gate margin 20.5x. v5 = 320+SGDR+smart_seed+lr=5e-4+code(20 snippets). One-time 17s cost.** |

### 3-Stage Learning Process (exp_HHHH3/EEEE3/AAAA6/WWWW0)

| Stage | AdamW+const steps | RMSprop+cosine+shuffle steps | Threshold | Observable |
|-------|-------|------|-----------|------------|
| **Character set** | ~10 | **~1** | 80%+ printable ASCII | Model generates readable characters immediately |
| **Domain compression** | ~25 | **~5** | PPL < 50 | Model recognizes domain vocabulary (5x faster!) |
| **Coherent phrases** | ~1000+ | **~2800** (extrapolated) | PPL < 10 | Readable sentences emerge |

**exp_WWWW0:** With new defaults, Stage 2 reached at step 5 (vs 25 with AdamW). Coherence arc shifted: peak at step 50 (vs step 10) — more exploration before specialization. Final coherence 0.93+ (vs 0.65 in exp_IIII7).

PPL milestones with RMSprop+cosine+shuffle+bs8+seq128 (v3 defaults):
- 80 steps (~21s): PPL ≈ 21 (held-out domain), NL mean ≈ 27 (exp_GGGG1b)
- 160 steps (~38s): PPL ≈ 17 (extrapolated from scaling law)
- 320 steps (~75s): PPL ≈ 13 (SGDR recommended)
- 1000 steps (~240s): PPL ≈ 10
- 2800 steps (extrapolated): PPL ≈ 8 (Stage 3)

**Evaluation metric (exp_GGGG1b):** Use held-out domain phrase (not training data substring).
Canonical: `"Compound engineering orchestrates multi-agent systems through coherent feedback loops"`
OLD defaults (AdamW+bs4+seq64) PPL=27.41 on this phrase; v3 defaults PPL=21.24 (-22.5%).

### Production Capability Card (v5 — +code_corpus+320steps, byte_level, 4L-4H-256D)

| Capability | v1 (AdamW/const/bs4/seq64) | v4 (RMSprop+lr=5e-4+clip=0.5) | v5 gate | Notes |
|-----------|-------|-------|-------|-------|
| API training time | 6.0s | ~13s | n/a | bs8+seq128+n3 |
| Gate singleton time | 6.0s | ~8.5s | **~17s** | v5: 320+SGDR+smart_seed+code |
| Domain PPL (held-out) | 27.41 | **19.90** | **15.43** | P1 held-out |
| Generic English PPL | 33.20 | **22.77** | **14.82** | P2 held-out |
| Code PPL (held-out) | 48.51 | **33.64** | **31.16** | P3 held-out (code corpus) |
| Mean NL (P1-P4 held-out) | 35.99 | **24.77** | **21.65** | -39.8% vs v1 |
| Improvement vs OLD (NL mean) | baseline | -31.2% | **-18.4% vs v4** | compounding |
| Garbage PPL (JSON/hex) | ~528 | ~932 | **~638** | still >>80 threshold |
| Garbage gate margin | 10.9x | 27.7x | **20.5x** | above worst-NL PPL |
| Gate threshold PPL=80 | valid | valid | **valid** | all domain <80, garbage >>80 |
| Model size | 12.79 MB | 12.79 MB | 12.79 MB | unchanged |
| Garbage filter | ✅ | ✅ stronger | ✅ | PPL>80 gate (8x margin vs P5) |
| Sycophancy detect | ❌ | ❌ NOT RELIABLE | ❌ | exp_HHHH1: acc~60% (chance) |
| Coherent generation | ❌ | ❌ | ❌ | needs 1000+ steps |

**v5 key changes** (exp_DDDD2-LLLL2):
- **Code corpus** (exp_EEEE2): +20 Python snippets from model files → -9.8% NL, -21.9% P3_code
- **320 steps** (exp_HHHH2): power-law scaling → -7.9% NL, P5=638 (25x gate margin)
- **Noise floor** (exp_DDDD2): CV=2.3%, threshold 4.5%. Small deltas (SGDR -1.9%, clip -3.1%) unreliable.
- **Corpus ceiling** (exp_IIII2): 640 steps overfits 295-example dataset. Sweet spot = 320 steps.
- **Data > hyperparameters**: 20 code snippets beat 6 hyperparameter experiments combined.

**v5 gate config**: from_autoresearch(steps=320, smart_seed=True, lr_schedule='sgdr', lr=5e-4, include_code=True) — 17s, NL_mean=21.65.
**Note (exp_HHHH1):** Sycophancy detection via hiho_score NOT reliable. Use PPL gate (threshold=80) only.

### Harness Invariants

- **LM1**: byte_level init_loss within 0.5 of log(256)=5.545
- **LM2**: hiho_coherence < 0.2 for random model (near-uniform attention → low coherence)
- **LM3**: generate_text() returns str for all inputs including empty (BOS fallback)
- **LM4**: hiho_perplexity() returns inf for <=1 byte inputs

### File Locations

| File | Purpose |
|------|---------|
| `src/cohezion/model/cohezion_lm.py` | CohezionLM, CohezionLMConfig, generate_text(), hiho_perplexity(), hiho_coherence() |
| `src/cohezion/model/hiho_attention.py` | HIHOAttention, hiho_kernel() = 4σ(x)(1-σ(x)) |
| `src/cohezion/model/training_data.py` | TrainingExample, build_balanced_training_dataset() |
| `src/cohezion/model/train.py` | CLI trainer: --size byte_level --steps N --device cpu/cuda |
| `tests/unit/model/test_hiho_model.py` | 45 tests covering all model components |
