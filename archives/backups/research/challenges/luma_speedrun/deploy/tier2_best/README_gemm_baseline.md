# Tier 2: GEMM Baseline Kernel

## File
`gemm_baseline.py`

## Strategy
**aiter gemm_a4w4 with MFMA FP4**

Current best-known GEMM implementation:

- FP4 MFMA with exact register layouts
- A/B loading patterns from AMD calculator
- Proper output mapping (column-major)

## Expected Performance
- **Baseline**: ~13.4 µs
- **Status**: API ceiling reached

## Risk Level
**LOW** - Proven implementation

## Test Commands

```bash
# Test correctness
popcorn run gemm_baseline.py --mode test --leaderboard amd-mxfp4-mm

# Benchmark
popcorn run gemm_baseline.py --mode benchmark --leaderboard amd-mxfp4-mm

# Leaderboard submission
popcorn run gemm_baseline.py --mode leaderboard --leaderboard amd-mxfp4-mm
```

## Key Features
- Exact MFMA register layouts
- B stored as B[N, K/2] layout
- D output: column-major per thread

## Success Criteria
- [ ] Passes correctness test
- [ ] Matches ~13.4 µs baseline
- [ ] Reliable reference

## Notes
This is the best achievable without custom kernel breakthrough.
