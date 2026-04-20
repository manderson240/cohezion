# Luma AMD Kernel Autoresearch

Autonomous kernel optimization for the Luma AMD Speedrun competition on MI355X (gfx950).
Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

## Model Tier Architecture

| Tier | Model | Role | When |
|------|-------|------|------|
| **T1: Local Loop** | `deepseek-r1:70b` / `qwen3-coder:30b` | Code generation, hypothesis, experiment loop | Always (autonomous, free) |
| **T2: Local Review** | `phi3:mini` | Safety check, blocked-pattern scan, diff review | Per-experiment (fast, free) |
| **T3: Frontier** | Claude Code (Opus) | Strategy pivots, dead-end analysis, skill updates | Only when stuck (expensive, quota-limited) |

**Rule**: The experiment loop (`autokernel.py`) runs entirely on T1/T2. Claude Code is NEVER
in the loop. It is called only for:
1. Initial setup (create kernel_program.md, results.tsv — done once)
2. Strategic review (after 20+ experiments with no improvement)
3. Skill extraction (`/learn` after a breakthrough)

**Usage**: `uv run python autokernel.py --kernel moe-mxfp4 --model deepseek-r1:70b`

## Setup

To set up a new experiment session:

1. **Pick a kernel target**: Choose ONE kernel to optimize this session:
   - `moe-mxfp4` — MoE MXFP4 (155us, leader 145us, gap 1.07x) — CLOSEST TO TOP 10
   - `mxfp4-mm` — GEMM MXFP4 (14.1us, leader 9.7us, gap 1.45x)
   - `mixed-mla` — MLA Decode (72us, leader 4.3us, gap 16.7x)
2. **Read context**: Load the relevant skill for your chosen kernel:
   - ALL kernels: Invoke skill `aiter-kernel-parameter-semantics`
   - ALL kernels: Invoke skill `competitive-kernel-optimization-ceiling`
   - ALL kernels: Invoke skill `popcorn-cli-amd-kernel-submission`
   - MoE: Read `cloud-vault-mcp/vault/projects/LUMA_STATE_SYNC.md`
   - GEMM: Invoke skill `triton-fp4-inline-quantization`
   - MLA: Invoke skill `deepseek-mla-decode-flash-attention-gap`
3. **Read the current submission**: Read `kernels/<kernel>/submission.py` in full.
4. **Read results log**: Read `results.tsv` (this file, same directory) for experiment history.
5. **Create backup**: `cp submission.py submission_autokernel_backup.py`
6. **Confirm and go**: Confirm setup looks good.

## Evaluation

### Commands

```bash
CLI=~/.local/bin/popcorn-cli
KERNELS=research/challenges/luma_amd_speedrun/kernels

# Step 1: ALWAYS test correctness first (~3 min)
$CLI submit --no-tui --mode test --gpu MI355X \
  --leaderboard amd-<kernel> $KERNELS/<kernel>/submission.py

# Step 2: Only if test passes, benchmark (~8 min)
$CLI submit --no-tui --mode benchmark --gpu MI355X \
  --leaderboard amd-<kernel> $KERNELS/<kernel>/submission.py

# Step 3: Only submit to leaderboard if benchmark beats current best
$CLI submit --no-tui --mode leaderboard --gpu MI355X \
  --leaderboard amd-<kernel> $KERNELS/<kernel>/submission.py
```

### Leaderboard names

| Directory | Leaderboard |
|-----------|-------------|
| `moe-mxfp4/` | `amd-moe-mxfp4` |
| `mxfp4-mm/` | `amd-mxfp4-mm` |
| `mixed-mla/` | `amd-mixed-mla` |

### Metrics

The benchmark output includes per-shape timing. Extract the geomean:

```bash
grep -i "geomean\|geometric" run.log
```

Or compute from individual shape times. **Lower geomean_us = better.**

### Timeouts

The entire workflow runs on GitHub Actions with a ~12 min hard timeout.
JIT builds consume 2-4 min. If the runner is busy, submissions may timeout
(status: cancelled). This is NOT a code error — retry during off-peak hours.

## Constraints

**What you CAN do:**
- Modify `submission.py` — this is the ONLY file uploaded to the runner.
- Use any module available on the runner: `torch`, `aiter`, `triton`, `numpy`.
- Import from `task` (provides `input_t`, `output_t` types).
- Import from `reference` (provides `ref_kernel` as correctness fallback).

