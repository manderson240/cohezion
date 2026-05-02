# Custom Triton MoE Kernel Specification

**Created:** 2026-03-20
**Status:** READY FOR IMPLEMENTATION
**Task:** Replace aiter.fused_moe with a custom Triton kernel using persistent tiles + fused permutation

---

## 1. Problem Statement

aiter's `fused_moe` sits at ~155µs (geomean over 7 benchmark shapes); leader is 145µs (1.07x gap).
All Python-level knobs on `fused_moe` are exhausted. The hypothesis for closing the gap:

1. **Persistent tile scheduling** — avoid per-expert kernel launch overhead
2. **Fused token permutation** — eliminate separate `moe_sorting_fwd` call + memory round-trip
3. **Native MXFP4 via `tl.dot_scaled`** — hardware-accelerated FP4 GEMM on MI355X gfx950

The approach is inspired by Unsloth's grouped GEMM MoE kernel (AGPL-3.0 — study only, no copying).

---

## 2. Exact Competition Interface

### Input tuple (12 elements)

```python
input_t = tuple of:
  [0]  hidden_states              [M, d_hidden]                         bf16
  [1]  gate_up_weight             [E, 2*d_expert_pad, d_hidden_pad//2]  fp4x2  (raw, UN-shuffled)
  [2]  down_weight                [E, d_hidden_pad, d_expert_pad//2]    fp4x2  (raw, UN-shuffled)
  [3]  gate_up_weight_scale       [E, 2*d_expert_pad, scale_K]          e8m0   (raw, UN-shuffled)
  [4]  down_weight_scale          [E, d_hidden_pad, scale_K]            e8m0   (raw, UN-shuffled)
  [5]  gate_up_weight_shuffled    [E, 2*d_expert_pad, d_hidden_pad//2]  fp4x2  (pre-shuffled for CK)
  [6]  down_weight_shuffled       [E, d_hidden_pad, d_expert_pad//2]    fp4x2  (pre-shuffled for CK)
  [7]  gate_up_weight_scale_shuffled  [padded, flat]                    e8m0   (pre-shuffled for CK)
  [8]  down_weight_scale_shuffled     [padded, flat]                    e8m0   (pre-shuffled for CK)
  [9]  topk_weights               [M, total_top_k]                      float32
  [10] topk_ids                   [M, total_top_k]                      int32
  [11] config                     dict with keys:
         d_hidden, d_expert, d_hidden_pad, d_expert_pad,
         n_routed_experts, n_shared_experts, n_experts_per_token,
         total_top_k, bs
```

### Output

```python
output: [M, d_hidden] bf16
```

### Key computed values

```python
M          = hidden_states.shape[0]        # number of tokens
E          = gate_up_weight.shape[0]       # total experts (routed + shared)
top_k      = topk_ids.shape[1]             # tokens per expert assignment
d_hidden   = config["d_hidden"]            # e.g. 4096 or 7168
d_expert   = config["d_expert"]            # e.g. 256, 512, 1536, 2048
d_hidden_pad  = config["d_hidden_pad"]     # padded to 256-align
d_expert_pad  = config["d_expert_pad"]     # padded to 256-align
hidden_pad    = d_hidden_pad - d_hidden
intermediate_pad = d_expert_pad - d_expert
```

### Benchmark shapes (March 2026, subject to change)

| E (total) | n_routed | d_expert | bs  | top_k | d_hidden |
|-----------|----------|----------|-----|-------|----------|
| 257       | 256      | 256      | 16  | 9     | 4096     |
| 257       | 256      | 256      | 128 | 9     | 4096     |
| 257       | 256      | 256      | 512 | 9     | 4096     |
| 33        | 32       | 512      | 16  | 9     | 7168     |
| 33        | 32       | 512      | 128 | 9     | 7168     |
| 33        | 32       | 512      | 512 | 9     | 7168     |
| 33        | 32       | 2048     | 512 | 9     | 7168     |

---

## 3. aiter fused_moe Dispatch Flow (What We Are Replacing)

Understanding the aiter pipeline enables targeted replacement.

### 3.1 fused_moe Python wrapper

