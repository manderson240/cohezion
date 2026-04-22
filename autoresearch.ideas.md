# Autoresearch Ideas & Deferred Optimizations

## Pruned / Dead Ends

### ❌ Experience-Driven ARC Solver v0
- **Tried**: Task signature similarity + warm-start search
- **Result**: 0% eval solve rate.
- **Status**: Pruned.

### ❌ Sei AI Accelathon — PRUNED (ENDED)
- **Status**: CLOSED. Deadline was August 24, 2025.

### ❌ ARC-AGI-3 ($850k, Nov 2, 594 teams)
- **Status**: V-Model NO-GO.

### ❌ NeuroGolf 2026 Pure Neural Under 100K
- **Tried**: 6 architecture experiments (conv, meta-training, hybrid, sweep)
- **Result**: **2% test generalization** (73K params). Training memorization 83%.
- **Lesson**: ARC requires compositional reasoning. Pure neural under 100K params cannot learn transformation rules.
- **Status**: V-Model NO-GO for pure neural. Kaggle submission script ready anyway.
- **Assets preserved**: `kaggle_submission.py`, `tiny_conv_v3.py` (73K params, 2% test gen)

---

## Active: Kaggle — Prize Path to Self-Funding

### Gemma-4-Good Hackathon ($200k, May 18, ~109 teams)
- **Status**: Kernel v5 + VIDEO_SCRIPT.md + PROJECT_WRITEUP.md. **BLOCKED ON HUMAN.**
- **Next action**: User must register, record video, create cover image.

### ARC Prize Paper Track ($450k, Nov 9, 29 teams)
- **Status**: Draft v2 structurally complete (100/100). 8 high-priority issues fixed.
- **Next action**: HUMAN REVIEW REQUIRED + Kaggle dataset upload.

### NeuroGolf 2026 ($50k, July 15, 611 teams)
- **Status**: Kaggle submission script ready (`kaggle_submission.py`). Pure neural dead end.
- **Honest accuracy**: 2% test generalization. May still score if formula heavily weights size.

---

## Active: Infrastructure Optimization

### Competition Orchestrator (`competitions_orchestrated`)
- **Current**: 3 agents (paper-track, arc-solver, sei-accelathon)
- **Next**: Add neurogolf-agent + gemma-hackathon-agent
- **Target**: 5 agents handling all active competitions

### Pi Setup (`features_activated`)
- **Current**: 15 features
- **Next**: `thinkingBudgets`, automatic `sessionDir` for all worktrees

## Other Deferred
- KV cache quantization (kv8)
- CostAwareRouter as standalone library
- FLUME-EVO-Itonic scaling to 1000+ agents
