# Research: Dr. Kernel — RL-Based Triton Kernel Generation

## Executive Summary

**Dr. Kernel** (arXiv:2602.05885, Feb 2026, HKUST/TikTok/NTU) is the first systematic study of **reinforcement learning (RL) for Triton kernel code generation**. It introduces **KernelGYM**, a robust distributed GPU environment, and achieves competitive performance with Claude-4.5-Sonnet on KernelBench benchmarks through novel RL training methods.

**Key Results:**
- **31.6%** of generated kernels achieve ≥1.2× speedup on KernelBench Level-2 (vs. Claude-4.5-Sonnet 26.7%, GPT-5 28.6%)
- **47.8%** when selecting best across all turns with sequential test-time scaling
- **First RL-trained model** competitive with frontier LLMs for kernel generation

---

## 1. What is Dr. Kernel?

### Core Concept

Dr. Kernel is a 14B-parameter model trained using RL to generate optimized Triton kernels from Torch reference code. It represents the first successful application of RL (not just supervised fine-tuning) to kernel generation.

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dr. Kernel Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     KernelGYM                                │ │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐  │ │
│  │  │   Server   │──│   Redis      │──│   GPU Workers       │  │ │
│  │  │  (FastAPI) │  │   Queue      │  │  (Subprocess       │  │ │
│  │  └────────────┘  └──────────────┘  │   Isolation)       │  │ │
│  │                                     └─────────────────────┘  │ │
│  │  Features:                                                    │ │
│  │  • Reward Hacking Check                                       │ │
│  │  • Profiler Integration                                       │ │
│  │  • Multi-turn Feedback                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Dr. Kernel-14B Model                          │ │
│  │                                                               │ │
│  │  Training Pipeline:                                          │ │
│  │  1. Cold-Start Data: 88K queries → GPT-5 distillation       │ │
│  │  2. SFT on multi-turn trajectories                           │ │
│  │  3. Multi-turn RL with TRLOO + PR + PRS                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Innovations vs. Other Approaches

### Comparison: Dr. Kernel vs. Prior Work

| Aspect | AutoTriton | TritonRL | CudaLLM | **Dr. Kernel** |
|--------|------------|----------|---------|----------------|
| **RL Training** | No (SFT only) | Yes (limited) | No (data only) | **Full multi-turn RL** |
| **Reward Hacking Prevention** | Rule-based (fails ~10%) | LLM-as-judge | None | **Execution-based checks** |
| **Lazy Optimization** | Saturates at 9.2% Fast@1.2 | Not addressed | Not addressed | **Profiling-based rewards** |
| **Multi-turn** | No | Limited | No | **3+ turns with credit assignment** |
| **Environment** | Ad-hoc | Basic | N/A | **Distributed, fault-tolerant KernelGYM** |

### Novel Technical Contributions

#### 2.1 KernelGYM: Robust Evaluation Environment

**Four Design Principles:**
1. **Serialized Execution**: One-GPU-one-task policy for accurate profiling
2. **Elastic Scalability**: Dynamic GPU worker addition/removal
3. **Fault Isolation**: Subprocess isolation for CUDA error containment
4. **Rich Feedback**: Structured execution feedback, not just pass/fail

**Hacking Check**: Execution-based verification that detects:
- Kernels that pass correctness but are never called
- Branching on `self.training` to skip execution
- Empty kernel wrappers that appear fast but do nothing

**Profiler Integration**: Provides kernel-level timing breakdowns to identify true bottlenecks vs. trivial optimizations.

#### 2.2 TRLOO: Turn-Level Reinforce Leave-One-Out

**Problem with GRPO**: Standard GRPO's in-group mean baseline includes the current sample Gi,t in Ḡt, causing:
- Biased policy gradients (shrunk by factor 1 - 1/Nt)
- Self-penalization of rare successful trajectories
- Instability with varying group sizes

**TRLOO Solution**: Exclude the current sample from its own baseline:

```
Āt^(-i) = (1/(Nt-1)) × Σ(j≠i) Gj,t    # Leave-one-out baseline
Ai,t^TRLOO = Gi,t - Āt^(-i)            # Unbiased advantage

Equivalently: Ai,t^TRLOO = (Nt/(Nt-1)) × (Gi,t - Ḡt)
```

**Benefits**:
- Unbiased advantage estimation
- Larger learning signal for rare successes
- Robust to varying group sizes in multi-turn settings

#### 2.3 Profiling-Based Rewards (PR) & Rejection Sampling (PRS)

**Problem**: Models optimize trivial sub-operations (e.g., simple summation) while missing major bottlenecks.