```
fused_moe(hidden_states, w1_shuffled, w2_shuffled, topk_weights, topk_ids, ...)
  ├── Compute: estimated_m = topk_ids.numel() // num_experts
  ├── Lookup: CSV config (dsv3_fp4_tuned_fmoe.csv) — competition shapes have ZERO matches
  ├── Heuristic path (always taken for competition shapes):
  │     ksplit = env["AITER_KSPLIT"] if set (default 0)
  │     block_m = auto-selected (32 for small bs, 64 for larger)
  ├── Allocate: sorted_token_ids, sorted_weights, sorted_expert_ids, num_valid_ids, moe_buf
  ├── Call: moe_sorting_fwd(topk_ids, topk_weights, → sorted outputs, num_experts, block_m)
  └── Branch:
        KSPLIT=0 (CK path):
          Call: ck_moe_stage1(hidden_states, w1, w2, sorted_token_ids,
                              sorted_expert_ids, num_valid_ids, out, topk,
                              w1_scale, is_shuffled=True, quant_type=0, activation=0, splitk=1)
          → output [M, top_k, N] bf16 (SiLU already fused)
          Call: ck_moe_stage2(out, w2, sorted_token_ids, topk_weights, ...)
          → output [M, d_hidden] bf16

        KSPLIT>0 (cktile path):
          Call: moe_cktile2stages_gemm1(hidden_q, w1, out, sorted_ids, ...)
          If split_k>0: Call silu_and_mul(out, tmp)
          Call: fused_dynamic_mxfp4_quant_moe_sort(intermediate, sorted_ids, ...)
          Call: moe_cktile2stages_gemm2(intermediate_q, w2, out, sorted_ids, ...)
```

### 3.2 moe_sorting_fwd outputs

```python
moe_sorting_fwd(
    topk_ids,           # [M, top_k] int32  — expert IDs per token
    topk_weights,       # [M, top_k] float32
    sorted_token_ids,   # OUTPUT: [E * block_m] int32 — token positions in expert-sorted order
    sorted_weights,     # OUTPUT: [E * block_m] float32 — weights in expert-sorted order
    sorted_expert_ids,  # OUTPUT: [ceil(E*block_m / block_m)] int32 — expert ID per tile
    num_valid_ids,      # OUTPUT: [1] int32 — total non-padding token slots
    moe_buf,            # workspace [M * top_k + E * block_m + 1] int32 (estimated)
    num_experts,        # int
    unit_size,          # int (= block_m, tile size in M dimension)
    local_expert_mask=None,  # Optional[Tensor] — EP-mode masking (DO NOT USE)
    num_local_tokens=None,
    dispatch_policy=0,
)
```

**sorted_token_ids** (`[E * block_m]`): Each expert gets `block_m` slots. Position `i` contains:
- A valid token index (0..M*top_k-1) if a token was routed to this slot
- A padding value (>= M*top_k) if the slot is empty

**sorted_expert_ids** (`[ceil(E*block_m / block_m)]`): One entry per tile (one tile = block_m rows).
Entry `t` is the expert ID for that tile. Length = `ceil((E * block_m) / block_m) = E`.

**num_valid_ids** (`[1]`): Total count of NON-padding entries in sorted_token_ids.
The CK kernel uses this to avoid processing empty tail tiles.

**Key property**: This is a compact sorted permutation. Token `j` routed to expert `e` appears
in `sorted_token_ids[e * block_m + offset]` for some offset < block_m.

### 3.3 What Python overhead we can eliminate

The key overhead in fused_moe's Python dispatch (per call):
- moe_sorting_fwd itself: ~5-10µs (separate kernel launch + small tensors)
- Python wrapper logic: ~2-3µs (shape inference, alloc, env var checks)
- Two separate kernel launches (stage1 + stage2): ~2µs launch overhead each

A fused Triton kernel eliminates sorting as a separate pass and fuses it into the load phase.

---

## 4. Weight Tensor Layout for Triton (Raw Path)

The custom Triton kernel uses the **raw (un-shuffled)** weights from inputs [1]-[4],
NOT the pre-shuffled variants [5]-[8] (which are formatted for CK hardware tiles).

### gate_up_weight (raw): `[E, 2*d_expert_pad, d_hidden_pad//2]` fp4x2

- Dtype on disk: `torch.float4_e2m1fn_x2` (2 fp4 values packed per byte)
- For Triton: view as `torch.uint8` → shape `[E, 2*d_expert_pad, d_hidden_pad//2]`
- Each uint8 holds 2 fp4 values: high nibble = fp4[0], low nibble = fp4[1]
- Row-major layout: last dim is K (hidden), second dim is N (expert intermediate)
- First half (`[:, :d_expert_pad, :]`) is gate weights; second half is up weights

