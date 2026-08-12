# Bleeding-Edge Local Inference Frontier Report (128GB Unified Memory Hardware)

> **Hardware Context**: AMD Framework Desktop 16 / AMD Strix Halo (128GB DDR5-5600 UMA, Radeon 8060S UMA iGPU `gfx1151`, NPU).  
> **Date**: August 2026

---

## Executive Summary

On a **128GB Unified Memory Architecture (UMA)** system, local inference is no longer restricted to 7B or 14B models. With **ROCmFP4 / GGUF quantization** and **Hybrid Mamba2 + Attention + MoE active sparsity**, you can achieve **86.0 tok/s decode speed** and **1,300 tok/s prompt processing speed** locally on Strix Halo hardware!

---

## 1. Breakthrough Spotlight: Nemotron 3.5 Lightning 30B-A3B (ROCmFP4 GGUF)

> **Repository**: [`julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF`](https://huggingface.co/julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF)  
> **GitHub**: [`julianmb/nemotron-3.5-30b-a3b-rocmfp4`](https://github.com/julianmb/nemotron-3.5-30b-a3b-rocmfp4)

### Benchmarks on Strix Halo (AMD Ryzen AI MAX+ 395 / `gfx1151` / 128GB UMA):

| Quantization Variant | Footprint (Disk) | Prompt Processing (pp512) | Decode Speed (tg128) | Perplexity (Wikitext-2) | Hardware Backend |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`STRIX_LEAN` (~4.38 bpw)** | **15.73 GiB** | **1,299.7 tok/s** | **85.6 tok/s** | **5.9936 ± 0.0358** | `-dev Vulkan0` (Vulkan beat ROCm by 21%) |
| **`FAST` (~4.25 bpw)** | **15.66 GiB** | **1,310.5 tok/s** | **86.0 tok/s** | Nominal | `-dev Vulkan0` |
| **`COHERENT` (~4.70 bpw)** | **16.74 GiB** | **1,290.4 tok/s** | **81.6 tok/s** | Nominal | `-dev Vulkan0` (Agentic / Coding) |

---

## 2. Explicit KV-Cache Memory Accounting Formula

KV-Cache consumption scales linearly with context length ($L_{\text{ctx}}$), transformer layers ($n_{\text{layers}}$), Grouped Query Attention key-value heads ($n_{\text{kv\_heads}}$), and element precision:

$$\text{Memory}_{\text{KVCache}} = 2 \times n_{\text{layers}} \times n_{\text{kv\_heads}} \times d_{\text{head}} \times L_{\text{ctx}} \times B \times \left(\frac{\text{bits}}{8}\right)$$

### KV-Cache Footprint Benchmark Table (for $n_{\text{layers}}=80, n_{\text{kv\_heads}}=8, d_{\text{head}}=128$):

| Context Window ($L_{\text{ctx}}$) | FP16 KV-Cache (16-bit) | Q8_0 KV-Cache (8-bit) | Q4_0 KV-Cache (4-bit) |
| :--- | :--- | :--- | :--- |
| **8,192 tokens** | 2.50 GB | 1.25 GB | 0.63 GB |
| **32,768 tokens** | 10.00 GB | 5.00 GB | 2.50 GB |
| **131,072 tokens (128k)** | 40.00 GB | 20.00 GB | 10.00 GB |
| **262,144 tokens (262k)** | 80.00 GB | 40.00 GB | 20.00 GB |

> **Key Rule**: For context windows $>32\text{k}$ tokens, enable **Q8_0 or Q4_0 KV-cache quantization** (`--ctk q4_0 --ctv q4_0` in `llama.cpp` / Lemonade) to reduce KV-cache footprint by up to $4.0\times$!

---

## 3. Top Frontier Local Models for 128GB Hardware

| Rank | Model Name | Architecture | Disk Size | FP16 KV-Cache (32k) | Total Inflated Footprint (1.7x) | Primary Capability & When to Run |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | **`Nemotron 3.5 Lightning`** | Hybrid Mamba2 + MoE (3.5B active) | **15.73 GB** (ROCmFP4) | 10.0 GB (Q8_0: 5.0GB) | **26.74 GB** | **Ultra-Fast Agentic & Coding**: **86.0 tok/s decode**, 1,300 tok/s prompt processing on `-dev Vulkan0`. |
| **#2** | **`Qwen3-Coder-Next`** | 80B MoE (12B active) | ~46.5 GB | 10.0 GB (Q4_0: 2.5GB) | **79.05 GB** | **SOTA Agentic Coding**: Multi-file refactoring, 262K native context repo ingestion. |
| **#3** | **`gpt-oss-120b`** | 120B Dense/MoE | ~65.0 GB (IQ4_XS) | 10.0 GB (Q4_0: 2.5GB) | **110.50 GB** | **Frontier Reasoning & Tool-Calling**: Complex multi-step reasoning, logic checks. |
| **#4** | **`DeepSeek-R1-70B`** | 70B Dense Distill | ~48.0 GB (Q5_K_M) | 10.0 GB (Q4_0: 2.5GB) | **81.60 GB** | **Unthrottled CoT Math & Logic**: Formal proof verification, complex debugging. |
| **#5** | **`Qwen3.6-35B-A3B`** | 35B MoE (3B active) | ~12.0 GB | 10.0 GB (Q4_0: 2.5GB) | **20.40 GB** | **High-Throughput Swarm Specialist**: Research synthesis, fast swarms (~100+ tok/s). |

---

## 4. Weight-Fit & Load Safety Policy (`check_load_safe`)

To guarantee zero kernel freezes and 100% uptime:
1. **Safety Floor**: Never allocate the last **16.0 GB** of RAM (`RAM_FLOOR_GB = 16.0`).
2. **Inflated Footprint Factor**: Catalog size is multiplied by **1.7x** (`SIZE_SAFETY_FACTOR = 1.7`) specifically to absorb KV-cache, mmap overhead, GTT, and mmproj.
3. **Max Model Footprint on 128GB RAM**:
   $$\text{Max Footprint} = 128.0\text{ GB} - 16.0\text{ GB} = 112.0\text{ GB}$$
   $$\text{Max Catalog Size} = \frac{112.0}{1.7} \approx 65.8\text{ GB}$$
