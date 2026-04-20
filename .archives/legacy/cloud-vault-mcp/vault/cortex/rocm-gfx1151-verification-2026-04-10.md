---
title: GFX1151 ROCm Fix Pre-Flight Verification
created: 2026-04-10
tags:
  - hardware
  - rocm
  - gfx1151
  - strix-halo
  - amd
  - npu
  - verification
  - cohezion
aliases:
  - ROCm gfx1151 Verification
category: hardware_acceleration
status: verified
---

# GFX1151 ROCm Fix Pre-Flight Verification

## Summary

Verified system state before applying `./fix_rocm_gfx1151.sh` to resolve [[gfx1151]] ROCm hangs on AMD Ryzen AI MAX+ 395 (Strix Halo). Confirmed [[NPU]] will remain operational after fix.

## System Configuration

| Component | Value | Status |
|-----------|-------|--------|
| OS | Ubuntu 24.04 (Framework Desktop) | ✅ |
| Kernel | 6.17.0-1008-oem | ✅ |
| CPU/GPU | AMD Ryzen AI MAX+ 395 w/ Radeon 8060S | ✅ |
| Architecture | gfx1151 | ✅ |
| ROCm | 7.2.0 | ✅ |
| linux-firmware | 20240318.git3b128b60-0ubuntu2.17+ | ✅ |

## NPU Status (Protected)

The [[NPU]] uses a separate driver stack from the GPU and will survive the ROCm fix:

| Check | Result |
|-------|--------|
| Device | `/dev/accel/accel0` with 8 columns ✅ |
| Firmware | 1.1.2.65 (requires ≥1.1.0.0) ✅ |
| Driver | amdxdna-dkms 7.0.0-rc1+git20260310.6b13cb8f4 ✅ |
| Memlock | infinity ✅ |
| IOMMU | Default (no `amd_iommu=off`) ✅ |

> **Critical Note**: The NPU requires IOMMU enabled. Some users disable it for GPU performance gains, but this breaks NPU functionality.

## GPU ROCm Issue

### Problem
The `amdgpu-dkms` package (6.16.13.30300000) is incompatible with kernel 6.17 and causes GPU hangs when running LLM inference via ROCm.

### Solution
The `./fix_rocm_gfx1151.sh` script removes the problematic DKMS modules and reinstalls ROCm without DKMS (`--no-dkms` flag).

### Safety Analysis
- ✅ **NPU uses `amdxdna-dkms`**: Separate from `amdgpu-dkms`
- ✅ **Device `/dev/accel/accel0` present**: Will remain after fix
- ✅ **No `amd_iommu=off`**: NPU will stay active
- ✅ **Firmware current**: No update needed before fix

## References

- [[GFX1151_ROCM_RESEARCH_SUMMARY]]: Full research document
- [Lemonade PR #826](https://github.com/lemonade-sdk/lemonade/pull/826): gfx1151 detection fix
- [[hw_acceleration]]: Hardware acceleration patterns
- [[hw_acceleration#ROCm\|ROCm Section]]: ROCm-specific patterns

## Next Steps

1. Run `./fix_rocm_gfx1151.sh` (verified safe)
2. Reboot system
3. Verify ROCm: `rocminfo | grep gfx1151`
4. Verify NPU: `flm validate`
5. Test lemonade with ROCm backend

## Related Sessions

- [[_index#Hardware Acceleration\|Hardware Acceleration Entries]]
- [[LEMONADE_NPU_ROCM_STRATEGY]]: NPU + ROCm dual strategy
- [[LEMONADE_LOCAL_INFERENCE_STATUS]]: Local inference status

---

*Session Date*: 2026-04-10  
*Verification Status*: ✅ PASSED - Safe to proceed with ROCm fix