### down_weight (raw): `[E, d_hidden_pad, d_expert_pad//2]` fp4x2

- Similar packing: view as `torch.uint8`
- Shape after view: `[E, d_hidden_pad, d_expert_pad//2]`
- Row-major: last dim is K (expert intermediate), second dim is N (hidden output)

### gate_up_weight_scale (raw): `[E, 2*d_expert_pad, scale_K]` e8m0

- `scale_K = ceil(d_hidden_pad / 32)` — one scale per 32 fp4 elements along K
- Dtype: `torch.float8_e8m0fnu` → view as `torch.uint8` for Triton
- Layout: `[E, N_rows, K_scales]` where N_rows=2*d_expert_pad, K_scales=d_hidden_pad//32

### How to recover un-shuffled scales from shuffled inputs (CRITICAL)

The competition provides pre-shuffled scales `w1ssh` / `w2ssh` but NOT raw scales directly
in a Triton-compatible layout. However raw scales ARE available as `w1s` / `w2s` (inputs [3],[4]).

**Triton-compatible scale layout** for `tl.dot_scaled`:
- A-scale (activation): `[M_tokens, K//32]` uint8
- B-scale (weight): `[N_rows, K//32]` uint8 — N-first (NOT transposed)

The raw `gate_up_weight_scale [E, 2*d_expert_pad, scale_K]` is already in this layout per-expert.
For expert `e`, slice `[e, :, :]` gives `[2*d_expert_pad, scale_K]` uint8 → correct B-scale layout.

---

## 5. Token Permutation Data Flow (Fused Approach)

The key innovation over aiter: fuse sorting INTO the kernel load phase.

### 5.1 Pre-computation (Python, before kernel launch)

```python
# Flatten topk_ids to [M * top_k] — token-expert pairs
flat_ids = topk_ids.view(-1)       # [M * top_k] int32
flat_weights = topk_weights.view(-1)  # [M * top_k] float32

# For each token-expert pair j, flat_ids[j] is the expert, j//top_k is the original token

# Sort by expert ID to group tokens per expert
sort_order = torch.argsort(flat_ids)   # [M * top_k] int64 — indices into flat_ids
sorted_experts = flat_ids[sort_order]  # [M * top_k] int32 — expert IDs, sorted
sorted_token_pos = (sort_order // top_k).to(torch.int32)  # original token index per sorted slot
sorted_weights_flat = flat_weights[sort_order]  # [M * top_k] float32

# Count tokens per expert
tokens_per_expert = torch.bincount(flat_ids, minlength=E).to(torch.int32)  # [E]
expert_offsets = torch.zeros(E+1, dtype=torch.int32, device=device)
expert_offsets[1:] = tokens_per_expert.cumsum(0)  # [E+1] start offset per expert
```

This Python-side sorting replaces `moe_sorting_fwd`. The kernel receives:
- `sorted_token_pos [M*top_k]`: position in original `hidden_states` for each sorted slot
- `sorted_weights_flat [M*top_k]`: topk weight for each sorted slot
- `expert_offsets [E+1]`: start/end positions in sorted arrays per expert

### 5.2 In-kernel gather (PERMUTE_X pattern)

For expert `e` processing tokens `[expert_offsets[e] : expert_offsets[e+1]]`:
```triton
# Gather token from original hidden_states using sorted_token_pos
orig_pos = tl.load(sorted_token_pos_ptr + sort_idx)  # scalar: original token index
x = tl.load(hidden_states_ptr + orig_pos * stride_hs_m + k_offs * stride_hs_k)
```

This eliminates a full scatter/gather pass — tokens are read in expert-sorted order directly.

### 5.3 Store with weight fusion (PERMUTE_Y pattern)

After computing expert output `y [block_m, d_hidden]`:
```triton
# Scatter back to original output positions with topk_weight multiplication
weight = tl.load(sorted_weights_ptr + sort_idx)  # topk weight for this slot
# Atomic add back to output (or use sorted order + reduction pass)
tl.atomic_add(out_ptr + orig_pos * stride_out_m + n_offs, y * weight[:, None])
```

**Note**: Atomic adds are required because multiple experts write to the same output token.
This is the key complexity vs aiter's approach (which uses a separate reduce pass).

---

