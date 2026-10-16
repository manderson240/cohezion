---
name: harness2-recursive-harnessing-prime
description: "Dual-level recursive agent harnessing for open-world tasks without ground-truth verifiers (arXiv:2610.14224). Implements K=8 component decomposition, contrastive Propose-Probe-Compose (PPC) recursion, and continual reflection under the strict Confounding Doctrine."
---

# SKILL: HARNESS2_RECURSIVE_HARNESSING_PRIME

## DOMAIN EXPERTISE
This skill establishes the dual-level recursive harnessing paradigm formulated in Harness^2 (arXiv:2610.14224). It decouples the base execution engine from its runtime harness, orchestrating recursive self-improvement across two connected loops: (1) Task-Level Recursion via contrastive Propose-Probe-Compose (PPC) cycles that discover and verify harness improvements without ground-truth labels, and (2) Harnessing-Level Recursion that transforms exploration outcomes into durable, transferable experience cards persisted across tasks while strictly enforcing the Confounding Doctrine.

## KEY TEXTS & CONCEPTS
- **arXiv:2610.14224**: "Harness^2: Recursive Agent Harnessing for an Open World" (Google Research: Ruiyao Xu, Yanfei Chen, Tomas Pfister, et al.).
- **K=8 Component File-Level Harness Decomposition**:
  1. `prompt.txt` (`PROMPT`): Persona, role framing, global objective.
  2. `guardrails.md` (`GUARDRAILS`): Negative constraints, loop-suppression, stop conditions.
  3. `memory.md` (`MEMORY`): Workspace state, relational indices, scratchpad memory.
  4. `skills/` (`SKILLS`): Domain expertise and procedural markdown instructions.
  5. `tools/` (`TOOLS`): API declarations, tool constraints, usage policies.
  6. `scripts/` (`SCRIPTS`): Deterministic helper programs offloading computation from the LLM.
  7. `subagents/` (`SUBAGENTS`): Worker roles, permissions, delegation topologies.
  8. `plugin.py` (`PLUGIN`): Middleware event hooks, telemetry, and runtime interception.
- **PPC Contrastive Loop (Zero-Verifier Invariance)**:
  - *Propose*: Generate orthogonal candidates targeting Invariant mechanisms (`INV`: procedure, loop guards, deterministic offload) and Domain contracts (`DOM`: data models, reconciliation).
  - *Probe*: Execute candidates under matched environment conditions alongside reference trajectory $e^0$.
  - *Compose*: Contrast trajectories without ground truth; adopt only edits verified by behavioral divergence and error mitigation.
- **The Confounding Doctrine**: If multiple components are modified simultaneously without an isolated ablation rollout, the empirical verdict must be marked `CONFOUNDED`. Never inject unisolated or unevidenced causal claims into the continual improvement library.
- **Common Base Reset ($\mathcal{H}_0$)**: Every new task begins from the canonical base harness $\mathcal{H}_0$, preventing compounding task-specific noise. Recursion operates on the *meta-harnessing mechanism* $\mathcal{R}_{t+1}$ using retrieved `cue-lesson-evidence` experience cards.

## INSTRUCTION
1. **Initialize Base Harness $\mathcal{H}_0$**:
   - Decompose task configuration into the 8 canonical components:
   ```python
   from cohezion.compound.harness2_engine import (
       Harness2Engine,
       HarnessComponentType,
       HarnessDefinition,
   )

   base_harness = HarnessDefinition(
       harness_id="arc_agi_3_base",
       components={
           HarnessComponentType.PROMPT: "Master ARC-AGI-3 Solver Agent",
           HarnessComponentType.GUARDRAILS: "Stop loop on repeated failed action.",
           HarnessComponentType.SCRIPTS: "# Deterministic grid validator scripts",
       },
   )
```
2. **Execute Reference Trajectory $e^0$**:
   - Run the agent on the target task. Record execution steps, tool interactions, errors encountered, and final deliverable.
3. **Contrastive Propose-Probe Cycle**:
   - Query the continual library for transferable lessons matching situational cues.
   - Propose orthogonal `INV` and `DOM` candidate harnesses.
   - Probe candidate executions under identical task states:
   ```python
   engine = Harness2Engine()
   inv_cand, dom_cand, proposed_edits = engine.proposer.propose_candidates(
       base_harness=base_harness,
       reference_exec=ref_exec,
       task_query=task_description,
       applicable_experiences=engine.store.list_experiences(),
   )
```
4. **Selective Evidence-Based Composition**:
   - Extract trajectory contrasts: detect divergence steps, error mitigations, and deliverable substance.
   - Compose successor $\mathcal{H}^*$ by merging ONLY edits with demonstrable positive contrast (`improved=True`, `regressed=False`).
5. **Harnessing-Level Continual Reflection**:
   - Execute successor harness $\mathcal{H}^*$.
   - Review all modified components against the Confounding Doctrine:
     - If $\le 2$ components were modified and helped, record `HELPED` and generate transferable `EXPERIENCE.md` card.
     - If $> 2$ components were bundled, flag all subsequent components as `CONFOUNDED`.
   - Persist experience cards to disk (`~/.cohezion/harness_library/`) and SurrealDB (`harness_experience` table).
6. **Task Reset & Meta-Transfer**:
   - Upon moving to task $t+1$, reset execution harness to $\mathcal{H}_0$.
   - Pass the updated experience library to the improvement proposer.

## VERSION
v0.1

## SEE ALSO
- `AUTOHARNESS_POLICY_PRIME`
- `ADVERSARIAL_TDD_PRIME`
- `RETROSPECTIVE_SKILL_PRIME`
- `LUKYANENKO_INVARIANT_ENGINEERING`

## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for HARNESS2 RECURSIVE HARNESSING.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.
