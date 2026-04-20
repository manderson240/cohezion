# Probe: MLA MXFP4 Native Decode Kernel Path

## Summary

**Status:** `mla_decode_fwd` with MXFP4 KV permanently blocked by assertion
**Alternative:** HipKittens custom attention kernel
**Potential Gain:** 2x KV cache bandwidth reduction vs FP8
**Challenge:** MLA's K=576, V=512 mismatch requires custom tile handling

---

## Current Reference Implementation

### What the Reference Does

```python
# Reference uses FP8 (a8w8) - NOT MXFP4
# Q quantized to fp8 on-the-fly
# KV buffer in fp8

Q_DTYPE = "fp8"  # a8w8 kernel
KV_DTYPE = "fp8"  # a8w8 kernel

def ref_kernel(data):
    q, kv_data, qo_indptr, kv_indptr, config = data
    q_input, q_scale = quantize_fp8(q)  # On-the-fly quant
    kv_buffer_fp8, kv_scale = kv_data["fp8"]  # Pre-quantized KV
    return _aiter_mla_decode(q_input, kv_buffer_fp8, q_scale, kv_scale)
```

### Available KV Formats in Input

```python
kv_data = {
    "bf16":  Tensor (total_kv, 1, 576) bf16,           # Reference quality
    "fp8":   (Tensor, Tensor) kv_buffer fp8 + scale,  # Current reference
    "mxfp4": (Tensor, Tensor) kv_buffer fp4x2 + e8m0 scale,  # Target
}
```

---

## Why MXFP4 MLA is Blocked

### The Assertion Failure

```python
# In aiter's mla_decode_fwd (C++):
# TORCH_CHECK(head_size == KV.size(3), "...")

# For MLA:
# - head_size = QK_HEAD_DIM = 576 (absorbed query dimension)
# - KV with MXFP4: shape is (total_kv, 1, 288)  # fp4x2 packed
# - 288 != 576 → assertion failure
```

**Root cause:** The MLA kernel expects KV head dimension to match Q head dimension (576). MXFP4 packing reduces this to 288 bytes, but the kernel doesn't understand packed dimensions.

### Failed Attempts

| Path | Error | Root Cause |
|------|-------|------------|
| `mla_decode_fwd` + MXFP4 KV | `head_size == KV.size(3)` | Kernel doesn't handle packed KV |
| `mla_decode_fwd` (non-ASM) | Same assertion | Same code path |
| `fav3_sage_mxfp4` | Incompatible | SAGE expects separate K/V, MLA has fused buffer |

---

## MLA Architecture Deep Dive

### DeepSeek R1 MLA Config

```python
TOTAL_NUM_HEADS = 128
NUM_KV_HEADS = 1  # Shared latent KV head
KV_LORA_RANK = 512
QK_ROPE_HEAD_DIM = 64
QK_HEAD_DIM = KV_LORA_RANK + QK_ROPE_HEAD_DIM  # 576
V_HEAD_DIM = KV_LORA_RANK  # 512

# Forward absorb path:
# - Q is "absorbed" with RoPE applied
# - KV buffer is compressed: 576 dims (used as K), first 512 as V
# - This is NOT standard MQA/GQA - it's latent attention
```

### Attention Computation

```python
# Standard attention:
# scores = softmax(Q @ K.T / sqrt(d_k)) @ V

# MLA attention:
# K is full 576 dims (includes RoPE)
# V is first 512 dims of same buffer
# This is the "compressed KV" representation

# So: Q @ K.T uses 576-dim Q and 576-dim K slice
#     @ V uses only first 512 dims
```

**Key challenge:** K and V have different dimensions (576 vs 512) from the same buffer. Standard attention kernels expect K and V to have the same head_dim.

---

## Potential Solutions

### Option 1: HipKittens Custom Attention Kernel

**Advantages:**
- Tile-based DSL can handle custom dimension splits
- ~500 LOC attention kernels beat AMD baselines
- 8-Wave Ping-Pong scheduling for decode

