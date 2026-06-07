---
title: "Bleeding-edge research feed — verified, fleet-runnable levers"
owner: "research loop (session cron dce62109, every 4h :41)"
policy: "Every HF id verified via huggingface_hub.model_info; every arXiv id via WebFetch. Unverifiable → OMITTED + logged. New claims default needs-experiment, never confirmed. Docs only — the build loop owns src/."
classes: "NEW · grounded · needs-experiment · regression-risk"
---

# Bleeding-edge feed

## 2026-06-06 (round 1)

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`Mungert/Qwen3-Reranker-0.6B-GGUF`** | ✅ model_info (738 dl, 21 GGUFs) | **NEW · additive · needs-experiment** | `FleetRegistry` / `Task.RERANK` (currently EMPTY, same gap EXTRACTION had) | 0.6B reranker, GGUF, $0 NPU/iGPU-runnable. **Serving trap**: GGUF rerankers on llama.cpp produce near-zero scores (4.5e-23) unless converted with `convert_hf_to_gguf.py` + `pooling=rank` + the `/v1/rerank` endpoint (`cls.output.weight`). So *registration* is additive; *serving* is needs-experiment. → backlog item 19. |
| `gpustack/gte-multilingual-reranker-base-GGUF` | ✅ model_info (148 dl, 9 GGUFs) | grounded · needs-experiment | `FleetRegistry` / `Task.RERANK` (alt) | Smaller encoder-only multilingual reranker; apache-ish. Fallback if Qwen3-Reranker's llama.cpp rerank path doesn't serve cleanly. Same `/v1/rerank` + `pooling=rank` caveat. |
| `Qwen/Qwen3-Embedding-0.6B-GGUF` | ✅ model_info (40,472 dl, 2 GGUFs) | **regression-risk** (NOT adopted) | `semantic_cache` encoder | Strong embedder, BUT **CA1** pins nomic-embed-text-v2-moe (768D → 0.58 threshold) as the calibrated cache encoder. Swapping requires a full FP-rate/hit-rate recalibration; do NOT swap without re-running the exp_OOOO2-class experiment. Logged, not queued. |
| `unsloth/Qwen3-Coder-Next-GGUF` | ✅ model_info (3.08M dl, 63 GGUFs) | grounded · needs-experiment | `FleetRegistry` / `Task.CODE_GEN` | Large multi-part BF16 coder. Fleet already has qwen3-coder:30b + Mellum (FIM). Not clearly additive over existing code lane on a memory-tight box; defer (K1 — multi-part BF16 is heavy). |
| MTP / "Qwen3.6-27B" blogspam (braincuber, dredyson, mer.vin) | ❌ unverifiable SEO content | **OMITTED** | — | MTP is already covered by the verified `Qwen3.6-35B-A3B-MTP-GGUF` in strix-halo-fleet-orchestration §1. The June-2026 "27B MTP" blog posts are AI-generated SEO with no primary source; not cited. |

**arXiv this round**: no NEW verifiable arXiv id surfaced (the harness-routing paper 2605.30621 is already in the harness). Not fabricating one — omitted honestly.

**Round verdict**: 1 high-value verified lever (Qwen3-Reranker-0.6B as the empty `Task.RERANK` specialist) → backlog item 19. Reranker GGUF serving on llama.cpp is the gated experiment (the near-zero-score trap).

## 2026-06-06 (round 2)

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`ibm-granite/granite-4.1-3b-GGUF`** | ✅ model_info (2949 dl, 15 GGUFs) | **NEW · additive · needs-experiment** | `FleetRegistry` / `Task.FUNCTION_CALL` (currently EMPTY) | 3B Granite-4.1 — the SAME validated no-thinking, tool-capable family as the Hermes main model (Granite-4.1-8B), but small enough for a $0 NPU/iGPU FUNCTION_CALL specialist. **Serving trap**: tool-calling breaks on chat-template / tool-call-special-token mismatch (the orchestrator's prompt format must match the model's template) — so *registration* is additive; *serving* is needs-experiment. → backlog item 21. |
| **arXiv 2606.05922** — Retrospective Harness Optimization (RHO), Pan et al., submitted 2026-06-04 | ✅ WebFetch (title/authors/date/abstract) | **NEW · needs-experiment · METHOD (not a model)** | `compound/` SkillRefiner + RetrospectionEngine; informs items 7/9 | RHO optimizes an agent's HARNESS *without labeled validation data*: select a coreset of hard tasks from past trajectories, re-solve in parallel, self-validate (self-consistency), generate candidate harness updates, pick the best by **pairwise self-preference**. Directly maps onto Cohezion's self-improvement loop — the routing corpus (item 9) is exactly the "past trajectories" RHO consumes. → backlog item 22 (adapt the self-preference selector to SkillRefiner; larger research integration, needs-experiment). |

**Round verdict**: 2 verified levers — Granite-4.1-3B (empty `Task.FUNCTION_CALL` specialist, item 21) and the RHO method (self-supervised harness optimization over the routing corpus, item 22). Both needs-experiment. No regression-risk or fabricated items this round.

## 2026-06-06 (round 3)

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`ggml-org/GLM-OCR-GGUF`** | ✅ model_info (23,009 dl, 69 likes, 3 GGUFs incl mmproj) | **NEW · additive · needs-experiment** | `FleetRegistry` / `Task.OCR_DOC` (the LAST empty slot) | Official **ggml-org** (llama.cpp's own org) OCR/document VLM in GGUF — files `GLM-OCR-Q8_0.gguf` + `GLM-OCR-f16.gguf` + `mmproj-GLM-OCR-Q8_0.gguf`. Runs via `llama-server -hf ggml-org/GLM-OCR-GGUF` (mmproj auto-paired). Directly fills the empty `OCR_DOC` specialist (un-gates backlog item 23). **Serving trap = SAME mmproj/llama-mtmd path as item 18 (LFM2.5-VL)**: lemonade `--mmproj` support UNPROVEN → llama-mtmd sidecar fallback; **K1/rule-5 OOM gate** must pass before pinning (size unconfirmed — check `free -h` first). So *registration* is additive ($0, verified_working=False); *serving* is needs-experiment (shares item-18's vision-projector experiment). |

**arXiv this round**: no NEW verifiable arXiv id surfaced this round (RHO 2606.05922 already queued as item 22). Not fabricating one — omitted honestly.

**Round verdict**: 1 high-value verified lever — `ggml-org/GLM-OCR-GGUF` un-gates the OCR_DOC specialist (item 23). It's an OFFICIAL ggml-org repo (highest provenance), GGUF + mmproj included, on the same vision-projector serving path as item 18 — so the OCR serving experiment piggybacks on the LFM2.5-VL mmproj work rather than being net-new infra.

