# SKILL: RRSI_PRIME

## DOMAIN EXPERTISE
Regularized Recursive Self-Improvement of Agent Harnesses (RRSI) based on Google Research (arXiv:2609.24972). Focuses on optimizing the agent harness (prompts, control-flow logic, tool calling, memory management, and verifiers surrounding a frozen model) while preventing benchmark overfitting and token bloat through proposal-side annealing, pre-evaluation leakage screening, noise-adjusted floors, and complexity pruning.

## KEY TEXTS & CONCEPTS
- **arXiv:2609.24972**: "RRSI: Regularized Recursive Self-Improvement of Agent Harnesses" (Google Research, Sept 2026).
- **Harness Overfitting**: Unregularized recursive prompt/code mutation leads to large in-distribution score jumps that vanish out-of-distribution while bloating token costs by 30-50%.
- **Annealed Edit Budget ($b_t$)**: Caps bundled candidate edits: $b_t = \max(1, \lfloor b_0 \cdot \gamma^t \rfloor)$, forcing late iterations to propose atomic, minimal edits.
- **RRSICritic (Pre-Evaluation Leakage Screen)**: Deterministically blocks candidates hardcoding benchmark task IDs, sample numbers, or suite-specific regex heuristics before wasting evaluation compute.
- **Noise-Adjusted Acceptance Rule**: A candidate is selected only if $\Delta \text{Score} > \delta_{\text{noise}} + \lambda_{\text{cost}} \cdot \max(0, \Delta \text{Tokens})$.
- **RRSIPruner**: Identifies and retires dormant harness machinery that no longer contributes to winning trajectories, driving a 30% reduction in policy tokens.

## INSTRUCTION

1. **Initialize the Regularized Engine**:
   ```python
   from cohezion.agi.rrsi_engine import RRSIRegularizedEngine

   engine = RRSIRegularizedEngine(
       initial_budget=5,
       decay_gamma=0.85,
       noise_delta=0.015,
       cost_lambda=0.00005,
   )
   ```

2. **Propose Regularized Edits**:
   Bundle atomic edits and submit for budget and critic screening:
   ```python
   from cohezion.agi.rrsi_engine import HarnessEdit

   edit = HarnessEdit(
       edit_id="ast_validator_v2",
       target_component="verifier",
       description="Enforce AST node validation for math expressions",
       diff_patch="+ return float(_eval_node(ast.parse(expr, mode='eval')))",
       added_tokens=15,
   )

   candidate, reason = engine.propose_candidate(
       candidate_id="cand_iter_1",
       parent_id="harness_v0",
       proposed_edits=[edit],
   )
   ```

3. **Evaluate and Step with Cost/Noise Gating**:
   ```python
   from cohezion.agi.rrsi_engine import EvaluationOutcome

   base_eval = EvaluationOutcome(empirical_score=0.72, total_tokens_consumed=1200, execution_time_ms=8.5)
   cand_eval = EvaluationOutcome(empirical_score=0.78, total_tokens_consumed=1220, execution_time_ms=8.7)

   accepted, status = engine.evaluate_and_step(candidate, base_eval, cand_eval)
   ```

4. **Prune Dormant Components**:
   ```python
   prunable = engine.pruner.identify_prunable_edits(
       active_edit_ids=list(engine.active_edits.keys()),
       current_iteration=engine.iteration,
   )
   ```

## VERSION
v0.1

## SEE ALSO
- `THE_TRINITY_RSI_PRIME`
- `AUTOHARNESS_POLICY_PRIME`
- `OPEN_ONTOLOGIES_PRIME`