## 6. Persistent Tile Scheduling (Kernel Architecture)

### 6.1 Stage 1: gate+up projection (gate_up_weight, d_hidden → d_expert)

One kernel walk for ALL experts:

```python
# Grid: (num_sms,) — one program per SM, persistent scheduling
# Each SM walks: expert 0 tiles, expert 1 tiles, ..., expert E-1 tiles

@triton.jit
def moe_stage1_kernel(
    hidden_states_ptr,     # [M, d_hidden] bf16
    gate_up_weight_ptr,    # [E, 2*d_expert_pad, d_hidden_pad//2] uint8 (fp4x2)
    gate_up_scale_ptr,     # [E, 2*d_expert_pad, scale_K] uint8 (e8m0)
    sorted_token_pos_ptr,  # [M*top_k] int32
    expert_offsets_ptr,    # [E+1] int32
    out_ptr,               # [M*top_k, 2*d_expert_pad] bf16  (intermediate, gate+up interleaved)
    M, E, d_hidden_half, d_expert_pad, top_k,
    stride_hs_m, stride_hs_k,
    stride_w1_e, stride_w1_n, stride_w1_k,
    stride_ws1_e, stride_ws1_n, stride_ws1_k,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,   # 64 or 128 (min 16 for tl.dot_scaled)
    BLOCK_N: tl.constexpr,   # 64 or 128
    BLOCK_K: tl.constexpr,   # 64 (minimum for gfx950 tl.dot_scaled)
):
    sm_id = tl.program_id(0)
    num_sms = tl.num_programs(0)

    # Compute total tiles across all experts
    # Each expert e has tokens_e = expert_offsets[e+1] - expert_offsets[e]
    # Tiles for expert e = ceil(tokens_e / BLOCK_M) * ceil(2*d_expert_pad / BLOCK_N)
    # Persistent: SM iterates over all tiles globally

    tile_id = sm_id  # start tile for this SM
    while tile_id < total_tiles:
        # Decode tile_id → (expert_id, tile_m, tile_n)
        # ... (see §6.3 for tile mapping)
        e, tile_m, tile_n = decode_tile(tile_id, expert_offsets, d_expert_pad, BLOCK_M, BLOCK_N)

        # Gather tokens for this tile
        token_start = expert_offsets[e] + tile_m * BLOCK_M
        token_end = min(token_start + BLOCK_M, expert_offsets[e+1])
        m_size = token_end - token_start

        # Load activation tile (gather from hidden_states)
        # A: [BLOCK_M, d_hidden_half] uint8 (fp4x2) — must quantize here
        # ... (activation quantization OR pass bf16 and use bf16 tl.dot)

        # Load weight tile (from gate_up_weight[e])
        n_start = tile_n * BLOCK_N
        # B: [d_hidden_half, BLOCK_N] uint8 (fp4x2) — transposed for K-major access

        # GEMM tile
        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        for k in range(0, d_hidden_half, BLOCK_K):
            a = tl.load(...)  # [BLOCK_M, BLOCK_K] uint8
            b = tl.load(...)  # [BLOCK_K, BLOCK_N] uint8
            a_scale = tl.load(...)  # [BLOCK_M, BLOCK_K//16] uint8
            b_scale = tl.load(...)  # [BLOCK_N, BLOCK_K//16] uint8  (N-first!)
            acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)

        # Store to intermediate buffer
        out_offs = ...
        tl.store(out_ptr + out_offs, acc.to(tl.bfloat16), mask=...)

        tile_id += num_sms  # persistent: claim next tile
```

### 6.2 Stage 1.5: SiLU + multiply (fused into Stage 1 or separate)

After Stage 1 GEMM, intermediate is `[M*top_k, 2*d_expert_pad]` bf16.
Split into gate half and up half, apply SiLU + multiply:

```triton
# In-kernel fusion (preferred):
gate = acc[:, :d_expert_pad]
up   = acc[:, d_expert_pad:]
intermediate = tl.sigmoid(gate) * gate * up  # SiLU(gate) * up
```

Or call `aiter.silu_and_mul(out, tmp)` as a separate kernel (adds ~2µs).

### 6.3 Stage 2: down projection (down_weight, d_expert → d_hidden)

Same persistent structure over `down_weight [E, d_hidden_pad, d_expert_pad//2]`.

