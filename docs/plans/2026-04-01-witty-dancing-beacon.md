# Session 87: Capture Learnings + Create Skills + Plan for Continued Success

## Context
Sessions 80-86 produced massive output (20+ commits, 2,034 tests, 4 training runs, 242 learnings in SurrealDB) but knowledge capture has fallen behind:
- KEY_LEARNINGS.md is AT the 300-line limit — can't add L233-L242 without compression
- MISSION_JOURNAL.md is OVER the 150-line limit (153)
- Sessions 84-86 learnings exist in SurrealDB but NOT in KEY_LEARNINGS.md
- 5+ reusable skills should have been created but weren't
- The cruft cleanup (Session 86) isn't documented anywhere

**This session**: Close the knowledge gap, create reusable skills, then plan the path to a coherent, validated, transformative platform.

## PHASE 1: Knowledge Capture (Compress + Persist)

### 1A. Compress KEY_LEARNINGS.md to Make Room
- [ ] Compress L96-L107 (agent validation, specialist pipeline, runaway files) into 3 lines
- [ ] Compress Sessions 59-67 research synthesis into 2 lines
- [ ] Compress L152-L156 (360-degree cycle, auth middleware, path sanitization, secret scrubbing, CI defense) into 2 lines
- [ ] Target: free up 15 lines for L233-L242
- [ ] Keep under 300 lines total

### 1B. Add Sessions 84-86 Learnings to KEY_LEARNINGS.md
- [ ] L233: ManifoldEnv Curriculum Reward — 3-stage reach→maintain→optimize
- [ ] L234: UniverseEvaluator — Bootstrap CI evaluation distinguishes genuine capability
- [ ] L235: RoutingOrchestrator — Unified entry for 4 routing systems
- [ ] L236: TDD + Code Review Compound Loop — catches type safety that TDD misses
- [ ] L237: Reward Alignment Must Match Physics Grounding (already added)
- [ ] L238: Small Actions Cooperate With Physics — action scale = dynamics timescale
- [ ] L239-L242: Research validation findings (action scaling, structural safety, Safety-Gymnasium, ERL)
- [ ] L243: Codebase Cruft Compounds — 867 traceability files accumulated silently. .gitignore is defense.

### 1C. Compress MISSION_JOURNAL.md Under 150 Lines
- [ ] Compress Sessions 72-73 (Nemotron + Enforcement) into 2 lines each
- [ ] Compress Phases 6-8.5 into single summary line
- [ ] Add Session 86 entry (cruft cleanup, Makefile targets)
- [ ] Target: <145 lines

### 1D. SurrealDB Sync
- [ ] Verify L233-L242 are in SurrealDB (they are from Session 85)
- [ ] Add L243 (cruft cleanup) to SurrealDB
- [ ] Add Session 86 universe snapshot
- [ ] Verify domain organization: all learnings tagged with correct domain

## PHASE 2: Create Reusable PRIME Skills

### 2A. RL Environment Design Skill
- [ ] Create `RL_ENVIRONMENT_DESIGN_PRIME.md`:
  - Curriculum reward design (3-stage pattern)
  - Action scale matching: small actions for strong attractors
  - Physics grounding: Lagrangian dynamics as structural safety
  - Episode statistics tracking
  - Evaluation with UniverseEvaluator + bootstrap CIs
  - Anti-pattern: differential-only rewards create oscillation incentive

### 2B. Training Diagnostic Loop Skill
- [ ] Create `TRAINING_DIAGNOSTIC_LOOP_PRIME.md`:
  - Pattern: train → diagnose failure → hypothesize fix → retrain → verify
  - Persist every run to SurrealDB (training_run table)
  - Random baseline as sanity check (if random > trained, reward is broken)
  - Action space, reward function, timesteps as the 3 diagnostic levers
  - Exit criteria: trained > random on target metrics

### 2C. Codebase Coherence Skill
- [ ] Create `CODEBASE_COHERENCE_PRIME.md`:
  - .gitignore as defense against cruft accumulation
  - File size limits: 300 soft, 500 hard
  - Makefile targets: train/evaluate/benchmark/demo for reproducibility
  - git rm --cached for cleaning tracked cruft without deleting files
  - Branch cleanup: 1,128 branches is pathological
  - Anti-pattern: autonomous cycles generate files without cleanup rules

### 2D. Multi-Perspective Review Skill
- [ ] Create `MULTI_PERSPECTIVE_REVIEW_PRIME.md`:
  - TDD catches behavioral correctness
  - Code review agent catches type safety + cross-cutting concerns
  - Run review in background while coding (zero idle time)
  - Party mode for strategic decisions (architect + PM + QA + dev + strategist)
  - Fix CRITICAL/HIGH before commit, MEDIUM/LOW in next session

