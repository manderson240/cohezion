# 🎯 MLA Agent — Claude Code Assignment

**Agent:** Claude Code  
**Kernel:** MLA (amd-mixed-mla)  
**Current Best:** 69.745µs (rank ~96)  
**Target:** <40µs (rank ~50)  
**Gap:** 1.7x improvement needed  

---

## 📋 CURRENT STATUS

**Phase:** Pending Agent Spawn  
**Started:** -  
**Last Update:** -  
**ETA:** T+1 hour for first discovery

---

## 🎯 ASSIGNMENT

### Primary Approach: ASM Decode Kernel Bypass

**From RUNNER_INVENTORY Discovery:**
The runner has a **dedicated BF16 decode kernel** that's NOT being dispatched:
- Kernel: `mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co`
- Location: `/home/runner/aiter/hsa/gfx950/mla/`
- Status: Exists but aiter's router selects prefill-style kernel instead

**Why This Could Win:**
1. Decode-optimized kernel has different tile scheduling
2. BF16 avoids FP8 quantization overhead
3. MLA tolerance is 10% — allows BF16 approximation
4. Gap to leader is 3.6x — needs algorithmic change

---

## 🔧 TECHNICAL DETAILS

### Discovery Mission

**Your Task:** Find the exact conditions that trigger `mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co`

**Approaches to Try:**

1. **Shape Manipulation**
   - Reshape KV to trigger decode path
   - Try different qseqlen values (1 vs 2 vs 4)
   - Vary head count to match mqa16 pattern

2. **Metadata Configuration**
   - Experiment with `fast_mode=True/False`
   - Try different `num_kv_splits` values
   - Vary `intra_batch_mode` settings

3. **Direct ASM Dispatch**
   - Use `mla_decode_stage1_asm_fwd` with explicit kernel selection
   - Try different argument combinations
   - Test if kernelName parameter works

### Key API: `mla_decode_stage1_asm_fwd`

```python
aiter.mla_decode_stage1_asm_fwd(
    Q: torch.Tensor,                    # [total_q, NUM_HEADS, QK_DIM] fp8
    KV: torch.Tensor,                   # [total_kv, PAGE_SIZE, 1, QK_DIM] fp8
    qo_indptr: torch.Tensor,
    kv_indptr: torch.Tensor,
    kv_page_indices: torch.Tensor,
    kv_last_page_lens: torch.Tensor,
    num_kv_splits_indptr: Optional[torch.Tensor],
    work_meta_data: Optional[torch.Tensor],
    work_indptr: Optional[torch.Tensor],
    work_info_set: Optional[torch.Tensor],
    max_seqlen_q: int,
    page_size: int,
    nhead_kv: int,
    softmax_scale: float,
    splitData: torch.Tensor,            # Output: logits
    splitLse: torch.Tensor,              # Output: LSE
    output: torch.Tensor,                # Output: [total_q, NUM_HEADS, V_DIM]
    q_scale: Optional[torch.Tensor] = None,
    kv_scale: Optional[torch.Tensor] = None
)
```

---

## 🧪 TESTING PROTOCOL

### Step 1: Correctness (Test Mode)
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-mixed-mla
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mixed-mla \
  submission_asm_decode_bypass.py
```

**Expected:** 4/4 tests pass

### Step 2: Benchmark (If Correct)
```bash
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-mixed-mla \
  submission_asm_decode_bypass.py
```

**Target:** <50µs geomean

---

## 📝 DISCOVERY LOG

### (To be populated by Claude Code...)

---

## 🚧 BLOCKER TRACKER

| Blocker | Status | Resolution |
|---------|--------|------------|
| Agent spawn | ⚪ PENDING | Waiting for activation signal |

---

## 🔗 REFERENCES

- [Session 95 Findings](../SESSION_95_CONTINUATION.md)
- [Runner Inventory](../RUNNER_INVENTORY.md) — See MLA section
- [Current MLA Submission](../amd-mixed-mla/submission.py)
- [COORDINATION_HUB](./COORDINATION_HUB.md)
- [SHARED_DISCOVERIES](./SHARED_DISCOVERIES.md)

---

**Activation Signal:** Begin when this file is modified with "🟢 ACTIVE"