Input: intermediate (after SiLU) `[M*top_k, d_expert_pad]` bf16 or fp4x2 (if requantized).
Output: `[M, d_hidden]` bf16 with topk_weight multiplication + atomic accumulation.

Key difference: **must atomic-add outputs** because multiple experts contribute to each token.

```triton
# After computing expert output [BLOCK_M, d_hidden]:
weight = tl.load(sorted_weights_ptr + sort_idx)  # [BLOCK_M] float32

# Option A: atomic add (correct but may serialize)
result = acc.to(tl.bfloat16) * weight[:, None]
tl.atomic_add(out_ptr + orig_pos_offs, result)

# Option B: write to intermediate [M*top_k, d_hidden] then reduce
# (avoids atomics, adds one more pass but enables better memory patterns)
```

---

## 7. tl.dot_scaled: MXFP4 Hardware Constraints (gfx950)

**CRITICAL**: These constraints cause silent wrong results or GPU assertion failures if violated.

### 7.1 Minimum tile sizes (MANDATORY)

| Constraint | Value | Violation |
|------------|-------|-----------|
| BLOCK_M minimum | 16 | Silent wrong results (no error) |
| BLOCK_K minimum | 64 (packed uint8 bytes) | `Assertion 'inputVals.size() % 4 == 0'` |
| BLOCK_N | >= 32 (power of 2) | Not documented but use >= 64 for perf |

```python
BLOCK_M = max(16, ...)   # MANDATORY minimum 16
BLOCK_K = 64             # MANDATORY minimum 64
BLOCK_N = 64             # recommended
```

### 7.2 Scale tensor layout

```python
# LHS (A activation) scale: [BLOCK_M, SCALE_PER_BLOCK]
SCALE_PER_BLOCK = BLOCK_K // 16   # = 4 for BLOCK_K=64

# RHS (B weight) scale: [BLOCK_N, SCALE_PER_BLOCK]  -- N-FIRST, not K-first
# Even though B data is [K//2, N], scale is [N, K//32] -- original N-first layout

# Load scales per tile:
scale_k_start = k_tile_start // 16
a_scale = tl.load(A_scale_ptr + m_offs[:, None] * stride_as_m + (scale_k_start + tl.arange(0, SCALE_PER_BLOCK))[None, :])
b_scale = tl.load(B_scale_ptr + n_offs[:, None] * stride_bs_n + (scale_k_start + tl.arange(0, SCALE_PER_BLOCK))[None, :])

# Accumulate:
acc = tl.dot_scaled(a, a_scale, "e2m1", b, b_scale, "e2m1", acc=acc)
```

### 7.3 CRITICAL: float4_e2m1fn_x2 KeyError blocker

`KeyError: 'float4_e2m1fn_x2'` fires in Triton's JIT when ANY tensor with dtype
`torch.float4_e2m1fn_x2` is passed to a kernel. This is a **permanent blocker on Popcorn CLI runners**.

**Workaround (MANDATORY)**:
```python
# WRONG — Triton JIT rejects this dtype:
gate_up_weight.view(torch.float4_e2m1fn_x2)

# CORRECT — view as uint8 before passing to kernel:
gate_up_weight_u8 = gate_up_weight.view(torch.uint8)  # safe
gate_up_weight_scale_u8 = gate_up_weight_scale.view(torch.uint8)  # safe

# Inside kernel, tl.dot_scaled interprets uint8 as packed fp4 via "e2m1" format string
# This works correctly — the "e2m1" string tells the hardware how to interpret the bytes
```

### 7.4 Activation quantization for tl.dot_scaled

Activations (bf16) must be quantized to fp4x2 for Stage 1 input. Options:

**Option A (fused in-kernel, preferred)**: Quantize bf16 activations inline.
Use `tl.float_to_int` or custom fp4 quantization within the kernel.
This is the "fused quant+GEMM" that eliminates a separate kernel launch.

**Option B (pre-quantize, simpler)**: Use `aiter.ops.triton.quant.dynamic_mxfp4_quant` before kernel.
```python
from aiter.ops.triton.quant import dynamic_mxfp4_quant
x_fp4, x_scale = dynamic_mxfp4_quant(hidden_states.contiguous())
x_u8 = x_fp4.view(torch.uint8)     # [M, d_hidden//2] uint8
x_scale_u8 = x_scale.view(torch.uint8)  # [M, d_hidden//32] uint8
```