### 2E. Overnight Autonomous Session Skill
- [ ] Create `OVERNIGHT_AUTONOMOUS_PRIME.md`:
  - Operating parameters: runtime, persistence, test baseline
  - Ralph Loop pattern: research → implement → verify → document → repeat
  - Commit at natural boundaries
  - Context management: persist and continue when approaching limits
  - Parallel execution: training + research + review simultaneously
  - Quality > quantity: one polished feature > five half-wired modules

## PHASE 3: Plan for Continued Success

### What Remains from Session 86 Plan (highest impact first)
- [ ] **End-to-end validation**: `scripts/validate_compound_loop.py` proving the full loop works
- [ ] **Split oversized files**: executor.py (1,342 lines), api/__init__.py (2,066 lines)
- [ ] **Fix ALL remaining test failures**: 4 holographic_projection + 2 r_zero_evolver
- [ ] **README.md overhaul**: Quick Start, architecture diagram, training results, compound loop story
- [ ] **CLAUDE.md refresh**: verify every number, remove stale references
- [ ] **SurrealDB schema hardening**: init script, port standardization (8001)
- [ ] **Lint sweep**: fix F-class errors (real bugs), then E-class (style)
- [ ] **Branch cleanup**: delete 1,100+ stale branches

### Forward Research + Development
- [ ] **SAC training**: PPO showed improvement but 0% convergence — SAC is better for continuous control
- [ ] **Reward hacking resistance benchmark**: adversarial probe showing ManifoldEnv agents can't hack
- [ ] **Marimo reactive notebook**: live training visualization
- [ ] **Quarto research document**: auto-regenerating paper from training results
- [ ] **Safety-Gymnasium registration**: publish ManifoldEnv as community package (after validation)
- [ ] **SwarmEnv MAPPO benchmark**: multi-agent scaling curve (2→16 agents)

### Compound Loop Goals
- [ ] **Every session auto-persists** to SurrealDB + vault (no manual retrospective needed)
- [ ] **SkillRefiner consumes training results** to update RL_ENVIRONMENT_DESIGN_PRIME
- [ ] **DegradationDetector monitors training** (plateau detection, constraint violation alerts)
- [ ] **Execution traces browsable** via Meta-Harness pattern (filesystem, not prompts)

## VERIFICATION

```bash
# Knowledge graph health
wc -l src/cohezion/knowledge_graph/KEY_LEARNINGS.md  # Must be <300
wc -l src/cohezion/knowledge_graph/MISSION_JOURNAL.md  # Must be <150

# SurrealDB sync
curl -s -X POST http://localhost:8001/sql -u "root:root" \
  -d "USE NS cohezion DB cohezion; SELECT count() FROM learning GROUP ALL;"

# Skills created
ls src/cohezion/skills/*PRIME*.md | wc -l  # Should be 196+

# Tests
uv run pytest tests/compound/ tests/swarm/ tests/environments/ -q --no-cov  # 0 regressions
```

---

# LEGACY: Session 86 Plan (in progress)

## The Real Problem

We have 760 Python files and 2,034 tests. But the codebase is NOT coherent. It's the accumulated output of 85 sessions of compound engineering — brilliant individual pieces connected by a growing web of wiring. To make this transformative and presentable, we need to do what a senior engineer does before shipping: **validate end-to-end, remove cruft, make the story visible from the code itself.**

## What "Transformative" Looks Like

The compound loop diagnosing its own training failures across 4 iterations IS transformative. But it needs to be:
1. **Reproducible**: `git clone → uv sync → python demo.py` produces the same results
2. **Visible**: The story is told by the code structure, not buried in commit messages
3. **Validated**: Every claim in README.md and the paper is adversarially verifiable
4. **Clean**: No cruft, no dead files, no 800-file traceability directories

## PHASE 0: Codebase Audit + Cleanup (THE FOUNDATION)

### 0A. Remove Accumulated Cruft
- [ ] Delete or `.gitignore` `_bmad/_config/traceability/cycles_continuous/*.json` (800+ files)
- [ ] Delete or `.gitignore` `_bmad/_config/traceability/repo_health/*.json` (dozens of snapshots)
- [ ] Move competition code to `research/challenges/` (already there) but `.gitignore` large artifacts
- [ ] Delete `test_audio_pipeline.py` from project root (misplaced)
- [ ] Audit `results/training/*.zip` — `.gitignore` model checkpoints (too large for git)

### 0B. Verify GitHub Repository Health
- [ ] `git log --oneline | wc -l` — how many commits? Is history clean?
- [ ] Check `.gitignore` covers: `*.zip`, `*.pt`, `*.safetensors`, `results/`, `_bmad/_config/traceability/cycles_continuous/`
- [ ] Check for accidentally committed secrets (grep for API keys, tokens)
- [ ] Verify branch structure: is main clean? Any stale branches?

### 0C. File Size Audit
- [ ] Find files >300 lines: `find src/cohezion/ -name '*.py' -exec wc -l {} + | sort -rn | head -20`
- [ ] executor.py (1,300+ lines) — must split per coding standards
- [ ] cost_aware_router.py — check line count after all additions
- [ ] Any other violations of the 300-line soft limit

