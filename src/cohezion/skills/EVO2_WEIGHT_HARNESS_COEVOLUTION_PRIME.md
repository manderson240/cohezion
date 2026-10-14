# SKILL: EVO2_WEIGHT_HARNESS_COEVOLUTION_PRIME

## DOMAIN EXPERTISE
Weight-Harness Co-Evolution and dual-role policy adaptation (arXiv:2610.13025). Coordinates the joint evolution of policy weights and evaluation harnesses using dual Proposer/Reflector decomposition, HarnessTree DAG exploration with genetic branch crossover, and EvoTIDE trajectory recovery.

## KEY TEXTS & CONCEPTS
- **arXiv:2610.13025**: *Evo$^2$: Evolving the Evolver through Weight-Harness Co-Evolution* (Xu et al., 2026).
- **Dual-Role Decomposition**: Unifying Proposer ($\pi_\theta^{\text{prop}}$, synthesizes harness mutations) and Reflector ($\pi_\theta^{\text{refl}}$, diagnoses execution feedback and isolates failure modes) within a single shared model.
- **HarnessTree ($\mathcal{T}$)**: Graph-structured search space of deterministic execution and verification harnesses, enabling non-linear exploration.
- **Genetic Crossover**: Splicing invariant modules and calibration rules across disparate branches of the harness tree.
- **EvoTIDE (Tree-guided Interleaved Dual-role Evolution)**: AST trajectory recovery via edit extraction, syntax sanitization, and prefix continuation.

## INSTRUCTION
1. **Initialize Harness Tree**:
   Anchor the initial baseline execution harness as the root node:
   ```python
   from cohezion.compound.evo2_coevolution import HarnessTree, DualRolePolicy, EvoTIDEEngine

   tree = HarnessTree(root_code=initial_harness_code)
   policy = DualRolePolicy(llm_fn=dispatch_ollama_cloud)
   engine = EvoTIDEEngine(tree=tree, policy=policy, eval_fn=run_eval)
   ```

2. **Step Through Co-Evolution**:
   For each iterative cycle, select parents, reflect on failure traces, propose mutations, recover AST errors, and evaluate:
   ```python
   child_node = engine.step(task_description="RSNA Knee SOTA calibration")
   if child_node.score > baseline_score:
       print(f"Improvement discovered: {child_node.score:.4f}")
   ```

3. **Execute Genetic Branch Crossover**:
   When distinct high-performing variants emerge on different branches, combine their invariants:
   ```python
   hybrid_child = engine.crossover_step(task_description="Combine R7 ConvNeXt + Raptor-384")
   ```

4. **Verify Two-Party Separation**:
   Ensure all candidate code passes independent verification (`IVVAuthority`) before deployment.

## VERSION
v0.1

## SEE ALSO
- STATELESS_LANGUAGE_AGENTS_PRIME
- AUTOHARNESS_POLICY_PRIME
- SELF_EVALUATION_PRIME
