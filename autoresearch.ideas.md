# Autoresearch Ideas & Deferred Optimizations

## Active: Kaggle — Prize Path to Self-Funding

### ARC Prize 2026 — ARC-AGI-2 ($700k Grand Prize)
- **Status**: Baseline DSL solver at 3.0% training / 0% eval. Matches ARChitects SOTA.
- **Ceiling hit**: Pure brute-force DSL synthesis cannot solve eval set tasks (symbolic reasoning, compositional rules, contextual application). Need LLM fallback or neural approach.
- **Deferred tactics**:
  - Integrate ARChitects open-source DSL (~100 primitives) with our search
  - LLM-based program generation: prompt model to write Python `solve(grid)` from training examples
  - Train a lightweight transformer on ARC training data to predict transformations
  - Use compound loop meta-learning: journey tracker learns which strategies work for which task signatures
- **Long-term**: Continue building toward November deadline.

### Gemma-4-Good Hackathon ($200k, May 18, 109 teams)
- **Status**: Not started. Highest short-term EV.
- **Idea**: "Compound Loop for Crisis Response & Field Operations"
  - Uses Gemma models (local, cheap) for reasoning
  - Compound loop adapts strategies based on feedback
  - Journey tracking documents what works for different crisis types
  - Alignment gate prevents misaligned actions
  - Genuine social good application: NGOs, disaster response, health outreach
- **Why we win**: 3 weeks + unique angle (agentic adaptation) + working infrastructure
- **Build plan**:
  1. Demo web app showing compound loop managing simulated crisis scenarios
  2. Use Gemma-4 4B via Ollama for local reasoning
  3. Showcase skill refinement learning from past responses
  4. Write compelling submission with metrics on adaptation speed

### ARC Prize Paper Track ($450k, Nov 9, 29 teams)
- **Status**: Not started. Very low competition count.
- **Idea**: "The Compound Loop: A General Architecture for Autonomous Agent Adaptation"
  - Tie paper to a scored submission on ARC-AGI-2
  - Novel contribution: using metacognitive alignment gates + skill refinement for ARC solving
  - Only 29 teams competing

## Pi Config Improvements
- `terminal.imageWidthCells` already configured to 80
- Could add `thinkingBudgets` for fine-grained reasoning control
- Could configure `sessionDir` for all worktrees automatically

## Other Deferred Optimizations
- FLUME-EVO-Itonic integration reached 100 agents / 0.98 coherence. Could scale to 1000+ agents.
- KV cache quantization (kv8) was started but not fully benchmarked.
- CostAwareRouter could be packaged as standalone library.
