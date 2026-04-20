---
name: amd-moe-dispatch-policy
description: |
  Undocumented moe_sorting_dispatch_policy parameter in aiter's fused_moe that changes
  expert token sorting strategy. Use when: (1) MoE worst-case shapes are 2-5x slower
  than best shapes, (2) large expert counts (64-256) show load imbalance, (3) optimizing
  fused_moe on AMD MI355X for competition kernels.
  Key finding: policy=1 reduces worst-case shapes by 37% (695→436µs) at cost of ~5µs
  on best shapes. Discovered Session 91, April 2026.
author: Claude Code (Session 91)
version: 1.0.0
---

# amd-moe-dispatch-policy

## Problem

MoE kernels using aiter's `fused_moe` show extreme variance across shapes:
- Best shape: 88µs
- Worst shape: 695µs (8× slower!)

The worst shapes have many routed experts (256) causing load imbalance across CUs.

## Solution

Pass `moe_sorting_dispatch_policy=1` to `fused_moe`:

```python
from aiter.fused_moe import fused_moe

result = fused_moe(
    hidden_states, w1_shuffled, w2_shuffled,
    topk_weights, topk_ids,
    activation=ActivationType.Silu,
    quant_type=QuantType.per_1x32,
    doweight_stage1=False,
    w1_scale=w1_scale_shuffled,
    w2_scale=w2_scale_shuffled,
    hidden_pad=hidden_pad,
    intermediate_pad=intermediate_pad,
    moe_sorting_dispatch_policy=1,  # KEY: different sorting strategy
)
```

## Results

### Benchmark (visible shapes)
| Metric | policy=0 (default) | policy=1 |
|--------|-------------------|----------|
| Best shape | 88µs | 93µs (+5µs) |
| Worst shape | 695µs | **436µs (-37%)** |

### RANKED (secret shapes — OPPOSITE result!)
| Metric | policy=0 (default) | policy=1 |
|--------|-------------------|----------|
| Ranked score | **154.183µs** | 214.153µs (+39% WORSE!) |

**WARNING:** dispatch_policy=1 improves benchmark worst-case but HURTS ranked
performance. The ranked shape distribution weights cases where policy=0 is better.
**DO NOT use policy=1 for leaderboard submissions.**

## Related Parameters Found (Untested)

- `moe_sorting_dispatch_policy=2,3,...` — may exist, untested
- `doweight_stage1=True` — runs but produces wrong results (3/4 fail)
- `expert_mask` — sparse dispatch, crashes on some shapes

## API Inventory (Session 91 Probe)

```
aiter.fmoe_g1u1          # requires pre-sorted tokens
aiter.fmoe_g1u1_a16      # bf16 activations, pre-sorted
aiter.fmoe_g1u1_tkw1     # token-weight variant, pre-sorted
aiter.fmoe_fp8_blockscale_g1u1  # fp8 blockscale, pre-sorted
aiter.ck_moe_stage1/stage2      # CK tile direct dispatch
```

All `fmoe_*` variants require pre-sorted tokens (`sorted_token_ids`, `sorted_weights`,
`sorted_expert_ids`, `num_valid_ids`). The `fused_moe` wrapper handles sorting internally.

## Verification

```bash
popcorn-cli submit --no-tui --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 submission.py
# Expect: 3/3 or 4/4 pass, max error ≤ 0.015625
```
