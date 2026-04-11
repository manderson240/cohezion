# gfx1151 ROCm Research Summary - Critical Findings

## Executive Summary

**Status**: The gfx1151 ROCm hang has a **known fix** that requires specific system configuration.

## Key Finding #1: Lemonade gfx1151 Detection Fixed (Jan 15, 2026)

**PR #826** merged into Lemonade adds proper detection:
```python
# Before (broken for OEM kernel):
if "radeon" not in device_name_lower:
    return None

# After (fixed):
if "radeon" not in device_name_lower and "amd" not in device_name_lower:
    return None
# Added: device 1586 detection for Strix Halo
if any(halo_igpu in device_name_lower for halo_igpu in ["8050s", "8060s", "device 1586"]):
    return "gfx1151"
```

**Current Lemonade version**: 10.2.0 (need to check if includes this fix)

## Key Finding #2: The Hang is Fixed (Sept 2025)

AMD confirmed the hang issue is resolved with:
1. **linux-firmware**: `20240318.git3b128b60-0ubuntu2.17` or newer
2. **No DKMS**: `amdgpu-install --usecase=rocm --no-dkms`
3. **TheRock wheels**: Latest version
4. **lemonacpp-rocm**: build b1064 or newer

## Key Finding #3: Critical - NO DKMS

From AMD engineer benrichard-amd:
> "There is an incompatibility between ROCm and Linux Kernel 6.17. This is a known issue and being addressed."

**Fix**: Install without DKMS
```bash
amdgpu-install --usecase=rocm --no-dkms
```

## Key Finding #4: Performance Boost - ROCWMMA

Building with `-DGGML_HIP_ROCWMMA_FATTN=ON` gives **2x performance boost**:

| Config | pp512 Throughput |
|--------|------------------|
| Standard ROCm | 592 t/s |
| With ROCWMMA | **1006 t/s** |

**Status**: Merged into llama.cpp Sept 9, 2025

## Key Finding #5: Ollama Has Native Support

Ollama 0.18+ has native gfx1151 support:
```
msg="amdgpu is supported" gpu=0 gpu_type=gfx1151
msg="inference compute" id=0 library=rocm variant="" compute=gfx1151
```

`HSA_OVERRIDE_GFX_VERSION` no longer needed as of Ollama 0.18.

## Our Current System State

**Last Verified**: 2026-04-10

### System Configuration (Verified)
- **OS**: Ubuntu 24.04 (Framework Desktop)
- **Kernel**: 6.17.0-1008-oem
- **CPU/GPU**: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S Graphics (gfx1151)
- **ROCm**: 7.2.0
- **linux-firmware**: 20240318.git3b128b60-0ubuntu2.17+ (✅ Verified current)
- **Lemonade**: 10.2.0

### NPU Status (Verified Working)
- **NPU Device**: `/dev/accel/accel0` with 8 columns ✅
- **NPU Firmware**: 1.1.2.65 (>= 1.1.0.0 required) ✅
- **amdxdna-driver**: 0.6 via amdxdna-dkms ✅
- **Memlock Limit**: infinity ✅
- **IOMMU**: Default (no amd_iommu=off) ✅

### GPU ROCm Status (Needs Fix)
- **ROCm Detection**: gfx1151 properly detected ✅
- **DKMS Modules**: amdgpu-dkms 6.16.13.30300000 installed ⚠️ **KNOWN ISSUE**
- **Problem**: amdgpu-dkms incompatible with kernel 6.17, causes hangs
- **Safe to Fix**: ✅ Yes - NPU uses separate amdxdna-dkms stack

### Verification Commands Used
```bash
# NPU Check
ls -la /dev/accel/accel0
flm validate

# GPU ROCm Check
rocminfo | grep gfx1151
dpkg -l | grep -E "amdgpu-dkms|amdxdna-dkms"

# IOMMU Check
cat /proc/cmdline | grep iommu
```

## Post-Fix Verification (2026-04-10)

### ✅ Successfully Fixed
| Component | Before | After |
|-----------|--------|-------|
| **amdgpu-dkms** | Installed (incompatible) | ✅ **Removed** |
| **ROCm Detection** | Present but unstable | ✅ **Stable - gfx1151 detected** |
| **NPU** | `/dev/accel/accel0` | ✅ **Still working** - driver independence confirmed |
| **amdxdna-dkms** | Installed | ✅ **Still installed** (unaffected) |