## 2026-06-06 (round 4)

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`JetBrains/Mellum-4b-base-gguf`** | ✅ model_info (406 dl, 41 likes, 1 GGUF `mellum-4b-base.Q8_0.gguf`) | **NEW · additive · needs-experiment** | `FleetRegistry` / `Task.FIM` (the LAST empty slot) | FIM-native BASE model — fill-in-the-middle via `/api/v1/completions` with `<fim_prefix>…<fim_suffix>…<fim_middle>` tokens (NOT chat). Verified id + filename match strix-halo-fleet-orchestration §8's claim. **Un-gates backlog item 28** — its research gate ("verify the GGUF id via model_info before registering, do NOT trust the skill's claim alone") is now SATISFIED. Registration is additive ($0, `verified_working=False`); FIM-completion serving stays needs-experiment. Q8_0 ≈ 4 GB → load on-demand, do NOT pin (K1/rule-5). |
| **arXiv 2605.17613** — VeriCache: Turning Lossy KV Cache into Lossless LLM Inference (Yao et al., submitted 2026-05-17) | ✅ WebFetch (title/authors/date/abstract) | **grounded · needs-experiment · METHOD (no llama.cpp impl)** | `resource_manager` / KV-cache pressure (conceptual only) | Lossless KV-cache compression: draft with the COMPRESSED KV cache, verify against the FULL cache kept OUTSIDE GPU memory; up to 4× throughput by overlapping bandwidth-bound decode with I/O-bound cache swap. Conceptually apt for the unified-memory Strix Halo regime (KV offload + minimize swap), but it is a research framework with NO llama.cpp/lemonade implementation → NOT fleet-runnable today. **WATCH-ITEM only — no backlog row** (nothing to register/run; would be fabricating actionability). Re-check if llama.cpp lands a compressed-KV draft-verify path. |

**arXiv this round**: RHO 2606.05922 (already item 22) and QuantSpec 2502.10424 / XQuant 2508.10395 / adaptive-KV-quant 2604.04722 all surfaced but are either already-queued or older than the ~30-day window — not re-logged. Only the May-17 VeriCache is in-window and new; logged as a watch-item.

**Round verdict**: 1 high-value verified, fleet-runnable lever — `JetBrains/Mellum-4b-base-gguf` VERIFIED, **un-gating backlog item 28** (the last empty `Task.FIM` slot; same family of empty-slot specialists as items 19/21/23). VeriCache (2605.17613) verified but logged as a KV-cache WATCH-ITEM (no implementation → not fleet-runnable; deliberately NOT made a backlog row). No fabricated or regression-risk items.

## 2026-06-06 (round 5)

Source: user-shared @googledevs post (x.com/.../2062930781945700861, 2026-06-05) — "Gemma 4 QAT
models". Tweet text verified via the syndication endpoint; HF ids verified via `model_info`.

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`google/gemma-4-E2B-it-qat-q4_0-gguf`** | ✅ model_info (1948 dl, 2 GGUF: model + mmproj) | **NEW · additive · needs-experiment** | `triune_orchestrator` NPU :13306 / `FleetRegistry` Gemma-4-E2B (Sensing) | Official Google QAT q4_0 of the fleet's E2B tier. QAT > PTQ at the same 4-bit width → better quality at ≤ current memory. Also the CLaSp draft tier. |
| **`google/gemma-4-E4B-it-qat-q4_0-gguf`** | ✅ model_info (1595 dl, 2 GGUF incl mmproj) | **NEW · additive · needs-experiment** | iGPU :13307 / `FleetRegistry` Gemma-4-E4B (Governance/Knower) | QAT q4_0 of the MAIN iGPU interactive tier. mmproj included → vision-capable (could also feed VISION/EXTRACTION/OCR mmproj path, items 4/18/23). |
| **`google/gemma-4-26B-A4B-it-qat-q4_0-gguf`** | ✅ list_models (search hit; verify `model_info` before serve) | **NEW · additive · needs-experiment** | iGPU Unified :13308 / Gemma-4-26B-A4B (Thinker, MoE) | QAT q4_0 of the 26B-A4B MoE tier. K1/rule-5 OOM gate MUST pass before pinning (MoE size). |
| **`google/gemma-4-31B-it-qat-q4_0-gguf`** | ✅ model_info (3821 dl, 37 likes, 2 GGUF incl mmproj) | **NEW · additive · needs-experiment** | CPU :13309 / Gemma-4-31B (Architect/Safety) | QAT q4_0 of the CPU reasoning tier. Highest-traction QAT repo. |

**Round verdict**: HIGH-VALUE verified lever — official Google **Gemma-4 QAT q4_0 GGUF** exists for
ALL FOUR fleet Gemma-4 tiers (E2B/E4B/26B-A4B/31B). QAT beats post-training quant at the same
bit-width → better quality at lower/equal memory, $0, directly relevant to the memory-tight Strix
Halo box (K1/rule-5). → backlog item 50 (per-tier swap, needs-experiment: serve + memory + quality
proof + K1/rule-5 gate + lanes-up window; NEVER auto-swapped). `unsloth/gemma-4-*-it-qat-GGUF`
mirrors exist (incl. `-mobile-` E2B/E4B) as alternates. NOT a behavior change until the proof passes.

## 2026-06-06 (round 6)

Source: user-shared HF model. Verified via `model_info`; assessed against the local AMD fleet.

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`nvidia/nemotron-3.5-asr-streaming-0.6b`** | ✅ model_info (1380 dl, 216 likes, pipeline=automatic-speech-recognition) | **grounded · WATCH-ITEM (NOT fleet-runnable today; NOT a backlog row)** | (would-be) audio speech-INPUT — but no such seam exists | High-quality streaming multilingual ASR (FastConformer-RNNT/Parakeet). **DECLINED for now, 3 blockers**: (1) format is `.nemo` ONLY — NO GGUF; runs on the NeMo toolkit/PyTorch, NOT lemonade/llama.cpp; `nemo` not even installed; (2) NeMo ASR is CUDA-centric → unverified/painful on AMD ROCm Strix Halo; (3) NO existing Cohezion ASR consumer — `audio/` is the TTS/narration OUTPUT side, not speech-input. License "other" (NVIDIA). Same filter as BigSet/LangChain: verified but off-stack/off-seam → watch-item, not actionable. **Name coincidence**: distinct from the Kaggle "Nemotron" reasoning challenge (`competition/nemotron_solver/`). Revisit IF a GGUF/ONNX export lands AND a voice-input feature is wanted. |

**Round verdict**: 0 fleet-runnable levers. `nvidia/nemotron-3.5-asr-streaming-0.6b` is verified
and impressive but off-stack (NeMo `.nemo`, CUDA-centric) and off-seam (no Cohezion ASR consumer)
→ logged as a WATCH-ITEM, deliberately NOT a backlog row (would fabricate actionability). Filter
tally across user-shared links: 1 embraced (Gemma-4 QAT, round 5 / item 50), 3 declined (LangChain
cloud-microVMs → item 48 audit only, BigSet TS-SaaS → item 49 data-discipline only, this ASR model).

## 2026-06-06 (round 7)

