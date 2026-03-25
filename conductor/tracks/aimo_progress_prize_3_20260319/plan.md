# Track: AIMO Progress Prize 3 - Mathematical Reasoning Swarm

## Objective
To win the **AI Mathematical Olympiad (AIMO) Progress Prize 3** ($2,207,152 prize pool) by developing a high-fidelity **Mathematical Reasoning Swarm**. This swarm will leverage Cohezion's **FLUME methodology** and **12D triune manifold** to solve IMO-level LaTeX problems with high stability and penalized accuracy.

## Key Files & Context
- **Competition Page**: [Kaggle AIMO Progress Prize 3](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3)
- **Problem Format**: LaTeX (Text-only).
- **Target Models**: DeepSeek-R1 (70B/32B), GPT-OSS-120B.
- **Cohezion Core**: `src/cohezion/flume/`, `src/cohezion/swarm/`, `src/cohezion/universe/`.
- **New Track Root**: `conductor/tracks/aimo_progress_prize_3_20260319/`

## Implementation Steps
### Phase 1: Environment & API Integration
- [ ] Set up the AIMO Python evaluation API in a local sandbox.
- [ ] Create a "Math Problem Parser" to convert LaTeX into a multi-manifold state vector (12D).
- [ ] Integrate the 10 reference problems for benchmarking.

### Phase 2: Reasoning Swarm Development
- [ ] Implement the **Specialist Swarm**:
    - **Algebraist**: Specialized in symbolic manipulation (SymPy).
    - **Geometer**: Specialized in spatial reasoning without diagrams.
    - **Number Theorist**: Specialized in modular arithmetic and prime theory.
    - **Combinatorist**: Specialized in counting and probability.
- [ ] Develop the **FLUME Proof Navigator**:
    - Uses VAE-compressed "thought vectors" to interpolate between known mathematical identities.
    - Identifies "stable proof trajectories" (HIHO Stability at 0.5 coherence).

### Phase 3: Verification & Stability
- [ ] Implement **Dual-Run Verification**:
    - Ensures the model produces the same integer (0-99,999) in two independent runs.
    - Uses "Adversarial Review" agents to poke holes in proof logic.
- [ ] Add **Python-based Simulation (Monte Carlo)** for probabilistic confirmation of answers.

### Phase 4: Submission & Optimization
- [ ] Optimize for the 5-hour H100 compute limit.
- [ ] Fine-tune local SLMs for "Math Reasoning" to offload simpler sub-tasks.

## Verification & Testing
- **Internal Benchmark**: Solve 100% of the AIMO reference problems.
- **Stability Test**: Achieve >90% consistency in dual-run integer output on AIME-level problems.
- **Safety**: Ensure LaTeX rendering and Python execution are sandboxed.
