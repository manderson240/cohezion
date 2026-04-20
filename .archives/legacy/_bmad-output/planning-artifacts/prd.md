---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
inputDocuments:
  - /home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/analysis/research-summary.md
  - /home/mike-anderson/dev/cohezion/_bmad-output/project-context.md
  - https://arxiv.org/html/2602.19128v1 (K-Search: LLM Kernel Generation via Co-Evolving Intrinsic World Model)
workflowType: prd
briefCount: 0
researchCount: 2
brainstormingCount: 0
projectDocsCount: 1
classification:
  projectType: Developer Tool / Optimization Framework
  domain: High-Performance Computing / GPU Optimization
  complexity: High
  projectContext: Greenfield
---

# Product Requirements Document - R-Zero Challenger Framework

**Author:** Mike-anderson
**Date:** 2026-03-17
**Version:** 1.0

---

## Executive Summary

The R-Zero Challenger Framework is an advanced optimization system for competitive GPU kernel development, inspired by cutting-edge research from UC Berkeley's K-Search (arXiv:2602.19128v1). The framework implements a "Search via Co-Evolving World Model" approach to systematically explore kernel variants and achieve breakthrough performance on the Luma AMD Speedrun competition.

**Key Innovation:** Unlike traditional evolutionary methods that treat LLMs as stochastic code generators, R-Zero decouples high-level algorithmic planning from low-level program instantiation, enabling navigation of non-monotonic optimization paths while remaining resilient to temporary implementation defects.

---

## Project Classification

- **Project Type:** Developer Tool / Optimization Framework
- **Domain:** High-Performance Computing / GPU Optimization
- **Complexity:** High
- **Project Context:** Greenfield
- **Target Hardware:** AMD MI355X (gfx950/CDNA4)
- **Competition:** Luma AMD Speedrun ($650K prize pool)

---

## Background Research

### 1. AITER Kernel Analysis (Existing)

**GEMM Optimization Patterns:**
- 20+ pre-compiled kernels in `/tmp/aiter/hsa/gfx950/f4gemm/`
- Tile sizes: 32×128 to 256×256
- Small M (≤32): Use 32×128/256/512 with high split-K
- Large M (>128): Use 192×128 or 256×128 with no split-K

**MoE Architecture:**
- Two-stage: Stage1 (ASM) + Stage2 (reduction)
- OPUS sorting improves routing efficiency
- Block size: 32 optimal
- Critical: `doweight_stage1=True` is broken

**MLA Implementation:**
- Two-stage: Q×K (ASM) + Softmax×V (Triton)
- Metadata: Complex work distribution system
- num_kv_splits formula: Minimize (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + 84.1 * i)

## Hybrid Methodology: R-Zero + K-Search + AutoResearch

Our approach combines three cutting-edge autonomous research methodologies into a unified framework optimized for GPU kernel optimization.

### 1. R-Zero: Self-Evolving Challenger-Solver Loop (Tencent AI Lab)

**Paper:** "R-Zero: Self-Evolving Reasoning LLM from Zero Data" (arXiv:2508.05004)

**Core Innovation:**
Dynamic co-evolution between two model instances without any pre-existing data:
- **Challenger 🎯:** Generates problems at the edge of Solver's capabilities
- **Solver 🧠:** Improves by solving increasingly difficult tasks
- **Result:** Progressive improvement through adaptive curriculum

**Application to GPU Kernels:**
- Challenger generates aggressive kernel variants (high split-K, large tiles)
- Solver evaluates performance on MI355X via popcorn-cli
- Co-evolution discovers which optimizations actually work
- Zero human GPU expertise required

### 2. K-Search: World Model-Guided Search (UC Berkeley)

**Paper:** "K-Search: LLM Kernel Generation via Co-Evolving Intrinsic World Model" (arXiv:2602.19128v1)

**Core Innovation:**
LLM as world model maintaining search tree with explicit planning:
- **Frontier-based search:** Priority scores V ∈ [0,1] for each hypothesis
- **Stagnation condition:** K=7 attempts before discarding strategy
- **Tree structure:** Closed nodes (evaluated) + Open nodes (frontier)
- **Co-evolution:** World model updates based on execution feedback

