# Probe: MoE Inter-Stage Fusion Opportunities

## Summary

**Status:** MoE closest to leader (1.4x gap: 154µs vs 109.8µs)
**Opportunity:** Fuse Gate+Up + SiLU + Down into single kernel
**Potential Gain:** Eliminate intermediate activation writeback (~30-50µs)
**Challenge:** Need custom CK/HipKittens kernel; fmoe_g1u1 is dead end

---

## Current Reference Implementation

### aiter fused_moe Pipeline

```python
# Current best: aiter.fused_moe with adaptive KSPLIT

output = aiter.fused_moe(
    hidden_states,           # [M, d_hidden] bf16
    gate_up_weight_shuffled, # [E, 2*d_expert_pad, d_hidden_pad//2] fp4x2
    down_weight_shuffled,    # [E, d_hidden_pad, d_expert_pad//2] fp4x2
    topk_weights,            # [M, total_top_k] float32
    topk_ids,                # [M, total_top_k] int32
    expert_mask=None,
    activation=ActivationType.Silu,
    quant_type=QuantType.per_1x32,  # MXFP4
    doweight_stage1=False,   # MUST be False (crashes if True)
    w1_scale=gate_up_weight_scale_shuffled,
    w2_scale=down_weight_scale_shuffled,
    hidden_pad=hidden_pad,
    intermediate_pad=intermediate_pad,
)

# Internal flow:
# 1. moe_sorting_fwd: token→expert dispatch
# 2. ck_moe_stage1: Gate+Up GEMM (fused with SiLU in cktile path)
# 3. ck_moe_stage2: Down GEMM + weight application
```

### Performance Breakdown

```
Typical MoE shape (bs=128, 257 experts, dexp=256, topk=9):
- Sorting:           ~15-25µs
- Stage 1 (Gate+Up): ~60-80µs
- Stage 2 (Down):    ~50-70µs
- Total:             ~154µs

Leader: ~109.8µs
Gap to close: ~44µs (28%)
```

---

## Inter-Stage Fusion Analysis

### What's Being Written to Global Memory

```python
# After Stage 1 (Gate+Up), before Stage 2 (Down):
intermediate = SiLU(gate_out) * up_out  # [M*topk, d_expert] bf16

# This is written to HBM, then read back in Stage 2
# For bs=128, topk=9, dexp=256:
# Size: 128 * 9 * 256 * 2 bytes = 589,824 bytes ~ 0.56 MB per batch

# Bandwidth cost:
# Write: 0.56 MB
# Read:  0.56 MB
# Total: 1.12 MB @ ~1.5 TB/s = ~0.7µs (negligible at this scale)
```

**Reality:** The intermediate size is small. The bigger cost is:
1. Kernel launch overhead (2 separate kernel launches)
2. Work distribution overhead (twice the dispatch)
3. L2 cache pollution between stages

### Fusion Target

**Goal:** Single kernel that does:
```python
# For each token assigned to each expert:
# 1. Load hidden state (bf16)
# 2. Load Gate+Up weights (MXFP4)
# 3. GEMM → dequantize to bf16
# 4. SiLU on gate portion
# 5. Multiply gate * up (in registers)
# 6. Load Down weights (MXFP4)
# 7. GEMM → dequantize to bf16
# 8. Write output (accumulate across experts with topk_weights)
```

**Potential savings:**
- Eliminate one kernel launch (~10-20µs Python overhead)
- Keep intermediate in registers/LDS (no HBM round-trip)
- Better L2 locality (weights loaded once)

---

## Implementation Paths

### Path 1: HipKittens 2-Stage Fusion

**Advantages:**
- HipKittens beats aiter hand-ASM on MI355X
- Tile-based DSL handles complex fusion patterns
- 8-Wave Ping-Pong scheduling

**Prototype structure:**
```python
import hipkittens as hk

@hk.kernel
def fused_moe_2stage(
    hidden: hk.Tensor[M, d_hidden],           # bf16
    topk_ids: hk.Tensor[M, topk],
    topk_weights: hk.Tensor[M, topk],
    w1: hk.Tensor[E, 2*d_expert, d_hidden//2],  # fp4x2
    w1_scale: hk.Tensor[E, 2*d_expert, d_hidden//32],  # e8m0
    w2: hk.Tensor[E, d_hidden, d_expert//2],  # fp4x2
    w2_scale: hk.Tensor[E, d_hidden, d_expert//32],  # e8m0
    output: hk.Tensor[M, d_hidden],
):
    # Per-token work distribution
    for m in range(M):
        accum = hk.zeros(d_hidden)

        for k in range(topk):
            eid = topk_ids[m, k]
            weight = topk_weights[m, k]

            # Load hidden for this token
            x = hidden[m]  # [d_hidden]

            # Stage 1: Gate+Up (in LDS)
            # Tile through d_expert dimension
            for n1 in range(0, 2*d_expert, TILE_N1):
                w1_tile = hk.load(w1, (eid, n1, 0), (TILE_N1, d_hidden//2))
                s1_tile = hk.load(w1_scale, (eid, n1, 0), (TILE_N1, d_hidden//32))

                # Dequantize and GEMM
                gate_up = hk.gemm_mxfp4(x, w1_tile, s1_tile)

            # Split gate/up
            gate, up = gate_up.split(d_expert)

            # SiLU + Mul
            activated = hk.silu(gate) * up  # [d_expert]

            # Stage 2: Down (in LDS)
            for n2 in range(0, d_hidden, TILE_N2):
                w2_tile = hk.load(w2, (eid, n2, 0), (TILE_N2, d_expert//2))
                s2_tile = hk.load(w2_scale, (eid, n2, 0), (TILE_N2, d_expert//32))

                # Dequantize and GEMM
                out = hk.gemm_mxfp4(activated, w2_tile, s2_tile)

            # Accumulate with topk weight
            accum += out * weight

        hk.store(output, m, accum)
```

