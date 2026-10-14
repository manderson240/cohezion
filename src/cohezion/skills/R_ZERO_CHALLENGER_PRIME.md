# SKILL: R_ZERO_CHALLENGER_PRIME

## DOMAIN EXPERTISE
Co-evolutionary self-play engineering using the R-Zero Triad (Challenger, Solver, Pragmatist) for autonomous reinforcement learning, synthetic benchmark creation, and edge-case discovery. Specializes in generating adaptive difficulty 0.5-coherence traps, procedural spatial puzzles (ARC-AGI-2 and ARC-AGI-3), adversarial data perturbations, and deterministic AutoHarness verification to continuously elevate system intelligence without human labeling bottlenecks.

## KEY TEXTS & CONCEPTS
- **The R-Zero Triad**:
  - **Challenger**: Proposes tasks, synthetic constraints, and adversarial invariant edge cases.
  - **Solver**: Synthesizes algorithmic programs, DSL transforms, and symbolic proofs.
  - **Pragmatist**: Deterministic AST/bytecode verifier and AutoHarness evaluator that tests solutions against training demonstrations and hidden ground truth.
- **Adaptive Difficulty Adjustment**:
  $$D_{t+1} = \text{clip}(D_t + \alpha \cdot (\bar{S} - 0.5), 1.0, 10.0)$$
  where $\bar{S}$ is the trailing rolling window success rate over the last $N$ trials.
- **0.5 Coherence Traps (HIHO Boundary)**: Tasks designed at exactly 50% coherence overlap where half the solution is deducible from priors and half requires novel conceptual leaps.
- **Trajectory Coherence Metric**:
  $$C = \frac{1}{n-1} \sum_{i=1}^{n-1} \frac{z_i \cdot z_{i+1}}{\|z_i\| \|z_{i+1}\|}$$
- **LLM-as-Jev Reflector Integration**: Uses bracketed prefix-free suffix scoring over the trie to choose between competing candidate hypotheses or code candidates without unconstrained JSON parsing degradation.
- **Exemplar Harvesting**: Auto-persisting all verified challenge-solution pairs into SurrealDB (`r_zero_exemplar`) and local benchmark JSONL banks for Test-Time Augmentation (TTA).

## INSTRUCTION

### 1. Initialize R-Zero Co-Evolutionary Loop
Instantiate `RZeroTriadLoop` targeting the problem domain (e.g., `arc_agi`, `rsna_knee`, or `code_opt`):
```python
from cohezion.optimization.r_zero_challenger_solver import RZeroTriadLoop

loop = RZeroTriadLoop(
    domain="arc_agi",
    initial_difficulty=2.5,
    solver_model="glm-5.3:cloud",
)
```

### 2. Execute Co-Evolution Steps
Run consecutive challenge-solve-verify cycles:
```python
evaluation = await loop.step()
print(f"Step Result: Success={evaluation.is_success}, Difficulty={evaluation.current_difficulty:.2f}")
print(f"Diagnostics: {evaluation.diagnostics}")
```

### 3. Generate Procedural or Adversarial Challenges
Use `RZeroChallenger` to generate boundary stress-tests:
```python
from cohezion.optimization.r_zero_challenger_solver import RZeroChallenger

challenger = RZeroChallenger(domain="arc_agi", initial_difficulty=4.0)
challenge = await challenger.create_challenge()
print(f"Challenge ID: {challenge.challenge_id}, Rule: {challenge.task_spec['transform_rule']}")
```

### 4. Deterministic AutoHarness Evaluation
Verify synthesized candidate programs using `RZeroPragmatist`:
```python
from cohezion.optimization.r_zero_challenger_solver import RZeroPragmatist

pragmatist = RZeroPragmatist()
eval_result = pragmatist.evaluate(challenge, solution, challenger)
assert eval_result.train_accuracy <= 1.0
```

## VERSION
v0.1

## SEE ALSO
- `LLM_AS_JEV_DECISION_PRIME.md`
- `STATELESS_LANGUAGE_AGENT_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `ENHANCED_SIMULATION_PRIME.md`
