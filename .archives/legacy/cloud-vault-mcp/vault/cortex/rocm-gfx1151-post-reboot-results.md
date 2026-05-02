---
title: ROCm gfx1151 Fix - Post-Reboot Results
created: 2026-04-10
tags:
  - hardware
  - rocm
  - gfx1151
  - post-mortem
  - partial-fix
  - lemonade
  - llama-cpp
aliases:
  - ROCm Fix Results
category: hardware_acceleration
status: partial-success
---

# ROCm gfx1151 Fix - Post-Reboot Results

## Summary

Executed `./fix_rocm_gfx1151.sh` and rebooted. **Partial success**: DKMS removal worked, NPU protected, but llama.cpp ROCm binary still hangs during model load.

## Results

### ✅ Successful

| Component | Finding |
|-----------|---------|
| DKMS Removal | `amdgpu-dkms` successfully removed |
| ROCm Detection | `gfx1151` properly detected via `rocminfo` |
| NPU Protection | `/dev/accel/accel0` still present, `flm validate` passes |
| Driver Independence | `amdxdna-dkms` unaffected (as predicted) |

### ⚠️ Remaining Issue

Lemonade's bundled `llama-server` (ROCm backend) still hangs at:
```
common_init_result: fitting params to device memory
```

This occurs during model loading despite ROCm proper detection.

## Root Cause Analysis

The DKMS fix resolved the **driver incompatibility**, but the **inference engine** (llama.cpp) may need:
1. Updated llama.cpp build with gfx1151-specific patches
2. [[ROCm TheRock]] wheels update
3. Lemonade version update (current 10.2.0 may predate full gfx1151 support)

## Current Working Alternatives

```bash
# NPU via FLM - WORKING
flm serve gemma3:4b --port 13306 --ctx-len 32768

# Cloud via Ollama - WORKING
ollama run gemma4:31b-cloud

# ROCm via Lemonade - HANGS
lemonade load Qwen3-0.6B-GGUF --llamacpp rocm
```

## References

- [[rocm-gfx1151-verification-2026-04-10]]: Pre-flight verification
- [[GFX1151_ROCM_RESEARCH_SUMMARY]]: Full research doc
- [[LEMONADE_NPU_ROCM_STRATEGY]]: Dual-backend strategy

## Recommendation

Use **FLM NPU** for local inference now. ROCm GPU requires either:
- Lemonade update beyond 10.2.0
- Manual llama.cpp build with gfx1151 patches
- Wait for [[ROCm]] TheRock updates

---

*Execution Date*: 2026-04-10 12:44 UTC  
*Reboot*: 12:44 UTC  
*Results Captured*: 13:00 UTC
