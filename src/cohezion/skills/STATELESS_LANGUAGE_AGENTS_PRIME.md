# SKILL: STATELESS_LANGUAGE_AGENTS_PRIME

## DOMAIN EXPERTISE
Stateless Language Agents (SLA) per arXiv:2610.07625 (FAIR at Meta, UT Austin, Georgia Tech) optimize long-horizon automated scientific research and Kaggle competition exploration by enforcing "Stateful Search in the Deterministic Harness, Stateless Execution in LLMs". Traditional multi-turn agent conversations suffer exponential token bloat (99.4% history tokens by epoch 30), context rot, and duplicate exploration. The SLA methodology achieves >84% token reduction while accelerating empirical search discovery through harness-reconstructed role-specific contexts, explicit failure disambiguation (`INCONCLUSIVE_FAILURE` vs `MEASURED_NON_IMPROVEMENT`), local candidate retention over $k$ iterations with global best reset, and zero conversational history replay.

## KEY TEXTS & CONCEPTS
- **arXiv:2610.07625**: *Stateless Language Agents: Scaling Long-Horizon Automated Research* (Crispino, Wang, Bohde, Stone, Tian, 2026).
- **Harness-Centric Statefulness**: All search state, candidate DAGs, evaluation logs, and diagnostics reside in the deterministic harness, never in LLM conversational memory.
- **Single-Turn Stateless Functions**: Advisor and Workers are invoked as pure single-turn mathematical functions $f(\mathcal{C}_{\text{reconstructed}})$ with fresh prompt context.
- **Failure Disambiguation**:
  - `INCONCLUSIVE_FAILURE`: Syntax errors, OOM, timeouts, unhandled exceptions. The scientific hypothesis was NOT tested. Direction remains open.
  - `MEASURED_NON_IMPROVEMENT`: Code compiled and executed cleanly, but the objective metric $s \le s_{\text{baseline}}$. Valid negative evidence dampening exploration.
  - `MEASURED_IMPROVEMENT`: Code executed cleanly and strictly improved metric ($s > s_{\text{baseline}}$). Updates global best $\theta^*$.
- **Local Candidate Retention with Global Reset**: Workers iterate on a local candidate for $k$ iterations ($k=3$ default) to allow complementary modifications to mature before resetting to $\theta^*$.
- **Advisor Token Parsimony**: Stateless Advisor consumes $<0.6\%$ of total swarm tokens while coordinating parallel workers.

## INSTRUCTION
1. **Initialize Stateless Kaggle Optimization Config**:
   Define target competition, metric, baseline score, and partitioned research directions.
   ```python
   from cohezion.competitions.stateless_kaggle_optimizer import (
       KaggleOptimizationConfig,
       StatelessKaggleOptimizer,
   )

   config = KaggleOptimizationConfig(
       competition_slug="rsna-knee-abnormality-detection",
       metric_name="Macro ROC-AUC (12 classes)",
       baseline_score=0.943,
       initial_code_path=Path("scripts/kaggle/rsna_speedy_raptors/patch_rsna_v30_pathology_temperature.py"),
       initial_directions=[
           {"direction_id": "dir_temp", "hypothesis": "Pre-fusion temperature scaling"},
           {"direction_id": "dir_weights", "hypothesis": "Pathology prior weights"},
           {"direction_id": "dir_copula", "hypothesis": "12x12 Clinical Prior Copula"},
           {"direction_id": "dir_r7_blend", "hypothesis": "R7 ConvNeXt-small 0.957 hybrid"},
       ],
       worker_models={"worker_0": "glm-5.3:cloud", "worker_1": "kimi-k2.7-code:cloud"},
       advisor_model="deepseek-v4-pro:cloud",
       local_retention_k=3,
       higher_is_better=True,
   )
   ```

2. **Define Sandbox Evaluator with AutoHarness Invariants**:
   Evaluate candidate code deterministically, returning `(score, diagnostics, is_error)`.
   ```python
   async def evaluate_candidate(code: str) -> tuple[float, str, bool]:
       try:
           # Verify syntax and execute validation on gold slice
           score = await run_gold_validation_slice(code)
           return score, "Evaluation completed successfully", False
       except SyntaxError as e:
           return 0.0, f"SyntaxError: {e}", True
       except Exception as e:
           return 0.0, f"RuntimeError: {e}", True
   ```

3. **Execute Search Iterations**:
   Run epochs where the deterministic harness routes evidence summaries and workers propose mutations.
   ```python
   optimizer = StatelessKaggleOptimizer(config)
   optimizer.build_harness(evaluator_fn=evaluate_candidate)
   history = await optimizer.run_iterations(epochs=3)
   ```

4. **Promote and Attest Global Best**:
   When a candidate achieves `MEASURED_IMPROVEMENT`, verify Two-Party IV&V assertion before pushing kernel to Kaggle.

## VERSION
v0.1

## SEE ALSO
- `TWO_PARTY_CRYPTOGRAPHIC_IVV_PRIME.md`
- `AUTOHARNESS_ZERO_COST_VERIFIER_PRIME.md`
- `MONADIC_LOCAL_MARKOV_PLANNING_PRIME.md`
