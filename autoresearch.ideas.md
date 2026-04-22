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
- **7 experiments** (conv, sweep, meta-training, hybrid, test-time tuning)
- **Result**: **2% test generalization** (73K params). Training memorization 83%.
- **Lesson**: ARC requires compositional reasoning. Pure neural under 100K cannot learn transformation rules.
- **Status**: V-Model NO-GO for pure neural. **Kaggle submission script ready**: `kaggle_submission.py` (produces valid JSON, 120 tasks).
- **Assets**: `tiny_conv_v3.py` (73K params), `meta_train.py`, `hybrid_selector.py`, `validate_100.py`, `generalize_test.py`

---

## Active: Kaggle — Prize Path to Self-Funding

### Gemma-4-Good Hackathon ($200k, May 18, ~109 teams)
- **Status**: Kernel v5 + VIDEO_SCRIPT.md + PROJECT_WRITEUP.md. **BLOCKED ON HUMAN.**
- **Orchestrator agent**: `gemma_hackathon_agent.py` — impact assessment + submission review

### ARC Prize Paper Track ($450k, Nov 9, 29 teams)
- **Status**: Draft v2 structurally complete (100/100). 8 high-priority issues fixed.
- **Orchestrator agent**: `paper_track_agent.py` — claim review + drafting
- **Next action**: HUMAN REVIEW REQUIRED + Kaggle dataset upload.

### NeuroGolf 2026 ($50k, July 15, 611 teams)
- **Status**: Kaggle submission script ready.
- **Orchestrator agent**: `neurogolf_agent.py` — architecture analysis, submission review

---

## Active: Infrastructure

### Competition Orchestrator (`competitions_orchestrated`)
- **Current**: **5/5 agents** (paper-track, arc-solver, gemma-hackathon, neurogolf, sei-accelathon)
- **Status**: MAXED OUT — all active competitions covered.
- **Next**: Improve agent quality (structured JSON, better prompts)

### Pi Setup (`features_activated`)
- **Current**: 15 features
- **Next**: `thinkingBudgets`, automatic `sessionDir` for all worktrees

## Other Deferred
- KV cache quantization (kv8)
- CostAwareRouter as standalone library
- FLUME-EVO-Itonic scaling to 1000+ agents
