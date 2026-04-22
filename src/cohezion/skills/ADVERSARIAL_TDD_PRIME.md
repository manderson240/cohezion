---
name: adversarial-tdd-prime
description: "This skill establishes a high-fidelity development and reasoning pattern where every output (code or proof) is subjected to a \"Red Team\" review before execution. It combines Test-Driven Development (TDD) principles with Adversarial Agentic Review to eliminate hallucinations and logical fallacies in complex systems."
---

# SKILL: ADVERSARIAL_TDD_PRIME

## DOMAIN EXPERTISE
This skill establishes a high-fidelity development and reasoning pattern where every output (code or proof) is subjected to a "Red Team" review before execution. It combines Test-Driven Development (TDD) principles with Adversarial Agentic Review to eliminate hallucinations and logical fallacies in complex systems.

## KEY TEXTS & CONCEPTS
- **Pre-Execution Audit**: Never run code or commit a proof without a second agent attempting to "break" or "disprove" it.
- **Test-First Reasoning**: Defining the "Success Criteria" (expected answer range, physical constraints, modular identities) before starting the reasoning chain.
- **Adversarial Feedback Loop**: The "Proposer" specialist and the "Adversary" reviewer engage in a multi-turn dialogue to refine the logic.
- **Edge Case Stress-Testing**: Explicitly searching for division by zero, sign flips, empty sets, and limit cases during the review phase.

## INSTRUCTION
1. **Define Success**: State the constraints and expected properties of the answer.
2. **Draft Solution**: The primary specialist generates a reasoning chain and any necessary symbolic code.
3. **Adversarial Review**: A separate model (the Adversary) is prompted to find flaws in the draft.
   - "Identify three ways this logic could fail."
   - "Check the SymPy code for syntax errors and sign flips."
4. **Refine**: The specialist updates the draft based on the Adversary's critique.
5. **Execute & Validate**: Run the refined code/logic and check against the initial success criteria.

## VERSION
v0.1

## SEE ALSO
- `MATH_REASONING_SWARM_PRIME`
- `HALLUCINATION_RESOLVER_PRIME`