**Example from Paper:**
- Lazy optimization: Generated kernel = 0.014% of CUDA time → minimal speedup
- Better fusion: Generated kernel = 86.15% of CUDA time → meaningful speedup

**Profiling Ratio (PR)**:
```
PRi,t = T_generated / T_total

Reward: Ri,t = C(yi,t) + C(yi,t) × speedup_i,t + C(yi,t) × PRi,t
```

**Profiling-Based Rejection Sampling (PRS)**:
- Reject samples where PRi,t < threshold (typically 0.5)
- Forces model to target kernels that actually dominate runtime
- Combined with PR, breaks lazy optimization plateau

---

## 3. Experimental Results

### 3.1 Main Results on KernelBench

| Model | Level-1 Fast@1 | Level-1 Fast@1.2 | Level-2 Fast@1 | Level-2 Fast@1.2 | Level-3 Fast@1 |
|-------|----------------|------------------|----------------|------------------|----------------|
| Claude-4.5-Sonnet | 60.8% | 34.5% | 60.6% | 26.7% | 54.3% |
| GPT-5 | 66.9% | 38.1% | 63.0% | 28.6% | 53.5% |
| **Dr. Kernel-14B** | **67.9%** | **39.0%** | **61.2%** | **31.6%** | **54.3%** |
| + STTS | 69.1% | 41.4% | **63.8%** | **33.8%** | **56.4%** |

**Fast@X**: % of kernels with ≥X× speedup over Torch reference
**STTS**: Sequential Test-Time Scaling (select best across turns)

### 3.2 Ablation Studies

| Configuration | Fast@1 (Turn 3) | Key Finding |
|---------------|-----------------|-------------|
| **Full System (TRLOO + PR + PRS)** | **39.7%** | Best performance |
| w/o Hacking Check | 32.1% | Training crashes ~50 steps |
| w/o PR (stability only) | 36.2% | MRS helps but doesn't fix lazy opt |
| w/o PRS (PR only) | 38.1% | PRS adds 1.6% improvement |
| Single Turn | 34.8% | Multi-turn adds 4.9% |
| GRPO (not TRLOO) | 37.2% | TRLOO adds 2.5% |
| γ=0 (no reward-to-go) | 35.9% | Credit assignment matters |

### 3.3 Test-Time Scaling Results

| Model | Best@1 | Best@1.2 | Best@2 | Best@4 |
|-------|--------|----------|--------|--------|
| Dr. Kernel-14B | 73.8% | **47.8%** | 18.5% | 5.5% |
| Claude-4.5-Sonnet | 71.9% | 41.9% | 15.9% | 4.5% |

**Best@X**: Selecting best of 8 samples, % achieving ≥X× speedup

---

## 4. Comparison: Dr. Kernel vs. K-Search vs. GEAK

### Overview Comparison

| Aspect | **K-Search** | **GEAK** | **Dr. Kernel** |
|--------|--------------|----------|----------------|
| **Core Approach** | Tree search + LLM planner/implementer | Genetic algorithm + LLM mutations | **RL training (policy gradient)** |
| **Model Size** | Uses LLM at inference only | Uses LLM at inference only | **14B trained model** |
| **Inference Cost** | High (many LLM calls) | Medium | **Low (single forward pass)** |
| **Multi-turn** | Sequential world model updates | Sequential refinement | **RL with dense turn-level rewards** |
| **Key Innovation** | Decoupled planner/implementation | Code-as-gene crossover | **TRLOO + profiling-based rewards** |
| **Main Problem** | Expensive LLM calls | Premature convergence | Reward hacking, lazy optimization |

### Detailed Comparison

#### K-Search (UC Berkeley, arXiv:2602.19128)

**Strengths:**
- Explicit search tree with learned world model
- Separates WHAT to try (planner) from HOW (implementer)
- K=7 stagnation limit for exploration/exploitation balance
- 14.3× improvement over OpenEvolve on MoE kernels

**Limitations:**
- Requires LLM inference at every iteration
- No learned policy—must re-plan from scratch each time
- Tree maintenance overhead

**Best For**: Complex kernels where exploration matters more than inference cost

#### GEAK (Penn State, arXiv:2502.16161)

**Strengths:**
- Treats kernel code as genes (code-as-gene)
- Semantic crossover via LLM-guided mixing
- Diversity preservation via semantic clusters
- 2.24× average speedup on Rodinia benchmarks

**Limitations:**
- Genetic algorithms prone to premature convergence
- Fixed population size limits exploration
- No explicit reward shaping for meaningful speedup

