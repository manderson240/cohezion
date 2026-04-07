# Gemma 4 Model Card & Integration Guide

![Gemma 4 Banner](https://ai.google.dev/static/gemma/images/gemma4_banner.png)

[Hugging Face](https://huggingface.co/collections/google/gemma-4) | [GitHub](https://github.com/google-gemma) | [Launch Blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/) | [Documentation](https://ai.google.dev/gemma/docs/core)

**License**: [Apache 2.0](https://ai.google.dev/gemma/docs/gemma_4_license) | **Authors**: [Google DeepMind](https://deepmind.google/models/gemma/)

## 🧬 Model Overview
Gemma 4 is a family of multimodal open-weights models supporting text, image, and (for smaller variants) audio inputs.

### Architecture Matrix
- **E2B / E4B**: Optimized for on-device (Pixel/Edge), support Audio + Vision. Linear-time efficiency via Per-Layer Embeddings (PLE).
- **26B A4B (MoE)**: Mixture-of-Experts. High reasoning capability with low active parameter count (3.8B active), ideal for local GPU (Strix Halo).
- **31B Dense**: Frontier-level reasoning, 256K context window, optimized for cloud/server deployment.

## 🛠️ Cohezion Integration Map

### 1. Hardware Mapping
- **Sensing (Edge)** $\rightarrow$ Pixel 10 Pro Fold / Pixel 6 $\rightarrow$ **Gemma 4 E2B/E4B** (Audio/Vision processing).
- **Symphony (Host)** $\rightarrow$ AMD Ryzen AI MAX+ 395 (Strix Halo) $\rightarrow$ **Gemma 4 26B A4B** (Reasoning/Synthesis).
- **Calculus (Cloud)** $\rightarrow$ Ollama Cloud $\rightarrow$ **Gemma 4 31B** (Deep Manifold Analysis).

### 2. Software Logic Bridges
- **Regime Routing**: Implemented in `src/cohezion/swarm/providers/gemma4_provider.py`.
- **Latent Projection**: FLUME (256D) $\rightarrow$ Manifold (12D) via `src/cohezion/flume/manifolds/translator.py`.
- **Compound Loop**: Reflexive refinement using `src/cohezion/compound/eco_symphony.py`.
- **Adversarial review**: Triune review logic in `src/cohezion/compound/triune_reviewer.py`.

### 3. Critical Parameters
- **Thinking Mode**: Enabled via `enable_thinking=True` for complex reasoning.
- **Context Window**: 128K (E2B/E4B) $\rightarrow$ 256K (26B/31B).
- **Sampling**: $\text{temp}=1.0, \text{top\_p}=0.95, \text{top\_k}=64$.

## 📈 Benchmarks (EcoResilience Baseline)
- **Total Pipeline Latency**: 1950.00 ms
- **Symphony Efficiency**: 0.513 Hz
- **Cores**: Zen 5 (Sensing $\rightarrow$ Steering)

## 🔗 Related Skills
- [[amd-moe-mxfp4-optimization]] - Optimization for the 26B MoE variant.
- [[compound-engineering]] - The reflexive symphony architecture.
- [[flume-vae-encoder]] - The latent foundation for the manifold.
