# Luma Speedrun - Quick Reference

## KEY INSIGHT: `load_inline` WORKS!

Official template proves custom HIP kernels work on Popcorn runners:
- **URL**: https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/fp8-mm/template-hip.py

This is how rank 1 achieves 1µs on GEMM!

## Submissions Ready to Test

### GEMM (Biggest gap - 22x to rank 1)
- `luma_speedrun/amd-mxfp4-mm/submission.py`
- Uses load_inline with block-wise GEMM + lifted scales

### MLA (2.6x gap to rank 1)
- `luma_speedrun/amd-mixed-mla/submission.py`
- SnapMLA optimized three-regime routing

### MoE (~1x gap - already competitive!)
- `luma_speedrun/amd-moe-mxfp4/submission.py`
- Adaptive KSPLIT + USE_NT=1

## Test Command
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun
./submit_all.sh
```

## Leaderboard Targets
| Kernel | Target | Rank 1 |
|--------|--------|--------|
| GEMM | 1-5µs | 1.000µs |
| MLA | 26-50µs | 26.812µs |
| MoE | ~110µs | 109.793µs |

## Key Files
- `research/challenges/luma_amd_speedrun/PRE_REBOOT_STATUS.md` - Full status
- `research/challenges/luma_amd_speedrun/RETROSPECTIVE.md` - Learnings
