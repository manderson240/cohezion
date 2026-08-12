# Bleeding-Edge Local Inference Frontier Report (128GB Unified Memory Hardware)

> **Hardware Context**: AMD Framework Desktop 16 / AMD Strix Halo (128GB DDR5-5600 UMA, Radeon 8060S UMA iGPU, NPU).  
> **Date**: August 2026

---

## Executive Summary

On a **128GB Unified Memory Architecture (UMA)** system, local inference is no longer restricted to 7B or 14B models. With **GGUF 4-bit/5-bit quantization (Q4_K_M, IQ4_XS, Q5_K_M)** and **Mixture-of-Experts (MoE) active sparsity**, you can run **70B to 120B parameter frontier models** entirely locked in RAM without disk swap or CPU offload.

---

## 1. Top Frontier Local Models for 128GB Hardware

| Rank | Model Name | Architecture | Disk Size | Footprint (1.7x) | Primary Capability & When to Run | Why Run Locally |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | **`Qwen3-Coder-Next`** | 80B MoE (12B active) | ~46.5 GB | 79.05 GB | **SOTA Agentic Coding**: Multi-file refactoring, 262K native context repository ingestion, AST verifiers. | Top open coding model; 262K context fits completely in 128GB RAM. |
| **#2** | **`gpt-oss-120b`** | 120B Dense/MoE | ~65.0 GB (IQ4_XS) | 110.50 GB | **Frontier Reasoning & Tool-Calling**: Complex multi-step reasoning, tool orchestration, logic checks. | Matches cloud GPT-4.5/Gemini 2.5 Pro performance locally. |
| **#3** | **`DeepSeek-R1-70B`** | 70B Dense Distill | ~48.0 GB (Q5_K_M) | 81.60 GB | **Unthrottled CoT Math & Logic**: Formal proof verification, complex debugging, deep planning. | Unrivaled reasoning per parameter; unthrottled `<think>` trace. |
| **#4** | **`Nemotron-3-Super-120B`**| 120B MoE (12B active)| ~64.0 GB | 108.80 GB | **1-Million Token Long-Context**: Entire codebase / vault ingestion, legal/academic deep retrieval. | 1M token context window runs without OOM on 128GB RAM. |
| **#5** | **`Qwen3.6-35B-A3B`** | 35B MoE (3B active) | ~12.0 GB | 20.40 GB | **High-Throughput Swarm Specialist**: Research synthesis, fast agentic swarms (~100+ tok/s). | Ultra-fast token generation speed on NPU/iGPU lanes. |

---

## 2. Weight-Fit & Load Safety Policy (`check_load_safe`)

To guarantee zero kernel freezes and 100% uptime:
1. **Safety Floor**: Never allocate the last **16.0 GB** of RAM (`RAM_FLOOR_GB = 16.0`).
2. **Inflated Footprint**: Catalog size is multiplied by **1.7x** (`SIZE_SAFETY_FACTOR = 1.7`) to account for KV-cache, mmap overhead, GTT, and mmproj.
3. **Max Model Footprint on 128GB RAM**:
   $$\text{Max Footprint} = 128.0\text{ GB} - 16.0\text{ GB} = 112.0\text{ GB}$$
   $$\text{Max Catalog Size} = \frac{112.0}{1.7} \approx 65.8\text{ GB}$$

---

## 3. Hardware Lane Allocation Protocol

```
                                  128GB UMA SILICON DISPATCH
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ NPU LANE (port 13305)                                                                       │
│ • `deepseek-r1-0528-8b-FLM`   (Fast CoT Reasoning)                                          │
│ • `qwen3.6-moe-35b-a3b-FLM`  (MoE Research Synthesis)                                       │
│ • `llama3.2-1b-FLM`          (Fast Intent QA <20ms)                                         │
│ • `embed-gemma-300m-FLM`      (768D Poincaré Vector Embeddings)                              │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ iGPU VULKAN / ROCm LANE (port 13305)                                                        │
│ • `Qwen3-Coder-Next-80B`     (Repository-Scale Coding & AST Verifiers)                    │
│ • `gpt-oss-120b`             (Frontier Multi-Step Reasoning & Tool Use)                     │
│ • `DeepSeek-R1-70B`          (Unthrottled Proof Verification)                              │
│ • `Muse-Glimmer-30B-GGUF`    (Ultra-Detailed Creative Reasoning)                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```
