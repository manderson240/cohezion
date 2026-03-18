---
title: "Strategic Recommendations - MoE MXFP4 Optimization"
date: 2026-03-15
status: in-progress
tags: [infinity, beta, gpu-optimization]
aspect: thinker
---

# Strategic Recommendations - MoE MXFP4 Optimization
**Agent**: B2 (Leaderboard Trend Analyst)  
**Team**: Beta (Research & Intelligence)  
**Generated**: 2026-03-14  
**Priority**: HIGH

---

## Executive Summary

**Current State**: Rank 14/43 (155µs) - Cluster C (Parameter Tuners)  
**Target State**: Rank 5-7 (120-125µs) - Cluster B (Competitive Optimizers)  
**Gap to Close**: 30-35µs (24% improvement)  
**Confidence**: HIGH (80% success probability)

**Primary Recommendation**: Implement CUDA Graph capture + AITER_KSPLIT tuning in next 3 submissions.

---

## Strategic Priorities

### Priority 1: CUDA Graph Capture (IMMEDIATE)
**Impact**: +15-25µs improvement  
**Effort**: 2-4 hours  
**Risk**: LOW  
**Confidence**: 90%

**Implementation**:
```python
import torch
import os
from task import input_t, output_t
from aiter import ActivationType, QuantType
from aiter.fused_moe import fused_moe

# Enable non-temporal loads
os.environ["AITER_USE_NT"] = "1"

# Graph cache per shape
_graphs: dict = {}

def _run_moe(h, w1, w2, tw, ti, s1, s2, hp, ip, out):
    res = fused_moe(
        h, w1, w2, tw, ti,
        expert_mask=None,
        activation=ActivationType.Silu,
        quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=s1,
        w2_scale=s2,
        hidden_pad=hp,
        intermediate_pad=ip,
    )
    out.copy_(res)

def custom_kernel(data: input_t) -> output_t:
    # ... unpack data ...
    
    key = (M, E, DE, DH)
    
    if key in _graphs:
        g, h_buf, tw_buf, ti_buf, out_buf = _graphs[key]
        if g is not None:
            h_buf.copy_(hidden_states)
            tw_buf.copy_(topk_weights)
            ti_buf.copy_(topk_ids)
            g.replay()
            return out_buf
    
    # Capture path
    h_buf = hidden_states.clone()
    tw_buf = topk_weights.clone()
    ti_buf = topk_ids.clone()
    out_buf = torch.empty((M, DH), dtype=torch.bfloat16, device=device)
    
    # Warmup (CRITICAL)
    for _ in range(3):
        _run_moe(h_buf, gate_up_weight_shuffled, down_weight_shuffled,
                tw_buf, ti_buf, gate_up_weight_scale_shuffled,
                down_weight_scale_shuffled, hidden_pad, intermediate_pad, out_buf)
    
    torch.cuda.synchronize()
    
    try:
        g = torch.cuda.CUDAGraph()
        with torch.cuda.graph(g):
            _run_moe(h_buf, gate_up_weight_shuffled, down_weight_shuffled,
                    tw_buf, ti_buf, gate_up_weight_scale_shuffled,
                    down_weight_scale_shuffled, hidden_pad, intermediate_pad, out_buf)
        g.replay()
        _graphs[key] = (g, h_buf, tw_buf, ti_buf, out_buf)
        return out_buf
    except Exception:
        _graphs[key] = (None, None, None, None, None)
        return fused_moe(...)  # Fallback
```

**Success Criteria**:
- [ ] All 3 test cases pass (rtol=5e-2)
- [ ] Time < 140µs (first submission)
- [ ] Time < 130µs (optimized)

---

### Priority 2: AITER_KSPLIT Tuning (HIGH)
**Impact**: +5-10µs improvement  
**Effort**: 1-2 hours  
**Risk**: LOW  
**Confidence**: 85%

**Implementation**:
```python
import os

# Set BEFORE importing aiter
os.environ["AITER_KSPLIT"] = "4"  # For sparse configs (E=257)
# OR
os.environ["AITER_KSPLIT"] = "2"  # For dense configs (E=33)

from aiter.fused_moe import fused_moe
```

**Strategy**:
- **KSPLIT=4**: For E=257 (sparse token distribution, m_per_expert < 50)
- **KSPLIT=2**: For E=33 (dense token distribution, m_per_expert > 50)
- **Shape-specific**: Set based on config at runtime

**Testing Plan**:
1. Submission 1: KSPLIT=4 for all shapes
2. Submission 2: KSPLIT=2 for all shapes
3. Submission 3: Shape-specific KSPLIT

**Expected Results**:
- KSPLIT=4: Best for bs=16, E=257 (sparse)
- KSPLIT=2: Best for bs=512, E=33 (dense)
- Shape-specific: Optimal across all configs

---

