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
- **Status**: Kernel v4 published. Need formal competition entry + submission.
- **Idea**: "Compound Loop for Crisis Response & Field Operations"
  - Self-contained Kaggle notebook (no external API dependencies)
  - Demonstrates: alignment gate, skill refinement, simulated Gemma reasoning
  - Includes: visual dashboard, training loop metrics, social good narrative
- **Blocker**: Kaggle hackathon submission mechanics unclear. NOTE.md says "no dataset."
- **Next action**: Discover submission process (Kaggle UI? DoraHacks?)
- **Why we win**: Unique angle (agentic adaptation), working infrastructure, 3 weeks remain

### ARC Prize Paper Track ($450k, Nov 9 deadline, only 29 teams)
- **Status**: Not started. Highest probability-to-prize ratio.
- **Idea**: "The Compound Loop: A General Architecture for Autonomous Agent Adaptation"
  - Tie to a scored submission on ARC-AGI-2 (even low scores qualify)
  - Novel: metacognitive alignment gates + skill refinement for program synthesis
  - Open-source compound engineering framework as artifact
- **Next action**: Outline paper sections, gather citations, produce first draft

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

### ARC Prize 2026 — ARC-AGI-3 ($850k Grand Prize, Nov 2, 594 teams)
- **Status**: Interactive environment. Requires agent SDK.
- **Human score**: 100%. **AI score**: 0.26%.
- **Status**: Too immature for our current stack. Defer to 2027 if grand prize rolls forward.

---

## Pi Config Improvements
- `terminal.imageWidthCells` already configured to 80
- Could add `thinkingBudgets` for fine-grained reasoning control
- Could configure `sessionDir` for all worktrees automatically

## Other Deferred Optimizations
- KV cache quantization (kv8) started but not fully benchmarked
- CostAwareRouter could be packaged as standalone library
- FLUME-EVO-Itonic at 100 agents / 0.98 coherence; scaling to 1000+ possible but not funding-relevant now
