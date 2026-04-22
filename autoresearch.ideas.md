# Autoresearch Ideas & Deferred Optimizations

## Pruned / Dead Ends

### ❌ Experience-Driven ARC Solver v0
- **Tried**: Task signature similarity + warm-start search
- **Result**: 0% eval solve rate. ARC eval tasks explicitly resist surface-feature matching.
- **Lesson**: ARC-AGI-2 requires symbolic program induction, not statistical transfer.
- **Status**: Pruned. Do not pursue shallow feature matching for ARC.

### ❌ Sei AI Accelathon — PRUNED (ENDED)
- **Status**: CLOSED. Deadline was August 24, 2025.
- **Lesson**: Always verify current dates before research effort.

### ❌ ARC-AGI-3 ($850k, Nov 2, 594 teams)
- **Status**: V-Model NO-GO. Agent cannot win simplest game after exhaustive attempts.
- **Assets preserved**: `experiential_agent.py`, `systematic_explorer.py` for 2027 or general agent research.

### ❌ Pure Tiny Conv Under 100K for ARC Generalization
- **Tried**: 5-layer residual conv + batch norm, 73,410 params
- **Result**: **83% training memorization but 2% test generalization** (41× gap)
- **Lesson**: Pure neural nets under 100K params memorize training pairs but fail to learn underlying transformation rules for unseen inputs. ARC requires compositional reasoning, not pixel-level matching.
- **Status**: Pruned for NeuroGolf. Need meta-training or hybrid approach.

---

## Active: Kaggle — Prize Path to Self-Funding

### NeuroGolf 2026 ($50k, July 15 deadline, 611 teams)
- **Status**: Honest finding: pure tiny conv fails at generalization (2% test). Exploring meta-training.
- **Current config**: 5-layer + batch norm, hidden=40, 73,410 params (under 100K)
- **Honest test generalization**: **2/100 = 2.0%** (not the 83% training memorization)
- **Key path**: Meta-train on all training tasks simultaneously, then test-time fine-tune per task
- **Architecture**: `src/cohezion/competition/neurogolf/tiny_conv_v3.py`
- **Next experiment**: Meta-training (pre-train on all task pairs → per-task fine-tune)

### Gemma-4-Good Hackathon ($200k, May 18 deadline, ~109 teams)
- **Status**: Kernel v5 published + VIDEO_SCRIPT.md + PROJECT_WRITEUP.md drafted. **BLOCKED ON HUMAN ACTIONS.**
- **Deadline**: 2026-05-18 (~25 days) — **MOST URGENT**
- **What you must do**: Log into Kaggle → register → record 60s video → create cover image → submit

### ARC Prize Paper Track ($450k, Nov 9 deadline, only 29 teams)
- **Status**: Draft v2 structurally complete (100/100), 8 high-priority issues fixed.
- **Next action**: HUMAN REVIEW REQUIRED. Also: upload Kaggle dataset and register.

---

## Pi Packages Research (Apr 22, 2026)

| Package | What It Does | Relevance |
|---|---|---|
| `subagent` | Isolated subprocess agents with parallel streaming | Replace custom `CompetitionOrchestrator` |
| `git-checkpoint` | Auto-commits at session boundaries | Safer autoresearch |
| `summarize` | Session compaction | Long paper review sessions |
| `custom-compaction` | Fine-grained context control | Keep reasoning in context |

**Status**: None installed yet. Recommend `subagent` + `git-checkpoint` first.

## Other Deferred
- KV cache quantization (kv8) — started, not benchmarked
- CostAwareRouter as standalone library
- FLUME-EVO-Itonic at 100 agents / 0.98 coherence
