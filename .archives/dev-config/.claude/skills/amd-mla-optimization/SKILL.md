# MLA Optimization Skill for AMD MI355X

## Purpose
Optimize DeepSeek MLA (Multi-head Latent Attention) decode kernel for AMD MI355X.

## Key Insight
MLA has heterogeneous quantization sensitivity - RoPE part needs high precision, per-token granularity aligns with autoregressive decoding (SnapMLA paper).

## MLA Configuration (DeepSeek R1)
- total_num_heads = 128
- num_kv_heads = 1 (shared latent KV)
- kv_lora_rank = 512
- qk_rope_head_dim = 64
- qk_head_dim = 576 (kv_lora_rank + qk_rope_head_dim)
- v_head_dim = 512

## Optimization Regimes

### Regime 1: Small Batch (bs<=4 OR total_kv<=32768)
Use torch.einsum bf16 - bypasses aiter dispatch overhead:
```python
scores = torch.einsum("bqnh,bsh->bnqs", q_r, kv).mul_(SM_SCALE)
weights = torch.softmax(scores, dim=-1)
out = torch.einsum("bnqs,bsd->bqnd", weights, v)
```

### Regime 2: Medium (total_kv<=262144)
Use aiter a16w8 direct ASM (bf16 Q + fp8 KV):
```python
kv_fp8, kv_scale = kv_data["fp8"]
# Use bf16 Q with fp8 KV
```

### Regime 3: Large (total_kv>262144)
Use aiter a8w8 direct ASM (fp8 Q + fp8 KV):
```python
q_input, q_scale = _quantize_fp8(q)
# Use fp8 Q with fp8 KV
```

## Key Parameters (Confirmed Optimal)
- `fast_mode=False` - 17-21% faster than True
- `kv_granularity=16` - confirmed optimal
- `num_kv_splits`: adaptive (4/8/16 based on total_kv)
- `sm_scale = 1/sqrt(576)`

## Persistent Scheduling
- Set `AITER_MLA_USE_PERSISTENT=1`
- num_splits: 4 (<=2048), 8 (<=16384), 16 (>16384)

## Reference
- SnapMLA paper (arXiv:2602.10718)
- aiter MLA kernels: `mla_decode_fwd`, `mla_decode_stage1_asm_fwd`, `mla_reduce_v1`

## Files
- `kernels/mixed-mla/submission_snapmla.py` - Current best implementation
