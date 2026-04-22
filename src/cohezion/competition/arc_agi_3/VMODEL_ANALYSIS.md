# V-Model Engineering Analysis: ARC-AGI-3 Agent for Milestone #1

## Executive Summary

**Date:** 2026-04-21
**Target:** ARC-AGI-3 Milestone #1 Prize ($25K 1st, $10K 2nd, $2.5K 3rd)
**Deadline:** June 30, 2026 (~69 days)
**Current Status:** V-Model Requirements Phase

---

## 1. REQUIREMENTS PHASE

### 1.1 Goal Statement
Build an AI agent capable of achieving competitive scores on the ARC-AGI-3 interactive reasoning benchmark to win milestone prize money that self-funds the Cohezion project.

### 1.2 Target Values
| Metric | Target | Minimum | Rationale |
|--------|--------|---------|-----------|
| Public Demo Score | Top 3 placement | Score > 0.0 | Milestone prizes require open source + competitive score |
| Efficiency | ≥50% median human baseline | ≥25% | Scoring is squared efficiency + level-weighted |
| Games Solved | ≥15/25 public demos | ≥5/25 | Must demonstrate generalization |
| Open Source | Full source MIT-licensed | N/A | Required for prize eligibility |

### 1.3 Constraints
- **Open Source:** All code must be MIT/CC0 licensed before prize evaluation
- **No Internet:** Evaluation environment has no API access (GPT/Claude unavailable)
- **Compute Limits:** To be announced by competition launch
- **Time:** June 30, 2026 deadline (~69 days)
- **Language:** Python 3.12+ (arc-agi-3 SDK requirement)
- **Hardware:** AMD Ryzen AI MAX+ 395 (55 TOPS NPU, 256GB RAM, shared GPU memory)

### 1.4 Acceptance Criteria
- [ ] Agent runs on all 25 public demo environments
- [ ] Agent produces valid scorecard in `COMPETITION` mode
- [ ] Score is in top 10 of unverified leaderboard at submission time
- [ ] All code committed to public GitHub repo with MIT license
- [ ] Agent completes games with ≥25% median human efficiency on average
- [ ] Submission made through official Kaggle competition before June 30

### 1.5 Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Top scores already >80% by incumbents | Medium | High | Research leaderboard first |
| Compute limits exclude local LLMs | Medium | High | Agent uses < 8GB VRAM |
| 69 days insufficient for novel approach | High | Medium | Reuse ARC-AGI-2 DSL primitives + grid reasoning |
| Evaluation games differ fundamentally from demos | Medium | High | Build generalization into agent architecture |

---

## 2. SYSTEM DESIGN PHASE

### 2.1 Concept of Operations
The agent must operate in novel interactive environments WITHOUT prior knowledge of rules. It receives:
- 64×64 grid observations (int8 values 0-15, representing colors/entities)
- Game state (NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER)
- Available actions (ACTION1-ACTION7, some with x,y coordinates)
- Score/levels completed

The agent must:
1. **Explore:** Discover what actions do through interaction
2. **Model:** Learn state transition dynamics from observations
3. **Goal-Set:** Infer what constitutes "winning" from sparse feedback
4. **Plan:** Select efficient action sequences to reach goals
5. **Execute:** Send actions to environment, recover from failures

### 2.2 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     ARC-AGI-3 Agent                          │
│                    (CompoundLoop Integration)                │
├─────────────────────────────────────────────────────────────┤
│  Perception        World Model       Goal        Planner     │
│  ───────────       ──────────       ────        ───────     │
│  Grid Parser  →   Transition    →   Detector →  Search    │
│  (DSL)            Model             (Heuristic)   (BFS/DFS) │
│                   (Learned)                     (A*/MCTS)   │
└─────────────────────────────────────────────────────────────┘
                    ↕
              ┌──────────┐
              │ Environment│
              │  (64×64)   │
              └──────────┘