### Priority 3: Non-Temporal Loads (MEDIUM)
**Impact**: +3-5µs improvement  
**Effort**: 5 minutes  
**Risk**: NONE  
**Confidence**: 95%

**Implementation**:
```python
import os

# At module level, BEFORE any aiter imports
os.environ["AITER_USE_NT"] = "1"
```

**Why It Works**:
- Reduces cache pollution for streaming data
- Improves memory bandwidth utilization
- Zero correctness risk

---

### Priority 4: Shape-Specific Dispatch (MEDIUM)
**Impact**: +5-8µs improvement  
**Effort**: 4-6 hours  
**Risk**: MEDIUM  
**Confidence**: 70%

**Implementation**:
```python
def custom_kernel(data: input_t) -> output_t:
    # ... unpack ...
    
    # Shape-specific optimization
    if M <= 32 and E == 257:
        # Small batch, many experts: use KSPLIT=4
        os.environ["AITER_KSPLIT"] = "4"
        # Additional small-batch optimizations
    elif M >= 256 and E == 33:
        # Large batch, few experts: use KSPLIT=2
        os.environ["AITER_KSPLIT"] = "2"
        # Additional large-batch optimizations
    
    # ... rest of kernel ...
```

**Rationale**:
- Different optimal parameters for different shapes
- Current one-size-fits-all leaves 5-8µs on table
- Top performers (ranks 4-10) all use shape dispatch

---

### Priority 5: Split Expert Processing (LOW)
**Impact**: +8-15µs improvement  
**Effort**: 8-12 hours  
**Risk**: HIGH  
**Confidence**: 60%

**Implementation**:
```python
def custom_kernel(data: input_t) -> output_t:
    # ... unpack ...
    
    # 1. Process routed experts with fused_moe
    top_k_routed = config["n_experts_per_token"]
    routed_ids = topk_ids[:, :top_k_routed]
    routed_weights = topk_weights[:, :top_k_routed]
    
    routed_output = fused_moe(
        hidden_states,
        gate_up_weight_shuffled,
        down_weight_shuffled,
        routed_weights,
        routed_ids,
        # ... other params ...
    )
    
    # 2. Process shared expert with tritonblas
    from tritonblas import matmul_fp4
    from aiter.ops.triton.quant import dynamic_mxfp4_quant
    import torch.nn.functional as F
    
    shared_w1 = gate_up_weight[-1]
    shared_w2 = down_weight[-1]
    
    # Quantize and GEMM
    h_q, h_s = dynamic_mxfp4_quant(hidden_states)
    inter = torch.empty((M, 2 * d_expert_pad), dtype=torch.bfloat16, device=device)
    matmul_fp4(h_q.view(torch.uint8), shared_w1.view(torch.uint8), 
               inter, h_s.view(torch.uint8), shared_s1.view(torch.uint8))
    
    # SwiGLU
    gate, up = inter.chunk(2, dim=-1)
    inter_act = F.silu(gate) * up
    
    # Second GEMM
    inter_q, inter_s = dynamic_mxfp4_quant(inter_act)
    shared_out = torch.empty((M, d_hidden_pad), dtype=torch.bfloat16, device=device)
    matmul_fp4(inter_q.view(torch.uint8), shared_w2.view(torch.uint8),
               shared_out, inter_s.view(torch.uint8), shared_s2.view(torch.uint8))
    
    # Combine
    return routed_output + shared_out[:, :d_hidden]
```

**Risk**: HIGH
- Requires tritonblas integration
- Correctness validation needed
- May not improve all shapes

**Recommendation**: Implement only after Priority 1-4 complete and stable.

---

## Submission Sequence

### Phase 1: Foundation (Submissions 1-3)
**Goal**: Establish Cluster B position (125-135µs)

| Submission | Changes | Expected Time | Target Rank |
|------------|---------|---------------|-------------|
| 1 | CUDA Graphs + AITER_USE_NT | 135µs | 10-12 |
| 2 | + AITER_KSPLIT=4 | 128µs | 7-9 |
| 3 | + Shape-specific KSPLIT | 125µs | 6-8 |

**Validation**: Each submission must pass all correctness tests.

### Phase 2: Optimization (Submissions 4-8)
**Goal**: Reach Cluster B upper boundary (115-120µs)

| Submission | Changes | Expected Time | Target Rank |
|------------|---------|---------------|-------------|
| 4 | Graph warmup tuning | 122µs | 5-7 |
| 5 | + Buffer reuse optimization | 120µs | 5-6 |
| 6 | + Advanced shape dispatch | 118µs | 4-5 |
| 7 | + Split expert processing | 115µs | 3-4 |
| 8 | Final tuning | 115µs | 3-4 |

### Phase 3: Breakthrough (Submissions 9+)
**Goal**: Cluster A entry (105-115µs)

**Only if Phase 2 successful**

| Submission | Changes | Expected Time | Target Rank |
|------------|---------|---------------|-------------|
| 9 | Custom HIP kernel v1 | 110µs | 2-3 |
| 10+ | Kernel optimization | 105µs | 1-2 |