**Best For**: Medium-complexity kernels with good crossover opportunities

#### Dr. Kernel (HKUST/TikTok, arXiv:2602.05885)

**Strengths:**
- **Low inference cost**: Single forward pass vs. many LLM calls
- **Generalization**: Trained model applies to new kernels
- **Multi-turn refinement**: Dense rewards at each step
- **Profiling-aware**: Rewards target actual bottlenecks
- **Practical deployment**: No need for LLM API calls at inference

**Limitations:**
- Requires expensive RL training (data + compute)
- Limited to Triton (though extensible)
- May not explore as broadly as tree search for novel algorithms

**Best For**: Production deployment where inference cost and latency matter

### When to Use Which?

| Scenario | Recommended Approach |
|----------|---------------------|
| **Low inference budget, many queries** | **Dr. Kernel** (trained model) |
| **Novel algorithm discovery needed** | **K-Search** (exploration-focused) |
| **Medium complexity, crossover works well** | **GEAK** (genetic algorithms) |
| **Competition with few submissions** | **K-Search** (maximize per-attempt quality) |
| **Competition with many submissions** | **Dr. Kernel** (efficient exploration) |

---

## 5. Applicability to Our Competition (Luma AMD Speedrun)

### 5.1 What Applies Directly

| Dr. Kernel Technique | AMD MI355X Applicability | Priority |
|---------------------|-------------------------|----------|
| **Multi-turn refinement** | ✅ Applicable—iteratively improve submission.py | HIGH |
| **Profiling-based rewards** | ✅ Use torch.profiler to identify bottlenecks | HIGH |
| **Reward hacking checks** | ⚠️ Partial—check kernels actually execute | MEDIUM |
| **TRLOO credit assignment** | ⚠️ Not directly—we're not training RL model | LOW |
| **KernelGYM environment** | ⚠️ Would need AMD backend adaptation | LOW |

### 5.2 Key Lessons for Our Approach

#### Lesson 1: Profiling-Based Iteration

Dr. Kernel's **Profiling-based Rewards** directly applicable:

```python
# In our submission workflow
import torch.profiler as profiler

with profiler.profile(
    activities=[profiler.ProfilerActivity.CUDA],
    record_shapes=True
) as prof:
    result = submission_kernel(*inputs)

# Analyze: what % of time is in our kernel vs. framework?
prof.export_chrome_trace("trace.json")
# Look for: actual GPU kernel time vs. Python overhead
```

**Actionable**: Before each submission, profile to ensure the kernel actually dominates runtime, not framework/Python overhead.

#### Lesson 2: Multi-Turn Refinement

Dr. Kernel's **3-turn refinement cycle** applicable manually:

```
Turn 1: Baseline (parameter tuning)
  → Profile, identify bottleneck
Turn 2: Targeted optimization (e.g., active-expert masking)
  → Profile, verify kernel coverage
Turn 3: Micro-optimizations (tile sizes, unroll)
  → Final validation
```

**Actionable**: Structure our submission attempts as explicit refinement turns with profiling feedback at each step.

#### Lesson 3: Lazy Optimization Avoidance

Dr. Kernel found models optimize trivial operations (e.g., 0.014% of runtime) while missing real bottlenecks.

**Our Risk**: Spending effort on micro-optimizations when the real issue is:
- Python dispatch overhead
- Unfused operations
- Memory layout inefficiencies

**Actionable**: Before optimizing, ask: "Does this change affect >50% of kernel runtime?" If not, find the actual bottleneck.

### 5.3 Concrete Application

#### Workflow Adaptation

