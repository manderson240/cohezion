---
name: nvidia-hardware-optimization-prime
description: "Expert in maximizing inference and training performance on NVIDIA GPU architectures (Hopper, Blackwell). Specializes in utilizing NVIDIA-specific toolkits like aitune, NIM, and ChatRTX patterns to achieve lowest-latency and highest-throughput reasoning."
---

# SKILL: NVIDIA_HARDWARE_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
Expert in maximizing inference and training performance on NVIDIA GPU architectures (Hopper, Blackwell). Specializes in utilizing NVIDIA-specific toolkits like `aitune`, `NIM`, and `ChatRTX` patterns to achieve lowest-latency and highest-throughput reasoning.

## KEY TEXTS & CONCEPTS
- **AITune (ai-dynamo)**: Automates backend selection (TensorRT, TorchInductor) and hyperparameter tuning for PyTorch models.
- **NVIDIA NIM (Inference Microservices)**: Standardized, containerized inference endpoints using TensorRT-LLM.
- **ChatRTX Patterns**: Local RAG optimizations and high-speed tensor offloading for consumer and enterprise GPUs.
- **CUDA Graphs**: Reducing CPU-launch overhead for repetitive inference tasks.

## INSTRUCTION
1. **Inference Acceleration (AITune)**:
   - Wrap models with `aitune.optimize(model)` to autonomously select the best backend.
   - Use `AITUNE_JIT=1` for zero-code-change JIT optimization in Kaggle environments.
2. **NIM Integration**:
   - For local/cloud targets, route requests to NIM-compatible OpenAI endpoints.
   - Prefer `gpu_nvidia` hardware target in `lemonade_config.yaml` for Nemotron and Qwen models.
3. **Blackwell/Hopper Handshake**:
   - Always verify `TRITON_PTXAS_PATH` matches the H100/Blackwell binary.
   - Enable `FP8` or `MXFP4` block-scaled quantization when hardware support is detected (via `kag_audit`).
4. **ChatRTX RAG**:
   - Implement localized vector stores (FAISS/Milvus) with TensorRT-LLM optimized embeddings for high-speed retrieval.

## VERSION
v1.0

## SEE ALSO
- KAGGLE_BLACKWELL_RUNNER_PRIME.md
- LEMONADE_EMBEDDABLE_INTEGRATION_PRIME.md
