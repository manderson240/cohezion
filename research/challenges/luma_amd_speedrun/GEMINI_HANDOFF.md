# Luma AMD Speedrun — Handoff Document

> **Date:** 2026-03-13
> **From:** Claude Code (Anthropic Sonnet 4.6)
> **To:** Gemini CLI
> **Competition:** Luma AMD Speedrun on Popcorn platform
> **Hardware:** AMD MI355X (gfx950) — remote execution only via Popcorn CLI

---

## TL;DR — What This Is

An AMD GPU kernel optimization competition. You write Python files that implement CUDA/HIP kernels for three workloads (GEMM, MoE, MLA), submit them to remote MI355X hardware via `popcorn-cli`, and try to beat the leaderboard. The kernels use AMD's `aiter` library (ROCm 7.1, Triton-ROCm 3.6.0, PyTorch 2.10+rocm7.1).

**You cannot test locally** — the local GPU is an AMD Radeon 8060S (RDNA4 gfx1151), which is incompatible with MI355X (CDNA3 gfx950). All testing goes through remote submission.

---

## Current Standings

| Kernel | Our Best | Leader | Gap | Leaderboard Name | Priority |
|--------|----------|--------|-----|-------------------|----------|
| **GEMM** | ~24 us | 9.7 us | **2.49x** | `amd-mxfp4-mm` | **HIGH — active work** |
| **MoE** | ~162 us | 145 us | 1.12x | `amd-moe-mxfp4` | Medium |
| **MLA** | ~97 us | 4.3 us | 22x | `amd-mixed-mla` | Low (big structural gap) |

---

## Directory Layout

```
~/dev/cohezion/.worktrees/spec-luma-amd-speedrun/research/challenges/luma_amd_speedrun/
├── kernels/
│   ├── mxfp4-mm/           # GEMM kernel
│   │   ├── submission.py    # <-- ACTIVE: your kernel goes here
│   │   ├── reference.py     # Reference implementation (gold standard)
│   │   ├── task.py           # Input/output type definitions
│   │   ├── task.yml          # Test shapes, benchmark shapes, description
│   │   └── submission_tritonblas_fused.py  # Experimental fused kernel (WIP, buggy)
│   ├── moe-mxfp4/           # MoE kernel
│   │   ├── submission.py     # Current best MoE submission
│   │   ├── reference.py
│   │   └── task.py
│   └── mixed-mla/           # MLA decode kernel
│       ├── submission.py     # Current best MLA submission (torch-native hybrid)
│       ├── reference.py
│       └── task.py
├── eval.py                   # Evaluation harness (do not modify)
└── utils.py                  # Shared utilities (do not modify)
```

---

## How to Submit

```bash
CLI=~/.local/bin/popcorn-cli
KERNELS=~/dev/cohezion/.worktrees/spec-luma-amd-speedrun/research/challenges/luma_amd_speedrun/kernels

# ALWAYS do: test → benchmark → leaderboard (in that order)

# GEMM
$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-mxfp4-mm $KERNELS/mxfp4-mm/submission.py
$CLI submit --no-tui --mode benchmark --gpu MI355X --leaderboard amd-mxfp4-mm $KERNELS/mxfp4-mm/submission.py
$CLI submit --no-tui --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm $KERNELS/mxfp4-mm/submission.py

# MoE
$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py
$CLI submit --no-tui --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py
$CLI submit --no-tui --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 $KERNELS/moe-mxfp4/submission.py

# MLA
$CLI submit --no-tui --mode test --gpu MI355X --leaderboard amd-mixed-mla $KERNELS/mixed-mla/submission.py
$CLI submit --no-tui --mode benchmark --gpu MI355X --leaderboard amd-mixed-mla $KERNELS/mixed-mla/submission.py
$CLI submit --no-tui --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla $KERNELS/mixed-mla/submission.py
```

