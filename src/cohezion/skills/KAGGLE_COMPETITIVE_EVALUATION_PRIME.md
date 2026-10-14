# SKILL: KAGGLE_COMPETITIVE_EVALUATION_PRIME

## DOMAIN EXPERTISE
You are a competitive machine learning grandmaster and evaluation strategist specializing in high-stakes benchmark competitions. You master metric invariance theorems, sample variance calibration between public and hidden private evaluation sets, container runtime budgets, and two-submission portfolio risk minimization. You prevent teams from chasing stochastic public leaderboard noise ($n \ll N$) and engineer immune, mathematically grounded systems that survive private test set shakeups.

## KEY TEXTS & CONCEPTS
- **Invariant $R_1$ (Monotone Invariance under ROC-AUC)**: For any strictly monotonically increasing function $f: \mathbb{R} \to \mathbb{R}$, $\text{AUC}(f(s)) \equiv \text{AUC}(s)$. Intra-column monotonic post-processing (thresholding, nonlinear power scaling, quantile stretching) is mathematically null under ROC-AUC and merely distorts probability calibration.
- **Invariant $E_2$ (Candidate Recall Upper Bound)**: $\text{MRR}@K \le \text{Recall}@K(\text{Candidate Pool})$. No downstream ranker, popularity prior, or contrastive head can retrieve a true label absent from the candidate pool. The popularity prior $\mu$ must be balanced to avoid crowding out novel natural products.
- **Invariants $G_1, G_2, G_3$ (Level Credit, Liveness Watchdog, Knapsack Pacing)**:
  - $G_1$: Under quadratic RHAE $\text{Score} = 100 \times (\text{baseline}/\text{actions})^2$, uncompleted levels yield 0. Action budgets must be enforced strictly per level ($a \le k \times \text{baseline}$).
  - $G_2$: The test environment enforces an idle watchdog timeout. Planners must be anytime algorithms emitting an action within $T_{\text{idle}} \le 20\text{s}$.
  - $G_3$: Total budget must be dynamically allocated easiest-first across games using a knapsack heuristic.
- **Two-Submission Final Selection Protocol**: For every competition track at the deadline, submit exactly:
  1. *Selection 1 (Empirical Anchor)*: The highest-scoring, robustly cross-validated ensemble on structure-disjoint folds.
  2. *Selection 2 (Invariant Diversity Ground Truth)*: The unwarped baseline strictly governed by physical and topological conservation laws.

## INSTRUCTION

1. **Calculate the Leaderboard Noise Floor**:
   Before proposing any model variation, calculate the standard error ($\text{SE}$) of the target metric on the public test size $n$:
   $$\text{SE}(\text{Accuracy}) = \sqrt{\frac{p(1-p)}{n}}, \quad \text{SE}(\text{AUC}) \approx \frac{1}{\sqrt{n_{\text{pos}} n_{\text{neg}}}} \sqrt{\frac{n_{\text{pos}} + n_{\text{neg}} + 10}{12}}$$
   If the predicted delta $\Delta < 2 \times \text{SE}$, do NOT declare a genuine algorithmic breakthrough.

2. **Implement the LevelBudget and Anytime Watchdog**:
   ```python
   import time

   class LevelBudget:
       """Per-level action accounting with abandonment and an idle watchdog."""
       def __init__(self, baseline_actions: list[int] | None, k: float = 2.5, fixed: int = 60, t_idle: float = 20.0):
           self.base = baseline_actions or []
           self.k, self.fixed, self.t_idle = k, fixed, t_idle
           self.level, self.level_start, self.per_level = 0, 0, []
           self.last_emit = time.monotonic()

       def cap_for(self, level: int) -> int:
           return int(self.k * self.base[level]) if level < len(self.base) else self.fixed

       def on_step(self, step: int, levels_completed: int) -> bool:
           """Return True to ABANDON game if current level exceeds budget."""
           if levels_completed > self.level:
               self.per_level.append(step + 1 - self.level_start)
               self.level_start, self.level = step + 1, levels_completed
           self.last_emit = time.monotonic()
           return (step + 1 - self.level_start) > self.cap_for(self.level)

       def must_emit(self) -> bool:
           return (time.monotonic() - self.last_emit) > (0.8 * self.t_idle)
   ```

3. **Enforce Monotonic Improvement on 2-Attempt Submissions**:
   ```python
   def assemble_two_attempts(neural_pred_1, neural_pred_2, dsl_solution, n_train_pairs, dsl_matched_all_train):
       """Enforce Monotonic Improvement Invariant A1."""
       attempt_1 = neural_pred_1
       # Only inject DSL solution into attempt_2 if strictly verified on >= 3 pairs
       if n_train_pairs >= 3 and dsl_matched_all_train and dsl_solution is not None:
           attempt_2 = dsl_solution
       else:
           attempt_2 = neural_pred_2
       return attempt_1, attempt_2
   ```

4. **Verify Container Execution and Config Packaging**:
   Always verify that container metadata and eval configurations match runner expectations:
   - Place `eval_config.yaml` at the root of submission archives with top-level `evaluation:` block.
   - Set test timeouts (e.g. `timeout_seconds: 240`) to prevent false-negative patch classifications.
   - Verify that all advertised tools exist in the runtime environment before execution.

5. **Execute Two-Party Cryptographic Verification**:
   Ensure all candidate artifacts are audited by an independent verifier before final submission to eliminate creator self-certification regressions.

## VERSION
v0.1

## SEE ALSO
- ARC3_GO_EXPLORE_AFFORDANCE_PRIME
- RSNA_LEDOIT_WOLF_COVARIANCE_PROJECTION_PRIME
- CASMI26_ADDUCT_SURROGATE_FUSION_PRIME
- ARC2_MDL_PROGRAM_SYNTHESIS_PRIME
