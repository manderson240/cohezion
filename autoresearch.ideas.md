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
- **10 experiments** (conv, sweep, meta-training, hybrid, coord-aware, ensemble, fallback)
- **Best result**: **Hybrid ensemble 5/100 = 5.0%** (DSL 3% + Conv 2%, zero overlap)
- **Lesson**: ARC requires compositional reasoning. Pure neural under 100K cannot learn transformation rules. Hybrid symbolic+neural doubles rate but still far from 20% target.
- **Status**: V-Model NO-GO for 20% target. Hybrid is best achievable.
- **Assets**:
  - `hybrid_ensemble.py` — 5% reproducible solver
  - `kaggle_submission.py` — standalone submission script
  - `neurogolf_kaggle.ipynb` — 12-cell self-contained notebook
  - `tiny_conv_v3.py` — 73K param conv net

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
- **Status**: Kaggle notebook + hybrid submission script ready.
- **Best achievable**: 5% test accuracy (hybrid). 73K params.
- **May submit anyway** — small model + novelty of hybrid approach could score if metric weights size heavily.

---

## Active: Infrastructure

### Competition Orchestrator (`competitions_orchestrated`)
- **Current**: **5/5 agents** (paper-track, arc-solver, gemma-hackathon, neurogolf, sei-accelathon)
- **Status**: MAXED OUT
- **Next**: Improve agent reasoning quality (thinkingBudgets, better structured JSON)

### Pi Config (`features_activated`)
- **Current**: 15 features
- **Next**: `thinkingBudgets`, automatic `sessionDir` for all worktrees

## Other Deferred
- KV cache quantization (kv8)
- CostAwareRouter as standalone library
- FLUME-EVO-Itonic scaling to 1000+ agents