**Challenges:**
- Need to verify HipKittens can do GEMM→SiLU→GEMM fusion
- Scale layout must match MXFP4 format
- Weight shuffling (16x16) must be handled

### Path 2: CK-Tile flatmm Extension

**Advantages:**
- Production-quality from AMD
- Native `mfma_f32_32x32x64_f8f6f4` support
- Existing MXFP4 examples

**Approach:**
```cpp
// Extend CK-Tile 18_flatmm example
// Flatmm = "flat" batched GEMM (non-grouped)

// Need to create custom tile operator:
// 1. Load A (bf16) + B1 (MXFP4)
// 2. MFMA with scale
// 3. SiLU + Mul in registers
// 4. Load B2 (MXFP4)
// 5. MFMA with scale
// 6. Store C (bf16)
```

**Challenges:**
- C++ template metaprogramming complexity
- Runner blocks direct kernel dispatch
- Need to find alternative to hipModuleLaunchKernel

### Path 3: AITER Internal Direct Dispatch (Already Exhausted)

**Status:** K-Search Phase 18 confirmed API ceiling

```python
# Tried: fmoe_g1u1, direct CK dispatch, adaptive KSPLIT
# All paths either:
# - Crash (doweight_stage1=True)
# - Wrong results (NaN for 32-expert)
# - No gain (replicates fused_moe internals)
```

---

## Shared Expert Specialization

### DeepSeek-R1 Architecture

```python
n_routed_experts = 256
n_shared_experts = 1  # Always active

# Current: All experts go through fused_moe
# Shared expert has weight=1.0, always selected
```

### Optimization: Separate Shared Expert Path

```python
# Shared expert is dense (all tokens hit it)
# Can compute as separate dense GEMM

# For bs=128, d_hidden=7168, d_expert=2048:
shared_out = dense_gemm(hidden, shared_w1, shared_w2)

# Then add to routed expert output
output = routed_output + shared_out
```

**Advantages:**
- Dense GEMM has better memory access patterns
- No sorting overhead for shared expert
- Can use optimized gemm_a4w4 directly

**Challenge:**
- Only saves if shared expert is significant fraction of work
- For DeepSeek-R1: shared expert is 1/257 of computation (~0.4%)
- Savings likely minimal

---

## Dynamic Quantization Fusion

### Current Flow

```python
# Before fused_moe:
hidden_fp4, hidden_scale = dynamic_mxfp4_quant(hidden)
hidden_scale_shuffled = e8m0_shuffle(hidden_scale)

# fused_moe re-quantizes internally
```

**Double quantization issue:**
- Input hidden is already quantized to MXFP4
- But `generate_input` provides bf16 hidden
- fused_moe quantizes inside

**Potential optimization:**
```python
# If generate_input provided pre-quantized hidden:
# (impossible under current task spec - generates bf16)

# Alternative: Fuse quant into kernel prologue
# - Load bf16 hidden
# - Quantize to MXFP4 in LDS
# - Use for Stage 1 GEMM
```

**Blocker:**
- Task generates bf16 hidden_states
- Cannot change input format
- fused_moe internal quantization is unavoidable

---

## Performance Modeling

### Expected Speedup from Fusion

| Optimization | Estimated Savings | Confidence |
|-------------|------------------|------------|
| Stage 1+2 fusion | 20-30µs | Medium |
| Shared expert split | 2-5µs | Low (small fraction) |
| Quant fusion | 5-10µs | Low (task constraints) |

**Total potential:** 27-45µs
**Required to match leader:** 44µs

**Verdict:** Fusion could close the gap, but requires custom kernel development.

---

## Implementation Recommendation

### Phase 1: Validate HipKittens Viability

1. Study HipKittens GEMM examples
2. Check if 2-stage GEMM→activation→GEMM pattern is expressible
3. Verify MXFP4 scale handling

### Phase 2: Prototype

1. Write simple 1-expert MoE in HipKittens (no sorting)
2. Add sorting dispatch (moe_sorting_fwd is reusable)
3. Test correctness vs aiter reference

### Phase 3: Optimize

1. Tune tile sizes for MI355X
2. XCD-aware scheduling
3. Integration into submission

---

## Open Questions

1. Does HipKittens support the 2-stage GEMM→activation→GEMM pattern?
2. Can we reuse aiter's moe_sorting_fwd with HipKittens GEMM?
3. How does HipKittens handle MXFP4 weight shuffling?
4. What's the minimum viable HipKittens kernel for MoE?
5. Can CK-Tile express MoE-style token routing?

---

## References

- `amd-moe-mxfp4-optimization` SKILL.md - Exhausted API paths
- `aiter-kernel-parameter-semantics` SKILL.md - KSPLIT, doweight_stage1 details
- CK-Tile flatmm: composable_kernel/example/ck_tile/18_flatmm/
- HipKittens paper: arxiv.org/abs/2511.08083
- DeepSeek MoE: https://huggingface.co/deepseek-ai/DeepSeek-R1-0528

---

*Probe created: 2026-03-27*
*Status: Research in progress*
