# ARC Prize 2026 — Competition Plan

## Strategy: Physics-Grounded Interactive World Modeling & Cross-Track Transfer

Our strategy leverages the synergy between three distinct ARC Prize tracks:
1.  **ARC-AGI-2 (Static):** Use 400+ training tasks to synthesize a library of "AutoHarness" code verifiers. These act as the fundamental laws of grid physics.
2.  **ARC-AGI-3 (Interactive):** Deploy our JEPA-based world model to navigate dynamic environments, using the AGI-2 verifiers to prune illegal actions and accelerate search in the 12D manifold.
3.  **Paper Track:** Formalize our "Hermetic Compound Engineering" and 12D topological routing results into a SOTA research submission.

## Architecture

```
ARC-AGI-3 Game Environment (64x64 grid, 7 actions)
    ↓
InteractiveGameEncoder (grid → FLUME 256D → 12D manifold)
    ↓
JEPA World Model (online training per game = TTT)
    ├─ Predict next grid state from current + action
    ├─ Surprise score = JEPA prediction error
    └─ Counterfactual predict = evaluate all 7 actions
    ↓
SurpriseExplorer (high surprise → high-information actions)
    ↓
TopologicalRouter (detect EXPLOIT/EXPLORE/PIVOT regime)
    ├─ EXPLOIT: repeat working strategy
    ├─ EXPLORE: try novel actions in high-surprise regions
    └─ PIVOT: completely change approach if stuck in loop
    ↓
Action Selection → Submit to ARC-AGI-3 environment
    ↓
Observe result → Update JEPA → Repeat
```

## Phased Development

### Phase 1: SDK Integration (Week 1 — by April 3)
- [x] Install arc-agi SDK: `uv run --no-project --python 3.12 --with arc-agi>=0.9.3`
- [x] Build ARC environment wrapper matching gymnasium API (`arc_gym_wrapper.py`)
- [x] Test with random agent on sample environments (`test_random_agent.py`)
- [x] Measure baseline score with random actions (Score: 0.0)

### Phase 2: JEPA Per-Game Training (Weeks 2-3)
- [x] Build CNN encoder for 64x64 grid → FLUME latent (`arc_jepa.py`)
- [x] Train JEPA online per-game (test-time training) (`train_jepa_online.py`)
- [ ] Implement surprise-driven action selection
- [ ] Measure: score improvement over random baseline

### Phase 3: Topological Routing (Weeks 4-5)
- [x] Wire TopologicalRouter for game trajectory analysis (`arc_topology_navigation.py`)
- [x] Detect behavioral regimes (EXPLOIT/EXPLORE/PIVOT) in latent space
- [ ] Detect exploitation loops → auto-switch to exploration
- [ ] Detect stagnation → pivot to completely new strategy
- [ ] Target: Milestone #1 deadline June 30

### Phase 4: ARC-AGI-2 (Static) & Advanced Techniques (Weeks 6-12)
- [x] Task: Download ARC-AGI-2 dataset (cloned to `data/arc-agi-2-repo`).
- [ ] Task: Apply AutoHarness to all 400+ AGI-2 training tasks to generate a deterministic "Grid Law" library.
- [ ] Task: Implementation of Cross-game transfer via shared 12D manifold (Transfer knowledge from Static to Interactive).
- [ ] Task: Evolutionary program synthesis (Poetiq-style) for complex AGI-2 patterns.

## Paper Track Submission
- **Title:** "Interactive Reasoning via Physics-Grounded World Models: JEPA + Topological Routing for ARC-AGI-3"
- **Objective:** Submit by November 9, 2026.
- **Key Sections:** 
    - 12D Axiomatic Layer for Grid Representation.
    - HIHO Stability (0.5 Coherence) in Latent Navigation.
    - AutoHarness: Programmatic Pruning of the Search Space.
    - Empirical results from AGI-2 and AGI-3 leaderboards.

## Phase: Review Fixes
- [x] Task: Apply review suggestions bd3e453