**WARNING**: Pre-quantizing and passing pre-quantized activations into fused_moe via `a1_scale`
was tested (contingency probe) and showed NO performance benefit. Option A (fused) is the
novel path not yet tried.

---

## 8. XCD Remapping (Tile Scheduling for MI355X)

MI355X has 8 XCDs (compute dies). XCD-aware tile ordering improves L2 cache reuse.

### 8.1 CRITICAL BUG: Origami XCD remapping with cdiv

The XCD remapping from `tritonblas.fp4_matmul` contains a **silent correctness bug**
when `total_tiles % 8 != 0`. Tiles are computed twice / never reached. **DO NOT USE**.

```python
# BUGGY (from tritonblas) — silent wrong results when total_tiles % 8 != 0:
remapped_chunk = xcd_id * tl.cdiv(num_chunks, NUM_XCDS) + chunk_in_xcd  # NON-BIJECTIVE
```

### 8.2 Safe alternative: group-M swizzle (RECOMMENDED)

```python
NUM_XCDS: tl.constexpr = 8
GROUP_SIZE_M: tl.constexpr = 8  # = NUM_XCDS for XCD alignment

pid = tl.program_id(0)
num_pid_m = tl.cdiv(m_tiles_for_expert, BLOCK_M)
num_pid_n = tl.cdiv(n_tiles_for_expert, BLOCK_N)
num_pid_in_group = GROUP_SIZE_M * num_pid_n
group_id = pid // num_pid_in_group
first_pid_m = group_id * GROUP_SIZE_M
group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
pid_m = first_pid_m + (pid % group_size_m)
pid_n = (pid % num_pid_in_group) // group_size_m
```

### 8.3 Correct XCD remapping (if XCD locality is essential)

If XCD remapping is needed, use floor division (not cdiv) to ensure bijection:
```python
tiles_per_xcd = total_tiles // NUM_XCDS  # floor
remainder = total_tiles % NUM_XCDS
xcd_id = pid % NUM_XCDS
chunk_in_xcd = pid // NUM_XCDS
if xcd_id < remainder:
    remapped = xcd_id * (tiles_per_xcd + 1) + chunk_in_xcd
else:
    remapped = remainder * (tiles_per_xcd + 1) + (xcd_id - remainder) * tiles_per_xcd + chunk_in_xcd
```

---

## 9. Autotune Config Space

Recommended autotune search space for MI355X gfx950:

```python
@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk},
                      num_warps=nw, num_stages=ns)
        for bm in [16, 32, 64, 128]
        for bn in [64, 128, 256]
        for bk in [64, 128]          # min 64 for tl.dot_scaled
        for nw in [4, 8]
        for ns in [2, 3, 4]
    ],
    key=["M", "E", "d_hidden", "d_expert"],
)
```

**Note**: BLOCK_M=16 is the minimum for gfx950 `tl.dot_scaled`. Use `max(16, ...)` in practice.

---

## 10. Key Constraints and Dead Ends

### HARD CONSTRAINTS (violations = crashes or wrong results)

| Constraint | Value | Why |
|------------|-------|-----|
| `doweight_stage1=True` | NEVER | GPU crash (cktile) or 82% mismatch (CK) |
| `expert_mask=bincount` | NEVER | cumsum -1 IDs → uint32(4.3B) → GPU fault |
| `tl.dot_scaled` dtype | Use `"e2m1"` string, NOT torch dtype | float4_e2m1fn_x2 KeyError |
| BLOCK_M | >= 16 | Silent wrong results on gfx950 |
| BLOCK_K | >= 64 (packed bytes) | GPU assertion failure |
| KSPLIT=4 for 32-expert | NEVER | K/4=128 below cktile minimum → ~1e27 overflow |
| XCD remapping with cdiv | NEVER | Non-bijective → zeros in output |
| Origami scheduling | Avoid | Only safe if total_tiles % 8 == 0 |

### CONFIRMED DEAD ENDS (do NOT retry)

| Approach | Status | Root Cause |
|----------|--------|------------|
| `fmoe_g1u1` | DEAD | NaN for 32-expert shapes; no gain for 256-expert |
| Direct CK dispatch | DEAD | Replicates fused_moe overhead |
| `torch.compile(fused_moe)` | DEAD | auto_functionalized_v2 on ROCm 7.1 |
| `AITER_BYPASS_TUNE_CONFIG` | DEAD CODE | Competition shapes have zero CSV matches |
| Custom Triton MoE (without fused permute) | 68% slower | Previous attempt didn't use fused permutation or tl.dot_scaled |
| `AITER_USE_OPUS_MOE_SORTING` | No effect | Not wired into fp4x2 code path |
| `block_size_M` override | GPU fault | Exceeds data bounds for small bs |