**Application to GPU Kernels:**
- World model estimates which kernel configurations will perform best
- Maintains frontier of pending optimizations to explore
- Updates beliefs based on actual MI355X execution results
- Avoids discarding promising strategies due to transient errors

### 3. AutoResearch: Fixed-Time Iteration (karpathy)

**Repository:** https://github.com/karpathy/autoresearch

**Core Innovation:**
Autonomous experimentation with fixed-time budget:
- **Fixed time budget:** Each experiment runs exactly 5 minutes
- **Single file modification:** Isolate changes to submission files
- **Metric-driven:** Track speedup_ratio as primary optimization metric
- **Self-contained:** No external dependencies beyond PyTorch

**Application to GPU Kernels:**
- Each challenger evaluation gets fixed evaluation budget
- Modify only submission.py (like train.py in autoresearch)
- Fixed utilities (rzero-eval.py) provide consistent testing
- Overnight autonomous iteration with morning review

### 4. Unified Hybrid Framework

**Synthesis of All Three Approaches:**

```
R-Zero-K-Auto Hybrid Loop:
├── Phase 1: Challenger Generation (R-Zero style)
│   ├── Generate kernel variants at performance frontier
│   ├── Use K-Search world model to prioritize promising configs
│   └── Apply AutoResearch fixed-time budget per evaluation
│
├── Phase 2: Solver Evaluation (R-Zero + AutoResearch)
│   ├── Submit to MI355X via popcorn-cli (fixed time)
│   ├── Evaluate correctness (rtol=1e-2)
│   └── Measure speedup_ratio vs reference
│
├── Phase 3: World Model Update (K-Search style)
│   ├── Update priority scores based on results
│   ├── Insert new hypotheses to frontier
│   ├── Update existing node beliefs
│   └── Prune underperforming branches
│
└── Phase 4: Co-Evolution (All three)
    ├── Challenger learns which strategies work (R-Zero)
    ├── World model refines transition dynamics (K-Search)
    └── Fixed-time iteration continues overnight (AutoResearch)
```

**Key Advantages of Hybrid Approach:**
1. **R-Zero:** Self-evolution from zero data, no human expertise needed
2. **K-Search:** Explicit world model prevents discarding good strategies
3. **AutoResearch:** Fixed-time budget enables fair comparison across variants
4. **Combined:** Systematic exploration + intelligent prioritization + autonomous execution

**Why This Wins:**
- Most competitors use manual tuning or simple grid search
- Some use basic evolutionary methods (discard promising strategies)
- Our hybrid: Self-evolving + World model guidance + Fixed-time rigor
- Result: Discovers optimizations others miss, resilient to transient failures

**Repository:** https://github.com/karpathy/autoresearch

**Key Concepts:**
- **Autonomous Experimentation:** AI agents modify code, run experiments, evaluate results, and iterate without human intervention
- **Fixed Time Budget:** Each experiment runs for exactly 5 minutes wall clock, making results comparable across different model sizes and architectures
- **Single File Modification:** Agent only modifies `train.py` while `prepare.py` provides fixed utilities and `program.md` contains human instructions
- **Self-Contained:** No external dependencies beyond PyTorch, designed for single-GPU setups
- **Metric-Driven:** Uses `val_bpb` (validation bits per byte) - lower is better, vocab-size-independent for fair comparison

**Integration Strategy:**
- Apply autoresearch "skill" concept to R-Zero via `program.md` files
- Use fixed-time evaluation budget instead of fixed-iteration count
- Isolate modifications to submission files only (like `train.py`)
- Maintain separate fixed utilities (`prepare.py` equivalent)
- Track `speedup_ratio` as the primary optimization metric

**Autonomous Research Loop:**
1. Agent reads `program.md` for context and instructions
2. Modifies submission file (e.g., `submission.py`)
3. Runs local evaluation against reference (5-minute budget)
4. Checks if `speedup_ratio` improved
5. Keeps or discards changes based on results
6. Repeats overnight with human reviewing logs in morning

