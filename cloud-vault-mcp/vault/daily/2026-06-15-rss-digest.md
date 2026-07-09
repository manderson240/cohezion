---
date: 2026-06-15
tags: [daily, rss-digest, local-inference, model-eval, llama.cpp, ai-policy]
---
# 2026-06-15 — RSS Digest (AI / Local Inference)

## Focus
Automated daily digest: Sebastian Raschka Architecture Gallery, Simon Willison, llama.cpp releases.

## Accomplished

### Sebastian Raschka Gallery (June 13)
- **Kimi K2.7 Code** (Moonshot AI): 1T total / 32B active MoE. MLA attention (same as DeepSeek), 384 experts (8 selected + 1 shared), SwiGLU, 61 layers, 256K ctx, MoonViT vision encoder (400M). GGUF available (unsloth, mradermacher, etc.). **Fleet verdict: Skip** — 1T total params = ~250GB+ at Q2, far exceeds 128GB unified RAM.
- **MiniMax M3** (428B): 428B total / 23B active MoE. MSA (MiniMax Sparse Attention), 1M context, 9× prefill / 15× decode speedup vs M2. GGUF: likely community only. **Fleet verdict: Skip** — at Q2 ~107GB with no headroom for KV cache or OS.

### Simon Willison
- **June 13 — US government suspended Fable 5 + "Mythos 5"**: Export control order received at 5:21pm ET; access cut by ~7pm PT globally. Trigger: demonstrated safety bypass via code analysis (present in competing models too). "Mythos 5" not publicly described by Anthropic. All other models (Sonnet, Haiku, etc.) remain accessible.
- June 14: Editorial — why AI hasn't replaced engineers (WARN Act data). Not technically actionable.
- June 15: Julia Evans quote. Not relevant.

### llama.cpp (10 releases, June 13–15)
- **b9626 (June 13)**: Cohere2MoE architecture support landed — enables North Mini Code 1.0 in llama.cpp (GGUF). Tensor mapping, sliding window, expert selection all wired.
- **b9637 (June 14)**: Dedicated Cohere2MoE parser (cleaner implementation).
- **b9631 (June 14)**: CLI fix — preserved tokens not being copied.
- **b9642 (June 15)**: CUDA GGML_OP_REPEAT restricted to F32/F16 (CUDA-only correctness fix, no AMD impact).
- ROCm 7.2 + Vulkan builds ship on every tag consistently.

## Decisions Made
- Kimi K2.7 Code: **Skip** — total param weight exceeds fleet RAM at any viable quantization.
- MiniMax M3: **Skip** — same reason, borderline fit with no margin.
- North Mini Code 1.0: **Evaluate** — GGUF now supported in llama.cpp; compact code model potentially fitting iGPU 4-8B tier. Blocked on confirming exact param count.

## Open Questions
- What is "Mythos 5"? Anthropic has not disclosed the model publicly.
- North Mini Code 1.0 exact param count and benchmark vs Granite-4.1-8B for iGPU slot?

## Tomorrow
- Optionally evaluate North Mini Code 1.0 GGUF for iGPU tier (vs current Granite-4.1-8B / Gemma-4-E4B).
