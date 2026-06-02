---
name: ARC_INTERACTIVE_REASONING
description: Skill definition
keywords:
- arc
- interactive
- reasoning
---

# ARC Interactive Reasoning Skill

**Auto-generated from experiential learning spike**
**Date:** 2026-04-21T23:49:07Z

## Principles Learned

- State abstraction must be invariant to irrelevant transformations (camera position vs scene content)
- Exploration should be systematic before stochastic (sweep > random)
- Player/object position is the key latent variable in interactive grid worlds
- ARC-AGI-3 tests the same core generalization as ARC-AGI-2, but with temporal dynamics

## Known Failure Modes

### State Abstraction Failure
- **Symptom:** Extremely low state diversity despite high interaction count
- **Root Cause:** grid_signature() hashes full 64x64 grid. Player movement changes ~64 pixels, making every frame unique.
- **Healing Action:** Switch to player-centric state: (player_x, player_y, surrounding_3x3) + game state

## Action Preferences (Empirical)


### r11l
- `ACTION6`: avg reward = 0.0325

### ls20
- `ACTION3`: avg reward = 0.0452
- `ACTION2`: avg reward = 0.0425
- `ACTION4`: avg reward = 0.0420

## Recommended Exploration Strategy


### Priority 1: experiential_agent.py::grid_signature()
- **Issue:** Full-grid hashing prevents generalization
- **Fix:** Implement player-centric state with relative coordinates

### Priority 2: experiential_agent.py::ExperientialAgent._plan()
- **Issue:** BFS on 5-state model is trivial, can't find win paths
- **Fix:** Increase state abstraction quality, then use A* with heuristics

### Priority 3: CompoundLoop
- **Issue:** Agent takes random actions when model is empty
- **Fix:** Systematic sweep pattern for initial exploration (row-major action sequence)

## Geometric Correspondences
- **0.5** = HIHO threshold (Shannon max)
- **256** = FLUME latent dimension
- **SU(2)** = agent state gauge group
