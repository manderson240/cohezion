---
title: "AMD XDNA 2 NPU Acceleration & FastFlowLM Optimization"
category: hardware
updated: 2026-10-15
coherence: 0.50
---

# AMD XDNA 2 NPU Acceleration & FastFlowLM Optimization

## Core Architecture
- **Hardware**: AMD Ryzen AI MAX+ 395 XDNA 2 NPU (50+ NPU TOPS, 8 compute columns).
- **Runtime**: ROCm FastFlowLM (`flm` v1.0.8) running on dedicated NPU SRAM (`/dev/accel/accel0`).
- **Power & Footprint**: <2W active power, **0 MB UMA aperture consumption**, 0% CPU/iGPU contention.
- **Microservices**:
  - Supervised FLM server: Port 8005 (`qwen3.5:4b` with `--socket 32 --q-len 32 --cors 1`).
  - A2A NPU microservice: Port 8008 (`a2a_npu_microservice.py`).
  - Lemonade OmniRouter: Port 13305.

## 170x Latency Optimization
- Transitioned from ad-hoc process invocations to persistent UNIX socket and streaming API daemon architecture.
- Turn latency reduced from ~1800s cold-start subprocess runs to **9.7s–24.5s** sustained execution.
- Enables continuous autonomous reflection, goal steering, and Kaggle ascension trajectories (over 850 epochs executed in `stateless_npu_ascension_worker.py`).

## Safe Silicon Rules
- All high-frequency reasoning, AST reflection, and prompt-as-action verification runs on NPU SRAM or Zen 5 CPU.
- Never allocate Vulkan/ROCm GGUF models on the 120GB UMA host aperture without prior GTT and PSI checks (`OOMGuard`).
- Heavy reasoning and large-scale model requirements route to Tier 2 Ollama Cloud or headless Claude.

## Related Artifacts & Code
- Server: `scripts/npu/supervised_flm_server.py`, `scripts/npu/a2a_npu_microservice.py`
- Worker: `scripts/kaggle/stateless_npu_ascension_worker.py`
- PRIME Skill: `src/cohezion/skills/FASTFLOWLM_PRIME.md`
- Documentation: `docs/hardware/AMD_ROCM_FASTFLOWLM_XDNA2_NPU.md`
- Learning: L430, L526, L537 in `KEY_LEARNINGS.md`