Source: user-shared HF paper. Verified via WebFetch (HF papers abstract).

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **arXiv 2605.31075** — Task-Focused Memorization for Multimodal Agents (TaskMem; ByteDance Seed + Fudan) | ✅ WebFetch (title/authors/abstract/method/benchmarks) | **grounded · METHOD · watch-item (method) + 1 transferable principle** | `governance/knowledge_bridge` deposit gates (items 15/16/24/29/51) — the neurogenesis "what to memorize" thread | Memory as a LEARNABLE policy (GSPO phase-1 + a 2,048-param DPO adapter phase-2), multi-objective rewards: **accuracy, non-redundancy, format compliance**. Built on Qwen3-VL-30B; +6.3% VideoMME / +7.0% EgoLife. **Method DECLINED** as off-stack (RL-train a 30B VL — not $0-fleet), off-modality (video-stream memory ≠ Cohezion's routing/skill/inference neurons), no confirmed artifact release. **Principle EMBRACED**: Cohezion's deposit gates are FIXED heuristics; TaskMem's reward taxonomy is the quality lens the store never measures. Note item 51 (recall-dedup) already = TaskMem's "non-redundancy" reward → paper validates that direction. → backlog item 52 (read-only deposit-quality audit over the existing neurons store). |

**Round verdict**: 0 fleet-runnable model levers; 1 transferable PRINCIPLE. TaskMem's method is too
heavy/off-modality for the $0 fleet (watch-item), but its memory-quality reward taxonomy
(non-redundancy / accuracy / format) maps cleanly onto Cohezion's neurogenesis deposit thread →
report-only item 52 (deposit-quality audit). Filter tally across user-shared links: 1 model embraced
(Gemma-4 QAT), 4 declined-but-mined-for-principle (LangChain→48, BigSet→49, Nemotron-ASR→none, TaskMem→52).

## 2026-06-06 (round 8)

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`byteshape/Qwen3.6-35B-A3B-MTP-GGUF`** | ✅ model_info (33,361 dl, 56 likes, apache-2.0, 6 GGUF IQ2_S→IQ4_XS, tag `mtp`) | **NEW · additive · needs-experiment** | `triune_orchestrator` iGPU main interactive tier (:13307) / `FleetRegistry` | CONFIRMS the strix-halo-fleet-orchestration §1 claim (`Qwen3.6-35B-A3B-MTP-GGUF`) — the MTP heads ship INSIDE the GGUF (no separate draft model, no vocab-match). Self-speculative decoding via `llama-server --spec-type draft-mtp --spec-draft-n-max 3` → ~1.7-1.9× at $0 on the 3B-active MoE. **Serving trap (§1)**: lemonade does NOT expose `--spec-type` → must launch `llama-server` directly (or a custom lemonade recipe), NOT the standard `lemonade load`. **K1/rule-5**: IQ4_XS ≈ 17 GB (under the 20 GB pin gate; 35 GB free now) — heavier than the current ~5 GB Gemma-4-E4B main tier, so a quality/speed-vs-memory swap. So *registration* is additive; *MTP serving + the model swap* is needs-experiment. → backlog item 53. |

**arXiv this round**: no NEW in-window (~30-day) verifiable method surfaced. The relevant KV-cache
papers — `2603.04428` (Persistent Q4 KV Cache for multi-agent edge, MARCH) and `2604.04722`
(adaptive on-device KV quant, APRIL) — are older than the window; `CostRoute` + the "Qwen3.5 on a
laptop @10.33 t/s" claims have no verifiable arXiv id. Not fabricating one — omitted honestly.
(`2603.04428` noted as an out-of-window watch candidate: multi-agent persistent Q4 KV → 4× more
agent contexts; relevant to `resource_manager`/`semantic_cache` IF a future tick re-scopes it.)

**Round verdict**: 1 HIGH-VALUE verified, fleet-runnable lever — `byteshape/Qwen3.6-35B-A3B-MTP-GGUF`
confirms the §1 MTP claim (apache-2.0, 33k dl) and unlocks ~1.7-1.9× self-speculative decoding on
the iGPU main tier at $0 → backlog item 53 (needs-experiment: direct-llama-server MTP serving +
memory/quality proof + K1/rule-5 gate). No fabricated or regression-risk items.

## 2026-06-06 (round 9)

Source: user-shared HF paper (arXiv 2606.03264, PaddleOCR-VL-1.6). Paper abstract via WebFetch;
the released GGUF id verified via `model_info`.

| Finding (HF id / arXiv) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`PaddlePaddle/PaddleOCR-VL-1.6-GGUF`** (arXiv 2606.03264) | ✅ model_info (4981 dl, apache-2.0, 2 GGUF: model + **mmproj**) | **NEW · additive · needs-experiment** | `FleetRegistry` / `Task.OCR_DOC` — an ALTERNATIVE to GLM-OCR (item 23) | OFFICIAL PaddlePaddle GGUF of the round's paper model — a **0.9B** document-parsing VLM, **96.33% OmniDocBench v1.6 (SOTA)** via data-curation + staged post-training (CPT→SFT→RL/GRPO). mmproj INCLUDED → serves on the SAME `llama-mtmd` vision-projector path as GLM-OCR (item 23) / item 18. At 0.9B it is far smaller than most OCR VLMs → easy K1/rule-5 gate, $0. Directly competes with the current OCR_DOC seed (GLM-OCR): a head-to-head on OmniDocBench picks the winner. So *registration* is additive (verified_working=False, like items 4/19/21/23); *serving + the GLM-OCR-vs-PaddleOCR bake-off* is needs-experiment (shares item-18's mmproj serving work). → backlog item 54. |

**Round verdict**: 1 HIGH-VALUE verified, fleet-runnable lever — `PaddlePaddle/PaddleOCR-VL-1.6-GGUF`
(official apache-2.0 GGUF+mmproj, 0.9B SOTA doc-OCR) is a strong alternative/upgrade to GLM-OCR for
the OCR_DOC slot → backlog item 54 (additive registration; serving + bake-off needs-experiment, on
item-18's mmproj path). Filter tally across user-shared links: 2 embraced (Gemma-4 QAT → item 50,
PaddleOCR-VL → item 54), 3 declined-but-mined (LangChain→48, BigSet→49, Nemotron-ASR→none, TaskMem→52).

## 2026-06-06 (round 10)

Source: user-shared GitHub (RyanCodrai/turbovec). PyPI package verified via the JSON API.

