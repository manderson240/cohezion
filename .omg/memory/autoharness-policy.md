---
title: "AutoHarness Policy & Zero-Cost AST Verification"
category: agi
updated: 2026-09-19
coherence: 0.50
---

# AutoHarness Policy (arXiv:2603.03329v1)

## Mandate
Automatically synthesize deterministic code harnesses (Code-as-action-verifier) and policies (Harness-as-policy) using local silicon to prevent illegal actions and bypass LLM calls at inference time with 0ms latency.

## Verification Checklist
1. **AST Parsable**: Code must parse cleanly via `ast.parse` without SyntaxError.
2. **No Eval/Exec**: Prohibit `eval()` and `exec()` in synthesized code artifacts.
3. **Type Annotated**: All function signatures must include return type hints.
4. **ZKFV Polynomial Proofs**: Validate structural invariants and negentropy ($\Delta S \le 0$).
5. **Score-as-Reward Flywheel**: Evaluate execution trajectories against formal tests.
