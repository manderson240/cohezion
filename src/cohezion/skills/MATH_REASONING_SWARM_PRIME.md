# SKILL: MATH_REASONING_SWARM_PRIME

## DOMAIN EXPERTISE
This skill defines the architectural pattern for deploying sovereign reasoning swarms to solve complex, Olympiad-level mathematical problems (e.g., AIMO). It leverages a Triune Manifold approach, separating perception (Doer), latent reasoning (Thinker), and validation (Knower) to ensure high-fidelity, deterministic mathematical proofs without calculation drift.

## KEY TEXTS & CONCEPTS
- **Triune Manifold Architecture**: Segregation of responsibilities into Doer (12D state), Thinker (512D reasoning), and Knower (2048D intent/validation).
- **12D Mathematical State Vector**: Parsing LaTeX into structural depth, domain probabilities, and logic types to route problems efficiently.
- **Sandboxed Symbolic Execution**: Using `SymPy` and `NumPy` within a restricted execution environment to deterministically verify logic steps.
- **Dual-Run Stability (0.5 Coherence)**: Running reasoning chains independently and verifying agreement to ensure the final answer is a stable attractor, not a hallucination.

## INSTRUCTION
1. **Perception (The Doer)**: Parse the incoming LaTeX problem string to extract equations, variables, and structural complexity. Generate a 12D state vector.
   ```python
   parser = MathParser()
   state = parser.parse(latex_string) # Returns MathProblemState
   ```
2. **Routing (The Thinker)**: Based on the 12D state vector, route the problem to the appropriate specialist agent (Algebraist, NumberTheorist, Geometer, Combinatorist).
   ```python
   coordinator = SwarmCoordinator()
   task = coordinator.plan_journey(problem_id, latex_string)
   ```
3. **Execution & Verification**: The specialist agent must generate reasoning chains and offload deterministic calculations to a `SymbolicExecutor`.
   ```python
   executor = SymbolicExecutor()
   result = executor.execute("ans = solve(Eq(x**2 - 4, 0), x)")
   ```
4. **Validation (The Knower)**: Perform a Dual-Run to ensure stability. If Run 1 and Run 2 disagree, trigger a tie-breaker or adversarial review to find the logical flaw.

## VERSION
v0.1

## SEE ALSO
- `FLUME_ENCODING_PRIME`
- `HIHO_STABILITY_PRIME`