### Submission Constraints
- **No per-user rate limit** — submit freely
- **Workflow timeout: ~12 minutes** (GitHub Actions)
- **aiter JIT compilation takes ~4 min** on first use (MoE: ~230s, MLA: ~224s)
- **STDERR output** is visible in test mode — use `print(..., file=sys.stderr)` for debugging
- **Transient failures** happen — retry if a previously-passing kernel suddenly fails

### Correctness Tolerances

| Kernel | rtol | atol |
|--------|------|------|
| GEMM | 1e-2 | 1e-2 |
| MLA | 1e-2 | 1e-2 |
| MoE | 5e-2 | 5e-2 |

---

## Kernel 1: GEMM (MXFP4 Matrix Multiply) — THE MAIN TARGET

### What It Does

Takes bf16 matrix A [M, K] and pre-quantized MXFP4 matrix B, quantizes A to MXFP4 on-the-fly, then performs fp4 GEMM → bf16 output C [M, N].

### Input Format
```python
(A, B, B_q, B_shuffle, B_scale_sh) = data
# A:          [M, K]    bf16         — activation matrix (needs quantization)
# B:          [N, K]    bf16         — weight matrix (reference only)
# B_q:        [N, K//2] fp4x2       — pre-quantized B
# B_shuffle:  [N, K//2] fp4x2       — shuffled B for gemm_a4w4
# B_scale_sh: [*, K//32] e8m0       — shuffled B scale (padded)
```

### Current Best Submission (submission.py — ~24 us)
```python
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle
import aiter
from aiter import dtypes

def custom_kernel(data):
    A, B, B_q, B_shuffle, B_scale_sh = data
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)              # ~33-39 us (BOTTLENECK)
    A_q = x_fp4.view(dtypes.fp4x2)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    return aiter.gemm_a4w4(                               # ~24 us (CK kernel)
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        dtype=dtypes.bf16, bpreshuffle=True,
    )
```

**The bottleneck is clear:** `dynamic_mxfp4_quant` takes 33-39 us — MORE than the GEMM itself for small shapes. The leader at 9.7 us is somehow doing quant+GEMM combined faster than our quant alone.

### Benchmark Shapes
```
M     N     K      seed
4     2880  512    4565
16    2112  7168   15
32    4096  512    457
32    2880  512    54
64    7168  2048   687
256   3072  1536   7856
```

### Test Shapes (correctness check)
```
M     N     K      seed
8     2112  7168   124
16    3072  1536   6635
64    3072  1536   45
256   2880  512    78
```

### What's Been Tried (and failed)

| Approach | Result | Why |
|----------|--------|-----|
| `aiter.get_triton_quant` directly | JIT call-site bug (~1-3% error) | Known aiter issue |
| `aiter.get_torch_quant` | Not yet tested | Plan Task 1 |
| `aiter.get_hip_quant` | Scale rounding mismatch | E8M0 scale incompatible with gemm_a4w4 |
| `tritonblas.matmul_fp4` | ~26 us (slower than gemm_a4w4) | Triton kernel, no fused quant |
| Fused quant+GEMM Triton kernel | Wrong results (15K-720K mismatches) | See below |

### The Fused Kernel Approach (submission_tritonblas_fused.py) — WIP

**The hypothesis:** Fuse bf16→fp4 quantization directly into the Triton GEMM kernel to eliminate the 33-39 us quantization kernel launch. This is the most promising path to beating 9.7 us.

**Current status:** The kernel compiles and runs but produces wrong GEMM results. After 3 rounds of fixes:
1. Fixed Triton 3D tensor indexing error (sum-as-OR nibble packing trick)
2. Fixed E8M0 scale formula (normalize to fp4_max=6.0, not 2.0)
3. Still produces systematically-too-large outputs (~15K mismatched elements)

