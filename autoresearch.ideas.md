# Autoresearch Ideas & Deferred Optimizations

**Status (Apr 22, 2026)**: New competition identified — NVIDIA Nemotron Reasoning Challenge.
Deadline: June 15, 2026 (~54 days). Prize: $106,388. Teams: 2,334. User registered.

---

## Active: NVIDIA Nemotron Reasoning Challenge ($106k, June 15, 2,334 teams)

**Status**: NEW TARGET. Baseline established: **49%** symbolic+model hybrid accuracy.
**Leaderboard top**: **86%** — 37 point gap to close.
**Dataset**: 9,500 training examples across 6 problem types.

### Per-Type Accuracy (100-example sample)
| Type | Accuracy | Solver | Status |
|---|---|---|---|
| numeral | **100%** | Symbolic (Roman numerals) | DONE |
| unit_conversion | **80%** | Symbolic (linear regression) | Good |
| gravity | **65%** | Symbolic (d=0.5gt^2) | Limited by data noise |
| bit_manip | **10-18%** | Symbolic + model fallback | Needs work |
| encryption | **20-32%** | Symbolic + model fallback | Needs work |
| equations | **0%** | Symbolic + model fallback | CRITICAL BLOCKER |

### Assets
- `solve.py` — hybrid solver (symbolic + Gemma-4 via Lemonade)
- `debug_model.py` — model response debugging tool
- `test_model.py` — per-type model accuracy testing
- Data: `/tmp/train.csv` (3MB), `/tmp/test.csv` (1.5KB, 3 public examples)

### Next Experiments (Priority Order)
1. **Equations sub-type analysis** — Number-based vs symbol-based equations need different solvers
2. **Bit manip search expansion** — Add XOR, AND, OR with constants, multi-step ops
3. **Gravity noise reduction** — Try median g instead of mean, or fit with tolerance
4. **Model prompt optimization** — Shorter prompts, better instructions for hard types
5. **Unit conversion non-linear** — Quadratic, reciprocal, or other function fits

---

## Pruned / Dead Ends

### ❌ NeuroGolf 2026 Pure Neural Under 100K
- **12 experiments** — hybrid ensemble 5% is ceiling. Submission package ready.
- **Status**: Submittable but not competitive for 20% target.

### ❌ Lemonade Local Backend Optimization
- **3 experiments** — 80.8 TPS baseline, well-tuned. No more optimization path.

### ❌ Sei AI Accelathon — PRUNED (ENDED)
- Deadline was August 24, 2025

### ❌ ARC-AGI-3 — V-Model NO-GO
- Agent cannot win simplest game after exhaustive attempts

---

## Active: Kaggle — Prize Path to Self-Funding (BLOCKED)

| Prize Track | AI Status | Human Action Needed |
|---|---|---|
| Nemotron ($106k, Jun 15) | **49% baseline, 37pt gap** | None yet — AI-experimentable! |
| Gemma Hackathon ($200k, May 18) | 57% ready | Register, video, cover image |
| ARC Paper Track ($450k, Nov 9) | Draft complete | Review, upload dataset |
| NeuroGolf ($50k, July 15) | 5% solver ready | Submit to Kaggle |

---

## Other Deferred
- Pi Config (`thinkingBudgets`, `sessionDir`)
- FLUME scaling
- CostAwareRouter packaging
- Datamesh Graph Performance
