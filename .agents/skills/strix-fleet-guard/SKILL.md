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
  - `13305`: Lemonade OmniRouter (NPU FastFlowLM + iGPU Vulkan)
  - `11434`: Ollama Server (Cloud and large models)

---

## Fleet Lock Discipline ("Quarter on a String")

### 1. Preflight Check
Before launching any local inference swarm or heavy training script, run:
```bash
bash scripts/preflight_fleet.sh
```
* Exit 0: Safe to proceed.
* Exit non-zero: Hardware aperture pressure detected; do not start.

### 2. Fleet Lock Acquisition
To prevent kernel faults caused by concurrent model loading races:
- Never call `lemonade load` or pull large models concurrently.
- All model loads must acquire `fleet_lock:modelload`:
```python
from cohezion.researcher.daily_researcher import FleetLock

with FleetLock("modelload", timeout=60.0):
    # Safe model load operation
    ...
```

### 3. Lane Allocation Matrix
| Task Class | Backend | Device | Memory Footprint |
|---|---|---|---|
| Invariant Verification | Zen 5 CPU (Rayon) | CPU | 0 MB GPU VRAM, <4 GB RAM |
| Planning & Reasoning | FastFlowLM (`qwen3.5-4b-FLM`) | NPU | <2W power, 0 UMA RAM (SRAM) |
| Multi-file Code Refactor | `Qwen3-Coder-30B` | iGPU (Vulkan) | ~18 GB VRAM |
| Heavy Search (ARC DSL) | Rust PyO3 SIMD | CPU | Multi-threaded, 15M ops/sec |
| 3D Deep Learning | Kaggle Cloud L4 GPUs | Cloud | 0 MB host memory |