**Root cause not yet isolated.** The next step is a **diagnostic hybrid kernel**:
- Use `dynamic_mxfp4_quant(A)` for quantization (known correct)
- Pass pre-quantized A directly to our custom Triton GEMM kernel
- If hybrid PASSES → our inline quantization formula is wrong
- If hybrid FAILS → the GEMM kernel itself has a bug

**Key technical pitfalls discovered:**

1. **Triton JIT does NOT support 3D integer indexing:** `tensor[:, :, 0]` → `CompilationError: unsupported tensor index: constexpr[0]`. Workaround: sum-as-OR trick for nibble packing.

2. **E8M0 scale formula for fp4 e2m1:** Must normalize to fp4_max=6.0, not 1.0.
   - WRONG: `floor(log2(amax)) + 127`
   - RIGHT: `floor(log2(amax / 6.0)) + 128`

3. **BLOCK_K minimum:** `tl.dot_scaled` requires packed_K >= 64 bytes → BLOCK_K >= 128 BF16 elements.

4. **Only `dynamic_mxfp4_quant` produces compatible scales** for tritonblas/gemm_a4w4. Other quant methods (hip_quant, torch_quant, triton_quant) produce different E8M0 scale rounding that causes 6.5-15.25 GEMM errors. The data (nibble ordering) is identical — the incompatibility is purely in scale computation precision.

### Available Libraries on MI355X

```python
import aiter       # AMD Inference Toolkit — CK kernels, fused_moe, MLA decode
import tritonblas  # Origami chiplet-aware MXFP4 GEMM
import triton      # Triton compiler (ROCm fork, 3.6.0)
import torch       # PyTorch 2.10+rocm7.1

# Key aiter APIs:
aiter.gemm_a4w4(A_q, B_shuffle, A_scale, B_scale, dtype=bf16, bpreshuffle=True)
aiter.get_triton_quant(QuantType.per_1x32)  # has JIT call-site bug
aiter.get_torch_quant(QuantType.per_1x32)   # pure PyTorch, untested for GEMM
aiter.get_hip_quant(QuantType.per_1x32)     # HIP kernel, scale mismatch
from aiter.ops.triton.quant import dynamic_mxfp4_quant  # patched, correct

# Key tritonblas APIs:
from tritonblas import matmul_fp4, OrigamiMatmulSelector
# matmul_fp4(a_uint8, b_uint8, c_out, a_scale, b_scale) — in-place, ~26 us
```

### Unexplored GEMM Paths

1. **`gemm_afp4wfp4`** — Triton-based alternative GEMM mentioned in reference.py line 97:
   `from aiter.ops.triton.gemm.basic.gemm_afp4wfp4 import gemm_afp4wfp4`
   Has split-K and auto-tuning. Signature unknown — needs a probe submission.

2. **`get_torch_quant` with `shuffle=True`** — Pure PyTorch quant, no JIT. MoE reference already uses it successfully. Untested for GEMM path.

3. **CK assembly kernel direct invocation** — `gemm_a4w4` wraps a CK assembly kernel. If we can call it with custom tile configs or bypass the Python wrapper overhead...

4. **Fix the fused kernel** — Isolate whether the bug is quant or GEMM, then fix it. If the fused approach works, it eliminates 33-39 us of quant overhead.

---

## Kernel 2: MoE (Mixture of Experts with MXFP4) — CLOSE TO LEADER

### Current Status: ~162 us vs leader 145 us (1.12x gap)

The current submission uses expert-count-aware KSPLIT selection:
- 257 experts + sparse: `KSPLIT=4`
- Few experts + sparse: `KSPLIT=2`
- Dense (estimated_m >= 50): `KSPLIT=0` (default CK path)

This is close to optimal for the `fused_moe` API. Further gains likely require:
- Direct CK 2-stage kernel calls bypassing `fused_moe` dispatch
- Custom tile configurations from the tuned CSV configs

### Input Format
```python
(hidden_states, gate_up_weight, down_weight,
 gate_up_weight_scale, down_weight_scale,
 gate_up_weight_shuffled, down_weight_shuffled,
 gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
 topk_weights, topk_ids, config) = data
```

