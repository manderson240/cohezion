# ROCm gfx1151 GPU Enablement - Final Status Report

**Date**: 2026-04-10  
**Hardware**: AMD Ryzen AI MAX+ 395 (Strix Halo / gfx1151)  
**System**: Ubuntu 24.04, kernel 6.17.0-1008-oem  
**Goal**: Enable ROCm GPU inference alongside NPU functionality

---

## Executive Summary

**Status**: ⚠️ PARTIAL SUCCESS

- ✅ NPU fully operational (75+ TPS via FLM)
- ✅ ROCm 7.2.1 installed, gfx1151 properly detected
- ✅ NPU now visible to ROCm (`aie2p`, `RyzenAI-npu5` devices)
- ❌ ROCm GPU inference still blocked by `sched_reserve` hang

The gfx1151 GPU is detected but llama.cpp ROCm backend enters an infinite loop during model loading.

---

## Attempts Made

### Attempt 1: ROCm 7.2.1 Upgrade
**Hypothesis**: ROCm 7.2.1 contains low power state fix for gfx1151 hang

**Actions**:
```bash
sudo sed -i 's|/rocm/apt/7.2|/rocm/apt/7.2.1|g' /etc/apt/sources.list.d/rocm.list
sudo apt update && sudo apt upgrade -y rocm
```

**Results**:
- ✅ ROCm upgraded from 7.2.0 → 7.2.1.70201-81
- ✅ `rocminfo` now shows both GPU (`gfx1151`) and NPU (`aie2p`)
- ❌ Lemonade llama-server still hangs at 100% CPU

---

### Attempt 2: Custom llama.cpp Build with gfx1151 Optimizations
**Hypothesis**: Building llama.cpp from source with gfx1151-specific flags resolves hang

**Actions**:
```bash
cd /tmp && git clone https://github.com/ggml-org/llama.cpp.git
cmake -B build \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS="gfx1151" \
  -DGGML_HIP_ROCWMMA_FATTN=ON \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

# Replace Lemonade's bundled binary
sudo mv /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server \
  /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server.backup.original
sudo cp build/bin/llama-server /var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server
```

**Results**:
- ✅ Build completed successfully (100s, 111 targets)
- ✅ Binary detects gfx1151 GPU (131072 MB VRAM)
- ❌ Still hangs at `sched_reserve` during model load
- Hang occurs immediately when Lemonade starts llama-server

---

### Attempt 3: Disable Tensor Fitting (`-fit off`)
**Hypothesis**: The "for bugs during this step try to reproduce them with -fit off" message indicates fix

**Actions**:
```bash
lemonade load <model> --llamacpp rocm -fit off
```

**Results**:
- ❌ No effect - hang persists
- The error message refers to a different issue

---

## Root Cause Analysis

The hang is **Issue #6027** in llama.cpp's ROCm backend:
- **Location**: `ggml_cuda_set_vmm` / `sched_reserve` / `load_tensors`
- **Trigger**: Tensor memory reservation during GPU layer offloading
- **Symptom**: Process spins at 100% CPU, ~300MB Resident, never completes
- **Affected**: RDNA3.5 (gfx1151) in specific low-power/power-saving states

Community findings confirm:
- ROCm 7.2.1 contains driver fixes but not llama.cpp scheduler fixes
- PR #21344 (VGPR optimizations) improves performance but doesn't fix initialization
- The issue is in llama.cpp's compute graph scheduling, not ROCm driver

---

## Working Alternatives

### Option A: FLM NPU Backend (RECOMMENDED)
```bash
flm serve gemma3:4b --port 13306
```
- ✅ Fully working now
- ✅ 60-80 TPS for 4B models
- ✅ No driver conflicts
- ⚠️ Model support limited (tested: Gemma 3/4, Qwen3)

### Option B: Vulkan Backend
```bash
flm serve <model> --backend vulkan
```
- Reported working by community ("runs super fast on Vulkan")
- Avoids ROCm scheduler entirely
- Requires: `sudo apt install vulkan-sdk glslc libvulkan-dev`
- Need to rebuild llama.cpp with `-DGGML_VULKAN=ON`

### Option C: Wait for Official Fix
- Monitor Lemonade releases >10.2.0
- Monitor llama.cpp Issue #6027 for resolution
- Likely requires scheduler rewrite for RDNA3.5

---

## Hybrid NPU+GPU Strategy (Future)

True hybrid execution (NPU prefill + GPU generation) is:
- ✅ Available on Windows via `ryzenai-llm`
- ⚠️ Not yet available on Linux
- ⚠️ Blocked by this ROCm hang on Linux

When GPU inference is enabled:
- Small models (<4B): FLM NPU
- Large models (>4B): GPU ROCm/Vulkan (when fixed)
- Cloud fallback: Via Ollama cloud bridge

---

## System Status

```bash
# NPU Status
$ flm validate
[Linux]  Kernel: 6.17.0-1008-oem
[Linux]  NPU: /dev/accel/accel0 with 8 columns
[Linux]  NPU FW Version: 1.1.2.65

# ROCm Status  
$ rocminfo | grep -E "(Name:|Device)"
  Name:                    gfx1151          <- GPU detected
  Marketing Name:          AMD Radeon Graphics
      Name:                amdgcn-amd-amdhsa--gfx1151
  Name:                    aie2p            <- NPU now visible!
  Marketing Name:          RyzenAI-npu5
      Name:                aie2-phy-xilinx

# Lemonade Version
$ lemonade --version
lemonade version 10.2.0

# llama-server Version (custom build)
/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server --version
version: 1 (5dd1025)
built with GNU 13.3.0 for Linux x86_64
```

---

## Recommendations

### Immediate (Today)
```bash
# Use NPU for local inference
flm serve gemma3:4b --port 13306

# For larger models, use cloud via Ollama
ollama run qwen3:32b
```

### Short Term (This Week)
1. Install Vulkan SDK to test Vulkan backend
2. Monitor for Lemonade SDK nightly with gfx1151 fixes
3. Track llama.cpp Issue #6027 for resolution

### Medium Term (Next Month)
1. Evaluate if AMD provides official fix in Lemonade update
2. Consider Vulkan as primary GPU backend if ROCm remains blocked
3. Research async NPU submission and GPU compute for hybrid execution

---

## Files Modified/Created

- `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server` - Replaced with custom build
- `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server.backup.original` - Original backup
- `/tmp/llama.cpp/` - Source build with gfx1151+ROCWMMA optimizations

---

## Vault References

- `rocm-gfx1151-verification-2026-04-10.md` - Initial verification
- `execution:rocm_fix_2026_04_10` - SurrealDB execution record
- `gfx1151-hybrid-strategy-compilation.md` - Hybrid execution research
- `lemonade-sdk-integration-2026-04-10.md` - SDK integration notes

---

## Conclusion

The Ryzen AI MAX+ 395 is a complex platform where:
- NPU (via FLM) works flawlessly for supported models
- ROCm GPU inference is blocked by llama.cpp scheduler hangs
- Hardware is capable but software support is still maturing

**Recommended approach**: Use NPU for now, monitor for GPU fixes, experiment with Vulkan when time permits.

---
*Report generated: 2026-04-10 13:50 UTC*
