# Entity: Lukyanenko Axioms

## Abstract
Empirical ML invariants abstracted from Kaggle Grandmaster Andrey Lukyanenko's analysis of autonomous agent workflows, combating silent data desynchronization, metric mismatch, and LLM confabulation.

## Four Foundational Axioms
1. **Primary Key Index Alignment:** Strict assertion that test IDs, precomputed fold masks, and submission files maintain exact order and cardinality:
   `assert sorted(sub["ID"].tolist()) == sorted(test_ids)`
2. **Metric Objective Alignment:** Aligning the training loss objective with the evaluation metric (e.g. weighted cross-entropy under 14.9x class imbalance for balanced accuracy).
3. **Probability Margin Insulation:** Enforcing probability clipping to $[10^{-6}, 1 - 10^{-6}]$ to prevent fatal log-loss divergences from unobserved edge cases.
4. **Anti-Confabulation AST Verification:** Pre-compiling code changes via Python's AST compiler (`compile(code, "<ast>", "exec")`) before execution to reject hallucinated syntax or phantom refactoring bugs.

## Operational Code
* Implementation: `src/cohezion/compound/invariant_factory.py`
* Tests: `tests/test_lukyanenko_invariants.py`
* Skill: `src/cohezion/skills/LUKYANENKO_INVARIANT_ENGINEERING_PRIME.md`

## Related Entities
* [[first-principles-invariants]]
* [[AutoHarness]]