```

### 2.3 Design Decisions
| Decision | Option A (Chosen) | Option B (Rejected) | Rationale |
|----------|-------------------|---------------------|-----------|
| Agent Type | Programmatic + learned transitions | Pure LLM (o4-mini) | No internet at eval; local LLM too slow |
| World Model | Tabular per-game + DSL primitives | Neural network | Tabular is faster, interpretable, sufficient for 64×64 grids |
| Planning | BFS with learned model + heuristics | MCTS | Deterministic games favor BFS; MCTS adds overhead |
| Goal Detection | Grid-statistic heuristics | Vision model | Heuristics are fast and generalize across game types |
| Exploration | Systematic action testing + memory | Random | Systematic discovers mechanics faster |

---

## 3. ARCHITECTURE PHASE

### 3.1 Component Breakdown

#### 3.1.1 Perception Module (`perception.py`)
- **Input:** 3D grid list from FrameData
- **Output:** Parsed scene representation (objects, regions, player position, walls, collectibles, exits)
- **Technology:** ARC-AGI-2 DSL primitives (connected components, bounding boxes, color histograms)
- **Interface:** `parse_frame(grid) -> SceneGraph`

#### 3.1.2 World Model Module (`world_model.py`)
- **Input:** SceneGraph(t), GameAction, SceneGraph(t+1)
- **Output:** Predicted next state, confidence
- **Technology:** Dictionary of observed transitions per (state_signature, action) pair
- **Interface:** `predict(state, action) -> predicted_state` or `explore(state) -> unexplored_actions`

#### 3.1.3 Goal Detector Module (`goal_detector.py`)
- **Input:** Frame history, current SceneGraph
- **Output:** Goal hypothesis list with confidence scores
- **Technology:** Heuristic rules based on game patterns:
  - Sudden grid changes = state transition detected
  - New elements appearing = progress toward goal
  - GAME_OVER = bad state to avoid
  - Score increase = good direction
- **Interface:** `detect_goals(history) -> List[GoalHypothesis]`

#### 3.1.4 Planner Module (`planner.py`)
- **Input:** Current state, world model, goals
- **Output:** Action sequence
- **Technology:** BFS/DFS through learned transition graph with heuristics
- **Interface:** `plan(current_state, goal, max_depth=20) -> List[GameAction]`

#### 3.1.5 Executive Module (`agent.py`)
- **Orchestrates:** Exploration → Learning → Planning → Execution loop
- **State Machine:** EXPLORE → MODEL → PLAN → EXECUTE → (WIN|GAME_OVER→RESET)
- **Interface:** Implements `arc_agi_3.Agent` base class

### 3.2 Data Flow
```
Environment → FrameData → Perception → SceneGraph
                                              ↓
World Model ←── Action ────────────────────┘
   ↓
Goal Detector (reads history)
   ↓
Planner (reads model + goals)
   ↓
Executive → Action → Environment
```

### 3.3 Dependencies
- `arc-agi` (toolkit, v0.9.6)
- `arc-agi-3` (agent SDK, v0.0.1)
- `numpy` (grid manipulation)
- `Pillow` (image rendering for debugging)
- Cohezion DSL primitives (from `arc_solver.py`)

---

## 4. MODULE DESIGN PHASE

### 4.1 Perception Module Design

```python
class SceneGraph:
    entities: dict[str, Entity]  # color -> list of connected components
    player_bbox: Optional[BBox]  # Detected player region
    walls: set[Coord]           # Immutable obstacle coordinates
    interactables: list[Entity]  # Collectibles, keys, doors, pills
    dimensions: tuple[int, int]  # Grid size (usually 64×64)
```

**Algorithm:**
1. Extract each grid from FrameData.frame (typically 1 grid)
2. Compute connected components per color value
3. Classify components by size/shape:
   - Large uniform regions = walls/floors
   - Small 2×2-4×4 regions = player, collectibles, keys
   - Border patterns = exits/doors
4. Track player position across frames (largest movable component)

### 4.2 World Model Design

```python
class TransitionModel:
    observations: dict[StateSignature, dict[str, StateSignature]]
    # Maps (grid_hash, action) -> next_grid_hash

    def learn(self, state: StateSignature, action: str, next_state: StateSignature):
        self.observations[state][action] = next_state

    def predict(self, state: StateSignature, action: str) -> Optional[StateSignature]:
        return self.observations.get(state, {}).get(action)

    def get_unexplored_actions(self, state: StateSignature, available_actions: list) -> list:
        known = set(self.observations.get(state, {}).keys())
        return [a for a in available_actions if a not in known]
