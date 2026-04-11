---
title: Lemonade SDK Integration - Implementation Path
created: 2026-04-10
tags:
  - implementation
  - lemonade-sdk
  - gfx1151
  - rocm
  - integration
  - strix-halo
aliases:
  - SDK Library Replacement
category: hardware_acceleration
status: ready-for-implementation
---

# Lemonade SDK Integration - Implementation Path

## Summary

Downloaded and analyzed **Lemonade SDK b1236** for gfx1151. The package contains optimized ROCm libraries but requires integration into Lemonade Server.

## SDK Package Contents

**Downloaded**: `llama-b1236-ubuntu-rocm-gfx1151-x64.zip` (extracted to `/tmp/lemonade-sdk-gfx1151/`)

**Key Libraries**:
- `libggml-hip.so` - Optimized HIP backend for gfx1151
- `libllama.so` - Core library with gfx1151 VGPR optimizations
- `librocroller.so` - AMD ROCm roller (kernel generation)
- `librocblas.so` - AMD BLAS library

**Note**: This is a **library package**, not standalone binaries. Requires integration.

## Three Implementation Options

### Option 1: Replace Lemonade Server Libraries ⭐ RECOMMENDED
Replace bundled libraries with SDK versions. See `LEMONADE_SDK_INTEGRATION_GUIDE.md` for detailed steps.

### Option 2: Build llama.cpp from Source
Build with gfx1151-specific flags:
```bash
cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS="gfx1151" \
  -DGGML_HIP_ROCWMMA_FATTN=ON -DCMAKE_BUILD_TYPE=Release
```

### Option 3: Use Standalone llama.cpp
Bypass Lemonade Server entirely; run llama.cpp server directly.

## Expected Performance

| Metric | Before (Lemonade 10.2.0) | After (SDK/Optimized) | Improvement |
|--------|-------------------------|----------------------|-------------|
| Model loading | Hangs at `common_init_result` | ✅ Works | **Fixed** |
| TPS (Qwen3.5 35B) | N/A | 25-35 TPS | **Working** |
| TPS with ROCWMMA | N/A | 50+ TPS | **2x boost** |
| Long context | N/A | Up to 120B models | **Enabled** |

## References

- [[LEMONADE_SDK_INTEGRATION_GUIDE]]: Detailed implementation steps
- [[GFX1151_HYBRID_STRATEGY_RESEARCH]]: Research compilation
- [[GFX1151_ROCM_RESEARCH_SUMMARY]]: Original DKMS fix
- [[rocm-gfx1151-verification-2026-04-10]]: Pre-flight verification
- [[rocm-gfx1151-post-reboot-results.md]]: Post-execution results

## External Resources

- [Lemonade SDK Releases](https://github.com/lemonade-sdk/llamacpp-rocm/releases)
- [AMD Trillion Parameter Guide](https://www.amd.com/de/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html)
- [llama.cpp PR #21344](https://github.com/ggml-org/llama.cpp/pull/21344)

---

*SDK Downloaded*: 2026-04-10  
*Location*: `/tmp/lemonade-sdk-gfx1151/`  
*Status*: ⏳ Ready for implementation
