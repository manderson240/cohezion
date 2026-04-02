# Luma AMD Speedrun — Consolidated State

**Deadline: April 6, 2026 11:59 PM PST**
**Last Updated: 2026-04-02 Session 88B**

## Competition Status

| Kernel | Our Best | Leader | Gap | Points | load_inline Variants |
|--------|----------|--------|-----|--------|---------------------|
| GEMM | 22.8µs | 4.3µs | 5.3× | 1,000 | 4 (v2 tiled, v3 MFMA, direct, clean) |
| MLA | 69.7µs | 33.0µs | 2.1× | 1,250 | 1 (fused FP8 quant) |
| MoE | 154.2µs | 109.8µs | 1.4× | 1,500 | 1 (fused prep) |

## Conductor Contributions

### Claude (Primary) — `luma_speedrun/`
- 200+ experiments documented
- 21 submission variants across 3 kernels
- load_inline enforcement rules (`.claude/rules/luma-kernels.md`)
- compound_kernel_cycle.py, kernel_learning_loop.py
- KERNEL_OPTIMIZATION_PRIME.md + 3 per-kernel PRIME skills
- SurrealDB persistence (13 kernel_run records)

### Autoresearch — `research/challenges/luma_amd_speedrun/`
- 111+67+66 K-Search tree nodes across GEMM/MLA/MoE
- RETROSPECTIVE, COORDINATION, kernel_program docs
- 3 load_inline GEMM variants (direct, rocWMMA, clean)
- Confirmed V_MFMA_SCALE_F32_16X16X128_F8F6F4 as cornerstone gfx950 intrinsic
- HipKittens integration feasibility research

### OpenCode/Kimi — `hip-kernels-kimi-k2-5/`
- 29 GEMM variants, 3 HIP kernels
- kernel_vmfma_tuned.hip (candidate for MFMA integration)
- rocWMMA approach analysis

### MoE-Specialist — `research/.../kernels/moe-mxfp4/`
- Exhaustive parameter sweep (results.tsv)
- KSPLIT tuning across 32/256-expert shapes
- Confirmed fmoe_g1u1 dead (NaN for 32-expert)

### Genesis Worktree — `.claude/worktrees/genesis-engine/`
- HipKittens MoE kernel .hpp file (fused 2-stage with MFMA)
- SiLU fusion, register-resident intermediates

### Gemini CLI — `.gemini/settings.json`
- 6 MCP servers configured, NOT YET DEPLOYED on kernel optimization
- Activate for parallel research + SurrealDB persistence

## Confirmed Dead Ends

| Approach | Why Dead | Conductor |
|----------|----------|-----------|
| ctypes HIP dispatch | Stream mismatch, HTTP 500 | Claude |
| CUDA graphs | torch.compile blocked on ROCm 7.1 | Claude/Autoresearch |
| Triton MXFP4 | 68% slower than CK ASM | Claude |
| fmoe_g1u1 | NaN for 32-expert shapes | MoE-specialist |
| doweight_stage1=True | GPU fault or 82% mismatch | Claude/MoE-specialist |
| KSPLIT=4 for 32-expert | Catastrophic overflow | Claude |
| expert_mask | Crashes CK stage1 kernel | Claude |
| API parameter tuning | ALL params exhausted across 4 conductors | All |

## Key Technical Insights

### GEMM
- **Quantization dominates**: ~26µs quant + ~7-10µs GEMM. Total 13-22µs.
- **Leader approach**: Single fused CK/ASM kernel, zero Python overhead. ~4.3µs.
- **Our path**: load_inline with MFMA instructions. V_MFMA_SCALE intrinsic does FP4 decode+multiply+accumulate in 1 instruction.
- **Scale-aligned tiling**: BLOCK_K=32 FP4 = 1 E8M0 scale group. Zero redundant lookups (L251).

### MLA
- **Python dispatch floor**: 3 calls × ~20µs = 60µs minimum from Python.
- **Leader**: Single fused attention kernel, 33µs.
- **Our path**: load_inline fused FP8 quant eliminates 1 dispatch. Need to fuse stage1+reduce for full win.
- **10% tolerance**: rtol=0.1 allows aggressive approximations.

### MoE
- **API ceiling at 154µs**: fused_moe with all optimal params.
- **Leader at 110µs**: Likely direct CK dispatch or fused 2-stage kernel.
- **Our path**: LDS bridge (keep intermediates in shared memory) or direct CK .co dispatch.
- **182 pre-compiled kernels**: Available at `/home/runner/aiter/hsa/gfx950/fmoe_2stages/`.

## Available Tools

| Tool | Status | Use For |
|------|--------|---------|
| load_inline | Proven on runner | All kernels |
| HipKittens | AITER backend, MI355X validated | GEMM, Attention |
| CK-Tile | gfx950 MXFP4 support | GEMM, MoE |
| K-Search | Framework exists, mutations stubbed | Systematic optimization |
| rocWMMA | Available on runner | MFMA tile ops |
| V_MFMA_SCALE | gfx950 native | Hardware FP4 multiply |

## Automation
- `kernel_learning_loop.py`: 12 benchmarks/hour × 3 kernels
- `kernel_submit_cron.sh`: Every 30 min during competition
- `email_status_cron.sh`: Hourly to manderson240@gmail.com
- `compound_kernel_cycle.py`: SurrealDB persistence + enforcement gate
