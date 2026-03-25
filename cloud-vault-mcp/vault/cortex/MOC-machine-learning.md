---
title: "MOC — Machine Learning"
date: 2026-03-04
tags: [moc, navigation, machine-learning]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 9
  synapse_out: 38
---

# Map of Content — Machine Learning

## Overview

Machine learning is the computational engine behind Cohezion's agent intelligence, semantic search, and knowledge graph embeddings. This map covers neural network architectures (especially transformers), training methodology, optimization techniques, and applied ML domains including NLP, computer vision, and anomaly detection. It connects foundational theory to the practical ML infrastructure that Cohezion agents use.

## Core Concepts

- [[machine-learning]] — Umbrella concept: supervised, unsupervised, and reinforcement learning paradigms
- [[neural-network-architecture]] — Design patterns for deep networks: layers, activations, skip connections
- [[transformer-architecture]] — The attention-based architecture behind modern LLMs and multimodal models
- [[self-attention-mechanism]] — Scaled dot-product attention: how transformers weight token relationships
- [[machine-learning-optimization]] — Gradient descent variants, learning rate schedules, regularization
- [[meta-learning]] — Learning to learn: few-shot adaptation and task-agnostic pretraining strategies
- [[natural-language-processing]] — Text understanding, generation, and information extraction via ML
- [[computer-vision]] — Image and video understanding using convolutional and vision transformer models
- [[anomaly-detection]] — Identifying outliers in data streams, applied to both astrophysics and agent observability
- [[reinforcement-learning]] — Policy optimization through environment interaction and reward signals
- [[bayesian-inference]] — Statistical framework for updating beliefs with evidence; underpins variational methods, VAEs, and probabilistic ML

## Supporting Concepts

- [[transfer-learning]] — Reusing pretrained model weights for downstream tasks with limited data
- [[federated-learning]] — Training models across distributed nodes without centralizing raw data
- [[semantic-search]] — Embedding-based retrieval that finds notes by meaning rather than keywords
- [[token-efficiency]] — Minimizing token cost while preserving model output quality
- [[token-efficiency-patterns]] — Concrete patterns for reducing token usage in agentic workflows
- [[cognitive-science]] — The Bayesian brain hypothesis and neural inspiration for ML architectures
- [[information-geometry]] — Fisher information metric on statistical manifolds; natural gradient descent
- [[data-analysis]] — Statistical and exploratory techniques applied before and during ML pipelines

## Key Decisions

- [[2026-02-13-experience-vae-training-pipeline-session-58]] — VAE training pipeline for encoding agent experience vectors
- [[2026-02-09-ai-model-strategy]] — Strategic model selection: when to use frontier vs. small/local models

## Patterns

- [[structured-experience-vector-layout]] — Fixed-dimension vector format for encoding agent state into ML models
- [[conservative-baseline-estimation]] — Establishing honest baselines before claiming ML improvement
- [[predictive-throttling-via-12d-trajectory-velocity]] — Using 12-dimensional trajectory velocity to predict and throttle agent behavior
- [[prompt-optimization-hypotheses]] — Pilot study of 98 agent sessions: 5 success hypotheses and 5 failure anti-patterns; context inheritance identified as the primary success factor

## Textbooks

- [[index|CS249R ML Systems Book]] — Harvard's comprehensive textbook: 21 chapters, 656 glossary terms covering full ML systems engineering spectrum

## Research Papers

- [[transformers-v5-huggingface-release]] — HuggingFace Transformers v5: 400+ architectures, 3M daily installs
- [[emu3-multimodal-next-token-prediction]] — Unified multimodal generation (text, image, video) via next-token prediction
- [[yann-lecun-agi-world-models]] — LeCun's argument for world models and causal reasoning as paths to AGI
- [[grok4-ai-benchmarks]] — Grok-4 benchmark results across reasoning and code generation tasks
- [[humanitys-last-exam-benchmark]] — A frontier benchmark designed to be unsolvable by current AI systems
- [[llm-training-methodology-changes]] — How LLM training has evolved: data curation, RLHF, synthetic data
- [[nvidia-nemotron-3-nano-nemo-gym]] — NVIDIA's small-model training framework for domain-specific fine-tuning
- [[alphafold-cryo-em-structure-prediction]] — AlphaFold combined with cryo-EM for protein structure prediction
- [[tonggeometry-ai-math]] — AI systems solving olympiad geometry via formal reasoning
- [[ai-anomaly-detection-hubble-archive]] — ML-based anomaly detection applied to Hubble Space Telescope data
- [[emoticons-llm-silent-failures]] — How emoji and emoticon tokens cause silent LLM failures

## GPU Kernel Optimization (AMD MI355X)

- [[2026-03-14-gemm-api-ceiling|GEMM MXFP4 API ceiling]] — Hit ~23µs floor; quantization bottleneck equals GEMM time
- [[2026-03-14-moe-optimization-state|MoE MXFP4 state]] — Rank 13/58 (~155µs) with adaptive KSPLIT routing
- [[2026-03-14-doweight-cktile-incompatibility|doweight_stage1 bug]] — Critical: broken on both CK and cktile paths
- [[2026-03-14-mla-three-regime|MLA decode three-regime]] — Rank 20/75 (~69.5µs) with metadata caching

## Experiments

- [[2026-02-13-first-real-data-vae-training-run]] — First VAE training run on real agent experience data (not synthetic)
- [[session-57-local-finetuning]] — Local fine-tuning experiment using Ollama models on vault data

## Competition & Optimization Campaigns

- [[luma-amd-speedrun-strategy|Luma AMD Speedrun Strategy]] — Competition tactics for MI355X GPU kernel optimization ($650K prize pool)
- [[amd-hip-kernel-development|AMD HIP Kernel Development]] — Custom HIP C++ kernels for AMD MI355X (gfx950): MFMA, LDS swizzle, ping-pong scheduling
- [[CENTRAL_COMMAND|Infinity Central Command]] — Multi-agent GPU optimization campaign coordination
- [[RESEARCH_REPORT|Infinity Research Report]] — Research findings across alpha/beta/gamma teams
- [[competition_log|Competition Log]] — Timeline of competitive kernel optimization attempts

## Start Here

- **New to this topic?** Start with [[machine-learning]] for the overview, then [[transformer-architecture]] for the architecture powering modern AI
- **Looking for patterns?** See [[structured-experience-vector-layout]] for how Cohezion encodes agent state into vectors
- **Recent work:** [[transformers-v5-huggingface-release]] covers the latest HuggingFace release with 400+ supported architectures

## Related Maps

- [[MOC-agentic-ai]] — Agents that consume ML models for reasoning, planning, and tool selection
- [[MOC-vault-architecture]] — The knowledge graph infrastructure that uses ML embeddings for semantic search
- [[MOC-quantum-physics]] — Emerging quantum-ML intersections in optimization and hybrid algorithms