```

**State Signature:**
- Downsampled grid (e.g. 16×16) + player position hash
- OR: Statistic fingerprint (color histogram, object count, player quadrant)

### 4.3 Goal Detector Design

**Hypothesis Types:**
1. **ReachExit:** Grid has a distinct exit region; goal is to reach it
2. **CollectAll:** Objects disappear on contact; goal is to collect all
3. **MatchPattern:** Grid must match target configuration
4. **AvoidHazards:** Certain regions cause GAME_OVER; goal is survival + progress
5. **EnergyManagement:** Resource depletes over time; goal is efficient completion

**Detection Rules:**
- If score increases after action → current direction promising
- If GAME_OVER after action → last action/state is hazardous
- If grid has distinct target-colored region → likely "reach target"
- If player can move freely but score doesn't increase → need to find trigger

### 4.4 Planner Design

**Algorithm: Model-Based BFS with Heuristics**
```
function plan(current_state, goal_hypothesis, world_model):
    frontier = [(current_state, [])]
    visited = {current_state}

    while frontier and steps < max_depth:
        state, path = frontier.pop(0)

        if goal_hypothesis.is_satisfied(state):
            return path

        for action in available_actions:
            if action not in world_model.known(state):
                continue  # Unknown transition - too risky

            next_state = world_model.predict(state, action)
            if next_state not in visited:
                visited.add(next_state)
                priority = heuristic(next_state, goal_hypothesis)
                frontier.append((next_state, path + [action]))
                frontier.sort(key=lambda x: heuristic(x[0], goal_hypothesis))

    return None  # No plan found within depth limit
```

**Heuristics:**
- Distance to goal region (Manhattan)
- Score delta (positive = good)
- Safety (avoids known GAME_OVER states)

---

## 5. IMPLEMENTATION PHASE

### 5.1 File Structure
```
src/cohezion/competition/arc_agi_3/
├── __init__.py
├── agent.py              # Executive: CohezionArcAgent
├── perception.py         # SceneGraph parser
├── world_model.py        # TransitionModel
├── goal_detector.py      # GoalHypothesis engine
├── planner.py            # Model-based BFS
├── strategies/           # Game-type-specific heuristics
│   ├── platformer.py     # Platformer logic (keys, doors, energy)
│   ├── puzzle.py         # Grid transformation puzzles
│   └── arcade.py         # Reflex/dodging games
└── tests/
    ├── test_perception.py
    ├── test_world_model.py
    └── test_agent.py
