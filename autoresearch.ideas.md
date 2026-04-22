# Autoresearch Ideas & Deferred Optimizations

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
- **Assets**:
  - `hybrid_ensemble.py` — 5% reproducible solver
  - `neurogolf_kaggle.ipynb` — 12-cell notebook
  - `kaggle_submission.py` — standalone script
  - `neurogolf-submission.zip` — 7.6KB package ready for Kaggle

### ❌ Lemonade Local Backend Optimization
- **3 experiments** (baseline 80 TPS, Ollama comparison 18 TPS, context scaling)
- **Finding**: KV cache is highly effective (320 TPS warm vs 65 TPS cold). No low-hanging optimization without server restart.
- **Status**: Well-tuned. Backend optimization exhausted.

---

## Active: Kaggle — Prize Path to Self-Funding

### Gemma-4-Good Hackathon ($200k, May 18, ~109 teams)
- **Status**: Kernel v5 + VIDEO_SCRIPT.md + PROJECT_WRITEUP.md + 3 production guides.
- **Readiness**: 57.14% (100% AI artifacts, 0% human blockers)
- **Orchestrator agent**: `gemma_hackathon_agent.py`
- **Blocked on**: Human must register, record video, create cover image

### ARC Prize Paper Track ($450k, Nov 9, 29 teams)
- **Status**: Draft v2 structurally complete (100/100). 8 high-priority issues fixed.
- **Orchestrator agent**: `paper_track_agent.py`
- **Blocked on**: Human review + Kaggle dataset upload

### NeuroGolf 2026 ($50k, July 15, 611 teams)
- **Status**: Submission package ready (zip + notebook).
- **Best achievable**: 5% test accuracy. 73K params.
- **May submit anyway** — novelty of hybrid approach could score if metric weights size.

---

## Active: Infrastructure

### Competition Orchestrator (`competitions_orchestrated`)
- **Current**: **5/5 agents** (paper-track, arc-solver, gemma-hackathon, neurogolf, sei-accelathon)
- **Status**: MAXED OUT
- **No prize-relevant optimization path remaining**

### Pi Config
- `thinkingBudgets` — not yet configured
- `sessionDir` automation for worktrees

## Other Deferred
- KV cache quantization further (would require Lemonade restart)
- CostAwareRouter as standalone library
- FLUME-EVO-Itonic scaling to 1000+ agents
- Datamesh Graph Performance (config exists, never run)

---

## Summary

**All AI-experimentable, prize-relevant paths are exhausted.** The remaining funding action items require **human execution**:

| Prize Track | AI Status | Human Action Needed |
|---|---|---|
| Gemma Hackathon ($200k) | 57% ready | Register, video, cover image |
| ARC Paper Track ($450k) | Draft complete | Review, upload dataset |
| NeuroGolf ($50k) | 5% solver ready | Submit to Kaggle |

**Next autoresearch target to switch to**: Pi config optimization (`thinkingBudgets`, `features_activated`) or FLUME infrastructure scaling. Neither is prize-relevant.
