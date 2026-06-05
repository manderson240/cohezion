---
title: "Tunable Levers & Knobs — HF/arxiv Research (10 rounds)"
date: 2026-06-05
method: "dynamic Workflow — 10 parallel research agents + 10 adversarial verifiers (general-purpose), grounded in fetched 2025-2026 sources, classified against Cohezion's calibrated invariants"
workflow_run: wf_97a0097e-958
agents: 20
classification_key: "NEW = we don't do this | ALREADY-CALIBRATED = targets a protected invariant | CHALLENGES-EXISTING = contradicts a calibration"
verdict_key: "accept = NEW+grounded+additive | needs-experiment = run the $0 iGPU/NPU eval first | reject = ungrounded/done/regression"
result: "10/10 NEW, 10/10 grounded, 0 touch calibrated invariants (0 regression risk). All verified to needs-experiment (none rubber-stamped)."
policy: "Every lever terminates in a falsifiable $0 local-silicon experiment, NOT a citation. Implement only after the experiment passes its falsification gate."
---

# Tunable Levers & Knobs to Strengthen Cohezion

Ten verified, source-grounded levers — one per subsystem — from a multi-agent
research+verify workflow. **None re-tunes a calibrated invariant** (A3/A4/A5 VAE,
CA1 cache 0.58, CC2 λ=100, LM6 ffn_scale, HIHO=0.5 are all untouched). Each carries
its falsifiable local-silicon experiment so research lands as *tested levers*, not a
bibliography (the codebase's #1 anti-pattern).

## Ranked levers (by impact, then ascending risk)


### 1. Local inference throughput — llama.cpp n-gram self-speculative decoding

- **Lever:** llama.cpp n-gram self-speculative decoding: `--spec-type ngram-mod` (also ngram-simple / ngram-map-k) with `--spec-ngram-mod-n-match` / `--draft-min` / `--draft-max` — draft-model-free, lossless, ~16MB constant memory
- **Source:** [llama.cpp PR #18471 — self-speculative (n-gram) decoding (merged); docs/speculative.md; cf. PR #18039 EAGLE-3 (draft, CU](https://github.com/ggml-org/llama.cpp/pull/18471)
- **Finding:** Merged-to-master (2026-01-28) self-speculative decoding that drafts from repeated n-grams in the token history — NO separate draft model, NO vocab matching, constant ~16MB hash pool, lossless (verify step guarantees output identical to autoregressive). PR #18471 reports gpt-oss-120b 181→445 tok/s (2.5x) and Qwen3-235B ~12→~21 tok/s (1.75x); gains concentrate on repetitive output (code refactor, structured/templated generation, RAG-grounded answers that echo context). Because it invokes no extra model inference, it is backend-agnostic and runs under our existing iGPU llama-server (Vulkan/ROCm),
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 iGPU experiment. Our existing CLaSpTier (clasp_tier.py) is only a REST-level, lossy, second-model (2B on port 13308) draft/verify approximation — NOT token-level spec-decode. Test true n-gram self-spec on the iGPU's main model: launch `llama-server` directly on 13307 (lemonade can't pass --spec-type; skill §1 escape hatch) twice — baseline (no flag) vs `--spec-type ngram-mod --spec-ngram-mod-n-match 24 --draft-min 12 --draft-max 48`. Run an identical fixed prompt set across (a) repetitive workloads (code-refactor, RAG answers echoing context, structured/JSON output) and (b) free-form prose, temp=0, seeded. Falsification gate: log tok/s for both arms; the lever WINS only if rep
- **Verifier note:** PR #18471 confirmed real, merged 2026-01-28, supports self-spec/no-draft-model/lossless/flags/throughput claims (16MB figure not explicitly confirmed by source). CLaSpTier verified as a distinct lossy second-model (E2B:13308 verified by E4B:13307) REST/QualityGate approximation, so NEW is correct, not a re-do. Additive gated ModelEntry recipe touch


### 2. KV cache / context memory — llama.cpp attention KV-cache quantization via `--cache-type-k`/`--cache-type-v` 

- **Lever:** llama.cpp attention KV-cache quantization via `--cache-type-k`/`--cache-type-v` (`q8_0`/`q4_0`) with flash-attention; TurboQuant `turbo3`/`tq3_0` as the 2026 frontier extension
- **Source:** [https://github.com/ggml-org/llama.cpp/discussions/20969](https://github.com/ggml-org/llama.cpp/discussions/20969)
- **Finding:** The llama.cpp KV-cache discussion documents that attention KV cache can be quantized at serve time. Mainline (not a 2026 invention) ships symmetric `q8_0` (~2x) and `q4_0` (~4x) cache compression usable on Vulkan; the 2025-2026 novelty is TurboQuant (Zandieh et al., ICLR 2026 — 3-bit keys/2-bit values, calibration-free, ~6x KV reduction, claimed near-zero quality loss) with community `turbo3`/`tq3_0` Vulkan/AMD forks (jesusmb1995, Aaryan-Kapoor) showing ~1.2x overhead on a Radeon 7900 XTX. Two AMD-deployability constraints are explicit in the source thread: (1) quantized KV requires flash atte
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none — this is the transformer attention KV cache; distinct from CA1's SemanticCache (an L2 semantic PROMPT cache keyed by embedding similarity), so it is not ALREADY-CALIBRATED against CA1
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 iGPU experiment on the lemonade-bundled Vulkan binary (`~/.cache/lemonade/bin/llamacpp/vulkan/llama-server`, confirmed to support `-ctk`/`-ctv`/`-fa`). Launch the same GGUF on the iGPU three ways at 32K and 128K context: (A) baseline `-ctk f16 -ctv f16`, (B) `-ctk q8_0 -ctv q8_0 -fa on`, (C) `-ctk q4_0 -ctv q4_0 -fa on`. Metrics per arm: peak unified-memory delta, prompt-eval + decode tok/s, and a Needle-In-A-Haystack retrieval accuracy probe. Fair-test guard: also run B/C with `-fa off` to confirm flash attention is the deciding factor (source warns FA-off can be net-slower). HONEST-NULL outcome is valid: if FA does not engage on the RDNA3.5 8060S iGPU (evidence is for a disc
- **Verifier note:** Source verified 3 ways: discussion #20969 documents -ctk/-ctv q8_0/q4_0 + FA-required + turbo3/tq3_0 on Vulkan/7900 XTX; TurboQuant (Zandieh et al., ICLR 2026, Google) is real and calibration-free; local lemonade Vulkan llama-server confirmed to expose -ctk/-ctv/-fa. NEW (attention KV cache, not CA1's semantic prompt cache; touches no invariant); l


### 3. Token efficiency / prompt compression — LLMLingua-2 hard prompt compression

- **Lever:** LLMLingua-2 hard prompt compression: a small multilingual-BERT/XLM-RoBERTa token-classifier that drops low-importance tokens, producing natural-language (hard) tokens ingestible by a black-box cloud API. Tunable knob = compression rate.
- **Source:** [LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression (arXiv 2403.12968); successor](https://arxiv.org/abs/2403.12968)
- **Finding:** LLMLingua-2 (microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank ~178M, or the xlm-roberta-large variant ~560M) formulates prompt compression as token classification and reports 2x-5x prompt compression with 1.6x-2.9x end-to-end latency reduction and minimal quality loss; it is 3x-6x faster than the original LLMLingua. The encoder is BERT-class — runs on CPU/iGPU, NO CUDA required — and ships as ready-to-download HuggingFace weights with a one-line pip API (compress_prompt(prompt, rate=0.33)). HONESTY CAVEAT: this is a March-2024 method. The strongest 2025 successor in the same line
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** $0 falsifiable 3-arm experiment on iGPU 13307 (use falsifiable-eval-harness). Load microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank (CPU/iGPU, no CUDA). On ~30 representative CompoundExecutor cloud-bound prompts (task_description + assembled context), compare three arms: (A) treatment = LLMLingua-2 at rate=0.5 and 0.33; (B) baseline = our existing src/cohezion/inference/entropy_compressor.py StepEntropyCompressor (heuristic Shannon-entropy pruner); (C) control = no compression. Metric 1: token reduction (tiktoken count). Metric 2: answer-quality preservation — feed each compressed prompt to a local model on 13307 (temp=0, word-boundary scoring) and check the answer still matche
- **Verifier note:** Grounded: both arXiv IDs (2403.12968 LLMLingua-2, 2503.07956 EFPC) are real; metrics (2-5x compression, 1.6-2.9x latency, 3-6x faster than LLMLingua, EFPC +4.8-11.4% F1 at 4x but no released weights) match the finding. NEW, not a duplicate: existing src/cohezion/inference/entropy_compressor.py StepEntropyCompressor is a line-level CoT-transcript pr


### 4. Semantic cache — Cost-aware semantic-cache eviction (Reverse-Greedy / LCB online variant)

- **Lever:** Cost-aware semantic-cache eviction (Reverse-Greedy / LCB online variant): replace plain LFU/FIFO eviction with a utility score min{c(q), d(q,M)} where c = serving cost and d = embedding mismatch cost
- **Source:** [Semantic Caching for Low-Cost LLM Serving: From Offline Learning to Online Adaptation (arXiv:2508.07675, INFOCOM 2026)](https://arxiv.org/html/2508.07675v1)
- **Finding:** "Semantic Caching for Low-Cost LLM Serving: From Offline Learning to Online Adaptation" (INFOCOM 2026) frames semantic-cache eviction as minimizing loss l(M;p,c,d) = sum_q p(q)*min{c(q), d(q,M)}, balancing per-query serving cost c(q) against mismatch cost d(q,M) (distance to nearest cached entry). Offline algo = Reverse-Greedy; online algo CLCB-SC-LS is a bandit using only empirical counters + confidence bounds (no neural net, no GPU, no training). Reports at least 11.75% improvement over the strongest baseline (Epsilon-Greedy), scaling 11.75%->54.04% with cache size, and up to 90.91% fewer ca
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none (CA1-adjacent but does NOT re-tune the calibrated similarity_threshold; it changes which entries are evicted, an orthogonal axis)
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 offline experiment (no production swap). Confirmed current eviction is uniform-utility: src/cohezion/cache/semantic_cache.py L1=_put_l1 FIFO (pop oldest), L2=_put_l2 plain LFU (min access count) — neither weights serving cost or mismatch. Experiment: replay a query trace at a fixed L2 size and compare current LFU vs the paper's Reverse-Greedy utility min{c(q),d(q,M)}, with the cost model RECAST for our $0 local silicon (CC2): serving cost c = tier LATENCY the miss would hit (NPU 24ms / iGPU 200ms / CPU 800ms), not dollars; mismatch cost d = (1 - cosine_sim) reusing the existing nomic-embed 768D vectors (zero new model). Metric = latency-weighted hit rate. Can return 'no improv
- **Verifier note:** Source arXiv:2508.07675v1 is real; WebFetch confirms the min{c(q),d(q,M)} loss, Reverse-Greedy offline, neural-free CLCB-SC-LS bandit, and all four figures vs the Epsilon-Greedy baseline. Code verified: L1=FIFO (l1_insertion_order.pop(0)), L2=plain LFU (min(l2_lfu_counts)) — no cost/mismatch weighting exists, so this is genuinely NEW and additive. 


### 5. Model routing / cascade — Cascade escalation signal

- **Lever:** Cascade escalation signal: token-level margin uncertainty calibrated via isotonic regression to a per-query error probability, with a cost-minimizing accept/escalate threshold (UCCI)
- **Source:** [UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing](https://arxiv.org/abs/2605.18796)
- **Finding:** UCCI computes a token-level margin uncertainty from the small model, maps it to a per-query error probability via isotonic regression (a lightweight, CPU-only, post-hoc monotonic fit requiring no GPU training), then picks the escalation threshold by constrained cost minimization. On a 75k-query production NER workload (4B and 12B instruct LLMs) it cut inference cost by 31% (95% CI [27%,35%]) at micro-F1=0.91 and reduced expected calibration error from 0.12 to 0.03, beating entropy thresholding, split-conformal routing, and a FrugalGPT-style learned threshold on measured hardware latency.
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 iGPU(13307)/NPU(13306) experiment. Our current escalation gate (src/cohezion/inference/quality_eval.py) decides accept-vs-escalate from OUTPUT TEXT heuristics (min_chars, uncertainty-disclaimer keywords) — it never consumes the model's token-level confidence. Experiment: (1) Request logprobs from lemonade's OpenAI-compatible API on the NPU/iGPU tier (llama.cpp backend already exposes them; flume/latent_engine.py already parses top-K logprobs). Compute per-query margin = mean(top1_logprob - top2_logprob). (2) On a labeled task set (e.g. BBQ/categorical or a held-out short-answer set), split train/test; fit sklearn.isotonic.IsotonicRegression mapping margin -> empirical error ra
- **Verifier note:** Source verified (arXiv 2605.18796, Varun Kotte, submitted 2026-05-11; abstract matches finding verbatim). Classification NEW is correct: quality_eval.py gates accept-vs-escalate purely on OUTPUT TEXT heuristics (_UNCERTAINTY_MARKERS, min_chars) and never consumes token-level confidence; no isotonic/IsotonicRegression anywhere in src/. No regression


### 6. Fine-tuning / adapters — rsLoRA

- **Lever:** rsLoRA — rank-stabilized LoRA scaling factor (use_rslora=True in PEFT LoraConfig): changes adapter scaling from alpha/r to alpha/sqrt(r)
- **Source:** [A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA (rsLoRA), Kalajdzievski 2023, arXiv:2312.03732](https://arxiv.org/abs/2312.03732)
- **Finding:** Kalajdzievski (2312.03732) proves the standard LoRA scaling factor alpha/r over-suppresses adapter contribution as rank grows, "slowing learning and stunting performance for higher-rank adapters," with collapsing gradient norms shown at the ranks they evaluate (4, 8, 32, 128, 512, 2048). The fix is to divide by sqrt(r) instead of r, which keeps activations/gradients stable at higher rank. Quantified property: zero change in inference compute cost and zero change in training memory/time — it only rescales a constant. At our r=32, alpha=64, this lifts the effective adapter scale from alpha/r=2.0
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Additive one-line change to src/cohezion/integrations/kaggle_training_improved.py LoraConfig (line 258, and the get_training_script_template variant): add use_rslora=True (r=32, lora_alpha=64 unchanged — rank invariant preserved). Falsifiable $0 iGPU(13307) experiment FIRST: load a small base (e.g. SmolLM/Qwen-0.5B) with PEFT, build two adapters identical except use_rslora, run ~50 SFT steps on a held-out math/boxed slice on the iGPU, and compare (a) mean LoRA-A/B gradient norm and (b) train loss trajectory. Pass criterion: rsLoRA shows >=20% higher mean adapter gradient norm AND lower loss at step 50; if not, the lever is null at our rank and we do NOT ship it. Verified locally: installed p
- **Verifier note:** Source real (arXiv:2312.03732, Kalajdzievski) and supports alpha/sqrt(r) fix; peft locally implements it at layer.py:212-213 and exposes use_rslora. NEW (current LoraConfig defaults use_rslora=False), no invariant re-tuned (r/alpha fixed). But benefit at r=32 is unproven on our stack — paper's strong evidence is at ranks 128-2048; run the $0 iGPU e


### 7. Agentic RAG / knowledge graph — LightRAG dual-level retrieval (low-level entity keywords + high-level theme keyw

- **Lever:** LightRAG dual-level retrieval (low-level entity keywords + high-level theme keywords) over a graph-enhanced text index, with union-based incremental graph update
- **Source:** [LightRAG: Simple and Fast Retrieval-Augmented Generation (EMNLP 2025)](https://arxiv.org/html/2410.05779v1)
- **Finding:** LightRAG extracts two keyword sets per query — local/low-level keywords (specific entities + attributes/relations) and global/high-level keywords (overarching themes) — and routes each to different graph elements via a graph-enhanced vector index. This beats Microsoft GraphRAG on win-rate across all four eval domains (e.g. Agriculture 56.38% vs 43.62%; Diversity metric 80.35% vs 19.65%) while cutting retrieval cost to under 100 tokens and a single LLM call (vs GraphRAG's ~610k tokens / hundreds of calls), and supports incremental updates by union of node/edge sets instead of full community-rep
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Add an additive dual_level_search() method to GraphRAGEngine (src/cohezion/knowledge_graph/graphrag_engine.py) alongside the existing flat hybrid_search() (which does only vector-seed + 1-hop synapse expansion). It extracts low-level entity keywords and high-level theme keywords from the query via the NPU (llama3.2-1b on 13306, a classification-class task), embeds each set with the already-local 768D nomic-embed (lemonade), runs two retrieval passes over the neurons graph, and merges. Falsifiable $0 experiment via falsifiable-eval-harness: build a small QA set over the existing neurons graph; treatment=dual_level_search vs frozen-baseline=hybrid_search, temp=0, word-boundary scoring on recal
- **Verifier note:** arxiv 2410.05779v1 verified real and supports dual-level retrieval + union incremental update + ~100-token single-call claims (one win-rate number misquoted: paper shows Agriculture Diversity 75.91% vs 19.65%, not 80.35%, but direction holds). graphrag_engine.py confirms hybrid_search() exists (vector-seed + 1-hop synapse) and dual_level_search() d


### 8. Quantization for local fleet — Unsloth Dynamic 2.0 imatrix-calibrated GGUF quants (per-layer mixed precision

- **Lever:** Unsloth Dynamic 2.0 imatrix-calibrated GGUF quants (per-layer mixed precision: important layers upcast to 8/16-bit, driven by an importance matrix over a 1.5M-token curated calibration set) — swap the served GGUF for the UD-* variant at the same nominal bitrate
- **Source:** [Unsloth Dynamic 2.0 GGUFs (Unsloth Documentation)](https://unsloth.ai/docs/basics/unsloth-dynamic-2.0-ggufs)
- **Finding:** Dynamic 2.0 GGUFs use imatrix calibration + per-layer bit-width selection to push quality-per-bit to the Pareto frontier. Measured at the SAME bitrate vs naive/QAT quants: Gemma-3-27B KL-divergence drops (IQ2_XXS 0.536->0.521, Q2_K_XL 0.230->0.221); UD-4bit MMLU 5-shot 71.47% beats Google's QAT 70.64%; DeepSeek-V3.1 UD-3bit hits 75.6% Aider Polyglot. UD-Q4_K_XL is on the 99.9%-KLD Pareto frontier and is ~8GB smaller than other Q4 quants. Concrete artifact for our tier exists: unsloth/Qwen3.6-27B-GGUF (UD-Q4_K_XL), runnable in standard llama.cpp -> lemonade Vulkan/ROCm. imatrix generally cuts p
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** medium · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 iGPU A/B (port 13307): pull unsloth/Qwen3.6-27B-GGUF UD-Q4_K_XL alongside our current generic Qwen3.6 GGUF quant; run `llama-perplexity` on an identical held-out text + a 10-prompt fleet-task set at temp=0 on both. Treatment = UD quant, baseline = current quant, frozen. Hypothesis (can return False): UD-Q4_K_XL gives lower perplexity / KL-divergence-vs-F16 than the current quant at equal-or-smaller file size. If confirmed, additively register the UD variant as a new ModelEntry in inference/registry.py for the iGPU lane (do not delete the existing one) and flip the main interactive tier model_id after re-running the FIM/chat smoke. OOM-gate via ResourceManager.can_load_model be
- **Verifier note:** Source real + supports finding: MMLU 71.47% vs QAT 70.64% and DeepSeek-V3.1 3-bit 75.6% Aider match exactly; unsloth/Qwen3.6-27B-GGUF UD-Q4_K_XL (17.6GB) confirmed on HF. Additive swap on iGPU 13307, touches no calibrated invariant (no regression). But quality gains are Unsloth's own benchmarks on OTHER models, unproven on our RDNA3.5/lemonade stac


### 9. Compound quality gates — CISC

- **Lever:** CISC — Confidence-Informed Self-Consistency (confidence-weighted majority vote over adversarial perspectives, replacing unweighted count vote)
- **Source:** [https://arxiv.org/abs/2502.06233](https://arxiv.org/abs/2502.06233)
- **Finding:** CISC replaces the unweighted majority vote in self-consistency with a weighted vote using confidence scores the model reports directly (inference/prompt-only, no training). Across 9 models and 4 datasets it outperforms plain self-consistency in nearly all configs and cuts the number of reasoning paths needed by >40% on average. Key nuance: it relies on "within-question" confidence (separating correct vs incorrect answers to the SAME question), and the most-calibrated global confidence method was the LEAST effective for CISC — so confidence must be used as a per-item weight, not a global calibr
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** low · **risk:** low · touches-invariant: none
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 fleet experiment + low-risk additive code. R0ChallengeResult already carries a per-perspective `score` (confidence in [0,1]) on every R0Challenge, but consensus_verdict() uses an UNWEIGHTED count (`CONFIRMED>=2`) and mean_score() an UNWEIGHTED mean — the confidence is only used for the sigma band, never to weight the vote. EXPERIMENT (can return False): take a labeled set of ~40 accept/reject outputs, run the 3 R0 perspectives on local silicon (NPU 13306 / iGPU 13307 / CPU 13309, $0), and compare accept/reject accuracy of (a) current unweighted 2/3 consensus vs (b) a CISC confidence-weighted consensus: accept iff sum(score_i for CONFIRMED/CONDITIONAL) / sum(score_i) >= 0.5, us
- **Verifier note:** Grounded: arXiv:2502.06233 "Confidence Improves Self-Consistency in LLMs" (Taubenfeld et al.) is real and supports all 5 claims (inference-only, 9 models/4 datasets, >40% path reduction, within-question confidence, most-calibrated-method-least-effective). Code claims verified in src/cohezion/compound/r0_sigma.py: R0Challenge.score is per-perspectiv


### 10. FLUME VAE — Latent Reconstruction (LR) loss

- **Lever:** Latent Reconstruction (LR) loss — additive latent-cycle-consistency term ||E_μ(D(z)) − z||² with warm-up weight α, added to the ELBO alongside (not replacing) the KL term
- **Source:** [Toward Architecture-Agnostic Local Control of Posterior Collapse in VAEs (Song, Kim, Lee, arXiv:2508.12530, Aug 2025)](https://arxiv.org/abs/2508.12530)
- **Finding:** Adding a latent-reconstruction (cycle-consistency) loss ||E(D(z))−z||² to the standard ELBO raises active units (AU) from 0.13 (vanilla VAE) to 0.95 on Fashion-MNIST — at β=0.1, the SAME low-beta regime where FLUME operates (we cap β≤0.01). It fights collapse via encoder/decoder invertibility rather than KL re-weighting, so it is orthogonal to free-bits/beta-VAE/cyclic-annealing. Architecture-agnostic (standard MLPs, ReLU/SiLU/GELU/Tanh), implemented as a single MSE term with a 0→α warm-up; no special training infra.
- **Classification:** `NEW` · **verdict:** `needs-experiment` · **impact:** low · **risk:** low · touches-invariant: none — it is purely additive and does NOT modify A3 (kl_weight≤0.01), A4 (2-layer/hd=4096) or A5 (cyclic amp=0.005). It addresses the collapse risk that our deliberately low β creates, from a different axis (latent identifiability) than the KL knob those invariants govern.
- **Falsifiable experiment ($0 local silicon):** Falsifiable $0 iGPU (13307) experiment, additive only: add an optional `lr_loss_weight` (default 0.0 → no behavior change) to FlumeVAE training. When >0, compute z'=encode_mu(decode(z)) for the sampled z and add α·MSE(z', z) to the loss, with α warming 0→target over the first ~30% of steps. Arm A = current build (β-cyclic amp=0.005, LR off). Arm B = identical + LR on (α≈0.1). Gate on active-units fraction (KL>0.01-per-dim count / 256) and the existing A3 KL-health metric (must stay healthy, KL≥~0.166 band). Hypothesis (can return FALSE): Arm B raises AU and reconstruction at equal-or-better KL health without violating A3. If AU does not rise or KL collapses below the A3 band, reject and keep
- **Verifier note:** Source real (arXiv:2508.12530, Song/Kim/Lee) and PDF confirms LR loss ||E(D(z))-z||^2, AU 0.13->0.95 on Fashion-MNIST, beta=0.1, alpha warm-up, arch-agnostic. Purely additive (lr_loss_weight default 0.0); does not re-tune A3/A4/A5. BUT the headline AU gain was measured at beta=0.1 (collapse regime — training.py confirms beta=0.1 collapses); FLUME r


## How to act on these (compound-engineering pipeline)

1. Each lever is **needs-experiment** — run its $0 iGPU/NPU falsification gate first
   (pairs with the `falsifiable-eval-harness` skill). Honest-null is a valid outcome.
2. Implement only the levers that pass their gate, **additively** (new module / gated
   recipe / opt-in flag), never by re-tuning a calibrated invariant.
3. Highest-leverage first experiments: **#? n-gram self-spec** (PR #18471, pure serving
   flag, lossless), **KV-cache `-ctk/-ctv` quant** (memory at 128K ctx), and the
   **semantic-cache cost-aware eviction** + **CISC quality gate** (pure-Python, unit-testable
   without a model).

## Provenance
Dynamic Workflow `wf_97a0097e-958`: 10 research agents (WebSearch/WebFetch, our skills)
→ 10 adversarial verifiers (WebFetch-confirmed grounding + invariant-collision check).
Full structured output retained in the run transcript.