**What you CANNOT do:**
- Create additional Python files (only `submission.py` is uploaded).
- Use `hipModuleLaunchKernel`, `hipModuleLoadData`, `libamdhip64.so` — source-scanned and blocked.
- Use `torch.compile(mode="reduce-overhead")` with aiter ops — crashes on ROCm 7.1.
- Set `doweight_stage1=True` for SiLU MoE — produces 82% element mismatches.
- Pass `expert_mask` to `fused_moe` — EP cumsum remapping produces -1 IDs, GPU crash.
- Use `AITER_ONLINE_TUNE=1` — blocks on full benchmark sweep, guaranteed timeout.

## Dead Ends (DO NOT RETRY)

These have been tested multiple times and confirmed as permanent failures.
Do NOT retry without genuinely new information (e.g., a new aiter release).

### MoE Dead Ends
- `doweight_stage1=True` — GPU memory fault + 82% mismatch (SiLU nonlinearity)
- `expert_mask=bincount` — EP cumsum -1 IDs → uint32(4.3B) → GPU crash
- `torch.compile(fused_moe)` — `auto_functionalized_v2` assertion on ROCm 7.1
- `cktile_moe_gemm1` direct dispatch — "Unsupported scales/output dtype!" on fp8_e8m0
- `AITER_BYPASS_TUNE_CONFIG` — dead code for competition shapes (zero CSV matches)
- `AITER_KSPLIT` env var — fused_moe ignores it regardless of BYPASS setting
- Adaptive KSPLIT routing (256E→4, 32E→2) — identical to BYPASS=1 baseline
- `moe_sorting_dispatch_policy=1` — 20-79% slower
- `AITER_USE_OPUS_MOE_SORTING` — no effect on MXFP4 variant
- `fmoe_g1u1` — hidden calling convention, can't determine correct args
- Custom Triton MoE — 68% slower than CK ASM

