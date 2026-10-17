---
name: strix-fleet-guard
description: Hardware safety and unified memory governance on AMD Strix Halo (128GB LPDDR5X UMA / AMD Ryzen AI MAX+ 395). Enforces fleet-lock discipline to prevent iGPU/NPU aperture races, monitors VRAM/SRAM allocation, and routes tasks across NPU FastFlowLM, Vulkan iGPU, and Zen 5 CPU lanes.
---

# Strix Halo Fleet & Hardware Guard

## Hardware Specifications
- **SoC**: AMD Ryzen AI MAX+ 395 (16 Zen 5 cores, 32 threads, XDNA 2 NPU)
- **iGPU**: AMD Radeon 8060S (40 CUs, RDNA 3.5, gfx1151)
- **Unified Memory (UMA)**: 128 GB LPDDR5X (~120 GB addressable GTT aperture)
- **Local Ports**:
  - `13305`: Cohezion Admission Proxy / Lemonade (Exclusive Single-Port Gateway: NPU FastFlowLM + lightweight CPU)
  - `11434`: Ollama Cloud Gateway (Large models, coding, deep reasoning)
- **Verified NPU FastFlowLM Models (SRAM <2W, 0 UMA RAM)**:
  - `deepseek-r1-0528-8b-FLM`: Grandmaster reasoning and step-function mathematical induction.
  - `qwen3.5-4b-FLM`: Rapid token parsing, structured JSON generation, and AST code verification.
  - `embed-gemma-300m-FLM`: Zero-footprint semantic embedding extraction.

---

## Fleet Lock Discipline ("Quarter on a String")

### 1. Preflight Check
Before launching any local inference swarm or heavy training script, run:
```bash
bash scripts/preflight_fleet.sh
```
* Exit 0: Safe to proceed.
* Exit non-zero: Hardware aperture pressure detected; do not start.

### 2. Fleet Lock Acquisition & Demand-Driven Hotswapping
To prevent kernel faults caused by concurrent model loading races:
- Never call `lemonade load` or pull large models concurrently.
- All model loads must acquire `fleet_lock:modelload`.
- Use demand-driven hotswapping with zero host UMA aperture footprint:
```python
from cohezion.inference.hotswap import demand_swap, ensure_resident

# Ensure deep reasoning model is resident on NPU SRAM
await ensure_resident("deepseek-r1-0528-8b-FLM")
```
Or via CLI:
```bash
python3 scripts/npu_hotswap.py swap deepseek-r1-0528-8b-FLM
python3 scripts/npu_hotswap.py active
```

### 3. Lane Allocation Matrix
| Task Class | Backend | Device | Memory Footprint |
|---|---|---|---|
| Invariant Verification | Zen 5 CPU (Rayon / AST) | CPU | 0 MB GPU VRAM, <4 GB RAM |
| Deep Reasoning & Invariant Proofs | FastFlowLM (`deepseek-r1-0528-8b-FLM`) | NPU SRAM | <2W power, 0 UMA RAM |
| Rapid Code & AST Drafts | FastFlowLM (`qwen3.5-4b-FLM`) | NPU SRAM | <2W power, 0 UMA RAM |
| Zero-Footprint Embeddings | FastFlowLM (`embed-gemma-300m-FLM`) | NPU SRAM | <2W power, 0 UMA RAM |
| Multi-file Code Refactor | `glm-5.3:cloud` / `kimi-k2.7-code:cloud` / Claude Code | Tier 2 Cloud | 0 MB host memory |
| Heavy Search & Math (ARC DSL) | Rust PyO3 SIMD / Highs MILP | CPU | Multi-threaded, 15M ops/sec |
| 3D Deep Learning & Model Training | Kaggle Cloud L4 / 2xT4 GPUs | Cloud | 0 MB host memory |

