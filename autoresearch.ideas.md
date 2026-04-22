# Autoresearch Ideas & Deferred Optimizations

**Status (Apr 22, 2026)**: Active competition — NVIDIA Nemotron Reasoning Challenge.
Deadline: June 15, 2026 (~54 days). Prize: $106,388. Teams: 2,334.

---

## Active: NVIDIA Nemotron Reasoning Challenge ($106k, June 15)

**Status**: Solver optimized to **54.6%** hybrid / **53.5%** pure-symbolic (1000-sample validation).
**User's previous best**: **49%** (LoRA fine-tuned model, March 26 submission).
**Improvement over user baseline**: +5.6 percentage points.
**Leaderboard top**: **86%** — ~31 point gap remains.

### Per-Type Accuracy (1000-sample validation, seed=42)
| Type | Symbolic Only | Hybrid (+Model) | Count | Notes |
|---|---|---|---|---|
| numeral | **100.0%** | **100.0%** | 148/148 | Roman numeral conversion |
| unit_conversion | **82.5%** | **82.5%** | 181/220 | Linear regression |
| gravity | **72.2%** | **72.2%** | 176/244 | Grid search on d=0.5gt^2 |
| bit_manip | **30.7%** | **31.8%** | 54/176 | Per-bit mapping + partial + affine |
| encryption | **32.1%** | **32.1%** | 166/518 | Character mapping (model adds nothing) |
| equations | **0.0%** | **1.1%** | 6/534 | Model fallback adds +1.1% total |

### Total: 531/1000 = 53.1% symbolic, 546/1000 = 54.6% hybrid

### Key Insight: Model Fallback is Marginal
Cross-validation across seeds (42, 123, 999, 1000-sample):
- Pure symbolic: **53.5%**
- Hybrid (+Gemma-4): **54.6%**
- Model fallback adds only **~1.1%** overall because:
  - Equations: Gemma-4 gets ~1% (too weak for custom multi-operator algebra)
  - Bit_manip: Gemma-4 gets ~1% more than symbolic
  - Encryption: Gemma-4 adds 0% (model as bad as symbolic at ciphers)

### Experiment History
| Run | Change | Result (500/1000) | Verdict |
|---|---|---|---|
| 117 | Baseline | 49.0% | Baseline |
| 119 | Gravity grid search | 53-54% | ✅ +4% on gravity |
| 120 | 500-sample validate | 53.0% | ✅ Stable |
| 121 | Encryption partial fallback | 52.8% | ❌ -0.2% |
| 122 | Unit conversion multi-model | 42.8% | ❌ REGRESSION |
| 126 | 4-example prompts | 53.2% | ✅ Marginal |
| 128 | Partial bit-manip mapping | 54.6% | ✅ +1.5% |
| 129 | Cross-val seed=123 | 56.0% | ✅ Variance confirmed |
| 130 | Cross-val seed=999 | 57.2% | ✅ Higher bound |
| 131 | 1000-sample seed=42 | 54.6% | ✅ Stable mean |
| — | Pure symbolic 1000 | 53.5% | ✅ No model needed for ~53% |

### What This Means for Kaggle
- **Pure symbolic = 53.5%** — no LLM server needed, runs in <1s, perfect for Kaggle notebooks
- **Hybrid = 54.6%** — requires Lemonade server running locally
- User's current **best live score = 49%**
- Pure symbolic **beats user's LoRA model by +4.5 points**

### Remaining Ideas (Deferred)
1. **Cloud model for equations only** (qwen3.5/deepseek via Ollama): Could add +2-4% if reliable. Timed out on first test.
2. **Equation operation search expansion**: Could theoretically help but search space is enormous. Gemma-4 is too weak.
3. **Bit-manip neighbor operations** (XOR with adjacent bits): Added rotations/shifts 1-4, no extra gain.
4. **Gravity precision ambiguity**: 3/1000 failures due to 1dp vs 2dp formatting. Tricky to fix without regressing 1dp cases.
5. **Encryption frequency analysis / word pattern dictionary**: Complex implementation, uncertain payoff.

### Assets
- `solve.py` — hybrid solver (symbolic + Gemma-4 fallback)
- `kaggle_pure_symbolic.py` — self-contained notebook, **53.5%**, zero LLM dependencies
- `kaggle_notebook.py` — hybrid notebook (requires local model server)
- `submit.py` — CSV generator

---

## Active: Kaggle — Prize Path to Self-Funding

| Prize Track | AI Status | Human Action Needed |
|---|---|---|
| Nemotron ($106k, Jun 15) | **53.5% pure symbolic ready** | Submit notebook to Kaggle |
| Gemma Hackathon ($200k, May 18) | 57% ready | Register, video, cover image |
| ARC Paper Track ($450k, Nov 9) | Draft complete | Review, upload dataset |
| NeuroGolf ($50k, July 15) | 5% solver ready | Submit to Kaggle |

---

## Pruned / Dead Ends
### ❌ NeuroGolf, Sei Accelathon, ARC-AGI-3
### ❌ Unit conversion non-linear regression (REGRESSION)
### ❌ Operator-filtered equations (symbolic worse than model-only)
### ❌ Encryption partial-decryption hints (model confused)
