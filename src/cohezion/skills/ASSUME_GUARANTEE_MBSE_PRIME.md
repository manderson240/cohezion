---
name: assume-guarantee-mbse-prime
description: "Model-Based Systems Engineering (MBSE) with Assume-Guarantee compositional contracts, contract refinement, and intensional interface verification for agent swarms."
metadata:
  version: "v1.0"
  concepts: ["Assume-Guarantee Contracts", "Compositional Verification", "Intensional Specification", "Refinement Checking", "Counterexample Synthesis"]
  see_also: ["VMODEL_COMPOUND_GRAPH_PRIME", "AUTOHARNESS_POLICY_PRIME", "HYPER_RELATIONAL_KG_PRIME"]
  source: "src/cohezion/skills/ASSUME_GUARANTEE_MBSE_PRIME.md"
---

# SKILL: ASSUME_GUARANTEE_MBSE_PRIME

## DOMAIN EXPERTISE
Model-Based Systems Engineering (MBSE), Assume-Guarantee Contract (AGC) algebra, and compositional verification for autonomous agent swarms.

## KEY TEXTS & CONCEPTS
- **Assume-Guarantee Contracts ($\mathcal{C} = \langle \mathcal{A}, \mathcal{G} \rangle$)**: Decomposes multi-agent interfaces into environmental assumptions $\mathcal{A}$ and behavioral guarantees $\mathcal{G}$.
- **Intensional vs Extensional Verification**: Replaces infinite stochastic path sampling with deterministic algebraic contract checking.
- **Contract Refinement ($\mathcal{C}_{\text{impl}} \preceq \mathcal{C}_{\text{spec}}$)**: Verifies that an implementation weakens no assumptions ($\mathcal{A}_{\text{spec}} \subseteq \mathcal{A}_{\text{impl}}$) and strengthens all guarantees ($\mathcal{G}_{\text{impl}} \subseteq \mathcal{G}_{\text{spec}}$).
- **Parallel Composition ($\mathcal{C}_1 \otimes \mathcal{C}_2$)**: Computes composite contract across interacting agents and guarantees compatibility.

## INSTRUCTION
1. **Define Interface Contracts**: Use `AssumeGuaranteeContract` from `cohezion.compound.assume_guarantee_mbse` for each agent and tool boundary.
2. **Verify Composition Compatibility**: Run `ContractCompositionEngine.check_compatibility(agent1, agent2, interaction_state)` before executing multi-agent pipelines.
3. **Refinement Auditing**: Verify that specialized models refine abstract system specifications using `impl.refines(spec)`.
4. **Counterexample Tracking**: In the event of contract failure, capture the minimal failing state vector and persist to the dead-end ledger.

## VERSION
v1.0

## SEE ALSO
- VMODEL_COMPOUND_GRAPH_PRIME
- AUTOHARNESS_POLICY_PRIME
- HYPER_RELATIONAL_KG_PRIME
