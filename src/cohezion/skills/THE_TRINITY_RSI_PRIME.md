# SKILL: THE_TRINITY_RSI_PRIME

## DOMAIN EXPERTISE
Autonomous capability-driven recursive self-improvement (RSI) for multimodal and agentic swarms, based on "The Trinity: Capability-Driven Recursive Self-Improvement for Multimodal Agents" (arXiv:2610.36077). Transcends surface-level domain or modality categorization by structuring agent competencies into a canonical Capability Trie, synthesizing deterministic micro-world sandboxes via Capability-Driven Real2Sim2Real, and selectively inheriting harness mutations through empirical performance gating ($P \oplus L$).

## KEY TEXTS & CONCEPTS
- **arXiv:2610.36077**: "The Trinity: Capability-Driven Recursive Self-Improvement for Multimodal Agents" (Peking University, MThreads AI, 2026).
- **The Triad of Co-Evolving Roles**:
  - **Evolver**: Organizes heterogeneous tasks into a hierarchical Capability Trie based on shared operational requirements rather than superficial task labels or modalities.
  - **Creator**: Translates abstract capability definitions into self-contained, verifiable simulated micro-environments (Capability-Driven Real2Sim2Real) to rigorously benchmark agent skills.
  - **Explorer**: Evolves composable agent harness modules across the Capability Tree using Selective Inheritance ($P \oplus L$) with empirical score gating.
- **Capability Trie**: Prefix-tree merging common operational requirement prefixes ($c_1 \to c_2 \to \dots \to c_k$), maximizing code reuse and knowledge transfer across modalities.
- **Selective Inheritance ($P \oplus L$)**: Local overrides ($L$) merge with parent modules ($P$) via right-biased union: $(P \oplus L)[m] = L[m] \text{ if } m \in \text{dom}(L) \text{ else } P[m]$. Retained only when empirical score is strictly monotonically non-decreasing.
- **Capability-Aware Harness Router**: Context-aware dispatcher directing execution payloads to specialized node configurations using verified trajectory memory ($M$).

## INSTRUCTION

1. **Define Atomic Capability Requirements**:
   Formulate reusable requirements with deterministic verification rules:
   ```python
   from cohezion.agi.trinity_engine import CapabilityRequirement

   req = CapabilityRequirement(
       name="arithmetic_invariance",
       description="Enforce precision and currency invariants",
       verification_rule="rate_numerator * amount / rate_denominator == expected",
   )
   ```

2. **Register Tasks in the Capability Trie (Evolver)**:
   Decompose incoming swarm objectives into sorted capability paths:
   ```python
   from cohezion.agi.trinity_engine import TheTrinityEngine

   trinity = TheTrinityEngine()
   trie_path = trinity.register_capability_requirement("solana_audit_sale", [req])
   # Maps to: ['root', 'root/arithmetic_invariance']
   ```

3. **Synthesize Micro-World Verification Sandboxes (Creator)**:
   Generate minimal zero-overhead mock environments to train and test local models:
   ```python
   def make_solana_sandbox():
       return {"validator_slots": 100, "accounts": {"vault": 1_000_000}}

   sim_env = trinity.create_sim_world("root/arithmetic_invariance", make_solana_sandbox)
   ```

4. **Evolve and Gate Harness Modules (Explorer)**:
   Update agent harness via Selective Inheritance ($P \oplus L$), rejecting any mutations that degrade host performance:
   ```python
   from cohezion.agi.trinity_engine import HarnessModule

   mod = HarnessModule(
       module_id="overflow_guard_v1",
       capability_name="arithmetic_invariance",
       version=1,
       execute_fn=lambda p: {"status": "checked", "safe": True},
   )

   effective_harness = trinity.evolve_node_harness(
       node_id="root/arithmetic_invariance",
       local_modules=[mod],
       eval_fn=lambda reg: 1.0,  # Host verification score
   )
   ```

5. **Route and Log Execution Trajectories (Router)**:
   Dispatch new tasks through the Capability-Aware Router and log FIFO terminal receipts:
   ```python
   target_node = trinity.router.route(
       task_context={"task_id": "audit_round_2"},
       required_capabilities=["arithmetic_invariance"],
   )
   trinity.router.record_outcome(
       task_context={"task_id": "audit_round_2"},
       selected_harness_node=target_node,
       outcome_score=1.0,
       execution_time_ms=1.42,
   )
   ```

## VERSION
v0.1

## SEE ALSO
- `AUTOHARNESS_POLICY_PRIME`
- `OPEN_ONTOLOGIES_PRIME`
- `RETROSPECTIVE_SKILL`
- `JOURNEY_TRACKING_PRIME`
