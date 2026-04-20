# Luma AMD Speedrun: Breakthrough Research Summary
Date: 2026-03-23

## 1. Competitive Landscape
- **GEMM**: Leader 9.7µs, Our Best 14.1µs (1.45x gap).
- **MoE**: Leader 145µs, Our Best 155µs (1.07x gap).
- **MLA**: Leader 4.3µs, Our Best 67.8µs (15.8x gap).

## 2. Key Breakthroughs Identified
### A. MLA: The Persistent Triton FlashMLA
The current 15x gap in MLA is due to Python/Triton dispatch overhead per batch item.
**Solution**: A single persistent Triton kernel that:
- Fuses QK dot product, Online Softmax, and V accumulation.
- Uses `tl.dot` (Matrix Cores) instead of `tl.sum(q * k)`.
- Bypasses the `aiter` multi-kernel pipeline.
- Port from `.worktrees/opus-mla-optimization/.../submission_triton_flash.py`.

### B. GEMM: Optimized tl.dot_scaled
**Solution**: Refine the `tl.dot_scaled` Triton kernel to use MI355X-specific tiling (BLOCK_M=64, BLOCK_N=128) and minimize `e8m0_unshuffle` overhead.

### C. MoE: Active-Expert Masking + JIT Persistence
**Solution**: Implement `expert_mask` to skip sorting for empty experts and use `AITER_JIT_DIR` to bypass the 720s timeout limit.

## 3. Implementation Plan
1. Create `research/challenges/luma_amd_speedrun/kernels/*/staging/submission.breakthrough.*.py`.
2. Verify correctness in `--mode test`.
3. Submit to leaderboard using `popcorn-cli`.

## 4. Risks & Constraints
- **Scanner Blocks**: Custom HIP (amdclang++) is blocked. Triton is the primary vehicle for breakthroughs.
- **Hardware Precision**: Native CDNA 4 intrinsics (`v_mfma_scale`) are supported by the compiler but blocked by the scanner if called via `ctypes`. Must find a way to access them via Triton or aiter.