| Finding (HF id / pkg) | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **`turbovec` (PyPI 0.7.0)** — Rust+Python ANN index, Google-Research TurboQuant quantizer | ✅ PyPI JSON (0.7.0, "2-4 bit compression + SIMD search", py≥3.9) | **NEW · additive · needs-experiment** | `knowledge_bridge` neurons-store recall (item 29) / vault embeddings — NOT the calibrated `semantic_cache` | Data-oblivious (no training) 2-4 bit embedding quantization, SIMD (AVX-512BW — the AMD box has it), local-only, 16× compression (10M docs 31GB→4GB), 12-20% faster than FAISS-PQ-FastScan on ARM, +0.4-3.4 R@1. On-philosophy (local, $0, memory-tight Strix Halo / K1/rule-5). **Cohezion ALREADY uses the TurboQuant algorithm** — `inference/turboquant_streaming.py` (StreamingKVCompressor) for KV-CACHE; turbovec extends the same family to the EMBEDDING-INDEX domain. Best fit: the GROWING neurons store — item-29 `recall_neurons` does a LINEAR SurrealDB SELECT; a turbovec ANN index would scale recall + cut memory. **Caveat 1**: NOT a `semantic_cache` drop-in — CA1 is calibrated (nomic-embed 768D → 0.58, 0% FP); 2-4 bit quantization shifts similarity → threshold recalibration (regression-risk, same as round-1 Qwen3-Embedding). **Caveat 2**: a Rust-backed pip dep, community single-maintainer → moderate supply-chain trust (the algorithm is Google Research; the impl is community). → backlog item 56. |

**Round verdict**: 1 verified, on-philosophy lever — `turbovec` (local TurboQuant ANN index) for the
GROWING neurons-store recall (item 29 currently linear-scans). Cohezion already uses TurboQuant for
KV-cache, so the algorithm is familiar. → backlog item 56 (needs-experiment: add dep + benchmark
recall/memory/latency vs the linear SELECT on a synthetic neuron corpus; NOT the calibrated cache
without a CA1 recalibration). Filter tally across user-shared links: 3 embraced (Gemma-4 QAT→50,
PaddleOCR-VL→54, turbovec→56), 4 declined-but-mined (LangChain→48, BigSet→49, Nemotron-ASR→none, TaskMem→52).

## Round 11 — 2026-06-06 (user-shared: arXiv 2606.02060, DRIFT / span-level error localization)
Source: user-shared HF paper. Verified via WebFetch (HF papers page + abstract).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **DRIFT** — claim-centric span-level error localization in agent trajectories (arXiv 2606.02060: *"Where Do Deep-Research Agents Go Wrong?"*) | ✅ HF papers + abstract (Claim Keeper → Support Seeker → Dependency Tracer; TELBench 1000 trajectories) | **NEW · additive · needs-experiment** | trajectory/claim seam: `compound/tape_logger`, `compound/journey_tracker`, `compound/retrospection_validator`, `inference/anti_sycophancy` | A methodology + dataset paper (no GGUF/model artifact). The PRINCIPLE maps directly to cohezion's observability: build a CLAIM LEDGER over an agent trajectory (introduced → consequential → reused), classify each consequential claim's support (supported / weakly / missing / contradicted), and DEPENDENCY-TRACE which spans propagate an unsupported claim → localize WHERE a trajectory "went wrong" (vs only checking the final answer). Separates "benign exploration from harmful commitments." Aligns with cohezion's metacognitive-calibration + measurement-integrity theme (the honest-NULL / pre-registered-bake-off discipline). **Caveat 1 (the experiment)**: faithful DRIFT uses STRONG judge models (GPT-5/Gemini-2.5/Sonnet-4.5) for support classification — cloud, which conflicts with local-$0/CC2. The LOCAL version routes support-classification through the fleet (extend_claude); whether a local judge is strong enough is the open question (regression-risk: a weak judge → noisy localization). **Caveat 2**: it is a methodology, not a drop-in — the structural instrument (claim ledger + dependency tracer + first-unsupported-claim localization) is additive/falsifiable with an INJECTED judge; the production judge quality is needs-experiment. → backlog item 69. |

**Round verdict**: 1 verified, on-theme methodology — DRIFT span-level claim-support localization for
cohezion's trajectory/retrospection seam. Structural instrument is additive + falsifiable (injected
judge); the local-judge support-classification quality is the needs-experiment part (faithful DRIFT
used cloud judges). NOT a model pull (no artifact). → backlog item 69 (report-only instrument with an
injectable judge; production judge = local fleet, quality TBD). Filter tally (user-shared links):
4 embraced (Gemma-4 QAT→50, PaddleOCR-VL→54, turbovec→56, DRIFT→69), 4 declined-but-mined.

## Round 12 — 2026-06-06 (user-shared: TDS "Automate Writing Your LLM Prompts" → DSPy)
Source: user-shared Towards Data Science article. Verified via WebFetch.

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **DSPy** (Stanford) — automated prompt optimization: generate candidates → evaluate vs test data + scoring fn → keep best → iterate (meta-prompting) | ✅ WebFetch (DSPy named; `dspy.LM("openai/gpt-4o-mini", …)`; "supports dozens of providers") | **GROUNDED · OVERLAPS-EXISTING · needs-experiment (dep-gated)** | `models/rho_selector` + `compound/skill_refiner` + `compound/harness_tuning_specialist` (cohezion's EXISTING prompt/harness optimizer) | **Not new capability** — cohezion ALREADY does generate→evaluate→keep-best: `generate_harness_candidates`→`select_harness_update` (RHO self-preference tournament, "winner beats baseline on a held-out check"), items 22/33/42. DSPy is the canonical external version. **Caveat 1 (off-philosophy as-demoed)**: the article uses PAID OpenAI; DSPy's value for cohezion exists ONLY pointed at the LOCAL fleet (lemonade exposes OpenAI-compatible `/api/v1` on :13305 → `dspy.LM("openai/Granite-4.1-8B-GGUF", api_base="http://localhost:13305/api/v1")` for $0). **Caveat 2 (architecture/dep decision)**: adopting DSPy = a framework dependency that could DUPLICATE or REPLACE the hand-rolled RHO — that is a human/architecture decision, NOT an auto-wire. The legitimate additive lever is a VALIDATION benchmark: DSPy-on-local-fleet vs the RHO selector on the SAME skill-optimization task — "is our hand-rolled loop competitive with the canonical framework?" (the systematic-debugging leaderboard-gap check). → backlog item 70 (needs-experiment, dep-gated). |

**Round verdict**: 1 verified but OVERLAPS existing capability — DSPy formalizes what cohezion's RHO
selector already does (items 22/33/42). NOT new capability; the article's paid-OpenAI demo is off
local-$0. Honest lever = a DSPy-on-fleet vs RHO VALIDATION benchmark ($0 via lemonade :13305), NOT a
framework swap (human/architecture decision). → backlog item 70 (needs-experiment + dep-gated;
validates the existing loop, does not replace it). Filter tally (user-shared links): 4 embraced,
4 declined-but-mined, 1 overlaps-existing-validate (DSPy→70).

## Round 13 — 2026-06-06 (user-shared: arXiv 2606.04743, TIDE / proactive multi-problem discovery)
Source: user-shared HF paper. Verified via WebFetch (abstract + datasets + backbones).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **TIDE** — proactive multi-problem discovery via template-guided iteration (arXiv 2606.04743) | ✅ HF papers + abstract (iterative discovery + thought templates; 150 workspace problems / 146 repo bugs; GPT-5/Sonnet/Gemini/Qwen3.6 backbones) | **GROUNDED · OVERLAPS-EXISTING · additive-lever** | `compound/simplicity_audit` + `exec_sandbox_audit` + `skill_adoption` (the audit instruments = implicit "thought templates"); `scope_frontier` + `research_feed_parser` (the iterative-discovery seam) | A methodology + dataset paper (no released code/model). TWO mechanisms, BOTH already present in cohezion but SCATTERED: (1) **thought templates** = reusable problem-class schemas → cohezion's deterministic audit instruments (complexity_outliers/nesting_outliers/passthrough_functions/needless_passthroughs/unsandboxed_exec_paths/skill_adoption_report) ARE exactly this — each encodes "what signals indicate a problem class"; (2) **iterative discovery conditioning on already-found** (so salient problems don't overshadow subtle) → the loop's accumulating backlog + scope-expansion, BUT no instrument CONDITIONS ON already-known findings to avoid re-surfacing. **The genuinely-additive lever**: a `ProblemTemplate` registry that unifies the scattered audit instruments under one `discover_problems(paths, *, exclude_known)` entry point + adds the TIDE iterative-discovery dedup (suppress findings already in the backlog). **Caveat**: TIDE's paper uses CLOUD backbones for discovery; cohezion's audit instruments are DETERMINISTIC (AST-based), so the local version is report-only/$0 (NOT needs-experiment) — the deterministic instruments ARE the templates. Not new capability per-instrument; the unification + condition-on-known IS new. → backlog item 73. |

