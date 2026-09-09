# Hermes Desktop ↔ Lemonade Custom Router Benchmark Report

**Hardware**: AMD Framework Desktop 16 (AMD Ryzen AI MAX+ 395, 128GB Unified RAM, Radeon 8060S iGPU)
**Endpoint**: `http://localhost:13305/api/v1`
**Router Policy**: `user.cohezion-hermes-router`

| Workload / Tier | Matched Route | Dispatched Model | Total Time | TTFT (ms) | Prefill (t/s) | Decode (t/s) | Quality |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Fast Q&A / Trivial Ack**<br>*Tier 1 (NPU Fast Chat)* | `hermes-fast-chat` | `waslmedia-qwen3-4b-Q4_K_M` | **0.82s** | 13.9ms | 71.8 | **75.9** | **100%** |
| **Algorithmic Code Generation**<br>*Tier 1 (iGPU Coding/Tools)* | `hermes-coding-skills` | `Qwen3-Coder-30B-A3B-Instruct-GGUF` | **2.30s** | 14.7ms | 68.0 | **88.1** | **100%** |
| **Diagnostic Causal Reasoning**<br>*Tier 1 (NPU/iGPU Reasoning)* | `hermes-deep-reasoning` | `deepseek-r1-0528:8b` | **24.49s** | 0.0ms | 0.0 | **7.1** | **100%** |
| **Structured Tool Calling**<br>*Tier 1 (Agentic Tool Dispatch)* | `hermes-agent-tools` | `Qwen3-Coder-30B-A3B-Instruct-GGUF` | **0.30s** | 14.6ms | 68.5 | **83.0** | **100%** |