### Critical Parameters (DO NOT CHANGE)
- `doweight_stage1=False` — changing to True causes correctness failure (SiLU is nonlinear)
- `block_size_M` — DO NOT override; causes GPU memory faults on some shapes
- `dispatch_policy=1` — 20-79% slower than default

---

## Kernel 3: MLA (Multi-Latent Attention Decode) — HUGE GAP

### Current Status: ~97 us vs leader 4.3 us (22x gap)

Current approach: **Hybrid** — torch-native `einsum` for small workloads (bs*kv < 400K tokens), aiter fp8 ASM kernel for large workloads. This 2x'd the reference.

The 22x gap suggests the leader uses a fundamentally different approach (possibly MXFP4 KV cache, or a completely different attention algorithm).

### Input Format
```python
q, kv_data, qo_indptr, kv_indptr, config = data
# q:        (total_q, num_heads, 576) bf16
# kv_data:  dict with three KV cache formats:
#   "bf16":  Tensor (total_kv, 1, 576) bf16
#   "fp8":   (kv_buffer, scale) — current reference uses this
#   "mxfp4": (kv_buffer_fp4x2, scale) — UNTESTED, could be 2x bandwidth reduction
```

### Unexplored MLA Paths
1. **MXFP4 KV cache** — `kv_data["mxfp4"]` is provided but never tested. 4-bit KV = half the bandwidth of fp8.
2. **FlashAttention-2 with custom gfx950 kernel** — if available in aiter
3. **Fused Q@K attention** — skip the 3-stage aiter pipeline entirely for all sizes

---

## Environment Details

### Remote (MI355X — where kernels run)
- GPU: AMD Instinct MI355X (gfx950, CDNA3, 8 XCDs, 304 CUs)
- ROCm: 7.1
- Triton: 3.6.0 (ROCm fork)
- PyTorch: 2.10+rocm7.1
- aiter: ROCm/aiter with patch #975
- tritonblas: Origami chiplet-aware MXFP4 GEMM

### Local (development machine — cannot run kernels)
- CPU: AMD Ryzen AI MAX+ 395 (Strix Halo)
- GPU: Radeon 8060S (RDNA4 gfx1151) — NOT compatible with MI355X kernels
- ROCm: 6.2.4 (cannot run gfx950 code)
- Use: Edit files, run popcorn-cli, read output

---

## Probe/Introspection Pattern

Since you can't test locally, use "probe submissions" to discover APIs:

```python
import sys
from task import input_t, output_t
from reference import ref_kernel

def custom_kernel(data: input_t) -> output_t:
    # Print whatever you want to discover
    import aiter
    import inspect
    print(dir(aiter), file=sys.stderr)
    print(inspect.getsource(some_function), file=sys.stderr)

    # ALWAYS fall back to ref_kernel for correctness
    return ref_kernel(data)
```

Submit with `--mode test` and read STDERR. This passes correctness (delegates to ref_kernel) while extracting info from the remote environment.

---

## Key Discoveries & Hard-Won Knowledge

