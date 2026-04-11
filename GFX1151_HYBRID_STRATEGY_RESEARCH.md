# GFX1151 Hybrid NPU+GPU Strategy - Research Findings

**Date**: 2026-04-10  
**Status**: Critical findings - path to full hybrid functionality identified

---

## Executive Summary

The **DKMS fix was only step 1**. The real issue is that **Lemonade 10.2.0 bundles an outdated llama.cpp** without proper gfx1151 optimizations. This research reveals:

1. ✅ **ROCm detection works** after DKMS removal
2. ❌ **Lemonade's bundled llama-server hangs** at `common_init_result` due to outdated build
3. 🎯 **Solution**: Use Lemonade SDK nightly builds OR build llama.cpp from source with gfx1151 patches
4. 💎 **Hybrid execution**: NPU prefill + GPU generation is supported via `ryzenai-llm` backend on Windows (Linux pending)

---

## Key Research Findings

### 1. ROCM Performance Breakthrough (April 2026)

Recent PR [#21344](https://github.com/ggml-org/llama.cpp/pull/21344) optimizes gfx1151 specifically:

| Model | Test | Before | After PR | Improvement |
|-------|------|--------|----------|-------------|
| Qwen3.5 35B | pp128 | 181 t/s | 314 t/s | **+73%** |
| Qwen3.5 35B | pp512 | 370 t/s | 492 t/s | **+33%** |
| Qwen3.5 122B | pp128 | 181 t/s | 315 t/s | **+74%** |
| Qwen3.5 122B | pp512 | 362 t/s | 497 t/s | **+37%** |

**Key optimization**: `mmq_x=48, mmq_y=64, nwarps=4` for RDNA3.5 to reduce VGPR pressure.

### 2. ROCWMMA Flash Attention (2x Performance Boost)

Building with `-DGGML_HIP_ROCWMMA_FATTN=ON` provides massive gains:

| Config | pp512 Throughput |
|--------|------------------|
| Standard ROCm | 592 t/s |
| With ROCWMMA | **1006 t/s** |

**Status**: Merged into llama.cpp September 2025, but requires explicit build flag.

### 3. Lemonade SDK vs Lemonade Server

**Critical distinction**:
- **Lemonade Server 10.2.0**: Stable release with outdated llama.cpp
- **Lemonade SDK**: Nightly builds with latest gfx1151 support

AMD officially recommends Lemonade SDK for Strix Halo:
> "For the easiest setup experience, we recommend using the Lemonade SDK pre-built binaries."

### 4. Hybrid Execution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hybrid NPU+GPU Execution                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐         ┌──────────────┐                    │
│   │   NPU (XDNA2)│         │ GPU (RDNA3.5)│                    │
│   │              │         │              │                    │
│   │  ┌────────┐  │         │  ┌────────┐  │                    │
│   │  │ Prefill│  │ ────────>│  │ Token  │  │                    │
│   │  │ (Prompt│  │         │  │ Gen    │  │                    │
│   │  │Process)│  │         │  │ (TG)   │  │                    │
│   │  └────────┘  │         │  └────────┘  │                    │
│   │              │         │              │                    │
│   │  60-80 TPS   │         │  25-50 TPS   │                    │
│   │  Low Power   │         │  High Power  │                    │
│   └──────────────┘         └──────────────┘                    │
│                                                                 │
│   Platform Support:                                             │
│   • Windows: ✅ Full hybrid via ryzenai-llm                    │
│   • Linux: ⚠️  FLM NPU only (GPU via ROCm)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Backends Comparison Matrix

| Backend | NPU | GPU | Hybrid | Linux Status | Best For |
|---------|-----|-----|--------|--------------|----------|
| `llamacpp` ROCm | ❌ | ✅ | ❌ | Works | Large models (GPU only) |
| `llamacpp` Vulkan | ❌ | ✅ | ❌ | Works | Stability over raw perf |
| `flm` | ✅ | ❌ | ❌ | ✅ Working | Small models on NPU |
| `ryzenai-llm` | ✅ | ✅ | ✅ | ❌ Windows only | Full hybrid |

---

## Immediate Action Items

### Option A: Quick Fix (Use Pre-built Binaries)

Download Lemonade SDK nightly with gfx1151 support:

```bash
# URL pattern (check latest release):
# https://github.com/lemonade-sdk/llamacpp-rocm/releases/latest/
# Download: llama-bxxxx-ubuntu-rocm-gfx1151-x64.zip

unzip llama-bxxxx-ubuntu-rocm-gfx1151-x64.zip
cd llama-bxxxx-ubuntu-rocm-gfx1151-x64
chmod +x llama-cli llama-server

# Test if it detects GPU properly
./llama-cli --list-devices
```

**Expected output**:
```
Device 0: AMD Radeon Graphics, gfx1151 (0x1151), VMM: no, Wave Size: 32
```

### Option B: Build from Source (Maximum Performance)

```bash
# Clone llama.cpp
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp

# Build with gfx1151 optimizations
cmake -B build -DGGML_HIP=ON \
  -DAMDGPU_TARGETS="gfx1151" \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j$(nproc)

# Test with ROCWMMA Flash Attention
./build/bin/llama-server \
  -m /path/to/model.gguf \
  -ngl 99 \
  -fa on \
  --no-mmap
```

### Option C: Hybrid Via Lemonade Router (Once Fixed)

```yaml
# lemonade_config.yaml for hybrid execution
device_routing:
  prefill: "npu"      # XDNA2 for prompt processing
  generation: "gpu"  # RDNA3.5 for token generation
  
models:
  "gemma4-26b-moe":
    backend: "hybrid"
    npu_layers: 0.3    # 30% on NPU (prefill)
    gpu_layers: 0.7    # 70% on GPU (generation)
```

---

## Verification Steps

### 1. Confirm ROCm Works
```bash
rocminfo | grep gfx1151
# Should show: Name: gfx1151
```

### 2. Test New llama.cpp Build
```bash
# Use Lemonade SDK binary or custom build
./llama-bench -m model.gguf -p 512 --flash-attn 1

# Should complete without hanging at "fitting params"
```

### 3. Benchmark Comparison
```bash
# Without ROCWMMA (baseline)
./llama-bench -m model.gguf -p 512 -fa 0

# With ROCWMMA (optimized)
./llama-bench -m model.gguf -p 512 -fa 1

# Expect 50-100% improvement with ROCWMMA
```

---

## NPU Preservation (Confirmed)

The fix script successfully preserved NPU functionality:

| Component | Status |
|-----------|--------|
| `/dev/accel/accel0` | ✅ Present |
| `flm validate` | ✅ Passes |
| NPU firmware 1.1.2.65 | ✅ Current |
| `amdxdna-dkms` | ✅ Unaffected |

---

## Known Limitations

1. **Linux NPU+GPU Hybrid**: Not yet available (Windows only)
2. **FLM NPU**: Works on Linux but Gemma 4 not yet supported
3. **Lemonade 10.2.0**: Bundled llama.cpp lacks gfx1151 optimizations

---

## Resources

1. **Lemonade SDK Nightly**: https://github.com/lemonade-sdk/llamacpp-rocm/releases
2. **AMD Trillion Param Guide**: https://www.amd.com/de/developer/resources/technical-articles/2026/how-to-run-a-one-trillion-parameter-llm-locally-an-amd.html
3. **llama.cpp gfx1151 PR**: https://github.com/ggml-org/llama.cpp/pull/21344
4. **ROCm TheRock**: https://github.com/ROCm/TheRock

---

## Conclusion

**Next Steps**:
1. ⬇️ Download Lemonade SDK nightly or build llama.cpp from source
2. 🔄 Test `llama-server` with `-fa on` (ROCWMMA)
3. ⏳ Wait for Lemonade Server update beyond 10.2.0
4. 🔄 Monitor for Linux hybrid support via `ryzenai-llm`

**Bottom Line**: The DKMS fix was necessary but not sufficient. The bundled inference engine needs updating. Use Lemonade SDK or custom llama.cpp build for full gfx1151 functionality.

---

*Research Date*: 2026-04-10  
*Key Discovery*: Lemonade SDK nightly builds > Lemonade Server stable for gfx1151