### ⚠️ Remaining Issue
The llama.cpp ROCm binary bundled with **Lemonade 10.2.0** still hangs during model loading:

```
common_init_result: fitting params to device memory
```

This suggests the bundled llama-server binary may need an update beyond the DKMS fix.

### Working Alternatives

| Backend | Status | Command |
|---------|--------|---------|
| **FLM NPU** | ✅ Working | `flm serve gemma3:4b --port 13306` |
| **Ollama Cloud** | ✅ Working | `ollama run gemma4:31b-cloud` |
| **Lemonade ROCm** | ⚠️ Partial | Detection works, load hangs |

### System Status (2026-04-10 13:00 UTC)

```bash
# NPU Verification
$ flm validate
[Linux]  NPU: /dev/accel/accel0 with 8 columns
[Linux]  NPU FW Version: 1.1.2.65
[Linux]  amdxdna version: 0.6
[Linux]  Memlock Limit: infinity

# ROCm Verification
$ rocminfo | grep gfx1151
  Name:                    gfx1151
      Name:                    amdgcn-amd-amdhsa--gfx1151

# DKMS Verification
$ dkms status | grep amdgpu
# (no output - successfully removed)
$ dkms status | grep amdxdna
amdxdna/7.0.0-rc1+git20260310.6b13cb8f4: installed
```

## Immediate Workaround

While waiting for fixes:

### FLM NPU (Working Now)
```bash
flm pull gemma3:4b
flm serve gemma3:4b --port 13306 --ctx-len 32768
```

### Ollama with ROCm (Working)
```bash
ollama run gemma4:e4b  # Already working on your system
```

## Performance Expectations (Fixed System)

| Model | Backend | Expected TPS | VRAM |
|-------|---------|--------------|------|
| Gemma 3:4B | FLM NPU | 60-80 | NPU |
| Gemma 4 E2B | ROCm | 25-35 | ~4GB |
| Gemma 4 26B | ROCm | 20-25 | ~18GB |
| Gemma 4 31B | ROCm | 15-20 | ~20GB |

With ROCWMMA: ~**2x faster prompt processing**

## References

1. **Lemonade PR #826**: Fix ROCm Detection for Strix Halo
   - https://github.com/lemonade-sdk/lemonade/pull/826

2. **Ollama Issue #14855**: Strix Halo ROCm Working Guide
   - https://github.com/ollama/ollama/issues/14855

3. **ROCm TheRock #1413**: gfx1151 Hang Fix
   - https://github.com/ROCm/TheRock/issues/1413

4. **lemonacpp-rocm #7**: ROCWMMA Performance Boost
   - https://github.com/lemonade-sdk/llamacpp-rocm/issues/7

5. **AMD Documentation**: Strix Halo Setup
   - https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/

6. **Hybrid Strategy Research**: Complete findings (April 2026)
   - `GFX1151_HYBRID_STRATEGY_RESEARCH.md`
   - llama.cpp PR #21344 (gfx1151 VGPR optimizations)
   - Lemonade SDK nightly builds recommendation

## Next Steps Priority

### Immediate (Today)
1. ⬇️ Download **Lemonade SDK nightly** for gfx1151: https://github.com/lemonade-sdk/llamacpp-rocm/releases
2. 🔄 Extract and test `llama-server` with `-fa on` (ROCWMMA)
3. ✅ Verify NPU still working with `flm validate`

### Short Term (This Week)
4. **Build Reference**: Use custom llama.cpp if SDK doesn't work
5. **Monitor**: Check for Lemonade Server update beyond 10.2.0

### Medium Term
6. **Hybrid Execution**: Wait for Linux `ryzenai-llm` support (currently Windows-only)
7. **Performance Tuning**: Apply VGPR optimizations when available in stable builds

---

*Status Update (2026-04-10)*: Research complete. **Solution identified**: Lemonade SDK nightly or build llama.cpp from source with gfx1151 + ROCWMMA optimizations. See `GFX1151_HYBRID_STRATEGY_RESEARCH.md` for detailed findings.
