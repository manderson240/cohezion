---
name: rigorous-evaluation-prime
description: "Auditing AI agents through objective, physics-grounded benchmarks and strict consensus-based grading."
metadata:
  version: "v0.1"
  concepts: ["Manifold Drift", "Draconian Consensus", "Axiomatic Grounding"]
  see_also: ["ADVERSARIAL_TESTING_PRIME", "SECURITY_GUARDRAILS_PRIME", "SYSTEM_HARDENING_PRIME"]
  source: "src/cohezion/skills/RIGOROUS_EVALUATION_PRIME.md"
---

# SKILL: RIGOROUS_EVALUATION_PRIME

## DOMAIN EXPERTISE
Auditing AI agents through objective, physics-grounded benchmarks and strict consensus-based grading.

## KEY TEXTS & CONCEPTS
- **Manifold Drift**: The cumulative deviation of an agent's trajectory from the 0.5 HIHO stability well. Indicates reasoning erraticism.
- **Draconian Consensus**: A grading protocol requiring ≥95% agreement across multiple expert models. A single "Strong Reject" results in an immediate fail.
- **Axiomatic Grounding**: The practice of verifying that evaluation metrics reflect physical system constraints (CPU, RAM, Dilation) rather than just semantic similarity.

## INSTRUCTION

1. **Calculate Drift**:
   ```python
   def manifold_drift(trajectory: list[Point]) -> float:
       coherences = [p.coherence for p in trajectory]
       avg_coherence = sum(coherences) / len(coherences)
       return 1.0 - avg_coherence # Higher = unstable
   ```
2. **Apply Draconian Filter**:
   - Assemble an Expert Domain Lattice (EDL) of diverse models.
   - Collect critiques with severity scores.
   - Block if `any(severity > 0.8)` or `any(vote == STRONG_REJECT)`.
3. **Hardware Pulse Check**: Ensure the evaluator has access to `ResourceMonitor` vitals to detect if agent "fever" (high CPU/thermal) correlates with reasoning failure.

## VERSION
v0.1

## SEE ALSO
- ADVERSARIAL_TESTING_PRIME
- SECURITY_GUARDRAILS_PRIME
- SYSTEM_HARDENING_PRIME