**Round verdict**: 1 verified, on-architecture methodology — TIDE formalizes what the self-improvement
loop already does (proactive audit discovery + scope expansion + skills-as-templates). The additive
lever is UNIFICATION + iterative-discovery dedup over the EXISTING deterministic audit instruments
($0, report-only — not needs-experiment). → backlog item 73. Filter tally (user-shared links): 4
embraced, 4 declined-but-mined, 2 overlaps-existing (DSPy→70 validate, TIDE→73 unify), 1 needs-exp-instrument (DRIFT→69).

## Round 14 — 2026-06-06 (user-shared: MS AI Red Team failure-mode taxonomy v2.0)
Source: user-shared Microsoft Security blog (2026-06-04). Verified via WebFetch.

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **Agentic AI failure-mode taxonomy v2.0** (MS AI Red Team) — 7 new modes: supply-chain compromise, goal hijacking, inter-agent trust escalation, CUA visual attack, session context contamination, MCP/plugin abuse, capability disclosure | ✅ WebFetch (MS Security blog, detailed taxonomy) | **GROUNDED · CHECKLIST · mostly-covered + 1 additive gap** | maps to MANY cohezion security seams (see below) | A security CHECKLIST, not a model/tool. **Validation outcome**: most modes ALREADY have cohezion coverage — exec/code-exec → item-48 `exec_sandbox_audit`; prompt-injection/credential-leak (goal hijacking / XPIA) → `inference/security_spec` (harness I7); memory poisoning → item-52 `neuron_quality` (non-redundancy/evidence/format); session context contamination → the Session Control Plane invariants (harness SCP1-5, UNTRUSTED framing); inter-agent trust escalation → SCP1 atomic ack/claim + record-id guards. **The one genuine GAP**: MCP/Plugin Abuse ("tool description poisoning, server-side instruction injection") — cohezion's MCP bridge (`integrations/hermes_mcp_bridge` `_tools_list`) exposes tool descriptions but has NO audit for instruction-injection IN those descriptions. **Caveat**: most of the taxonomy is architectural posture (already addressed), not net-new deterministic checks; CUA-visual-attack + supply-chain are off cohezion's current surface (no CUA; dep supply-chain already flagged per-lever in this feed). → 1 additive lever: backlog item 76 (tool-description-poisoning audit). |

**Round verdict**: 1 verified security CHECKLIST — and the honest outcome is mostly VALIDATION (cohezion
already covers exec/injection/memory/session/inter-agent modes via items 48/52 + security_spec + SCP).
The single net-new deterministic instrument = an MCP tool-description-poisoning audit (the one mode with
a real cohezion surface + no existing check). → backlog item 76. Filter tally (user-shared links): 4
embraced, 4 declined-but-mined, 2 overlaps-existing, 1 needs-exp-instrument, 1 checklist-validates+1-gap.

## Round 15 — 2026-06-06 (user-shared: arXiv 2606.03890, OVO-S-Bench)
Source: user-shared HF paper. Verified via WebFetch.

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **OVO-S-Bench** — hierarchical benchmark for STREAMING SPATIAL intelligence in multimodal LLMs (arXiv 2606.03890; 1,680 Q / 348 egocentric videos / 4 abstraction levels; dataset+code on GitHub) | ✅ HF papers + abstract (InternLM; Gemini-3.1-Pro 59.2 vs human 86.6) | **DECLINE · off-modality · off-use-case** | NONE | A streaming egocentric-VIDEO spatial-reasoning BENCHMARK for robotics/AR/autonomous-driving. **No cohezion seam**: cohezion's only VLM surface is the DOCUMENT/EXTRACTION tier (EXTRACTION/VISION/OCR_DOC — tiny 1.6B LFM2.5-VL / 0.9B PaddleOCR for image→YAML + doc OCR), NOT streaming video; cohezion has no robotics/AR/AV/egocentric surface. It is a benchmark (no servable model artifact to register). The mineable eval-design ideas (PREFIX-ONLY streaming evaluation; HIERARCHICAL abstraction levels) have no cohezion task to apply to — cohezion has no streaming-video task. Same class as round-6 Nemotron-ASR (off-modality streaming, declined). **No transferable principle that maps to an existing seam → NO backlog item** (non-fabrication: a row with no real seam is drift). |

**Round verdict**: 0 levers — clean DECLINE. OVO-S-Bench is off cohezion's modality (streaming egocentric
video) AND use-case (robotics/AR/AV); cohezion's VLMs are document-extraction tier; no servable artifact;
no transferable principle with a target task. Like Nemotron-ASR (round 6), the honest outcome is "no real
seam → no item" — the filter declining is the filter WORKING. Filter tally (user-shared links): 4 embraced,
5 declined-but-mined/declined, 2 overlaps-existing, 1 needs-exp-instrument, 1 checklist-validates.

### CORRECTION (2026-06-06, user pushback) — RECLASSIFY: DECLINE-product → decline-product / **mine the spatial-reasoning HIERARCHY**

The original DECLINE judged OVO-S-Bench on its **modality** (egocentric video) and **artifact** (a
benchmark, no servable model) — both still true; we register no video model. But the user pointed out the
miss: *"capture agentic journeys as EVO analogues … spatial awareness for novel physics research."* The
**structural principle** — that spatial intelligence is a HIERARCHY of abstraction levels — is modality-
independent, and cohezion already moves agents through a literal 12D/256D manifold. The hierarchy maps:

| OVO-S-Bench level | cohezion seam | Status |
|---|---|---|
| L1 instantaneous position | a journey's current FLUME / 12D point | exists (`JourneyTracker.record_state`) |
| L2 spatiotemporal tracking | the recorded 12D trajectory | exists (`JourneyTracker`, FLUME `journey_encoder` / `trajectory_capture`) |
| L3 spatial simulation | per-trajectory CURVATURE | exists (JEPA `measure_temporal_straightening`) |
| **L4 allocentric mapping** | GLOBAL geometry of where ALL journeys live relative to each other | **was THE GAP — now built** |

**Mined → real lever**: built `compound/journey_spatial.py::journey_allocentric_map` (centroids /
pairwise distance / nearest-neighbour over injected trajectory vectors; report-only, pure) — the L4
allocentric view, committed `87bacb79e`, 5 discriminating tests. The benchmark itself stays DECLINED (no
video task); the **hierarchy-as-design-principle** is embraced and instrumented. Backlog item 79 tracks the
full hierarchy as the frontier (L4 done; L1–L3→L4 composition + a curvature/allocentric drift signal next).
Lesson recorded: judge a research artifact's transferable PRINCIPLE separately from its modality/artifact —
an off-modality benchmark can still carry an on-substrate structural idea. Tally update: OVO-S-Bench moves
from `declined` to `declined-product / mined-principle` (4 embraced, 4 declined, 1 declined-but-mined→**+1
OVO-S-Bench = 2 declined-but-mined**, 2 overlaps-existing, 1 needs-exp-instrument, 1 checklist-validates).