## PHASE 1: End-to-End Validation (PROVE IT WORKS)

### 1A. Reproducible Training Pipeline
- [ ] Create `Makefile` targets:
  - `make train` → train PPO on ManifoldEnv (small actions, 20K steps, ~5 min)
  - `make evaluate` → evaluate trained model vs baselines
  - `make benchmark` → full 100K training + safety metrics + robustness test
  - `make demo` → quick demo showing the compound loop in action
- [ ] Verify from clean clone: `git clone → uv sync → make train → make evaluate`
- [ ] All results saved to `results/` with deterministic seeds

### 1B. Validate Every CLAUDE.md Claim
- [ ] Test count: run `uv run pytest` and record exact numbers
- [ ] Module count: `find src/cohezion/ -name '*.py' | wc -l`
- [ ] Skill count: `find src/cohezion/skills/ -name '*.md' | wc -l`
- [ ] API endpoint count: verify programmatically
- [ ] SurrealDB: verify tables exist and have data
- [ ] FLUME VAE: verify encoding/decoding works
- [ ] Update CLAUDE.md with EXACT verified numbers

### 1C. Validate the Compound Loop End-to-End
- [ ] Script: `scripts/validate_compound_loop.py`
  - Create a task → Execute via CompoundExecutor → DegradationDetector monitors
  - Alerts fire → CostAwareRouter adjusts (backward feedback)
  - SkillRefiner updates skill → Persist to vault + SurrealDB
  - Verify: execution trace exists in `execution_traces/`
  - Verify: SurrealDB has learning record
  - Verify: DegradationDetector → CostAwareRouter callback fired
- [ ] This script IS the demo of compound engineering

## PHASE 2: Code Quality (MAKE IT CLEAN)

### 2A. Split Oversized Files
- [ ] `executor.py` (1,300 lines) → split into:
  - `executor.py`: Core execute_task flow (<300 lines)
  - `executor_physics.py`: Steps 5.9 (natural capital), 7.6 (bioelectric)
  - `executor_enrichment.py`: JEPA surprise, execution traces
  - `executor_factory.py`: ExecutorFactory class
- [ ] `cost_aware_router.py` → check size, split if >500 lines
- [ ] Keep all tests passing through each split

### 2B. Fix ALL Remaining Test Failures
- [ ] Fix 4 holographic_projection failures (chunk-mean vs 2048D mismatch)
- [ ] Fix 2 r_zero_evolver collection errors
- [ ] Target: 0 failures, 0 errors across full suite

### 2C. Lint Sweep
- [ ] `ruff check src/cohezion/ --statistics` — categorize errors
- [ ] Fix all F-class errors (real bugs) first
- [ ] Fix E-class errors (style) next
- [ ] Run `ruff format src/cohezion/`

## PHASE 3: Documentation (TELL THE STORY)

### 3A. README.md Overhaul
- [ ] Clear "What is Cohezion?" section
- [ ] Quick Start: `git clone → uv sync → make demo`
- [ ] Architecture diagram (text-based, not image)
- [ ] Training results table (from validated runs)
- [ ] The compound loop story (4-iteration training diagnostic)
- [ ] Contributing guide (for portfolio reviewers to understand the code)

### 3B. Update Research Paper with Validated Results
- [ ] Replace placeholder tables with actual `make benchmark` output
- [ ] Add the 4-run diagnostic narrative as an experiment
- [ ] Ensure all citations are correct
- [ ] Add reproducibility section: "To reproduce: `make benchmark`"

### 3C. CLAUDE.md Refresh
- [ ] Verify every number against actual codebase
- [ ] Remove stale references to old sessions
- [ ] Add Session 85 findings (action scale, structural safety)

## PHASE 4: SurrealDB + Vault Coherence

### 4A. SurrealDB Schema Hardening
- [ ] Create `scripts/init_surrealdb.sh` — initializes all tables + indexes
- [ ] Document the schema: what tables exist, what they contain
- [ ] Fix port inconsistency: standardize on 8001 across all code
- [ ] Verify all knowledge_bridge.py, surreal_client.py, surreal_logger.py use correct port

### 4B. Vault Organization
- [ ] Verify brain-region directories match what CLAUDE.md documents
- [ ] Create missing directories if needed
- [ ] Cross-reference vault notes with SurrealDB records

## PHASE 5: Continuous Compound Improvement

### 5A. Overnight Autonomous Validation
- [ ] `scripts/overnight_validate.py`:
  - Run full test suite → persist results to SurrealDB
  - Run `make benchmark` → persist training metrics
  - Run lint sweep → persist error counts
  - Compare against previous snapshot → detect regressions
  - Generate report → vault + SurrealDB

### 5B. Hookify Rules for Continuous Quality
- [ ] Rule: `post_commit` → run affected tests
- [ ] Rule: `post_session` → persist universe snapshot to SurrealDB
- [ ] Rule: `pre_publish` → verify all claims, run full benchmark

