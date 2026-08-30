# 🍋 Master Finely-Crafted Lemonade Server Recipes

**Hardware Platform**: AMD Strix Halo (128GB LPDDR5X-8000, 210 GB/s bandwidth)  
**Port**: `13305` (Lemonade OmniRouter)  
**Date**: 2026-08-24  

## Recipe 1: The Sovereign Code Synthesizer
- **Model**: `Qwen3-Coder-30B`
- **Silicon Target**: AMD Radeon 8060S iGPU (Vulkan backend)
- **Quantization**: Q4_K_M GGUF (18.5 GiB)
- **KV-Cache Recipe**: FP8 Quantized KV-Cache (3.0 GiB for 32k context)
- **Sampling Recipe**: `{'temperature': 0.1, 'top_p': 0.9, 'min_p': 0.05, 'max_tokens': 4096}`
- **Purpose**: Deterministic Python AST synthesis, 0ms AutoHarness verification, multi-file refactors.

---

## Recipe 2: The Deep Mathematical Reasoner
- **Model**: `deepseek-r1-0528-8b-FLM`
- **Silicon Target**: AMD XDNA2 NPU (Direct NPU Engine)
- **Quantization**: Q4_K_M with MLA Latent Compression (5.2 GiB)
- **KV-Cache Recipe**: FP16 Uncompressed Native (2.5 GiB for 40k context)
- **Sampling Recipe**: `{'temperature': 0.6, 'top_p': 0.95, 'repetition_penalty': 1.05, 'max_tokens': 8192}`
- **Purpose**: Sheaf Cohomology restriction maps, Poincaré geodesic derivations, topological invariants.

---

## Recipe 3: The Fast Macro Action Planner
- **Model**: `qwen3.6-moe-35b-a3b-FLM`
- **Silicon Target**: AMD XDNA2 NPU (35B Total / 3B Active)
- **Quantization**: MoE Sparse GGUF (9.8 GiB)
- **KV-Cache Recipe**: FP8 Bounded KV-Cache (0.44 GiB for 16k context)
- **Sampling Recipe**: `{'temperature': 0.2, 'top_p': 0.9, 'max_tokens': 2048}`
- **Purpose**: Microsecond 3-token DSL planning (PAIR_CONNECT -> ROOM_FILL) without syntax errors.

---

## Recipe 4: The Adversarial Red-Team Auditor
- **Model**: `gpt-oss-20b`
- **Silicon Target**: AMD Radeon 8060S iGPU (Vulkan / MXFP4)
- **Quantization**: MXFP4 Sub-4-Bit Quantization (11.2 GiB)
- **KV-Cache Recipe**: MXFP4 KV-Cache (1.25 GiB for 32k context)
- **Sampling Recipe**: `{'temperature': 0.2, 'top_p': 0.9, 'max_tokens': 4096}`
- **Purpose**: Multi-perspective adversarial review, sandbox security analysis, edge-case hunting.

---

## Recipe 5: The Voice & Multimodal Edge Suite
- **Model**: `Whisper-Large-v3-Turbo + Kokoro-v1`
- **Silicon Target**: AMD Ryzen 9 CPU + iGPU Audio Lane
- **Quantization**: FP16 PyTorch / ONNX Runtime (<1.5 GiB)
- **KV-Cache Recipe**: Zero KV Overhead (Streaming Audio Buffer)
- **Sampling Recipe**: `{'temperature': 0.0, 'max_tokens': 512}`
- **Purpose**: Offline Local STT / TTS (Official AMD skills catalog aligned).

---

