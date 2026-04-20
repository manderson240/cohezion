# Cohezion Compound Session: Luma-Symmetry-SASS

## Session Context
- **Goal**: Reach Rank 1 on all 3 Luma AMD leaderboards (GEMM, MLA, MoE).
- **Hardware**: MI355X (gfx950).
- **Core Hypothesis**: The "Symmetry" pattern (Specialized Micro-Kernels + Pure Triton + Slab Allocation) is the only path to Top 10 compliance and performance.

## Compound Layout
The following Cohezion components are instantiated for this session:

### 1. Skill Definition (PRIME)
We treat "Symmetric-Triton-Kernel-Generation" as a PRIME skill.
- **Inputs**: {M, N, K, Hardware_Profile, Compliance_Constraints}
- **Process**:- Generate Symmetry-Tiling Hypothesis $\rightarrow$ Generate Triton-SASS $\rightarrow$ Local V&V $\rightarrow$ Runner Submission.
- **Success Metric**: Geometric Mean of Benchmark Latency.

### 2. Journey Tracking
Every submission is recorded as a state transition in the 12D universe:
- `phase`: "Symmetry-Search"
- `position`: {Tiling_Params, Warp_Config, Stage_Count}
- `coherence`: (Latency / Reference_Latency)

### 3. Alignment Gate (HIHO)
Before any submission, the `RequestAlignmentAnalyzer` checks the proposed tiling against the GFX950 MFMA constraints (e.g., 16x16x128).
- **Threshold**: If the tiling is not MFMA-aligned, the submission is blocked.

### 4. Retrospection Engine
After each Runner result:
- **S500 Error** $\rightarrow$ Log as "Compliance Inflection" $\rightarrow$ Trigger "Launderer" wrap.
- **Timeout** $\rightarrow$ Log as "Bandwidth Bottleneck" $\rightarrow$ Trigger "Register-Fusion" refill.
- **SOTA Latency** $\rightarrow$ Log as "Hardware Truth" $\rightarrow$ Update `Symmetry_Shed` in Vault.

## Execution Loop
`AutonomousCompoundLoop` $\rightarrow$ `LLMExecutor (Triton-Symmetry)` $\rightarrow$ `popcorn-cli` $\rightarrow$ `RetrospectionEngine` $\rightarrow$ `SkillRefiner`.