---

## Risk Mitigation

### Risk 1: Graph Capture Failure
**Probability**: 20%  
**Impact**: HIGH

**Mitigation**:
- Implement robust fallback to direct path
- Test with `--mode test` before benchmark
- Check torch.cuda.is_available() and graph support

### Risk 2: KSPLIT Hurts Performance
**Probability**: 30%  
**Impact**: MEDIUM

**Mitigation**:
- Test both KSPLIT=2 and KSPLIT=4
- Implement shape-specific selection
- Revert to default if negative impact

### Risk 3: Split Expert Breaks Correctness
**Probability**: 40%  
**Impact**: HIGH

**Mitigation**:
- Validate against reference output
- Use rtol=5e-2 tolerance
- Implement gradual rollout (one shape at a time)

### Risk 4: Competition Advances
**Probability**: 50%  
**Impact**: MEDIUM

**Mitigation**:
- Daily leaderboard monitoring
- Rapid iteration (submit every 2-3 days)
- Focus on proven techniques first

---

## Resource Allocation

### Time Budget (Next 2 Weeks)

| Activity | Hours | Priority |
|----------|-------|----------|
| Graph capture implementation | 4 | P0 |
| KSPLIT tuning | 2 | P0 |
| Shape-specific dispatch | 6 | P1 |
| Split expert processing | 10 | P2 |
| Testing and validation | 4 | P0 |
| Documentation | 2 | P3 |
| **Total** | **28** | |

### Submission Budget
- **Test submissions**: 5-8 (validate correctness)
- **Benchmark submissions**: 10-15 (performance tuning)
- **Leaderboard submissions**: 3-5 (official entries)

---

## Success Metrics

### Phase 1 Success (Week 1)
- [ ] Time < 130µs (Rank 8-10)
- [ ] All correctness tests pass
- [ ] Graph capture stable across shapes

### Phase 2 Success (Week 2)
- [ ] Time < 120µs (Rank 5-7)
- [ ] Top 10 aggregate score qualification
- [ ] Documented optimization techniques

### Phase 3 Success (Week 3+)
- [ ] Time < 115µs (Rank 3-5)
- [ ] Competitive with elite performers
- [ ] Custom kernel knowledge base

---

## Alternative Strategies

### If Graph Capture Fails
**Fallback**: Focus on KSPLIT + non-temporal loads only
**Expected**: 140-145µs (Rank 10-12)
**Action**: Still valuable, proceed to Phase 2

### If KSPLIT Has No Effect
**Fallback**: Shape-specific dispatch becomes Priority 2
**Expected**: 135-140µs (Rank 8-10)
**Action**: Investigate aiter version differences

### If Competition Accelerates
**Fallback**: Skip to custom kernel development
**Risk**: HIGH, but may be necessary
**Trigger**: If rank 10 time drops below 130µs

---

## Coordination with Other Teams

### Alpha Team (Implementation)
- Provide: Optimized submission templates
- Receive: Performance feedback, iteration results

### Gamma Team (Testing)
- Provide: Correctness validation requirements
- Receive: Test results, regression reports

### Delta Team (Documentation)
- Provide: Technique documentation, lessons learned
- Receive: Knowledge base updates

---

## Daily Standup Agenda

### Questions for Each Submission
1. What technique was tested?
2. What was the result (time, rank, correctness)?
3. What was learned?
4. What is the next experiment?
5. Any blockers or risks?

### Metrics to Track
- Submission count per technique
- Time improvement per submission
- Rank progression
- Correctness pass rate
- Technique adoption rate

---

## Conclusion

**Primary Recommendation**: Execute Phase 1 immediately (graph capture + KSPLIT tuning). This provides the highest confidence path to Rank 5-7 with minimal risk.

**Secondary Recommendation**: Begin Phase 2 preparation (shape-specific dispatch) in parallel, ready to deploy once Phase 1 stabilizes.

**Contingency**: Monitor competition daily. If leaderboard compresses faster than expected, escalate to custom kernel development.

**Success Probability**: 80% for Rank 7, 60% for Rank 5, 40% for Rank 3.

---

**Recommendations Complete** - Ready for implementation phase


## Related
- [[john_hahn_intelligence_analysis|John Hahn Intelligence Analysis]] (b1)
- [[B1_SUMMARY|B1 Summary]] (b1)
- [[README|Readme]] (b2)
- [[performance_cluster_report|Performance Cluster Report]] (b2)
- [[leaderboard_trend_analysis|Leaderboard Trend Analysis]] (b2)
- [[optimization_ceiling_prediction|Optimization Ceiling Prediction]] (b2)
- [[best_practices_guide|Best Practices Guide]] (b3)
- [[technique_extraction_report|Technique Extraction Report]] (b3)
- [[common_patterns|Common Patterns]] (b3)
