# Autoresearch Ideas & Deferred Optimizations

## Pruned / Dead Ends

### ❌ Experience-Driven ARC Solver v0
- **Tried**: Task signature similarity + warm-start search
- **Result**: 0% eval solve rate. ARC eval tasks explicitly resist surface-feature matching.
- **Lesson**: ARC-AGI-2 requires symbolic program induction, not statistical transfer.
- **Status**: Pruned. Do not pursue shallow feature matching for ARC.

---

## Active: Kaggle — Prize Path to Self-Funding

### Gemma-4-Good Hackathon ($200k, May 18 deadline, ~109 teams)
- **Status**: Kernel v5 published + PROJECT_WRITEUP.md drafted. **NEED TO REGISTER AND SUBMIT.**
- **Submission requirements discovered** (from research):
  - Kaggle account + identity verification
  - Public project write-up ← drafted
  - Public code repository ← exists (cohezion repo)
  - Public demo or demo files ← Kaggle kernel serves this
  - Public video ← **NEEDS TO BE CREATED**
  - Cover image / media gallery assets ← **NEEDS TO BE CREATED**
- **Judging criteria**: Impact & Vision, Video Pitch & Storytelling, Technical Depth & Execution
- **Category fit**: Global Resilience — strong match for crisis response + offline deployment
- **Why Gemma 4 is right**: local inference, Apache 2.0, multilingual, edge deployment
- **Next action**: REGISTER on Kaggle → produce 60-second demo video → upload cover image → submit

### ARC Prize Paper Track ($450k, Nov 9 deadline, only 29 teams)
- **Status**: Draft v2 is **complete with empirical data**.
- **Completed**:
  - ✅ 7 citations in Prior Work (ARChitects, DreamCoder, metacognition, meta-learning, MAML)
  - ✅ Table 1: Ablation on 1000 tasks (all primitive subsets: 0.7–0.8%)
  - ✅ Table 2: Strategy selection multiplier (0.8% → 3.4% = **4.2×**)
  - ✅ Section 5.4: Honest alignment gate analysis (precision ~0%, value = interpretability)
  - ✅ Figure 1: Compound Loop architecture diagram
  - ✅ SUBMISSION_README.md for reproduction
- **Remaining claim to validate**: Skill refinement convergence — does `_select_strategies` improve when trained on sequential task batches?
- **Next action**: Test skill refinement convergence over task batches; evaluate Sei Accelathon MCP tooling track

### Sei AI Accelathon ($1M total, Aug 24 deadline)
- **Status**: Not started.
- **Prize pools**: DeFi/Payments ($60k), Consumer Agents ($60k), Tooling/Infra ($75k), Frontier Tech ($50k), Unexpected ($30k)
- **Why relevant**: MCP tooling track matches our infrastructure (Cohezion MCP servers)
- **Next action**: Research Sei MCP kit, evaluate integration effort vs. prize fit

### ARC Prize 2026 — ARC-AGI-2 ($700k Grand Prize, Nov 2, 448 teams)
- **Status**: Baseline DSL solver at 3.0% training / 0% eval.
- **Ceiling confirmed**: Pure DSL search cannot solve eval tasks (symbolic reasoning, compositional rules).
- **Deferred tactics**:
  - Integrate ARChitects open-source DSL (~100 primitives)
  - LLM-based program generation (Kaggle blocks internet APIs though)
  - Neural program induction (requires training data)
- **Status**: Background research only. Focus hackathon + paper track first.

## Active: Kaggle — Prize Path to Self-Funding

### ARC Prize 2026 — ARC-AGI-3 ($850k Grand Prize, Nov 2, 594 teams)
- **Status**: Interactive environment. Requires agent SDK.
- **Human score**: 100%. **AI score**: 0.26%.
- **Status**: Too immature for our current stack. Defer to 2027 if grand prize rolls forward.

### ARC-AGI-3 Experiential Learning Spike (COMPLETED)
- **Discovery from 7 experiments**:
  - Games are real interactive video games (sprite physics, collision, cameras)
  - **Two action modes**: Click-only (`available_actions=[6]`) vs Directional-only (`[1,2,3,4]`)
  - **Camera viewport**: ls20 is 16x16 viewport (player follows camera, hiding full state)
  - **Step budgets**: 42-60 actions total per game — extremely tight for exploration
  - **Local LLM (phi4) text-only**: insufficient without vision; hallucinates action choices
  - Programmatic region-clicking on r11l found 9 sprites but 0 wins — suggests sequence/order matters
- **V-Model Decision**: NO-GO for Milestone #1 (June 30). Agent cannot win simplest game after exhaustive systematic attempts.
- **Learning**: Interactive reasoning requires game-type recognition + specialized per-type agents, not a single generic agent.
- **Assets preserved**: `experiential_agent.py`, `vmodel_gate.py`, `systematic_explorer.py` — useful for 2027 or general agent research.

### Gemma-4-Good Hackathon ($200k, May 18 deadline, ~109 teams)

---

## Pi Config Improvements
- `terminal.imageWidthCells` already configured to 80
- Could add `thinkingBudgets` for fine-grained reasoning control
- Could configure `sessionDir` for all worktrees automatically

## Other Deferred Optimizations
- KV cache quantization (kv8) started but not fully benchmarked
- CostAwareRouter could be packaged as standalone library
- FLUME-EVO-Itonic at 100 agents / 0.98 coherence; scaling to 1000+ possible but not funding-relevant now