**Implementation approach:**
```python
# Hypothetical HipKittens MLA kernel
@hk.kernel
def mla_decode_mxfp4(
    q: hk.Tensor[total_q, num_heads, 576],      # bf16
    kv: hk.Tensor[total_kv, 1, 288],            # fp4x2 packed
    kv_scale: hk.Tensor[total_kv, 18],          # e8m0 (576/32=18 scales)
    qo_indptr: hk.Tensor[batch_size+1],
    kv_indptr: hk.Tensor[batch_size+1],
):
    # Per-sequence decode
    for b in range(batch_size):
        q_start, q_end = qo_indptr[b], qo_indptr[b+1]
        kv_start, kv_end = kv_indptr[b], kv_indptr[b+1]

        # Load Q for this sequence
        q_seq = hk.load(q, (q_start, 0, 0), (q_end-q_start, num_heads, 576))

        # Attention over KV cache
        for kv_idx in range(kv_start, kv_end, BLOCK_KV):
            # Load KV tile (fp4x2)
            kv_tile = hk.load(kv, (kv_idx, 0, 0), (BLOCK_KV, 1, 288))
            kv_scale_tile = hk.load(kv_scale, (kv_idx, 0), (BLOCK_KV, 18))

            # Dequantize to bf16 in LDS
            kv_bf16 = hk.mxfp4_to_bf16(kv_tile, kv_scale_tile)

            # Split into K (576) and V (512)
            k_tile = kv_bf16  # 576 dims
            v_tile = kv_bf16[:, :512]  # First 512

            # Compute attention
            scores = hk.matmul(q_seq, k_tile.T) * SM_SCALE
            weights = hk.softmax(scores, dim=-1)
            out = hk.matmul(weights, v_tile)

        hk.store(output, out)
```

**Challenges:**
- Need to verify HipKittens supports variable-length sequences (indptr-based)
- Need segmented softmax across KV cache
- 576 is not power-of-2 (may need padding)

### Option 2: FP8 with Optimized Splits (Current Best)

**Status:** Already implemented, gap is 2.1x

```python
# Three-regime routing
MATMUL_MAX_BS = 4
MATMUL_MAX_TOTAL_KV = 32768
A16W8_THRESHOLD = 262144

# Direct ASM dispatch (fast_mode=False)
# Adaptive num_kv_splits based on total_kv
```

**Remaining optimizations:**
- Metadata caching (already done)
- Pre-allocated intermediate buffers
- Fast mode False confirmed optimal

### Option 3: Custom Triton (Blocked)

**Blocker:** `float4_e2m1fn_x2` KeyError on runner

Even if unblocked, would need:
- 576-dim handling (non-power-of-2)
- Segmented attention with indptr
- Separate K (576) and V (512) paths from same buffer

---

## Bandwidth Analysis

### Why MXFP4 is Worth Pursuing

```
KV cache sizes for 8192 sequence length:
- bf16: 8192 * 576 * 2 bytes = 9.44 MB
- fp8:  8192 * 576 * 1 byte = 4.72 MB
- mxfp4: 8192 * 288 * 1 byte + scales = 2.36 MB + 0.46 MB = 2.82 MB

Bandwidth reduction: 4.72 MB → 2.82 MB = 1.67x (vs fp8)
                      9.44 MB → 2.82 MB = 3.35x (vs bf16)
```

**At large batch (bs=256, kv=8192):**
- Total KV = 2,097,152 tokens
- FP8 KV bandwidth: ~1 GB per attention pass
- MXFP4 KV bandwidth: ~600 MB per attention pass

**Potential speedup:** 1.5-2x on memory-bound decode

---

## Implementation Path

### Phase 1: HipKittens Research

1. Study HipKittens attention examples
2. Identify tile primitives for variable-length attention
3. Design MLA-specific tile layout (K=576, V=512 split)

### Phase 2: Prototype

1. Write simple HipKittens attention without MXFP4 first
2. Verify correctness against aiter reference
3. Add MXFP4 dequantization in LDS
4. Integrate into submission

### Phase 3: Optimization

1. Tune tile sizes for MI355X
2. Optimize scale application (E8M0 → f32)
3. XCD-aware scheduling

---

## Open Questions

1. Does HipKittens support indptr-based segmented attention?
2. How does HipKittens handle non-power-of-2 dimensions (576)?
3. Can we fuse MXFP4 dequantization with attention in tiles?
4. What's the overhead of E8M0 → f32 scale conversion?
5. Is there a way to use aiter's ASM kernels with custom KV packing?

---

## References

- `amd-mla-decode-optimization` SKILL.md - Current best implementation
- `deepseek-mla-decode-flash-attention-gap` SKILL.md - Gap analysis
- HipKittens paper: arxiv.org/abs/2511.08083
- DeepSeek R1 config: https://huggingface.co/deepseek-ai/DeepSeek-R1-0528
- FlashMLA blog: blog.vllm.ai/2026/02/27/rocm-attention-backend.html

---

*Probe created: 2026-03-27*
*Status: Research in progress*