**Key Insights:**
- Traditional evolutionary methods treat LLMs as stochastic code generators
- K-Search uses LLM as "World Model" for planning
- Decouples algorithmic planning from implementation
- Achieves 2.10× improvement over OpenEvolve
- Up to 14.3× gain on complex MoE kernels
- State-of-the-art on GPUMode TriMul task (1030µs on H100)

**Three-Phase Search Process:**
1. **Action Selection:** Select most promising hypothesis from frontier based on world model estimated priority score
2. **Local Refinement:** Stochastic policy samples concrete implementations until stagnation (K=7 consecutive failures)
3. **World Model Update:** LLM reasons over trajectory to update search tree via Insert, Update, and Prune operations

**Critical Differentiators:**
- Frontier-based search (not archive-based)
- Priority scores V ∈ [0,1] estimated by world model
- Stagnation condition prevents discarding valid strategies due to transient errors
- Tree-structured state with Closed and Open nodes
- Co-evolution: World model refines based on execution feedback via in-context learning

---

## Goals and Objectives

### Primary Goals

1. **Achieve Top 10 on Luma AMD Speedrun Leaderboard**
   - GEMM: ≤10µs (current ~20.8µs, leader 9.671µs)
   - MLA: ≤15µs (current ~72µs, leader ~4.3µs)
   - MoE: ≤145µs (current ~155µs, leader ~145µs)

2. **Systematic Search via Co-Evolving World Model**
   - Generate 100 diverse kernel variants
   - Evaluate locally against reference implementations
   - Select top performers via tournament selection
   - Mutate and evolve until breakthrough achieved

3. **Research Contribution**
   - Adapt K-Search methodology to AMD MI355X (CDNA4) architecture
   - Document patterns for FP4/MXFP4 quantization on AMD GPUs
   - Create reusable framework for future competitions

### Success Metrics

| Kernel | Current | Target | Speedup Required |
|--------|---------|--------|------------------|
| GEMM | 20.8µs | 10µs | 2.08× |
| MLA | 72µs | 15µs | 4.8× |
| MoE | 155µs | 145µs | 1.07× |

**Combined Impact:** Should reach Top 10 overall ranking (~$650K prize pool)

---

## Architecture Overview

### Core Components

```
R-Zero Challenger Framework
├── rzero-challengers/          # Generated kernel variants
│   ├── gemm/                   # 33 challengers
│   ├── moe/                    # 33 challengers
│   └── mla/                    # 34 challengers
├── rzero-eval.py               # Local evaluation framework
├── rzero_select.py             # Tournament selection
├── rzero_mutate.py             # Evolutionary operators
└── rzero-results/              # Performance logs
```

### Three-Phase Workflow (Based on K-Search)

**Phase 1: Challenger Generation (Iterations 1-20)**
- Grid search over parameter space
- Generate 100 diverse candidates
- Test shapes from competition benchmarks

**Phase 2: Selection & Mutation (Iterations 21-60)**
- Tournament selection: Random pairing, winner advances
- Keep top 20% from each kernel
- Mutate middle 30% via parameter perturbation
- Crossover: Combine best features from multiple winners

**Phase 3: Deep Refinement (Iterations 61-100)**
- Micro-optimization: Fine-tune thresholds by 1-2%
- Shape-specific variants for per-shape specialization
- Hybrid approaches combining multiple winning strategies
- **Breakthrough Criteria:**
  - GEMM: <12µs
  - MoE: <150µs
  - MLA: <20µs

### Evaluation Framework

**Local Testing Against Reference:**
```python
def evaluate_challenger(challenger_file, reference_func):
    # Load challenger
    # Run on test shapes: (4, 2880, 512), (16, 2112, 7168), etc.
    # Compare to reference implementation
    # Check correctness: rtol=1e-2, atol=1e-2
    # Return: (speedup_ratio, is_correct, error_message)
```

**Success Criteria per Iteration:**
- Pass if: correctness OK + faster than baseline
- Fail if: incorrect OR slower
- Track: speedup vs reference, correctness pass/fail, generation time

---

## Technical Requirements