## Round 16 — 2026-06-06 (fleet scan: MTP drafters/rerankers + user-shared arXiv 2605.27492, 2606.04703)
Sources: HuggingFace `model_info` (every id verified) + WebFetch (every arXiv id verified). Tight round — a
couple of verified fleet-runnable levers over a hype list. NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **Gemma-4-26B-A4B assistant-drafter** — `google/gemma-4-26B-A4B-it-assistant` (official MTP/assistant drafter, dl 159k, apache-2.0) + GGUF `AtomicChat/gemma-4-26B-A4B-it-assistant-GGUF` (5 gguf, dl 32k) | ✅ `model_info` both ids | **needs-experiment / regression-risk** | triune `iGPU-Unified` Gemma-4-26B-A4B tier; `FleetRegistry` ModelEntry | Classic draft-model speculative decoding for the Gemma-4-26B-A4B tier (~1.85-2× at $0 IF it serves). **NOT fleet-runnable on stable**: llama.cpp `Gemma4AssistantForCausalLM` support is WIP (PR #23398 UNMERGED — conversion fails on `layer_scalar`; only an experimental fork works). VERIFIED model, unproven runtime → **feed-only, NO backlog item** (the backlog rule needs *fleet-runnable*). WATCH PR #23398; promote to a backlog needs-experiment item (sibling of item 53) only when it merges into llama.cpp + lemonade. K1/rule-5 OOM gate + lanes-up window will apply. |
| **Qwen3.6-27B-MTP-GGUF** — `unsloth/Qwen3.6-27B-MTP-GGUF` (dl 1.12M, 26 gguf, apache-2.0) / `froggeric/Qwen3.6-27B-MTP-GGUF` (dl 83k) | ✅ `model_info` both ids | **overlaps-existing (item 53)** | iGPU main tier; same `--spec-type draft-mtp` path as item 53 | Merged MTP (PR #22673, 2026-05-16) runs these. But this is a 27B **DENSE** MTP; item 53 already owns `byteshape/Qwen3.6-35B-A3B-MTP-GGUF` (3B-active MoE — faster on the memory-tight box, K1/rule-5). A dense 27B is NOT a better fit for any cohezion tier → no new lever, no backlog item. Records the variant exists. |
| **Ramp — "Benchmarks are Not Enough: Runtime Assessing of Agentic Models"** (arXiv 2605.27492, May 2026; YatCC repo, no servable model) | ✅ WebFetch | **grounded / mine-principle** | `DegradationDetector` + `loop_telemetry` (items 25/30/58) | Long-horizon SERIAL-DEPENDENCY workloads expose per-stage completion COLLAPSE (100%→20% over 6 stages) invisible to single-shot benchmarks; a "resurrection protocol" injects a corrected intermediate artifact to isolate DOWNSTREAM capability. No model. Mineable PRINCIPLE: measure stage-by-stage attrition across the loop's serial pipeline (a sharper signal than item-30 stall / item-58 regression, which are aggregate counts). Logged as a future report-only telemetry candidate; NOT added to backlog this round (kept tight — one lever/round). |
| **ExpInternalization — "Rethinking Continual Experience Internalization for Self-Evolving LLM Agents"** (arXiv 2606.04703, **June 2026 — in window**; code `github.com/RUCBM/ExpInternalization`) | ✅ WebFetch | **grounded / VALIDATES thread M + 1 additive refinement** | neuron-deposit quality (items 52/55/74) + thread M (88/90) | Three findings: (1) abstract **principle-level** experience beats instance-specific detail; (2) step-wise injection aligned to intermediate decisions; (3) off-policy distillation on **high-quality** teacher trajectories. (2)+(3) VALIDATE cohezion's existing design — the cerebellum stores *procedural/abstract* neurons, and the experiential hook deposits only **ACCEPTED** (AUTODQA-gated) outcomes (= high-quality teacher trajectories, not on-policy noise). (1) is the additive REFINEMENT → **new backlog item 92**: a neuron-deposit ABSTRACTION-quality dimension flagging instance-specific deposits that should be principle-level (extends the item-52 deposit-quality audit). Report-only, fleet-runnable (pure Python), $0. |

**Round verdict**: 2 verified GGUF levers (1 needs-experiment-not-yet-runnable = Gemma-4 drafter behind PR #23398; 1 overlaps item 53 = Qwen3.6-27B-MTP) + 2 verified arXiv papers (Ramp grounds the degradation-telemetry thread; ExpInternalization VALIDATES thread M's deposit-only-accepted + abstract-cerebellum design and yields ONE additive refinement → backlog item 92). Non-fabrication held: the high-value Gemma-4 drafter is feed-only because it is NOT yet fleet-runnable (stable llama.cpp can't convert it); it gets a backlog row only after PR #23398 merges. Self-improving-agent arXiv space (ERL 2603.24639, EvoTest 2510.13220) is out of the 30-day window and already covered by thread M — no row. Filter tally (user-shared links): +2605.27492 grounded-mine-principle, +2606.04703 grounded-validates+refine → 5 embraced/refined, 4 declined, 2 declined-but-mined, 2 overlaps-existing, 1 needs-exp-instrument, 1 checklist-validates.

## Round 17 — 2026-06-06 (user-shared: HF CohereLabs/BLS-Mini-Code-1.0)
Source: user-shared HuggingFace repo. Verified via `model_info` + `list_repo_files` + `config.json` + a
llama.cpp arch-support check. NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **CohereLabs/BLS-Mini-Code-1.0** — a `cohere2_moe` (`Cohere2MoeForCausalLM`) CODE MoE: 49 layers, hidden 2048, **128 experts / 8 active** (~30B-total / ~2B-active), 262k vocab, 500k context | ✅ `model_info` (dl 70, likes 23, gated=False) + `config.json` (arch/size) + `list_repo_files` (57 files, **0 GGUF**, 49 safetensors shards) | **needs-experiment / NOT fleet-runnable (decline-for-now)** | `Task.CODE_GEN` / `Task.FIM` (currently `Mellum-4b`, strix-halo §8); `FleetRegistry` ModelEntry | A small-active-param code MoE with 500k context — on paper an attractive $0 code-completion/codegen tier. **Three hard blockers, all verified, none fabricated**: (1) **0 GGUF** in the repo (49 safetensors shards only); (2) **novel arch** — llama.cpp supports `cohere2` (DENSE) but **`cohere2_moe` conversion is unconfirmed** and no community GGUF exists anywhere (strong evidence the converter doesn't handle it yet); (3) **no declared license** (`license=None`) → adoption/supply-chain blocker. Verified model, unproven runtime + no license → **feed-only, NO backlog item** (the backlog rule needs *fleet-runnable*; same precedent as round-16 Gemma-4 drafter). WATCH: a community GGUF + llama.cpp `cohere2_moe` support landing + a declared license; promote to a needs-experiment backlog item (sibling of item 18/54 mmproj/serving-proof items) only when all three clear, behind a K1/rule-5 OOM gate + a CODE_GEN head-to-head vs Mellum-4b. |

**Round verdict**: 0 actionable levers — a clean **decline-for-now**. BLS-Mini-Code is a genuinely interesting ~2B-active code MoE on a real cohezion seam (CODE_GEN/FIM), but it is NOT $0-fleet-runnable today (no GGUF, `cohere2_moe` unsupported by llama.cpp, no license). The honest outcome is feed-only with a 3-condition watch — the filter declining a not-yet-runnable model is the filter WORKING, not a miss. Filter tally (user-shared links): +BLS-Mini-Code needs-experiment-not-runnable → 5 embraced/refined, 4 declined, 2 declined-but-mined, 2 overlaps-existing, **2 needs-exp-instrument/not-runnable**, 1 checklist-validates.

## Round 18 — 2026-06-06 (user-shared: HF higgs-audio-v3-tts-4b + Supra-50M-Reasoning)
Sources: user-shared HuggingFace repos. Verified via `model_info` + `list_repo_files` + `config.json` +
the model card (license/runtime). NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **bosonai/higgs-audio-v3-tts-4b** — expressive/controllable/multilingual **TTS with voices** (`higgs_multimodal_qwen3`, 4B; zero-shot voice cloning, 21 emotion tokens, prosody/SFX control, 100+ languages) | ✅ `model_info` (dl 2.2k, likes 153, pipeline=text-to-speech) + card | **needs-experiment / NON-COMMERCIAL-LICENSED → human decision (feed-only)** | thread M item 85 `Task.AUDIO_TTS`; the audio runtime tier (`audio/narrator.py` PocketTTS / `moshi_client.py`), NOT lemonade | The quality CEILING for cohezion's "audio including voices" directive — strong expressive TTS. **But** (1) license = **Boson Research & Non-Commercial** (production/hosted-API/revenue use PROHIBITED without a separate commercial license) → a HUMAN license-acceptability call, not an autonomous-loop decision; (2) **0 GGUF**, runs via SGLang-Omni / HF Transformers (`AutoModelForSeq2SeqLM`), GPU-focused (H100-benchmarked) → not the $0 lemonade fleet, 4B serving on the iGPU is memory-unproven (K1/rule-5); (3) `higgs_multimodal_qwen3` is a novel arch. **Feed-only, NO backlog item**: item 85 stays on PocketTTS (permissive) as the default AUDIO_TTS seed; Higgs is the higher-quality NC alternative to evaluate ONLY IF a human accepts the research-only constraint AND a transformers-serving + memory proof passes. Logged as a `## Needs human decision` candidate (license acceptability). |
| **SupraLabs/Supra-50M-Reasoning** — a 50M-param `llama`-arch reasoning SLM (apache-2.0; tags slm/tiny/cpu/reasoning) | ✅ `model_info` (dl 808, likes 30, pipeline=text-generation, license=apache-2.0) + `config.json` (llama arch) | **needs-experiment / low-value → feed-only** | NPU tier (`triune_orchestrator`, currently `llama3.2-1b-FLM`); harness N1/N2 | Genuinely fleet-runnable in principle (standard `llama` arch → GGUF-convertible → lemonade), permissive license — the GOOD news. But 50M is below useful single-model quality, and the NPU tier is harness-PINNED to the validated `llama3.2-1b-FLM` (N1/N2) — routing real classification/reasoning to a 50M model is regression-risk, not an upgrade. Only conceivable additive use is a spec-decode DRAFT for the NPU tier, which requires EXACT vocab match with `llama3.2-1b` (unverified; a from-scratch 50M likely has its own vocab → no match). **Feed-only, NO backlog item** (not genuinely high-value; would regress the pinned NPU tier). Records the model + the draft-pairing idea for a future spec-decode experiment IF vocab-compatibility is ever verified. |

**Round verdict**: 0 backlog levers — both feed-only. Higgs-Audio is the strongest "voices" finding so far (directly on the user's thread-M audio directive) but its NON-COMMERCIAL license is a human decision the autonomous loop must not make — surfaced as a Needs-human-decision candidate, with PocketTTS (permissive, item 85) remaining the default lever. Supra-50M is permissive + fleet-convertible but below useful quality and would regress the harness-pinned NPU tier. Non-fabrication + invariant-respect held (N1/N2 NPU pin honored). Filter tally (user-shared links): +higgs-audio NC-human-decision, +Supra-50M low-value → 5 embraced/refined, 4 declined, 2 declined-but-mined, 2 overlaps-existing, **3 needs-exp/not-runnable**, 1 NC-human-decision, 1 checklist-validates.

### RESOLUTION (2026-06-06, user delegated the license call → "pick the path that leads to compound engineering solutions")
Chose the research-only path: Higgs-Audio is added as **backlog item 93** — an ALTERNATIVE `AUDIO_TTS`
tier for LOCAL RESEARCH / SHOWCASE use only (cohezion is a $0 local research platform; the Boson
license permits non-commercial/research/showcase use, which matches the user's "showcase our work"
intent). The compound discipline is the GUARDRAIL: PocketTTS (item 85, permissive) stays the DEFAULT
and the only productizable path, and item 93's Higgs ModelEntry must carry `research_only` +
`non-commercial` tags plus a selection guard so it can NEVER leak into a hosted/revenue/product surface
— captured as a falsifiable check (a test asserts the product-surface selector never returns it). This
captures the quality lever without burning the permissive fallback or crossing the license boundary.

## Round 19 — 2026-06-06 (user-shared: The Conversation, "sophrosyne in the age of AI")
Source: user-shared article. Verified via WebFetch. A PHILOSOPHY essay, not a model/paper/method — the
author explicitly frames sophrosyne (moderation, reflectiveness, self-knowledge) as a CULTURAL problem
with NO proposed technical mechanism, benchmark, metric, or design pattern. NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **Sophrosyne** — the Greek virtue of moderation / self-restraint / self-knowledge ("sound-mindedness": discriminate true from false, know your own limits) as an antidote to AI-era excess | ✅ WebFetch (no technical claims; author calls it cultural, not engineering) | **declined-product / mined-principle (OVERLAPS-EXISTING — no new lever)** | the design ethos already woven through HIHO + metacognitive-calibration + non-fabrication + human-gate + K1/rule-5 | Sophrosyne is the philosophical NAME for principles cohezion already operationalizes — it maps onto existing seams rather than adding one: **HIHO** (50% coherence = the balanced *mean between extremes*, the `4x(1-x)` kernel peaking at the midpoint = exploitation/exploration moderation); **metacognitive-calibration** (confidence ∝ evidence; honest-NULL / abstain = self-knowledge of one's limits); **non-fabrication** (the research filter declining unverifiable models = self-restraint — rounds 16-18's three "feed-only, not-runnable" declines ARE sophrosyne); **human-gate / Needs-human-decision** (deferring the Higgs NC-license call to a human = knowing the limit of autonomous authority); **K1/rule-5 OOM + budget gates** (not loading what would overrun = literal temperance). **No backlog item** — and the DECISION not to manufacture a "sophrosyne metric" is itself the sophrosyne-aligned move: inventing a number for a virtue would be the false precision that `metacognitive-calibration.md` forbids ("a number is a smell, not a verdict") AND would contradict the article's own thesis. The lever already exists, distributed across the harness; naming it is the value, not a new check. |

**Round verdict**: 0 new levers, by design — a reflective DECLINE that names an existing ethos. The
disciplined outcome is to recognize cohezion already embodies sophrosyne (HIHO balance, calibrated
abstention, non-fabrication, human-gating, OOM/budget restraint) and to NOT fabricate a metric for it —
manufacturing false precision here would itself violate the virtue. The filter exercising restraint is
the virtue in action. Filter tally (user-shared links): +sophrosyne mined-principle/overlaps-existing →
5 embraced/refined, 4 declined, **3 declined-but-mined**, 3 overlaps-existing, 3 needs-exp/not-runnable,
1 NC-human-decision, 1 checklist-validates.

## Round 20 — 2026-06-06 (user-shared: arXiv 2606.02482, X-Stream)
Source: user-shared HF paper. Verified via WebFetch. NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **X-Stream** — "Exploring MLLMs as Multiplexers for Multi-Stream Understanding" (arXiv 2606.02482, 2026-06-02; benchmark: 4,220 QA / 932 videos; code+data released, NO custom model) | ✅ WebFetch (eval-only; SOTA ~50% on multi-stream tasks) | **DECLINE · off-modality (streaming video) · no servable model** | NONE (checked: no concrete transferable lever) | A multi-stream STREAMING-VIDEO understanding benchmark analyzing MLLMs as spatial/temporal/semantic "multiplexers" (signal-multiplexing theory). Off cohezion's modality (no video task; the VLM tier is document/image INPUT only — LFM2.5-VL/PaddleOCR) and use-case; no servable artifact to register. Per the OVO-S-Bench lesson I checked for a transferable PRINCIPLE: the "semantic multiplexing" idea loosely OVERLAPS cohezion's existing task-classifier routing (`_classify_task` → tiers — already built), and the "proactive capabilities" gap is already covered by the embraced TIDE thread (round 13). No NEW concrete seam → **no transferable lever**. Same class as round-15 OVO-S-Bench / round-6 Nemotron-ASR (video benchmarks, declined). **Feed-only, NO backlog item** (non-fabrication: a row with no real seam is drift). |

**Round verdict**: 0 levers — clean DECLINE. X-Stream is off-modality (streaming video), has no servable model, and its multiplexing/proactive framings map only onto cohezion capabilities that ALREADY exist (task-classifier routing; TIDE proactive discovery) — no new lever. The filter declining an off-modality benchmark whose principle overlaps existing seams is the filter WORKING. Filter tally (user-shared links): +X-Stream declined → 5 embraced/refined, **5 declined**, 3 declined-but-mined, 3 overlaps-existing, 3 needs-exp/not-runnable, 1 NC-human-decision, 1 checklist-validates.

## Round 21 — 2026-06-06 (user-shared: SpaceDaily, "why years speed up as we age")
Source: user-shared article. Verified via WebFetch. Popular-science psychology, no technical claim —
but the core MECHANISM is concrete and maps to a real lever. NO `src/` changes (docs only).

| Finding | Verified | Class | Fleet seam | Notes |
|---|---|---|---|---|
| **Memory-density theory of subjective time** (Eagleman) + proportional theory (Janet): subjective time ∝ NOVELTY/memory DENSITY — novelty creates rich/dense memories, ROUTINE creates "compressed, impoverished" ones; sustained focus on ONE thing also densifies | ✅ WebFetch (reflective psychology, no controlled data) | **grounded / mine-principle → ADD backlog item 95** | `geometric_correspondence` (items 66/67) + the backlog/loop output | Distinct from the sophrosyne round (19): that virtue was already embodied with NO new measurable; THIS carries a concrete, falsifiable mechanism — *novelty density* — that cohezion can compute over its OWN output. cohezion already has the encoder: `geometric_correspondence` measures how similar a new item is to prior commits (HIGH correspondence = "routine/compressed"; LOW = "novel/dense"). The Eagleman principle → a loop self-monitor: are the scope-expansion items geometrically NOVEL (rich, exploring new territory) or near-duplicates (compressed, the loop "spinning")? → **backlog item 95** `novelty_density(items, corpus)` = fraction of items whose max correspondence to the corpus is below a novelty threshold. Report-only, additive, composes existing machinery, NON-fabricated. Caveat: inherits geometric-correspondence's short-title imperfection (item 68) → advisory, never a gate. Distinct from item-80 journey-novelty (FLUME trajectories) — this is novelty of BACKLOG ITEMS. |

**Round verdict**: 1 grounded lever (item 95) — the memory-density principle yields a real loop-novelty self-monitor via the EXISTING geometric-correspondence encoder, unlike round-19 sophrosyne (no concrete measurable → correctly added nothing). The discriminating question "is there a concrete falsifiable instrument on a real seam?" is what separates this (yes — novelty density over loop output) from sophrosyne/X-Stream (no). Filter tally (user-shared links): +time-perception grounded-mine→item-95 → **6 embraced/refined**, 5 declined, 3 declined-but-mined, 3 overlaps-existing, 3 needs-exp/not-runnable, 1 NC-human-decision, 1 checklist-validates.
