# Sync Status: Competition Directory ↔ Official References

**Last Updated**: 2026-03-18 15:15 UTC
**Action**: Aligned reference implementations with official luma_speedrun/

## Changes Made

### Reference Implementations Updated

| Kernel | Status | Key Changes |
|--------|--------|-------------|
| **GEMM** (amd-mxfp4-mm) | ✅ Synced | Uses `dynamic_mxfp4_quant` from `aiter.ops.triton.quant` (#975 patch) |
| **MLA** (amd-mixed-mla) | ✅ Synced | FP8 optimized with a8w8 kernel, proper metadata handling |
| **MoE** (amd-moe-mxfp4) | ✅ Synced | Uses `fused_moe` with proper quantization |

### Backups Created
- `reference.py.backup` for all three kernels
- Preserved previous versions in case of issues

### Documentation Updated
- `README.md` - Added reference implementation section
- `COORDINATION.md` - Updated submission status
- Added official luma_speedrun/ path documentation

## Official Source
All reference implementations now match:
`/home/mike-anderson/dev/cohezion/luma_speedrun/`

## Next Steps
1. Sessions should verify their submissions work with new references
2. Test mode submissions to verify correctness
3. Continue optimization from aligned baselines