### WHAT IS NOVEL (not previously attempted)

1. **Fused token permutation** — eliminate `moe_sorting_fwd` as separate kernel
2. **`tl.dot_scaled` with `"e2m1"` string** (not dtype) — hardware MXFP4 GEMM
3. **Persistent tiles over ALL experts** — single kernel launch for all E experts
4. **Fused SiLU in Stage 1** — no separate `silu_and_mul` call
5. **Inline activation quantization** — fuse fp4 quant into Stage 1 GEMM

---

## 11. Recommended Implementation Path

### Phase 1: Correctness (bf16 GEMM, no fused permute)

Start with bf16 (not fp4) to validate the persistent tile loop and permutation logic:
1. Sort tokens per expert in Python (§5.1)
2. Implement Stage 1 kernel: persistent tiles, gather from sorted_token_pos, bf16 matmul
3. Fuse SiLU+multiply
4. Implement Stage 2: persistent tiles, atomic-add with topk_weight
5. Verify correctness vs reference (rtol=2e-2, atol=2e-2)

### Phase 2: MXFP4 acceleration

Replace bf16 matmul with `tl.dot_scaled`:
1. View fp4x2 weights as uint8 before kernel call
2. Pre-quantize activations via `dynamic_mxfp4_quant` → uint8 view
3. Pass scales as uint8, load per-tile with N-first layout for B-scale
4. Use BLOCK_K=64 minimum

### Phase 3: Performance tuning

1. Autotune BLOCK_M/N/K
2. Try inline activation quantization (fuse Stage 1 quant)
3. Try group-M swizzle scheduling
4. Profile with `torch.cuda.nvtx` to identify bottleneck

### Phase 4: Risk mitigation fallback

If custom Triton is slower than ~155µs, fall back to `aiter.fused_moe` as a baseline.
The submission structure should support:
```python
if USE_CUSTOM_KERNEL:
    return custom_triton_moe(...)
else:
    return fm(hs, w1sh, w2sh, ...)  # aiter fallback
```

---

## 12. Expected Performance Analysis

| Source | Latency | Notes |
|--------|---------|-------|
| aiter fused_moe (current) | ~155µs geomean | Baseline |
| Leader | ~145µs | Target |
| Custom Triton (previous, no fused permute) | ~250µs | 68% slower — dead end |
| Custom Triton (with fused permute + tl.dot_scaled) | ??? | Novel path |

Expected savings from the novel approach:
- Fused permutation: -5-10µs (eliminates `moe_sorting_fwd` kernel)
- Persistent scheduling: -2-5µs (fewer kernel launches)
- Native MXFP4 via tl.dot_scaled: hardware-accelerated, potentially faster for small tiles

Risk: Previous custom Triton was 68% slower than CK ASM. The new approach differs in:
(a) fused permutation (not tried before), (b) tl.dot_scaled (not tried before),
(c) persistent-tile scheduling (not tried before). Combined effect is unknown.

---

## 13. Code Skeleton (Implementation Starting Point)