### Hardware Requirements (Development vs Target)

**Development Environment (Current):**
- AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (gfx1151)
- ROCm 6.x with HIP runtime
- Shared memory architecture
- Note: This is a development/testing platform

**Target Competition Environment:**
- AMD MI355X GPU (gfx950/CDNA4 architecture)
- ROCm 6.0+ with HIP runtime
- HBM3 memory (128-bit global→LDS transfers)
- 304 Compute Units
- Located on Luma competition servers

### Platform Architecture

**Development Platform (Local Silicon) - VERIFIED SPECS:**
```
CPU: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S
- Cores: 16 cores, 32 threads
- Memory: 125GB RAM
- Disk: 1.5TB ZFS (326GB used, 1.1TB free)
- OS: Ubuntu 24.04.1, Kernel 6.17.0-14

GPU: AMD Radeon Graphics (gfx1151)
- Architecture: RDNA3.5 (APU/Integrated)
- Compute Units: 40 CUs
- Wavefront Size: 32 threads
- VRAM: 512MB (APU shared memory)
- L1 Cache: 32KB
- L2 Cache: 2MB
- L3 Cache: 32MB
- Max Clock: 2900 MHz
- Features: Fast F16 Operation, KERNEL_DISPATCH
```

**Deployment Platform (Runner) - TARGET SPECS:**
```
GPU: AMD MI355X (gfx950/CDNA4)
- Architecture: CDNA4 (Discrete Data Center GPU)
- Compute Units: 304 CUs (7.6× more than local)
- Wavefront Size: 64 threads (2× local)
- Memory: HBM3 (High Bandwidth Memory)
- Cache: Multi-level with LDS (Local Data Share)
- Features: Full AITER library, MFMA instructions
```

**Critical Architecture Differences:**
| Feature | Local (gfx1151) | Runner (gfx950) | Impact |
|---------|-----------------|-----------------|---------|
| CUs | 40 | 304 | Runner has 7.6× parallelism |
| Wavefront | 32 | 64 | Different thread scheduling |
| Memory | 512MB shared | HBM3 dedicated | Runner has bandwidth advantage |
| Architecture | RDNA3.5 (APU) | CDNA4 (Data Center) | Different optimization targets |
| AITER | Not available | Full support | Can only test on runner |

**Two-Phase Workflow:**
```
Phase 1: Local Development (gfx1151)
├── Generate challenger variants
├── Validate Python syntax and imports
├── Test basic logic structure
├── Prepare submission files
└── Note: Cannot execute AITER kernels locally

Phase 2: Runner Deployment (MI355X)
├── Submit to competition servers via popcorn-cli
├── Execute on gfx950 with full AITER
├── Get actual performance metrics
├── Results feed back to local iteration
└── Iterate based on real performance data
```

**Platform-Specific Considerations:**
- Local: Python development, file generation, version control
- Runner: Actual GPU kernel execution, AITER library, performance profiling
- Custom HIP kernels: Can compile locally but target gfx950 for runner
- Reference implementations: Work on both (PyTorch-based)

