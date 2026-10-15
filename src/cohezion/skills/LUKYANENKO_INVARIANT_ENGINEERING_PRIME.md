# SKILL: LUKYANENKO_INVARIANT_ENGINEERING_PRIME

## DOMAIN EXPERTISE
Expertise in operationalizing Grandmaster Andrey Lukyanenko's hard-learned competitive ML axioms: primary key index alignment, loss-vs-metric objective alignment (countering severe class imbalance), probability noise insulation, and anti-confabulation AST validation to prevent catastrophic post-merge and submission drops.

## KEY TEXTS & CONCEPTS
- **Primary Key Alignment Invariant**: Verification that test IDs, precomputed fold masks, and submission rows match identically without silent index desynchronization.
- **Metric Objective Alignment**: Guarding against optimizing unweighted loss functions on highly imbalanced targets (e.g. 14.9x class imbalance) where macro-balanced metrics govern final rankings.
- **Probability Margin Insulation**: Clipping raw prediction probabilities to $[10^{-6}, 1 - 10^{-6}]$ to prevent fatal log-loss divergences from unobserved out-of-distribution instances.
- **Anti-Confabulation AST Verification**: Parsing and compiling code modifications via AST prior to execution to prevent LLM hallucinations from introducing invisible syntax or variable drift.

## INSTRUCTION
1. Verify Primary Key Alignment:
   ```python
   assert sorted(sub["ID"].tolist()) == sorted(test_ids), "Index desynchronization detected!"
   ```
2. Verify Metric Objective Congruence:
   ```python
   # Verify that training loss objective matches competition evaluation metric
   if metric == "balanced_accuracy" and class_imbalance_ratio > 3.0:
       loss_fn = BalancedClassCrossEntropy(weights=class_weights)
   ```
3. Apply Probability Insulation Floor:
   ```python
   probs = np.clip(probs, 1e-6, 1.0 - 1e-6)
   ```
4. Enforce AST Compile Verification:
   ```python
   compile(source_code, "<candidate>", "exec")
   ```

## VERSION
v1.0

## SEE ALSO
- ANTI_PATTERN_GUARDIAN_PRIME
- ALGORITHMIC_FOUNDATIONS_PRIME
- ADVERSARIAL_TESTING_PRIME