```python
# research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/submission.py
import os, torch, triton, triton.language as tl
from task import input_t, output_t
from aiter.ops.triton.quant import dynamic_mxfp4_quant

os.environ["AITER_USE_NT"] = "1"

# ── Stage 1 kernel: hidden × gate_up_weight → intermediate (gate+up) ──────────
@triton.autotune(configs=[...], key=["M", "E", "d_hidden", "d_expert"])
@triton.jit
def _moe_stage1_kernel(
    hidden_ptr, w1_ptr, w1_scale_ptr,
    sorted_pos_ptr, expert_offsets_ptr,
    out_ptr,
    M, E: tl.constexpr, d_hidden_half, d_expert_pad,
    # strides...
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16
    sm_id = tl.program_id(0)
    num_sms = tl.num_programs(0)
    # persistent tile loop...

# ── Stage 2 kernel: intermediate × down_weight → output (with atomic add) ─────
@triton.autotune(configs=[...], key=["M", "E", "d_hidden", "d_expert"])
@triton.jit
def _moe_stage2_kernel(
    intermediate_ptr, w2_ptr, w2_scale_ptr,
    sorted_pos_ptr, sorted_weights_ptr, expert_offsets_ptr,
    out_ptr,
    M, E: tl.constexpr, d_expert_pad, d_hidden,
    # strides...
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    SCALE_PER_BLOCK: tl.constexpr = BLOCK_K // 16
    sm_id = tl.program_id(0)
    # persistent tile loop with atomic_add...

def custom_kernel(data: input_t) -> output_t:
    (hs, w1, w2, w1s, w2s, w1sh, w2sh, w1ssh, w2ssh, tw, ti, cfg) = data

    M, d_hidden = hs.shape
    E = w1.shape[0]
    d_expert_pad = cfg["d_expert_pad"]
    top_k = ti.shape[1]

    # Pre-sort tokens by expert (replaces moe_sorting_fwd)
    flat_ids = ti.view(-1).long()
    flat_w = tw.view(-1)
    sort_order = torch.argsort(flat_ids)
    sorted_experts = flat_ids[sort_order].to(torch.int32)
    sorted_pos = (sort_order // top_k).to(torch.int32)  # original token index
    sorted_weights = flat_w[sort_order]
    tokens_per_expert = torch.bincount(ti.view(-1).long(), minlength=E).to(torch.int32)
    expert_offsets = torch.zeros(E+1, dtype=torch.int32, device=hs.device)
    expert_offsets[1:] = tokens_per_expert.cumsum(0)

    # Pre-quantize activations (Option B — simplest)
    # For Option A (in-kernel quant), skip this step
    x_fp4, x_scale = dynamic_mxfp4_quant(hs.contiguous())
    x_u8 = x_fp4.view(torch.uint8)
    x_scale_u8 = x_scale.view(torch.uint8)

    # View weights as uint8 (required — float4_e2m1fn_x2 KeyError workaround)
    w1_u8 = w1.view(torch.uint8)       # [E, 2*d_expert_pad, d_hidden_pad//2]
    w1s_u8 = w1s.view(torch.uint8)     # [E, 2*d_expert_pad, scale_K]
    w2_u8 = w2.view(torch.uint8)       # [E, d_hidden_pad, d_expert_pad//2]
    w2s_u8 = w2s.view(torch.uint8)     # [E, d_hidden_pad, scale_K]

    # Allocate intermediates
    intermediate = torch.zeros(M * top_k, 2 * d_expert_pad, dtype=torch.bfloat16, device=hs.device)
    output = torch.zeros(M, d_hidden, dtype=torch.bfloat16, device=hs.device)

    # Launch Stage 1
    num_sms = torch.cuda.get_device_properties(0).multi_processor_count
    _moe_stage1_kernel[(num_sms,)](
        x_u8, w1_u8, w1s_u8,
        sorted_pos, expert_offsets,
        intermediate,
        M, E, ...
    )

    # Apply SiLU + multiply (fuse into stage1 or separate)
    gate = intermediate[:, :d_expert_pad]
    up = intermediate[:, d_expert_pad:]
    intermediate_silu = torch.nn.functional.silu(gate) * up  # [M*top_k, d_expert_pad]

    # Re-quantize for Stage 2 (or keep bf16)
    # ...

    # Launch Stage 2
    _moe_stage2_kernel[(num_sms,)](
        intermediate_silu, w2_u8, w2s_u8,
        sorted_pos, sorted_weights, expert_offsets,
        output,
        M, E, ...
    )

    return output
```

---

## 14. Files to Read Before Implementing

| File | Relevance |
|------|-----------|
| `kernels/moe-mxfp4/reference.py` | Competition interface (ground truth) |
| `.claude/skills/amd-gfx950-tl-dot-scaled-constraints/SKILL.md` | tl.dot_scaled scale layout + min tile sizes |
| `.claude/skills/tritonblas-origami-xcd-remapping-bug/SKILL.md` | XCD remapping bug — avoid cdiv pattern |
| `.claude/skills/amd-moe-mxfp4-optimization/SKILL.md` | All dead ends and working patterns |
| `.claude/skills/aiter-kernel-parameter-semantics/SKILL.md` | KSPLIT semantics, overflow conditions |
| `.claude/skills/aiter-mxfp4-api-limitations/SKILL.md` | Limitation 11: e8m0_unshuffle for scale recovery |
| `autoresearch/research_strategy.md` | Current focus and dead ends |