## VERIFICATION

```bash
# The ultimate validation: from clean clone
git clone <repo> /tmp/cohezion-test
cd /tmp/cohezion-test
uv sync
make train      # Should complete in <5 min
make evaluate   # Should show PPO > random
make demo       # Should demonstrate compound loop
uv run pytest tests/ -q  # Should show 0 failures
```

---

# LEGACY: Session 85 Plan (completed)

## Party Mode Consensus (Architect + PM + QA + Dev + Problem Solver + Strategist)

**Root cause of all remaining gaps:** No demonstrated learning agent. Everything built so far is infrastructure FOR training. The single highest-leverage action is training a PPO agent on ManifoldEnv and plotting the learning curve. This transforms the paper from theory to results, validates the HIHO thesis, and creates a runnable demo.

## PHASE 0: Train Agents + Triple Benchmark Suite (HIGHEST PRIORITY)

### 0A. Standard RL Training (credibility through methodology)
- [ ] Install stable-baselines3: `uv pip install stable-baselines3`
- [ ] Create `scripts/train_manifold_agent.py`:
  - Train PPO, SAC, DQN on ManifoldEnv, 50K timesteps each, seed=42
  - Log per-episode: reward, convergence rate, curriculum stage, HIHO stability duration
  - Save: model checkpoints + learning curve plots (matplotlib)
  - Compare: PPO vs SAC vs DQN vs random vs greedy baselines
  - Standard metrics: sample efficiency, mean return, convergence rate, wall time
- [ ] Run training (all 3 algorithms, ~30-60 min total on CPU)
- [ ] Generate paper figures:
  - Learning curve comparison (3 algorithms + 2 baselines)
  - Convergence rate over training
  - Curriculum stage progression (Stage 1→2→3)

### 0B. Safety-RL Bridge (credibility through safety community)
- [ ] Create `scripts/benchmark_safety.py`:
  - Map ManifoldEnv to Safety-Gymnasium metrics:
    - **Cost rate**: Energy expenditure per step (Lagrangian action)
    - **Constraint satisfaction**: % of time in HIHO band [0.4, 0.6]
    - **Safe return**: Reward only counting steps where agent is in safe region
  - Compare: ManifoldEnv safety metrics vs CartPole-Cost (standard safety env)
  - Show HIHO convergence IS constraint satisfaction (structural, not learned)
- [ ] Report: cost-return Pareto frontier (higher return with lower cost = better)

### 0C. Reward Hacking Resistance (credibility through novelty)
- [ ] Create `scripts/benchmark_robustness.py`:
  - **Reward probe**: Modify reward function to add a "shortcut" — does agent exploit it?
    - ManifoldEnv: Add bonus for high velocity (violates physics — Lagrangian penalizes)
    - CartPole: Add bonus for staying left (exploitable — no physics constraint)
  - **Perturbation test**: Train on nominal env, evaluate on perturbed (noise, shifted dynamics)
    - ManifoldEnv: Add Gaussian noise to Lagrangian potential
    - CartPole: Add wind force
  - Compare robustness: physics-grounded vs standard env
  - Hypothesis: ManifoldEnv agents resist reward hacking because gauge invariance prevents shortcuts
- [ ] Report: hack rate (fraction of episodes where agent exploits shortcut)

### 0D. Multi-Agent Validation
- [ ] Create `scripts/train_swarm_agent.py`:
  - Train independent PPO agents in SwarmEnv (2, 4, 8 agents)
  - Measure: team coherence, individual convergence, coordination overhead
  - Compare: independent learning vs shared reward
- [ ] Report: scaling curve (agents vs convergence time)

### 0E. Reactive Research Documents (Marimo + Quarto)
- [ ] Create `notebooks/manifold_training.py` (Marimo reactive notebook):
  - Live training visualization: reward curve updates as agent trains
  - Interactive parameter sliders: dt, damping, reward weights, curriculum thresholds
  - Real-time ManifoldEnv state visualization (12D → 2D projection)
  - Auto-regenerating comparison tables: PPO vs SAC vs DQN
  - Publishable: `marimo export html` for static sharing
- [ ] Create `research/papers/physics-grounded-training-universes.qmd` (Quarto document):
  - Embed Marimo notebook outputs as live figures
  - Cross-reference code: `{{python}} from cohezion.eval.universe_evaluator import ...`
  - Auto-regenerate on `quarto render` — paper always reflects latest training
  - Output: HTML (interactive) + PDF (arXiv submission)
- [ ] Wire to Anima Dashboard webapp:
  - New `/training` route: live training dashboard with Three.js manifold visualization
  - SSE stream: training metrics fed via AG-UI events as they're computed
  - Episode replay: select an episode → watch agent trajectory on Bloch sphere

