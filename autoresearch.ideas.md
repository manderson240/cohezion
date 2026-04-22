# Autoresearch Ideas & Deferred Optimizations

**Status (Apr 22, 2026)**: ALL AI-experimentable, prize-relevant paths are **exhausted**.
Last 10 runs: 105-114. No new configs to try. Loop needs a new target or human actions.

---

## Pruned / Dead Ends

### ❌ Experience-Driven ARC Solver v0
- Tried: Task signature similarity + warm-start search
- Result: 0% eval solve rate

### ❌ Sei AI Accelathon — PRUNED (ENDED)
- Deadline was August 24, 2025

### ❌ ARC-AGI-3 — V-Model NO-GO
- Agent cannot win simplest game after exhaustive attempts

### ❌ NeuroGolf 2026 Pure Neural Under 100K
- **12 experiments** (conv, sweep, meta-training, hybrid, coord-aware, ensemble, fallback, transformer)
- **Best result**: **Hybrid ensemble 5/100 = 5.0%** (DSL 3% + Conv 2%, zero overlap)
- **Ceiling confirmed**: Training memorization 83%, test generalization 2-5%. Transformer 0%. CoordConv 0%. All under 100K.
- **Status**: V-Model NO-GO for 20% target. Hybrid is best achievable.
- **Assets**: `hybrid_ensemble.py`, `neurogolf_kaggle.ipynb`, `kaggle_submission.py`, `neurogolf-submission.zip` (7.6KB)

### ❌ Lemonade Local Backend Optimization
- **3 experiments** (baseline 80 TPS, Ollama comparison 18 TPS, context scaling)
- **Finding**: KV cache is highly effective (320 TPS warm vs 65 TPS cold). No low-hanging optimization.
- **Status**: Well-tuned. Backend optimization exhausted.

---

## Active: Kaggle — Prize Path to Self-Funding (BLOCKED)

| Prize Track | AI Status | Human Action Needed |
|---|---|---|
| Gemma Hackathon ($200k, May 18) | 57% ready | Register, video, cover image |
| ARC Paper Track ($450k, Nov 9) | Draft complete | Review, upload dataset |
| NeuroGolf ($50k, July 15) | 5% solver ready | Submit to Kaggle |

All three are **blocked on human execution.** No further AI experiments can advance these.

---

## What the Autoresearch Loop Could Do Next

### Option A: Wait for Human (Recommended)
- Loop paused until user acts on blocked competitions
- Resume when new data/inputs arrive

### Option B: Pi Config Optimization
- `thinkingBudgets` — configure custom reasoning budgets
- `sessionDir` automation for worktrees
- **Metric**: `features_activated` (current: 15)
- **Prize-relevant**: No

### Option C: FLUME Infrastructure
- Scale from 100 to 1000+ agents
- **Metric**: `integration_score` or `agents_encoded`
- **Prize-relevant**: No

### Option D: Datamesh Graph Performance
- Config exists but was never run (segment 0)
- **Metric**: `query_latency_ms`
- **Prize-relevant**: No

---

## Honest Assessment

The autoresearch loop has reached a **natural plateau** after 114 experiments across 7 different config targets. The most promising next step is **not more experiments** — it's **human action on the blocked prize tracks** or a **new high-value target** identified by the user.