### Software Requirements
- Python 3.13+
- PyTorch 2.8.0+ with ROCm 6.0+ support
- AITER library (AMD's optimized kernels for gfx950)
- hipcc compiler (ROCm 6.0+, gfx950 target)
- FlashInfer 0.5.3 (ROCm port)

### MI355X Hardware Verification
```bash
# Verify MI355X detection
rocminfo | grep -E "(Name|Device|gcnArchName)"
# Should show: gfx950

# Verify ROCm version
rocm-smi --showdriverversion
# Should show: 6.0+

# Test AITER installation
python3 -c "import aiter; print(aiter.__version__)"
```

### Key Dependencies
```
aiter>=0.5.0          # AMD optimized kernels
torch>=2.8.0          # PyTorch with ROCm
numpy>=1.24.0         # Numerical operations
pytest>=8.0.0         # Testing framework
pytest-asyncio>=0.23  # Async test support
```

---

## Implementation Strategy

### Wave 1: Foundation (Days 1-3)

**Tasks:**
1. Complete existing `gemm_final.hip` integration
2. Create Python wrapper using ctypes
3. Compile with `hipcc -O3 --offload-arch=gfx950`
4. Test all competition shapes

**Deliverables:**
- Working GEMM submission targeting 9.7µs
- Build system for HIP kernels
- Local evaluation pipeline

### Wave 2: MLA Breakthrough (Days 4-7)

**Tasks:**
1. Complete `mla_top10.hip` implementation
2. Add FP4 lookup table in constant memory
3. Implement wave shuffle for softmax
4. Fuse dequantization with attention

**Key Optimizations from K-Search:**
```cpp
__constant__ float FP4_LUT[16] = {...};

__device__ __forceinline__ float wave_max(float val) {
    for (int offset = 32; offset > 0; offset /= 2)
        val = fmaxf(val, __shfl_xor(val, offset));
    return val;
}
```

**Deliverables:**
- MLA kernel achieving <20µs
- Wave-level primitives implementation
- Single-stage fused attention

### Wave 3: MoE Polish (Days 8-10)

**Tasks:**
1. Implement adaptive KSPLIT based on token distribution
2. Enable OPUS sorting
3. Test all expert configurations (32E, 256E)
4. Validate against FlashInfer baseline

**Deliverables:**
- MoE kernel achieving <150µs
- Environment variable tuning system
- Comprehensive test coverage

### Wave 4: Integration & Submission (Days 11-14)

**Tasks:**
1. Create unified submission pipeline
2. Batch test all kernels
3. Fine-tune based on results
4. Final leaderboard push

**Deliverables:**
- Top 10 leaderboard submission
- Complete documentation
- Research artifacts for future competitions

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HIP compilation fails | Medium | High | Test locally first, fallback to reference |
| Numerical accuracy issues | High | High | Test with rtol=1e-2, validate all shapes |
| MLA kernel slower than expected | Medium | High | Profile with rocprof, optimize hotspots |
| Time overrun | Low | Medium | Prioritize MLA (biggest impact) |
| Hardware availability | Low | Critical | Ensure MI355X access confirmed |

---

## Research Artifacts

### Documentation
- Vault documentation in `~/vaults/cohezion-vault/luma-amd-speedrun-kimi-k2-5/`
- Patterns: GEMM tile optimization, MoE KSPLIT strategies
- Failures: `doweight_stage1=True` is broken
- Decisions: Prioritize custom HIP over Python tuning

### Code Artifacts
- 18 submission variants (v1-v6 for all 3 kernels)
- Research analysis document
- Local evaluation framework
- R-Zero challenger generation system

### External References
- **K-Search Paper:** https://arxiv.org/html/2602.19128v1 (UC Berkeley)
- **AITER Repository:** `/tmp/aiter/` (AMD optimized kernels)
- **Competition Rules:** https://luma.com/cqq4mojz?tk=5NV3rC
- **Project Context:** `~/vaults/cohezion-vault/`

---

## Conclusion

The R-Zero Challenger Framework represents a systematic approach to GPU kernel optimization, combining:
1. **Deep hardware research** (MI355X/gfx950 architecture)
2. **Cutting-edge methodology** (K-Search's co-evolving world model)
3. **Systematic evaluation** (100 local iterations before submission)
4. **Breakthrough focus** (Top 10 on $650K competition)

By decoupling high-level planning from low-level implementation and maintaining a co-evolving world model, we can navigate non-monotonic optimization paths and achieve breakthrough performance that would be impossible with traditional evolutionary approaches.

**Ready to proceed to Phase 3: Solutioning**

---

## Success Criteria

### User Success

**Primary User Outcome:** 
Users with zero GPU kernel optimization experience can achieve Top 10 performance on competitive leaderboards through autonomous AI-guided optimization.

**Specific Success Metrics:**
- **Competition Performance:** Top 10 ranking on all three Luma AMD Speedrun leaderboards (GEMM, MLA, MoE)
- **Educational Value:** Complete tutorial series enabling replication by inexperienced users
- **Autonomy Level:** Zero human GPU expertise required during optimization process
- **Discovery Quality:** Systematic exploration of 100+ kernel variants with documented learnings

**Emotional Success Moments:**
- "I can't believe we achieved Top 10 without knowing anything about GPU kernels!"
- "The tutorials made it clear exactly what optimizations worked and why"
- "The system discovered optimizations I never would have thought of"

### Business Success

**Primary Business Outcome:**
Win $650K prize pool from Luma AMD Speedrun competition while establishing framework as reference implementation for autonomous GPU optimization.

**Specific Success Metrics:**
- **Financial:** Prize winnings from Top 10 placement (estimated $50K-$100K)
- **Reputation:** Recognition as first fully autonomous GPU optimization system to win major competition
- **Adoption:** Framework used as reference for future competitions and research
- **Timeline:** 14-day execution from start to Top 10 submission

**3-Month Success:**
- Complete documentation and tutorial series published
- Framework adapted for other GPU architectures (NVIDIA, Intel)
- Community contributions and forks

**12-Month Success:**
- Multiple competition wins using R-Zero methodology
- Academic paper publication on autonomous GPU optimization
- Open-source community maintaining and extending framework

### Technical Success

**Primary Technical Outcome:**
Implement true R-Zero methodology (Challenger-Solver co-evolution) for GPU kernel optimization, achieving breakthrough performance through self-evolution from zero data.

**Specific Success Metrics:**

**Performance Targets:**
| Kernel | Baseline | Target | Leader | Required Speedup |
|--------|----------|--------|--------|------------------|
| GEMM | 20.8µs | ≤10µs | 9.671µs | 2.08× |
| MLA | 72µs | ≤15µs | ~4.3µs | 4.8× |
| MoE | 155µs | ≤145µs | ~145µs | 1.07× |

**Hybrid Methodology Implementation:**
- ✅ R-Zero: Challenger generates variants, Solver evaluates, co-evolution
- ✅ K-Search: World model with priority scores V ∈ [0,1], frontier-based search
- ✅ AutoResearch: Fixed-time budget (5 min), single-file modification
- ✅ Combined: Systematic exploration + intelligent prioritization + autonomous execution

**Technical Requirements:**
- 100+ kernel variants generated and evaluated
- Systematic parameter exploration (tile sizes, split-K, KSPLIT, num_kv_splits)
- Deep MI355X exploitation (MFMA 16x16, 128-bit LDS, FP4 instructions)
- Correctness validation: rtol=1e-2, atol=1e-2 against reference

### Measurable Outcomes

**Quantitative:**
- Top 10 on all three leaderboards (verified by competition results)
- 100+ challenger variants evaluated
- 14-day timeline adherence
- Tutorial completion rate: 100% (all steps documented)

**Qualitative:**
- Educational content enables inexperienced users to replicate success
- Framework demonstrates autonomous discovery of breakthrough optimizations
- Research contribution: First hybrid R-Zero/K-Search/AutoResearch implementation for GPU kernels

---

## Product Scope

### MVP - Minimum Viable Product (Days 1-14)

**Must Have:**
- Working submissions for all three kernels (GEMM, MLA, MoE)
- Top 10 leaderboard placement achieved
- Basic documentation of optimization strategies
- 100 challenger variants generated and evaluated

**Success Criteria:**
- Submit to all three leaderboards
- Achieve measurable performance improvements
- Document which optimizations worked

### Growth Features (Post-MVP)

**Should Have:**
- Comprehensive tutorial series (7+ walkthroughs)
- Custom HIP kernel development beyond AITER
- Multi-architecture support (NVIDIA, Intel)
- Automated submission pipeline
- Performance regression testing

**Success Criteria:**
- Tutorial enables replication by new users
- Framework wins additional competitions
- Community adoption and contributions

### Vision (Future)

**Could Have:**
- Fully autonomous research agent (no human intervention)
- Real-time kernel optimization during model training
- Cross-platform GPU optimization (cloud, edge, mobile)
- Academic publication on autonomous optimization
- Commercial product for ML infrastructure optimization

**Success Criteria:**
- Zero human input required for new competitions
- Framework discovers novel optimization techniques
- Industry adoption for production ML systems
