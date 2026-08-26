# SKILL: KAGGLE_EMBEDDED_AGENT_SWARMS_PRIME

## DOMAIN EXPERTISE
Embedding zero-dependency, autonomous multi-agent swarms (Hypothesis Generator, DSL Code Synthesizer, AutoHarness Verifier, Error Reflector) directly inside single-file offline Kaggle submission kernels across dual-T4 GPUs and CPUs.

## KEY TEXTS & CONCEPTS
- **The Embedded Swarm Advantage**:
  * Instead of a static, linear inference pipeline, the kernel acts as an **autonomous collaborative laboratory** that runs for the full 9-hour budget.
  * Multi-agent debate and consensus loops synthesize, verify, reject, and mutate candidate solutions until convergence.
- **4 Specialized In-Memory Micro-Agent Roles**:
  1. **`HypothesisAgent` (CPU / Memory)**:
     - Extracts topological invariants, color counts, and coordinate symmetries ($O(N^2)$ in $<0.01\text{ms}$).
     - Formulates natural language and symbolic hypothesis tags (e.g. `ROT_90 + COLOR_INVERT`).
  2. **`ProgramSynthesizerAgent` (GPU 1 / Qwen-Coder-7B)**:
     - Consumes the hypothesis tag and generates structured Python/DSL transformation functions.
  3. **`VerifierAgent` (CPU / 0ms AutoHarness Verifier)**:
     - Compiles candidate AST code to bytecode and validates against train input/output grids.
     - Detects infinite recursion, out-of-bounds indexing, or shape mismatches with zero latency.
  4. **`ReflectorAgent` (GPU 0 / DeepSeek-R1-Distill-7B-AWQ)**:
     - Analyzes verifier error traces (e.g. "Failed on Pair 2: expected 4x4, got 3x3") and mutates the hypothesis or prompt context.

## INSTRUCTION

1. **Embedded Swarm Orchestration Loop in `submission.py`**:
```python
class EmbeddedKaggleSwarm:
    """Coordinates in-memory multi-agent hypothesis, synthesis, verification, and reflection."""
    def __init__(self, task: dict, time_budget: float = 60.0):
        self.task = task
        self.time_budget = time_budget
        self.hypotheses = []
        self.verified_programs = []

    def run_swarm_loop(self):
        t0 = time.perf_counter()
        # Step 1: Hypothesis Agent
        hyp = HypothesisAgent.analyze(self.task)
        
        while (time.perf_counter() - t0) < self.time_budget:
            # Step 2: Synthesizer Agent (GPU 1)
            code = ProgramSynthesizerAgent.generate(self.task, hyp)
            
            # Step 3: Verifier Agent (CPU AST)
            passed, err = VerifierAgent.verify(self.task, code)
            if passed:
                return code
                
            # Step 4: Reflector Agent (GPU 0)
            hyp = ReflectorAgent.mutate(hyp, err)
            
        return FallbackHeuristics.best_guess(self.task)
```

## VERSION
v1.0

## SEE ALSO
- `KAGGLE_EMBEDDED_WORLD_MODELS_PRIME`
- `LOCAL_TO_KAGGLE_HARNESS_SYNERGY_PRIME`
- `VMODEL_SYSTEMS_ENGINEERING_PRIME`