### 1. tritonblas.matmul_fp4 API
- All tensors MUST be `torch.uint8` views (not native fp4 dtype)
- B layout: `[N, K//2]` row-major (NOT transposed like aiter)
- Output `C` must be pre-allocated and passed as 3rd positional arg
- Wrapper internally transposes B before the Triton kernel
- Performance: ~26 us geomean (slightly slower than gemm_a4w4's ~24 us)

### 2. e8m0_unshuffle (skip B re-quantization)
```python
def e8m0_unshuffle(scale_shuffled, orig_m, orig_n):
    sm, sn = scale_shuffled.shape
    scale = scale_shuffled.view(sm // 32, sn // 8, 4, 16, 2, 2)
    scale = scale.permute(0, 5, 3, 1, 4, 2).contiguous()
    scale = scale.view(sm, sn)
    return scale[:orig_m, :orig_n]
```
Cost: ~0.1 us. Reverses `e8m0_shuffle` without re-quantizing B.

### 3. Quantization Compatibility
Only `dynamic_mxfp4_quant` is compatible with both `gemm_a4w4` and `tritonblas.matmul_fp4`. Other quant methods produce scale rounding differences (NOT nibble ordering differences) causing GEMM errors of 6.5-15.25.

### 4. A Quantization is the Bottleneck
```
dynamic_mxfp4_quant(A): 33-39 us
e8m0_unshuffle(B_scale): ~0.1 us
gemm_a4w4/matmul_fp4:   24-58 us
TOTAL:                   66-92 us geomean
```
The leader at 9.7 us is doing quant+GEMM in less time than our quant alone.

### 5. Origami Chiplet Scheduling
MI355X has 8 XCDs (chiplet dies). The `OrigamiMatmulSelector` auto-tunes tile sizes:
```python
from tritonblas import OrigamiMatmulSelector
selector = OrigamiMatmulSelector(m, n, k, "f4", "f4", torch.bfloat16, device, mx_block_size=32)
# selector.block_m, selector.block_n, selector.block_k, selector.group_m, selector.num_sms
```

---

## Suggested Attack Plan

### Priority 1: GEMM (biggest gap, most explored)

**Option A: Fix the fused kernel**
1. Create diagnostic hybrid: `dynamic_mxfp4_quant(A)` + custom Triton GEMM
2. If hybrid passes → fix inline quant formula (may need to match `dynamic_mxfp4_quant` exactly)
3. If hybrid fails → debug GEMM kernel (Origami scheduling, tl.dot_scaled, B loading)

**Option B: Try `gemm_afp4wfp4` Triton GEMM**
1. Probe submission to get its signature
2. May have split-K that outperforms CK `gemm_a4w4` for small M shapes

**Option C: Try `get_torch_quant` with `gemm_a4w4`**
1. Bypasses Triton JIT entirely for quantization
2. May be faster than `dynamic_mxfp4_quant` (which is also Triton-based)

### Priority 2: MoE (small gap, diminishing returns)
- Introspect aiter CK configs via probe submission
- Try direct CK 2-stage kernel calls with custom tile configs

### Priority 3: MLA (huge gap, likely structural)
- Try MXFP4 KV cache (`kv_data["mxfp4"]`)
- Look for alternative attention kernels in aiter

---

## Files You'll Want to Read

| File | Why |
|------|-----|
| `kernels/mxfp4-mm/reference.py` | Gold standard GEMM implementation |
| `kernels/mxfp4-mm/submission_tritonblas_fused.py` | WIP fused kernel (264 lines, has bugs) |
| `kernels/mxfp4-mm/task.yml` | All test/benchmark shapes and aiter reference times |
| `kernels/moe-mxfp4/submission.py` | Current best MoE (expert-count-aware KSPLIT) |
| `kernels/mixed-mla/submission.py` | Current best MLA (torch-native hybrid) |

---

## Gotchas

1. **Don't use `uv run`** in this directory — it will overwrite the ROCm torch install with CUDA torch from the project lockfile.

2. **JIT build times eat into the 12-min timeout.** First submission for each kernel type takes ~4 min just for JIT compilation. Plan accordingly.

3. **`--mode test` output includes STDERR** — this is your primary debugging channel. Always start with test mode.

4. **Transient failures look like real failures.** If a kernel that previously passed suddenly fails, retry before debugging.

5. **The eval harness clears L2 cache between benchmark runs** (`clear_l2_cache_large()`), so cache warming tricks don't help.

6. **`submission.py` is the only file that gets uploaded.** Your kernel must be self-contained in that single file (plus imports from the remote environment).

Good luck! The 9.7 us GEMM leader is the white whale. Fusing the quantization into the GEMM kernel (or finding a faster quant path) is the key.
