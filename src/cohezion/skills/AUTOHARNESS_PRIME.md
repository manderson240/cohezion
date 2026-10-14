# SKILL: AUTOHARNESS_PRIME

## DOMAIN EXPERTISE
Autonomous Synthesis of Deterministic Code-as-Action Verifiers, Zero-Cost Bytecode Compilers, and Invariant Action Guards (arXiv:2603.03329v1). Specializes in bypassing LLM inference calls at runtime with 0 ms latency, pruning illegal or suicidal trajectories, and enforcing mathematical, topological, and hardware invariants across competitive AI benchmarks and autonomous agent loops.

## KEY TEXTS & CONCEPTS
* **Code-as-Action-Verifier (AutoHarness)**: Synthesizing deterministic Python/Rust code to validate candidate model generations prior to execution or submission.
* **Harness-as-Policy**: Distilling complex reasoning into ultra-fast AST bytecode rejection samplers that run with 0 ms latency and 0 cloud token cost.
* **Topological & Group Invariants**:
  - D4 Dihedral Group Symmetries: Horizontal, vertical, 180° rotation, and diagonal transpose reflection invariance.
  - Euler Characteristic Conservation: Topological invariant $\chi = V - E + F$ preserved across discrete 2D/3D grid transformations.
* **Probability Calibration & Kolmogorov Monotonicity**: Enforcing $P(\text{Abnormal}) \ge \max_k P_k$ to eliminate metric blowout under weighted multi-label log-loss.
* **Hardware & Memory Guards**: Enforcing strict UMA aperture safety (e.g. Strix Halo 25 GB RAM floor, 10% swap threshold) before dispatching compute.
* **Atomic Agent Tool Wrapping**: Exposing AutoHarness verifiers as `@tool(atomic=True)` functions inside AMD GAIA SDK agents.

## INSTRUCTION

1. **Identify Critical Invariants**:
   Before running a model or submitting a candidate output, extract the non-negotiable domain invariants:
   ```python
   # Example: ARC D4 Dihedral Group & Euler Invariant Check
   import numpy as np

   def verify_d4_and_topology(grid: np.ndarray) -> bool:
       h_sym = np.array_equal(grid, np.flipud(grid))
       v_sym = np.array_equal(grid, np.fliplr(grid))
       rot_sym = np.array_equal(grid, np.rot90(grid, 2))
       # Euler characteristic chi on binary foreground
       v = np.sum(grid > 0)
       # Zero-cost assertion: must be symmetric or match boundary condition
       return bool((h_sym and v_sym) or rot_sym)
   ```

2. **Synthesize Zero-Cost Rejection Sampler**:
   Wrap candidate generation pipelines with deterministic bytecode filters:
   ```python
   def autoharness_filter(candidates: list[np.ndarray]) -> list[np.ndarray]:
       valid = []
       for cand in candidates:
           if verify_d4_and_topology(cand):
               valid.append(cand)
       return valid if valid else candidates  # Fail-safe fallback
   ```

3. **Enforce Kolmogorov Monotonicity on Probabilities**:
   Project uncalibrated model outputs onto valid probability spaces:
   ```python
   def calibrate_kolmogorov(p_abnormal: float, p_conditions: list[float]) -> float:
       max_cond = max(p_conditions) if p_conditions else 0.0
       # P(Abnormal) must be >= max_k P(condition_k)
       return max(p_abnormal, max_cond)
   ```

4. **Integrate into GAIA Agent / Swarm Lifecycle**:
   Decorate the verifier as an atomic tool within `gaia.Agent`:
   ```python
   from gaia import tool

   @tool(atomic=True)
   def verify_candidate_invariants(data: dict) -> dict:
       passed = verify_d4_and_topology(np.array(data["grid"]))
       return {"success": True, "passed": passed, "status": "PROVEN_INVARIANT" if passed else "REJECTED"}
   ```

5. **Persist Verification Evidence**:
   Record harness verdicts, execution times, and invariant proof logs into SurrealDB (`verification_gate` table) and Obsidian Vault.

## VERSION
v1.0

## SEE ALSO
- `AMD_GAIA_ORCHESTRATION_PRIME.md`
- `KAGGLE_GRANDMASTER_ASCENT_PRIME.md`
- `COMPOUND_ENGINEERING_PRIME.md`
- `VMODEL_SYSTEMS_ENGINEERING_PRIME.md`