```

### 5.2 Integration with Cohezion Systems
- **CompoundLoop:** Agent uses alignment gate before executing plans; logs inflections when expectations violated
- **Ouroboros:** Detects when agent fails repeatedly on same game type; triggers strategy refinement
- **Mycelium:** Distributes exploration across game types; shares learned transitions
- **Experience Vault:** Stores successful strategies per game signature

### 5.3 Lever Configuration
Using DynamicLeverSystem, define ARC-AGI-3 specific levers:

| Lever | Current | Target | Range | Goal |
|-------|---------|--------|-------|------|
| `exploration_budget` | 50 | 200 | [10, 500] | Max actions per exploration phase |
| `planning_depth` | 10 | 20 | [5, 50] | BFS search depth |
| `scene_downsample` | 4 | 4 | [1, 8] | Grid downsample factor (64→16 etc) |
| `goal_confidence_threshold` | 0.5 | 0.7 | [0.1, 1.0] | Min confidence to commit to goal |
| `efficiency_target` | 0.25 | 0.50 | [0.0, 1.0] | Target human efficiency ratio |

---

## 6. UNIT TESTING PHASE

### 6.1 Test Strategy
- **Perception:** Test on synthetic grids with known entities
- **World Model:** Verify deterministic transitions learned correctly
- **Goal Detector:** Test hypotheses on known game replay data
- **Planner:** Verify BFS finds shortest path in simple mazes

### 6.2 Test Targets
| Component | Coverage Target | Test Count |
|-----------|--------------|------------|
| Perception | 80% | 20 tests |
| World Model | 90% | 15 tests |
| Goal Detector | 70% | 10 tests |
| Planner | 80% | 15 tests |
| Full Agent | Integration | 5 end-to-end |

---

## 7. INTEGRATION TESTING PHASE

### 7.1 Test Scenarios
1. Agent plays `ls20` (known 2D platformer) end-to-end
2. Agent handles `r11l` (easiest: 10/10 human solvability)
3. Agent handles `tr87` (hardest: 6/12 human solvability)
4. Agent recovers from GAME_OVER and retries
5. Agent completes all 25 public demos within action budget

### 7.2 Acceptance Gates
- Must solve `ls20` with < 200 actions (efficiency threshold)
- Must solve `r11l` on first attempt (easiest game)
- Must handle `tr87` without infinite loops (hardest game)

---

## 8. SYSTEM TESTING PHASE

### 8.1 Competition Mode Simulation
- Run agent in `OperationMode.COMPETITION`
- Verify: single scorecard, no game resets, proper scoring
- Compare against random agent baseline
- Compare against `llm` agent baseline (GPT-4o-mini)

### 8.2 Baseline Comparison
| Agent Type | Expected Score | Notes |
|------------|---------------|-------|
| Random | ~0.5% | Baseline |
| GPT-4o-mini (LLM) | ~2-5% | Template from SDK |
| o4-mini (ReasoningLLM) | ~5-10% | Better hypothesis formation |
| **CohezionArcAgent (Target)** | **>25%** | Programmatic + learned |

### 8.3 Performance Requirements
- Agent must complete 25 games in < 30 minutes total
- Perception latency < 50ms per frame
- Planning latency < 500ms per action selection

---

## 9. SYSTEM VALIDATION PHASE

### 9.1 Requirements Traceability
| Requirement | Verification Method | Status |
|------------|-------------------|--------|
| Top 3 placement | Unverified leaderboard comparison | Pending |
| ≥25% efficiency | Scoring API + manual replay inspection | Pending |
| ≥15/25 demos solved | Automated test suite | Pending |
| Open source | GitHub repo + LICENSE file | Pending |
| No internet | Local-only dependencies | Pending |
| Deadline met | Calendar check + Kaggle submission | Pending |

### 9.2 Exit Criteria
Full V-Model validation is achieved when:
1. All left-side phases complete (design + implementation)
2. All right-side phases complete (testing + validation)
3. Score meets or exceeds acceptance criteria on public demos
4. Code is open sourced and submitted

---

## 10. DECISION GATE

### 10.1 Go/No-Go Assessment

**GO if ALL of the following are true:**
- [ ] Baseline random agent score is known
- [ ] Baseline LLM agent score is known
- [ ] Unverified leaderboard shows feasible target score (< 50% for top 3)
- [ ] Agent solves ≥5/25 demos within 2 weeks of development
- [ ] Code architecture is clean and maintainable

**NO-GO if ANY of the following are true:**
- [ ] Leaderboard scores already >80% by established teams
- [ ] Agent cannot solve simplest game (r11l) within 1 week
- [ ] Compute requirements exceed available hardware
- [ ] Conflict with Paper Track deadline (November) causes resource strain

### 10.2 Recommended Path

**Primary:** Continue ARC Prize Paper Track (highest EV, November deadline, 99% draft done)
**Secondary:** Run ARC-AGI-3 agent experiment in parallel for 1 week as a "spike"
**Decision Date:** 2026-04-28 (7 days)
**Decision Criteria:** If agent solves ≥3/25 demos with >10% efficiency, proceed with Milestone #1

---

## Appendix: Lever System Integration

```python
from cohezion.swarm.dynamic_levers import create_default_lever_system
from cohezion.swarm.vmodel_engineering import VModelIntegratedLeverSystem

lever_system = create_default_lever_system()
vmodel = VModelIntegratedLeverSystem(lever_system)

requirements = {
    "goal": "Build ARC-AGI-3 agent scoring >25% median human efficiency",
    "target_value": 0.25,
    "justification": "Milestone #1 prize self-funds Cohezion development",
    "constraints": [
        "open_source_mit",
        "no_internet_eval",
        "python_3_12_plus",
        "deadline_june_30_2026",
        "hardware_ryzen_ai_max_395"
    ],
    "acceptance_criteria": {
        "demos_solved": 15,
        "efficiency_ratio": 0.25,
        "top_3_leaderboard": True
    }
}

adj_id = vmodel.adjust_lever_vmodel(
    lever_name="efficiency_target",
    target_value=0.25,
    requirements=requirements
)

status = vmodel.ve_process.get_lifecycle_status(adj_id)
print(f"Validated: {status['validated']}")
```
