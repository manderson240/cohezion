# Lemonade SDK Option 1 - Results and Findings

**Date**: 2026-04-10  
**Status**: ⚠️ Partial Success - Issue Persists

## What Was Done

1. **Located libraries**: Found Lemonade Server uses `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/` (system-level, not user-level)
2. **Downloaded SDK**: Lemonade SDK b1236 (latest nightly) for gfx1151
3. **Replaced libraries**: Backed up and replaced system libraries with SDK versions
4. **Tested**: Restarted Lemonade and attempted model load

## Results

### ✅ What Worked
- Library replacement successful (libggml-hip.so size: 61M → 64M)
- Lemonade Server started correctly with new libraries
- Services restarted without errors
- User cache also updated (has backup)

### ❌ What Still Fails
**Model load still hangs at `common_init_result: fitting params to device memory`**

```
2026-04-10 13:24:14.090 [Info] (Process) common_init_result: fitting params to device memory,
  for bugs during this step try to reproduce them with -fit off, or provide --verbose logs
  if the bug only occurs with -fit on
2026-04-10 13:24:24.072 [Debug] (WrappedServer) Still waiting for llama-server...
```

## Root Cause Analysis

The SDK b1236 build:
1. **Is newer** than Lemonade 10.2.0 bundled (file size 61M → 64M indicates newer code)
2. **Does NOT include** the gfx1151-specific VGPR optimizations (PR #21344, merged April 2026)
3. **May NOT be** built with `-DGGML_HIP_ROCWMMA_FATTN=ON`

**The hang at `common_init_result` is a known issue** that requires either:
- The ROCWMMA Flash Attention build flag, OR
- The VGPR optimization patches from PR #21344

## Rollback Performed

Libraries restored to original (Apr 5, 2026):
- Backup location: `/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/backup_sdk_b1236/`
- Also backed up in: `~/.cache/lemonade/bin/llamacpp/rocm/backup_sdk_b1236/`

## Conclusion

**Option 1 (SDK libraries): NOT SUFFICIENT**

The SDK nightly builds provide newer ROCm libraries but do not include the specific gfx1151 optimizations needed to fix the `common_init_result` hang.

**Recommended Next Steps:**
1. ✅ Attempt Option 2: Build llama.cpp from source
   - Requires: `cmake -DGGML_HIP=ON -DAMDGPU_TARGETS="gfx1151" -DGGML_HIP_ROCWMMA_FATTN=ON`
2. Monitor Lemonade SDK releases for gfx1151-specific builds
3. Wait for Lemonade Server update beyond 10.2.0

## Documentation
- See `GFX1151_HYBRID_STRATEGY_RESEARCH.md` for full research
- Vault entry: `cloud-vault-mcp/vault/cortex/lemonade-sdk-integration-2026-04-10.md`
- SurrealDB: `implementation:lemonade_sdk_b1236`

---

*Attempted*: 2026-04-10 13:23 UTC  
*Rollback*: Completed  
*Status*: Proceed to Option 2 (Source Build)
