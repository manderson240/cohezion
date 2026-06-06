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