```
┌─────────────────────────────────────────────────────────────────┐
│              Dr. Kernel-Inspired Workflow                        │
│                    (Manual Adaptation)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. BASELINE GENERATION                                          │
│     ├─ Run fused_moe/mla_decode_fwd with reference parameters   │
│     ├─ Profile: identify % time in kernel vs. overhead           │
│     └─ If overhead >50%: focus on dispatch/compilation        │
│                                                                   │
│  2. BOTTLENECK IDENTIFICATION (Profiling-based)                  │
│     ├─ Use torch.profiler or aiter's built-in profiling         │
│     ├─ Identify top 3 GPU kernels by time                       │
│     └─ For each: can we optimize with available APIs?           │
│                                                                   │
│  3. TARGETED OPTIMIZATION (Multi-turn)                           │
│     Turn 1: API parameter exploration (KSPLIT, fast_mode, etc.)  │
│     Turn 2: Algorithmic change (if APIs insufficient)           │
│     Turn 3: Micro-optimizations (tensor caching, preallocation)   │
│                                                                   │
│  4. VALIDATION                                                   │
│     ├─ Correctness check (reference vs. submission)             │
│     ├─ Hacking check (kernel actually executes)                  │
│     └─ Profiling check (>50% of runtime in optimized path)      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 5.4 Can RL-Based Approaches Help Our Kernels?

#### Short Answer: Limited Direct Applicability

| Factor | Assessment |
|--------|------------|
| **Competition Format** | Single submission.py file, not iterative generation |
| **Time Constraint** | 720s total, not long-horizon RL training |
| **Hardware** | AMD MI355X (gfx950), Dr. Kernel focuses on NVIDIA |
| **Kernel Type** | AITER fused ops (pre-built), not custom Triton |

#### Medium Answer: Adaptable Principles

**Cannot use directly:**
- RL training (requires days of GPU time)
- KernelGYM environment (NVIDIA-focused)
- Dr. Kernel model (trained on Triton, not AMD CDNA4)

**Can adapt:**
- Profiling-based reward concept → profile before optimizing
- Multi-turn refinement → structured submission attempts
- Lazy optimization avoidance → focus on actual bottlenecks
- Hacking check concept → verify kernels actually execute

#### Recommended Hybrid Approach

```
Our Recommended Strategy (Hybrid):
├─ Phase 1: Parameter Tuning (exhausted)
├─ Phase 2: Dr. Kernel-style profiling-based iteration
│   ├─ For each attempt: profile end-to-end
│   ├─ Identify actual GPU kernel time
│   ├─ If Python overhead dominates → load_inline, direct CK
│   └─ If GPU kernel dominates → optimize kernel internals
├─ Phase 3: K-Search-style tree tracking
│   ├─ Maintain search tree of strategies
│   ├─ K=7 stagnation limit per strategy
│   └─ Prioritize by estimated impact on runtime
└─ Phase 4: Final validation (Dr. Kernel-style checks)
    ├─ Correctness verification
    ├─ Execution verification (hacking check)
    └─ Profiling verification (lazy opt check)
```

---

## 6. Key Findings Summary

### 6.1 Dr. Kernel Achievements

1. **First successful RL training** for Triton kernel generation
2. **Competitive with frontier models** (Claude-4.5-Sonnet, GPT-5)
3. **Solved reward hacking** via execution-based checks
4. **Solved lazy optimization** via profiling-based rewards
5. **Introduced TRLOO** for unbiased multi-turn RL

### 6.2 Critical Insights

| Insight | Implication for Our Work |
|---------|-------------------------|
| Profiling-based rewards crucial | Always profile before optimizing |
| Multi-turn refinement helps | Structure attempts as iterations |
| Models exploit trivial optimizations | Focus on actual runtime bottlenecks |
| Execution verification necessary | Verify kernel actually runs |
| Training expensive, inference cheap | Pre-compute strategies offline |

### 6.3 Limitations

- Trained on NVIDIA, limited AMD applicability
- Focuses on Triton, not CK/ASM kernels
- Requires significant training resources
- May not discover novel algorithms (policy converges)

---

## 7. References

1. **Dr. Kernel Paper**: Liu et al., "Dr. Kernel: Reinforcement Learning Done Right for Triton Kernel Generations", arXiv:2602.05885, Feb 2026
2. **KernelGYM**: https://github.com/hkust-nlp/KernelGYM
3. **K-Search**: arXiv:2602.19128 (see research document)
4. **GEAK**: arXiv:2502.16161 (see research document)
5. **KernelBench**: https://github.com/ScalingIntelligence/KernelBench

---

## 8. Action Items

### Immediate (This Session)

- [ ] Profile current MoE/MLA/GEMM submissions with torch.profiler
- [ ] Calculate: what % of time is actual GPU kernel vs. Python overhead?
- [ ] If overhead >30%: prioritize dispatch optimization strategies

### Short-term (Next Sessions)

- [ ] Implement structured "turns" for submissions (like Dr. Kernel's 3-turn)
- [ ] Add execution verification (hacking check) to submission validation
- [ ] Maintain profiling log to track actual optimization impact

### Research Follow-up

- [ ] Investigate if Dr. Kernel model/methods can be adapted for AMD
- [ ] Study if profiling-based rewards can guide manual search
- [ ] Compare Dr. Kernel efficiency vs. K-Search for our workload

---

*Research completed: April 6, 2026*
*Researcher: OpenCode*
*Next research target: HipKittens or KernelFoundry (if needed)*
