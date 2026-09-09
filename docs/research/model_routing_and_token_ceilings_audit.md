# 🧠 Model-to-Task Routing & Token Ceiling Audit

**Date**: 2026-08-24  

| Task Class | Model | Hardware Context | Enforced Max Tokens | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| 1. Deep Mathematical Reasoning & Sheaf Theory | **DeepSeek-R1-8B (NPU) / DeepSeek-V4 Pro (Cloud)** | `40,960 tokens` | **8192** | Thinking models output 3,000 - 6,000 tokens of internal reasoning before emitting final formulas. Constraining to 150-512 truncates the thinking block. |
| 2. Python Code Generation & ARC Invariant Synthesis | **Qwen3-Coder-30B (iGPU / Vulkan)** | `32,768 tokens` | **4096** | Full Python functions with edge-case handling require 1,024 - 2,048 tokens. |
| 3. Tokenized Macro DSL Planning | **qwen3.6-moe-35b-a3b-FLM (NPU) / gpt-oss-20b (iGPU)** | `16,384 tokens` | **2048** | Allows structured chain-of-thought analysis of grid symmetries before emitting the 3-5 macro action tokens. |
| 4. Multi-Perspective Adversarial Review | **GLM-5.2 (Cloud) / Qwen3-Coder-30B (iGPU)** | `32,768 tokens` | **4096** | Red-team critiques need room to outline multi-step attack vectors and test cases. |