### 0F. Cohezion Learns From Its Own Training
- [ ] **Compound loop integration**: Training results feed back into Cohezion's knowledge:
  - Each training run → `execution_traces/training/` filesystem (Meta-Harness L225)
  - Training metrics → SurrealDB `training_run` table (experiment tracking)
  - Best hyperparams → vault `cerebellum/training-patterns/` (reusable knowledge)
  - Failed experiments → vault `hippocampus/experiments/` (what NOT to do)
- [ ] **SkillRefiner learns from training**:
  - If PPO converges faster than SAC → update `RL_TRAINING_PRIME.md` with this finding
  - If curriculum Stage 3 is never reached → update reward shaping guidance
  - If reward hacking detected → create new `REWARD_HACKING_DEFENSE_PRIME.md` skill
- [ ] **DegradationDetector monitors training**:
  - Alert if training reward plateaus for >1000 steps (pivot trigger)
  - Alert if constraint violation rate exceeds 20% (safety concern)
  - Feed training coherence metrics to the same pipeline as execution coherence
- [ ] **Knowledge Bridge persistence**: Every training run produces:
  - Learning record in SurrealDB (what worked, what didn't)
  - Vault note with YAML frontmatter (searchable by future sessions)
  - KEY_LEARNINGS entry if result is novel (manual gate)

### 0G. Paper Update + Demo
- [ ] Update paper with ALL benchmark results from Marimo notebooks
- [ ] Create `demo.py`: train for 5K steps → evaluate → open Marimo notebook
- [ ] README.md "Quick Start" with: `uv run marimo edit notebooks/manifold_training.py`

## PHASE 1: Fix All Pre-Existing Test Failures (PORTFOLIO POLISH)
- [ ] Fix 10 pre-existing failures (tip_of_spear, journey_tracker FLUME)
- [ ] Fix 2 collection errors (r_zero_evolver)
- [ ] Target: 0 failures, 0 errors, 2,023+ passing

## PHASE 2: Executor Refactoring (CODE QUALITY SIGNAL)
- [ ] Split executor.py (1,300 lines) into:
  - `executor_core.py`: execute_task main flow
  - `executor_physics.py`: PhysicsEnrichmentMixin (natural capital, bioelectric, JEPA)
  - `executor_traces.py`: Execution trace logging
- [ ] Keep all tests passing through refactoring

## PHASE 3: End-to-End Demo Script
- [ ] `scripts/demo_cohezion.py`:
  - Train agent for 5K steps (quick demo)
  - Evaluate with UniverseEvaluator
  - Show compound loop in action
  - Print summary with coherence metrics
- [ ] README.md update with "Quick Start" section

## PHASE 4: Knowledge Persistence + Retrospective
- [ ] Persist all new learnings to SurrealDB (port 8001)
- [ ] Update KEY_LEARNINGS with training results
- [ ] Update MISSION_JOURNAL with Session 85
- [ ] Final retrospective

---

# LEGACY: Overnight Session Plan (Sessions 80-84, completed)

## WHY THIS MATTERS

Anthropic's **Research Engineer, Universes** role ($500K-$850K) builds "training environments where AI models learn complex, long-horizon agentic tasks." Cohezion IS this — a 12D physics-grounded universe with RL environments, compound engineering, multi-agent swarm, and autonomous skill refinement. Every hour of improvement tonight directly strengthens the portfolio case.

**Job requirements → Cohezion mapping:**
| Requirement | Cohezion Component | Gap | Tonight's Work |
|------------|-------------------|-----|----------------|
| RL environments | ManifoldEnv, SwarmEnv | Not production-polished | Polish + benchmark |
| Rigorous evaluations | DegradationDetector, JEPA surprise | Scattered, not unified | Evaluation framework |
| Simulation systems | 12D physics, cosmogony, gauge theory | Working but undocumented | Paper draft |
| Large-scale ML infra | CompoundExecutor, CostAwareRouter | Wired but not benchmarked | Production metrics |
| Sandboxing/containers | sandbox_validation.py (vanguard/) | Orphaned | Wire into compound loop |
| Published research | 16 cosmogonies, HIHO attractor | No paper | Draft arXiv preprint |

## OPERATING PARAMETERS

- **Runtime**: Now → 7:00 AM EST (autonomous, long-horizon)
- **Strategy**: Ralph Loop pattern — research → implement → verify → document → repeat
- **Context management**: Use Claude's built-in context awareness (NOT `cz context`). When approaching limits, persist and continue in new session.
- **Persistence**: Every significant finding → vault + KEY_LEARNINGS. Every code change → commit.
- **Test baseline**: 1,895 core tests passing. 0 regressions tolerated.

## Prior Sessions Summary (80-83)
- 17+ commits, 14/15 orphan modules wired, 3 feedback loops closed
- OI-MAS confidence routing, TurboQuant/IsoQuant compression, LatentMAS channel implemented
- L225-L232 extracted, 12 PRIME skills created, 757 Python modules, 183 skills

---

## PHASE 0: Persistence Foundation (30 min)
Ensure ALL subsequent work persists to vault + SurrealDB.

- [ ] **Start SurrealDB**: `surreal start --log info --user root --pass root file:///home/mike-anderson/.local/share/surreal/cohezion.db` or verify running
- [ ] **Verify vault write**: Test `vault_log_decision()` writes to `~/vaults/cohezion-vault/prefrontal/decisions/`
- [ ] **Create session continuation file**: `~/.cohezion-engine/sessions/<session-id>/continuation.md`
- [x] **Commit checkpoint**: 2df34f820 — Session 83 work committed

## PHASE 1: RL Environment Production Polish (2 hours)
**Anthropic signal: "RL environments, simulation systems"**

### 1A. ManifoldEnv Enhancement
- [x] **Proper reward shaping**: 3-stage curriculum (reach→maintain→optimize). Stage 1: 2x coherence gain + entry bonus. Stage 2: band maintenance + energy penalty. Stage 3: strong energy minimization.
- [ ] **Observation normalization**: Add `gymnasium.wrappers.NormalizeObservation` compatibility
- [x] **Episode statistics**: avg_coherence, avg_energy, hiho_time_ratio, convergence_step, curriculum_stage in info dict
- [ ] **Benchmark suite**: Train PPO (via stable-baselines3) for 10K steps, report learning curve + final performance
- [x] **Human-readable render**: `render(mode='human')` outputs step/stage/coherence_bar/deviation/streak/reward

**Files:** `src/cohezion/environments/manifold_env.py`, `tests/environments/test_manifold_env.py`

### 1B. SwarmEnv Multi-Agent Polish
- [ ] **PettingZoo compliance**: Verify full parallel API contract (reset, step, observe, close)
- [ ] **Communication channel**: Agents observe each other's positions (partial observability via gauge coupling)
- [ ] **Cooperative metrics**: Team coherence, Pareto efficiency, coordination overhead
- [ ] **Scalability benchmark**: 2, 4, 8, 16 agents — measure step time and convergence

**Files:** `src/cohezion/environments/swarm_env.py`, `tests/environments/test_swarm_env.py`

### 1C. Evaluation Framework
- [ ] **UniverseEvaluator class**: Unified evaluation across ManifoldEnv + SwarmEnv
  - Metrics: convergence rate, HIHO stability duration, energy efficiency, coordination index
  - Baseline comparisons: random policy, greedy policy, RL policy
  - Statistical significance: bootstrap confidence intervals
- [ ] **Eval API endpoints**: `/eval/run`, `/eval/compare`, `/eval/leaderboard`

**Files:** `src/cohezion/eval/universe_evaluator.py` (new), `src/cohezion/api/services/evaluation.py` (new)

## PHASE 2: Full Platform Coherence (2 hours)
**Anthropic signal: "build robust infrastructure", "high agency"**

### 2A. Wire Remaining Orphans
- [ ] **vibe/ → CompoundExecutor**: Wire NL→workflow compiler as alternative task intake
  - `VibeOrchestrator.compile(text)` → `WorkflowSpec` → CompoundExecutor.execute_task()
- [ ] **vanguard/ → sandbox isolation**: Wire sandbox_validation into execution pipeline
  - Pre-execution sandbox check before any code execution task
- [ ] **MCP Wire 5**: Convert top 2 HTTP servers to FastMCP stdio (journey, skills)

### 2B. Router Unification
- [ ] **RoutingOrchestrator**: Single entry point combining SmartRouter + CostAwareRouter + TipOfTheSpearRouter + DynamicModelRouter + TopologicalRouter
  - Input: task description + confidence requirements + budget constraints
  - Output: ModelRoutingDecision with unified confidence score
  - Pattern: Chain of Responsibility — each router adds information, final one decides

### 2C. Test Infrastructure
- [ ] **Fix remaining collection errors**: `test_context_engineering.py` (delete — tests external bmad), `test_api_endpoints_tdd.py` (already fixed import)
- [ ] **Fix physics/test_wiring*.py**: Identify missing imports, fix or skip
- [ ] **Target: 2,000+ tests passing** with 0 collection errors

## PHASE 3: Research Paper Draft (2 hours)
**Anthropic signal: "published influential ML research"**

### 3A. Paper Structure
Title: "Physics-Grounded Training Universes: Symmetry Breaking, Coherence Attractors, and Multi-Agent Governance for Safe AI"

- [ ] **Abstract**: 12D manifold + HIHO attractor + cosmogonic autonomy → safe agent training
- [ ] **Introduction**: Why physics-grounded > reward hacking. HIHO = Friston's FEP = Brahmagupta's zero.
- [ ] **Method**:
  - §3.1 Axiomatic State Space (12D manifold, SU(2) spinors, Fisher metric)
  - §3.2 Cosmogonic Autonomy (symmetry breaking → graduated trust)
  - §3.3 Compound Engineering Loop (SkillRefiner, RetrospectionEngine, DegradationDetector)
  - §3.4 Multi-Agent Gauge Coupling (SwarmEnv, TopologicalRouter, LatentMAS)
- [ ] **Experiments**:
  - ManifoldEnv convergence curves (PPO vs random)
  - SwarmEnv scaling (2-16 agents)
  - Compound loop: skill refinement trajectory over 100 executions
  - HIHO stability under adversarial perturbation
- [ ] **Results**: Quantitative metrics from Phase 1 benchmarks
- [ ] **Discussion**: Connection to Anthropic's Constitution (reason-based alignment = HIHO)
- [ ] **Related Work**: Active Inference (Friston), Constitutional AI (Anthropic), LatentMAS, V-JEPA

**Output**: `research/papers/physics-grounded-training-universes.md` (LaTeX-ready markdown)

### 3B. Figures
- [ ] HIHO convergence plot (coherence vs time, 25M cycles)
- [ ] Cosmogonic autonomy tier diagram (∅→HIHO)
- [ ] Compound loop architecture diagram
- [ ] SwarmEnv agent coordination visualization

## PHASE 4: Knowledge Persistence + Compounding (1 hour)
**Anthropic signal: "impact-driven", "good judgment"**

### 4A. Vault Persistence
- [ ] **Persist all learnings** (L225-L232+) to vault via `vault_log_decision()` + `vault_log_experiment()`
- [ ] **Cross-reference**: Link code modules ↔ learnings via `bidirectional_linker.py`
- [ ] **Graph health check**: Measure connectivity, reciprocity, freshness, orphan ratio → Graph HIHO score

### 4B. SurrealDB Persistence
- [ ] **Universe snapshot**: Current test count, module count, coherence metrics → `persist_universe_snapshot(tick=83)`
- [ ] **Learning artifacts**: Each L### → `persist_prompt_artifact(model_id="retrospective")`
- [ ] **Genesis tables**: Verify journey_transitions, universe_snapshots populated

### 4C. Knowledge Extraction
- [ ] **New learnings**: Extract L233+ from tonight's work
- [ ] **PRIME skill creation**: Skills for RL environment design, evaluation framework, router unification
- [ ] **Retrospective**: Full `/retrospect` cycle — prune, propagate, persist, verify

## PHASE 5: External Research + Integration (1 hour)
**Anthropic signal: "comfort with uncertainty", "rapid adaptation"**

- [ ] **arXiv sweep**: Latest agent training, RL environment design, multi-agent governance papers
- [ ] **HuggingFace**: New evaluation frameworks, agent benchmarks, training tools
- [ ] **GitHub**: LatentMAS implementations, TurboQuant code, Gymnasium environment patterns
- [ ] **Anthropic-specific**: Claude Constitution updates, MCP v2 patterns, new safety research
- [ ] **Integrate findings**: Wire new discoveries into codebase where actionable

## PHASE 6: Documentation + Portfolio Assembly (1 hour)
**Anthropic signal: "contribute to research culture"**

- [ ] **README.md overhaul**: Accurate metrics, clear architecture, getting started guide
- [ ] **CLAUDE.md verification**: All claims adversarially verifiable
- [ ] **Portfolio README**: Why Cohezion demonstrates Universes role capabilities
- [ ] **Demo script**: 5-minute walkthrough showing RL training → evaluation → compound refinement

## PHASE 7: Final Retrospective + Handoff (30 min)
- [ ] **Run full test suite**: Target 2,000+ passing, 0 regressions
- [ ] **Commit all work**: Conventional commits, meaningful messages
- [ ] **Update MISSION_JOURNAL**: Session 84 entry
- [ ] **Write continuation file**: For morning review
- [ ] **Graph HIHO score**: Report final health metrics

---

## AUTONOMOUS EXECUTION RULES

1. **Test after every change**: `uv run pytest tests/compound/ tests/swarm/ tests/physics/ tests/environments/ -q --no-cov` (quick check)
2. **Commit at natural boundaries**: After each sub-phase completion
3. **Context awareness**: Use Claude's built-in context tracking. When approaching limits, persist work and continue in new session
4. **Persist before exploring**: Always commit + vault before starting research
5. **No infrastructure drift**: If building something not in the plan, STOP and re-read the plan
6. **Skip if stuck >15 min**: Move to next task, note the blocker
7. **Quality > quantity**: One polished RL environment > five half-wired modules

## VERIFICATION

```bash
# Quick check (after each change)
uv run pytest tests/compound/ tests/swarm/ tests/environments/ -q --no-cov -k "not TextToLatent and not HolographicProjection"

# Full check (end of session)
uv run pytest tests/ -q --no-cov --ignore=tests/test_api_integration.py --ignore=tests/test_api_phase2.py --ignore=tests/test_observability.py

# Metrics
find src/cohezion/ -name '*.py' | wc -l  # Target: 760+
find src/cohezion/skills/ -name '*.md' | wc -l  # Target: 185+
wc -l src/cohezion/knowledge_graph/KEY_LEARNINGS.md  # Target: <300
wc -l src/cohezion/knowledge_graph/MISSION_JOURNAL.md  # Target: <150
```

## Implementation Plan (4 phases) — LEGACY (Session 82, completed)

### Phase 1: Internal Code Sweep + Infrastructure (PARALLEL with research)
- [ ] **Audit remaining unwired modules**: ouroboros/, data_mesh/, vanguard/, vibe/, pipelines/
- [ ] **Fix test collection errors**: 15 files with pre-existing import issues — fix the top 5
- [ ] **SurrealDB health check**: verify connection, list tables, check genesis schema
- [ ] **Vault health audit**: count notes, check orphan ratio, measure freshness
- [ ] **MCP Wire 5**: Rewrite top 2 MCP servers from HTTP→stdio (FastMCP pattern)

### Phase 2: OI-MAS Confidence-Aware Routing
Based on arXiv:2601.04861 — joint role+scale decision per agent step.
- [ ] **Add confidence scoring to ModelRoutingDecision**: extend dataclass with `confidence: float` field
- [ ] **Unify 4 routers**: SmartRouter(task→capability) + CostAwareRouter(complexity→model) + TipOfTheSpearRouter(constitutional→escalation) + DynamicModelRouter(health→fallback) should share confidence signals
- [ ] **Confidence-based escalation**: if model confidence <0.7 on a task, auto-escalate tier
- [ ] **TopologicalRouter integration**: wire exploit/explore/pivot regime detection into main routing pipeline
- [ ] **Task complexity from execution history**: use CapabilityMatrix success rates to inform complexity classification

**Critical files:**
- `src/cohezion/swarm/cost_aware_router.py` — confidence field + escalation logic
- `src/cohezion/swarm/smart_router.py` — affinity confidence scoring
- `src/cohezion/swarm/tip_of_spear_router.py` — wire confidence to sovereignty check
- `src/cohezion/swarm/topological_router.py` — wire to main pipeline (currently isolated)
- `src/cohezion/compound/capability_matrix.py` — provide execution history for complexity inference

### Phase 3: TurboQuant / IsoQuant KV Compression
Based on TurboQuant (Google), IsoQuant (arXiv:2603.28430), VQKV.
- [ ] **PolarQuant for FLUME 256D**: implement Cartesian→polar encoding for manifold vectors (preserves geometric structure)
- [ ] **QJL 1-bit for SemanticCache L2**: Johnson-Lindenstrauss sign-only projection for cosine similarity (32x storage reduction)
- [ ] **VQKV training-free KV compression**: apply to Ollama model context windows (82.8% compression, no retraining)

**Critical files:**
- `src/cohezion/flume/flume_vae.py` — PolarQuant encoding/decoding
- `src/cohezion/cache/semantic_cache.py` — QJL compressed L2 layer
- `src/cohezion/swarm/providers/ollama_provider.py` — VQKV context extension

### Phase 4: LatentMAS Agent Communication
Based on arXiv:2511.20639 (LatentMAS) + arXiv:2511.09149 (Interlat).
- [ ] **FLUME vector agent-to-agent channel**: agents exchange 256D FLUME embeddings instead of text
- [ ] **Shared latent working memory**: central buffer for agent KV cache transfer (training-free)
- [ ] **LatentMAS integration**: implement the Gen-Verse/LatentMAS pattern with FLUME as the latent space

**Critical files:**
- `src/cohezion/flume/flume_bridge.py` — latent communication channel
- `src/cohezion/swarm/team_orchestrator.py` — agent-to-agent routing via FLUME
- `src/cohezion/compound/executor.py` — latent context passing between execution steps

### External Research (background, parallel with all phases)
- [ ] Latest arXiv: agent governance, multi-agent orchestration, KV compression, VAE reasoning
- [ ] HuggingFace: agent frameworks, evaluation tools, training infrastructure
- [ ] GitHub: OI-MAS implementations, LatentMAS repos, FastMCP patterns
- [ ] Extract L230+ learnings from findings

## Task Dependencies

```
Phase 1 (Sweep + Infra) ────────── Independent, do first
Phase 2 (OI-MAS Routing) ───────── Builds on Session 82 feedback loop
Phase 3 (TurboQuant) ───────────── Independent of routing
Phase 4 (LatentMAS) ─────────────── Needs FLUME (Phase 3 PolarQuant helps)
Research ────────────────────────── Background, parallel with all phases
```

## Verification

```bash
# Core regression check
uv run pytest tests/compound/ tests/swarm/ tests/physics/ tests/world_model/ tests/environments/ -q --no-cov -k "not TextToLatent and not HolographicProjection and not Determinism" --ignore=tests/physics/test_wiring.py --ignore=tests/physics/test_wiring_batch2.py --ignore=tests/physics/test_wiring_batch3.py

# Target: 1,895+ core tests passing, 0 regressions
```

## Research Findings (to be populated by sweep agents)

_Agents running in background — findings will be integrated when complete._
