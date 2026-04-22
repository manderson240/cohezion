# Autoresearch Ideas & Deferred Optimizations

**Status (Apr 22, 2026)**: New competition identified — NVIDIA Nemotron Reasoning Challenge.
Deadline: June 15, 2026 (~54 days). Prize: $106,388. Teams: 2,334. User registered.

---

## Active: NVIDIA Nemotron Reasoning Challenge ($106k, June 15, 2,334 teams)

**Status**: Baseline established: **53.0%** symbolic+model hybrid accuracy (500-sample validation).
**Leaderboard top**: **86%** — 33 point gap to close.
**Dataset**: 9,500 training examples across 6 problem types.

### Per-Type Accuracy (500-sample validation)
| Type | Accuracy | Count | Gap to Perfect | Notes |
|---|---|---|---|---|
| numeral | **100.0%** | 74/74 | 0 | Fully solved by Roman numeral symbolic |
| unit_conversion | **81.9%** | 77/94 | 17 | Linear fit; rounding errors cause ~2% failures |
| gravity | **72.4%** | 63/87 | 24 | Grid search helped but rounding in examples creates ceiling |
| encryption | **32.1%** | 26/81 | 55 | Symbolic mapping + model fallback; model poor at ciphers |
| bit_manip | **22.7%** | 20/88 | 68 | Brute-force per-bit/affine/unary/constant; complex rules miss |
| equations | **6.6%** | 5/76 | 71 | Gemma-4 gets ~6%; symbolic is ~0-1%; operators are custom per problem |

### Total: 266/500 = 53.2% (with 4-example prompts)

### Experiments Completed (10 total)
| # | Change | Result | Verdict |
|---|---|---|---|
| 117 | Baseline 100-sample | 49.0% | Baseline |
| 118 | Equations always-model + bit-manip v2 | 51.0% | ✅ +2% |
| 119 | Robust gravity grid search | 54.0% | ✅ +3% |
| 120 | 500-sample validation | 53.0% | ✅ Baseline established |
| 121 | Encryption partial-mapping fallback | 52.8% | ❌ -0.2% |
| 122 | Unit conversion multi-model | 42.8% | ❌ REGRESSION |
| 123 | Revert to stable baseline | 53.0% | ✅ Stable |
| 124 | Unit conversion RMSE selection | 53.0% | ❌ No change |
| 125 | Operator-filtered equations | 52.4% | ❌ REGRESSION (symbolic useless) |
| 126 | 4-example model prompts | 53.2% | ✅ Marginal gain |

### Key Findings
1. **Gemma-4 model fallback ceiling**: Gets ~6% on equations, ~33% on encryption (with 2-4 examples), ~24% on bit_manip. The model is not capable of complex 8-bit pattern induction or multi-operator algebra.
2. **Gravity rounding noise is fundamental**: Examples are generated from exact g then rounded to 2 decimals. With only 3-5 examples, the true g cannot be uniquely recovered. ~25% of gravity problems are inherently ambiguous.
3. **Equations are the hardest type**: 97% of problems mix multiple operators in examples. The test operator appears in examples 80% of the time for number-based equations, BUT the rules are NOT simple operations (+, -, *, concat, digit_sum). Custom digit-manipulation rules are too diverse to brute-force.
4. **Improvement ceiling with current setup**: ~53-55% appears to be the honest ceiling for hybrid symbolic + Gemma-4. Further gains require either (a) a significantly better model or (b) a much more sophisticated symbolic solver.
5. **Using more examples in model prompts (4 vs 2)** gives marginal +0.2% improvement. Diminishing returns.

### Remaining Ideas (Deferred)
- **Partial-decryption hint for encryption**: Send symbolic partial mapping + unknown blanks to model, ask it to fill from context. Risk: complex implementation, model might still fail.
- **Ollama cloud models (qwen3.5, deepseek, nemotron-super)**: Could dramatically improve model fallback but may cost money/limits. Not tested due to empty responses on first attempt.
- **Train a bit-manip classifier**: Given examples, predict transformation class (XOR, permutation, shift, etc.) and only search in that class. Would reduce search space and might catch more patterns.
- **Gravity: accept ambiguity range**: If multiple g values are consistent with examples (accounting for rounding), try both rounded results and pick one. Could recover some of the ~25% failures.
- **Unit conversion: try reciprocal/power fits**: Some conversions might be non-linear. The previous attempt broke due to implementation bugs.

### Assets
- `solve.py` — hybrid solver (symbolic + Gemma-4 via Lemonade)
- `submit.py` — submission.csv generator
- `debug_model.py` — model response debugging
- Data: `/tmp/train.csv`, `/tmp/test.csv`

---

## Pruned / Dead Ends

### ❌ NeuroGolf 2026 Pure Neural Under 100K
- **12 experiments** — hybrid ensemble 5% is ceiling. Submission package ready.

### ❌ Sei AI Accelathon — PRUNED (ENDED)
- Deadline was August 24, 2025

### ❌ ARC-AGI-3 — V-Model NO-GO
- Agent cannot win simplest game after exhaustive attempts

### ❌ Operator-filtered equation solver
- Symbolic solver returns wrong answers that prevent model fallback. Always-model is better.

### ❌ Unit conversion non-linear fit (REGRESSION)
- Tried power/reciprocal models, implementation bugs caused 10-point drop.

---

## Active: Kaggle — Prize Path to Self-Funding (BLOCKED)

| Prize Track | AI Status | Human Action Needed |
|---|---|---|
| Nemotron ($106k, Jun 15) | **53% baseline, ~33pt gap** | Package/submit to Kaggle |
| Gemma Hackathon ($200k, May 18) | 57% ready | Register, video, cover image |
| ARC Paper Track ($450k, Nov 9) | Draft complete | Review, upload dataset |
| NeuroGolf ($50k, July 15) | 5% solver ready | Submit to Kaggle |

---

## Other Deferred
- Pi Config (`thinkingBudgets`, `sessionDir`)
- FLUME scaling
- CostAwareRouter packaging
- Datamesh Graph Performance