### GEMM Dead Ends
- `get_triton_quant(QuantType.per_1x32)` — unpatched fp4_utils.py bug (ROCm/aiter #974)
- `get_torch_quant` — different rounding than triton_quant
- `gemm_afp4wfp4` + CUDA graph — silent graph capture failure
- `gemm_a4w4` + HIP graph — copy_() overhead exceeds kernel time (+78%)
- Custom `tl.dot_scaled` kernel — 68% slower than ASM persistent kernel
- `hipblaslt` — no fp4 functions exposed
- `aiter.deepgemm` — grouped GEMM for MoE only, needs `group_layout`

### MLA Dead Ends
- Custom Triton FlashDecoding — ~130us dispatch floor (same as aiter)
- `fav3_sage_mxfp4` — requires separate K/V, incompatible with MLA fused buffer
- `F.scaled_dot_product_attention` with padded V — 10x slower (head_dim=576 > flash limit)
- 4D matmul broadcast — materializes KV 16x per head, 9-53x regression
- `fast_mode=True` — 17-21% slower on MI355X
- `num_kv_splits=64` — exceeds aiter API limits, test failure
- hiprtc — source-scanned and blocked by competition runner

## The Experiment Loop

LOOP FOREVER:

1. **Plan**: Based on results.tsv history and dead ends above, choose an experiment.
   Think about what hasn't been tried yet. Consult the K-Search tree in the skills.
2. **Modify**: Edit `submission.py` with the experimental idea.
3. **Commit**: `git add submission.py && git commit -m "autokernel: <description>"`
4. **Test**: Run correctness test via popcorn-cli. Redirect output to a file.
   ```
   $CLI submit --no-tui --mode test --gpu MI355X \
     --leaderboard <name> $KERNELS/<kernel>/submission.py > run.log 2>&1
   ```
5. **Check correctness**: `grep -i "pass\|fail\|error" run.log`
   - If FAILED or CRASH: Read the error. If fixable (typo, import), fix and re-test.
     If fundamental (GPU fault, dtype rejection), log as crash and revert.
   - If TIMEOUT: Retry once. If still timeout, log as timeout and revert.
6. **Benchmark** (only if test passed):
   ```
   $CLI submit --no-tui --mode benchmark --gpu MI355X \
     --leaderboard <name> $KERNELS/<kernel>/submission.py > bench.log 2>&1
   ```
7. **Extract metric**: `grep -i "geomean\|median" bench.log`
8. **Record**: Append to `results.tsv` (tab-separated):
   ```
   <commit_hash>\t<geomean_us>\t<status>\t<description>
   ```
9. **Decision**:
   - If geomean_us < best_so_far: **KEEP** (advance branch)
   - If geomean_us >= best_so_far: **DISCARD** (`git reset --hard HEAD~1`)
   - If crash/timeout: **CRASH** (`git reset --hard HEAD~1`)
10. **Leaderboard**: If this is a new best AND improvement > 1%, submit to leaderboard.
11. **Repeat**: Go to step 1. NEVER STOP.

## Strategy Guidance

### MoE (155us → 145us, 1.07x gap)

All Python API paths are exhausted. Remaining strategies (low confidence):

- **V=0.3**: Set `AITER_JIT_DIR=/tmp/aiter_jit_cache` before `import aiter` to pre-warm JIT.
  This only solves the 720s timeout problem, not performance.
- **V=0.2**: Probe whether MI355X hits IREE K-tile heuristic bug (Issue #22309).
- **Novel**: Study `aiter.fused_moe` source for any env vars or code paths not yet tested.
  Use `inspect.getsource(fused_moe)` in a probe submission to read the latest source.
- **Novel**: Try `fused_moe` with different `quant_type` values if MXFP4 isn't mandatory.

### GEMM (14.1us → 9.7us, 1.45x gap)

The bottleneck is quantization time (~10-13us per call = GEMM time itself).

- **Fused quant+GEMM**: Write a Triton kernel that quantizes A inline during the GEMM.
  This eliminates the separate `dynamic_mxfp4_quant` call.
- **Split-K for large K**: M=16,N=2112,K=7168 is the bottleneck shape (21.7us).
  Try `gemm_a4w4` with manually constructed split-K by calling it on K-chunks.
- **Shape-specific routing**: Route small-K shapes (K=512) to a faster path.

### MLA (72us → 4.3us, 16.7x gap)

The gap is enormous. The leader uses a single fused CK/ASM kernel.

- **Novel**: Search for undiscovered `torch.ops.aiter` attention ops.
  Use `[x for x in dir(torch.ops.aiter) if 'attn' in x.lower() or 'mla' in x.lower()]`.
- **Novel**: Try `aiter.paged_attention_fwd` or `aiter.flash_attn_fwd` if they exist.
- **Matmul regime optimization**: The einsum/matmul path (bs<=4) is already fast (~23us).
  Focus on medium shapes (bs=32-64) where aiter overhead dominates.

### Cross-Kernel Transfer

When you discover something in one kernel, check if it applies to others:

| Discovery | Source | Test on |
|-----------|--------|---------|
| Direct `torch.ops.aiter` calls save overhead | MLA Phase 15 | MoE |
| Pre-allocated buffer caching saves 2-3us | MLA Phase 15 | GEMM |
| `dynamic_mxfp4_quant` is bit-exact | GEMM Phase 15 | MoE stage1 activations |

## Output Format

The benchmark output looks like:

```
Shape 1: median 23.5 us
Shape 2: median 38.1 us
...
Geomean: 71.1 us
```

Extract the geomean for results.tsv. If no geomean is printed, compute it:
`(shape1 * shape2 * ... * shapeN) ^ (1/N)`

## NEVER STOP

Once the experiment loop has begun, do NOT pause to ask the human if you should continue.
The human may be asleep or away. You are autonomous. If you run out of ideas:

1. Re-read the submission.py and look for micro-optimizations
2. Re-read the dead ends — is there a variant that hasn't been tried?
3. Try combining two near-miss ideas
4. Probe the runner for undiscovered aiter APIs via `inspect` or `dir()`
5. Read the latest aiter source via `inspect.getsource()` in a probe submission
6. Try radical changes (different algorithm, different data layout)

The loop runs until the human interrupts you.

## Safety

- Always keep a backup: `submission_autokernel_backup.py`
- Never submit to leaderboard unless benchmark confirms improvement
- If 3 consecutive experiments crash, STOP and ask the human
- Revert on any GPU memory fault immediately
