---
title: GFX1151 Hybrid Strategy - Research Compilation
created: 2026-04-10
tags:
  - hardware
  - rocm
  - gfx1151
  - hybrid
  - npu
  - gpu
  - strix-halo
  - lemonade-sdk
  - llama-cpp
  - rocwmma
aliases:
  - Hybrid NPU GPU Execution
  - GFX1151 optimizations
category: hardware_acceleration
status: research-complete
---

# GFX1151 Hybrid Strategy - Research Compilation

## Research Summary

Compiled comprehensive research on achieving full hybrid NPU+GPU execution on AMD Ryzen AI MAX+ 395 (Strix Halo / gfx1151). Key discovery: **Lemonade Server 10.2.0 bundles outdated llama.cpp**; solution requires Lemonade SDK nightly or custom build.

## Critical Findings

### 1. DKMS Fix Was Step 1, Not Complete Solution

The `./fix_rocm_gfx1151.sh` script successfully:
- ✅ Removed incompatible `amdgpu-dkms`
- ✅ Enabled ROCm detection of gfx1151
- ✅ Preserved NPU functionality

However, **Lemonade 10.2.0's bundled llama-server still hangs** at `common_init_result: fitting params`.

### 2. Performance Optimizations Discovered

#### ROCWMMA Flash Attention (September 2025)
- Build flag: `-DGGML_HIP_ROCWMMA_FATTN=ON`
- **2x performance boost**: 592 t/s → 1006 t/s
- Merged into llama.cpp mainline

#### gfx1151 VGPR Optimization (April 2026)
- PR #21344: Tuned `mmq_x=48, mmq_y=64, nwarps=4`
- **20-73% prefill improvement** for Qwen models
- Specifically targets RDNA3.5 wave occupancy

### 3. Hybrid Execution Architecture

| Component | Device | Role | Speed |
|-----------|--------|------|-------|
| Prefill | NPU (XDNA2) | Prompt processing | 60-80 TPS |
| Generation | GPU (RDNA3.5) | Token generation | 25-50 TPS |

**Platform Support**:
- Windows: ✅ Full hybrid via `ryzenai-llm`
- Linux: ⚠️ Partial (NPU via FLM, GPU via ROCm)

## Recommended Solutions

### Option 1: Lemonade SDK Nightly (Easiest)
AMD officially recommends for Strix Halo:
> "For the easiest setup experience, we recommend using the Lemonade SDK pre-built binaries."

Download from: https://github.com/lemonade-sdk/llamacpp-rocm/releases

### Option 2: Build from Source (Maximum Performance)
```bash
cmake -B build -DGGML_HIP=ON \
  -DAMDGPU_TARGETS="gfx1151" \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DCMAKE_BUILD_TYPE=Release
```

### Option 3: Wait for Lemonade Update
- Monitor for Lemonade Server >10.2.0
- Should include gfx1151-optimized llama.cpp

## Current Working Solutions

| Use Case | Solution | Status |
|----------|----------|--------|
| Small models (4B) | FLM NPU | ✅ Working |
| Large models (26B+) | ROCm GPU (custom build) | ✅ Requires SDK/custom |
| Very large (31B+) | Ollama Cloud | ✅ Fallback |
| True hybrid | Unavailable on Linux | ❌ Windows only |

## References

- [[GFX1151_ROCM_RESEARCH_SUMMARY]]: Original DKMS fix documentation
- [[rocm-gfx1151-verification-2026-04-10]]: Pre-flight verification
- [[rocm-gfx1151-post-reboot-results.md]]: Post-execution results
- [[GFX1151_HYBRID_STRATEGY_RESEARCH]]: This research document

### External Links
- [Lemonade SDK Nightly Builds](https://github.com/lemonade-sdk/llamacpp-rocm/releases)
- [AMD Trillion Parameter Guide](https://www.amd.com/de/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html)
- [llama.cpp gfx1151 PR #21344](https://github.com/ggml-org/llama.cpp/pull/21344)
- [ROCm TheRock](https://github.com/ROCm/TheRock)

## SurrealDB References

- `research:gfx1151_hybrid_2026_04_10`: Research record
- `execution:rocm_fix_2026_04_10`: Execution details
- `verification:rocm_gfx1151_preflight_2026_04_10`: Verification status

---

*Research Date*: 2026-04-10  
*Compiled By*: Cohezion Agent  
*Status*: ✅ Complete - Actionable Solutions Identified
