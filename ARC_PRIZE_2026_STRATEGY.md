ARC Prize 2026: 6-Month Strategy (All 3 Tracks)
==============================================
Deadline: 2026-11-02 (27 weeks) | Total Prize Pool: $2,000,000

SUMMARY OF CURRENT STATE
------------------------
Three competition tracks exist for ARC Prize 2026:
1. Static Track (ARC-AGI-2): Program-synthesis benchmark on grid reasoning
2. Interactive Track (ARC-AGI-3): Novel interactive environments, agent must explore / plan / win
3. Paper Track: Novelty-focused; highest EV of the three (99% draft already written)

Current assets (as of 2026-04-28):
- Static solver: 3.4% solve rate on 1k training tasks (metacognitive DSL search)
- ARC-AGI-3 agents: 6 experimental variants (experiential, phi4, action-aware, systematic, goal-aware, object-clicker); V-Model gate exists; demo-only with no confirmed score
- Paper: DRAFT_v2.md (complete with ablation data, theorems, figures); gate_precision_v2.py instruments alignment gate; score_draft.py validates paper quality (~83/100)

TRACK ASSESSMENTS
-----------------
TRACK 1: Static (ARC-AGI-2)
- Current: 3.4% solve rate (strategy selection gives 4x over raw brute-force)
- Top leaderboard: ~4-5% (within 1-2pp)
- Highest-impact gap: Primitive library too shallow (33 primitives vs ARChitects >100)
- Second gap: No LLM program generation fallback for DSL-resistant tasks
- Resource need: Medium (local compute OK)

TRACK 2: Interactive (ARC-AGI-3)
- Current: 0 confirmed score; 6 prototype agents exist; V-Model gate active
- Top leaderboard: unknown, but milestone #1 (June 30, ~$25K) already at risk due to 69 day runway
- Highest-impact gap: No unified agent architecture (6 loose prototypes)
- Second gap: No training data (novel interactive tasks); learning is purely online/tabular
- Third gap: No world model generalization across games
- Resource need: High (arc-agi-3 SDK, environment iteration)

TRACK 3: Paper
- Current: 99% complete draft (v2); ablation results instrumented; novelty claims backed by data
- Gap: Final polish, supplementary materials, reproducibility artifacts
- Resource need: Low (editing + artifact packaging)

HIGHEST-IMPACT IMPROVEMENTS
---------------------------
Across tracks, ranked by expected score gain per unit effort:

1. DSL PRIMITIVE EXPANSION (Static Track) — HIGH IMPACT
   Expected: +2-3pp solve rate (from 3.4% to 5-6%)
   Approach: Port ARChitects-style object/relational primitives; add color histogram-based remapping, symmetry detection beyond diagonal, flood fill, path planning, and object containment tests. Add auto-discovery of new primitives via K-Search autoresearch loop.
   Effort: 2-3 weeks

2. LLM PROGRAM-GENERATION FALLBACK (Static Track) — HIGH IMPACT
   Expected: +1-2pp on hardest 50 tasks
   Approach: Use local Gemma-4 / Qwen2.5-Coder / phi4 to generate candidate program sketches for tasks where DSL budget exhausts. Validate with alignment gate; only emit if structural score = 1.0.
   Effort: 2 weeks

3. UNIFIED INTERACTIVE AGENT (Interactive Track) — CRITICAL
   Expected: Convert 0 to first confirmed score
   Approach: Merge experiential_agent + systematic_explorer + goal_aware_explorer into a single compound loop. Replace 6 separate files with one agent class that:
     a) Detects game type (click-only, action-sequential, puzzle)
     b) Routes to the specialized sub-agent (object_clicker for r11l/lp85 style, systematic explorer for others)
     c) Uses the V-Model gate for real threshold-based go/no-go
   Effort: 3-4 weeks

4. WORLD MODEL TRAINING WITH JEPA (Interactive Track) — HIGH IMPACT
   Expected: Better generalization across games
   Approach: The test_arc_jepa.py infra already exists (encoder 256D, predictor, world model with stop-gradient target). Train on ARC-AGI-3 public demos to learn transition dynamics instead of purely tabular memory. Use FLUME latent manifold (256D) for state representation.
   Effort: 3-4 weeks; blocked by training data availability

5. PAPER POLISH & ARTIFACTS (Paper Track) — HIGH EV
   Expected: Highest expected value ($2M pool, paper-only entry viable)
   Approach: Complete missing sections, run final ablation with expanded primitive set, generate supplementary figures, create reproducibility repo with MIT license. Score draft using score_draft.py to hit >90/100.
   Effort: 1-2 weeks

6. AUTORESEARCH ORCHESTRATION (Cross-track)
   Expected: Continuous marginal gains overnight
   Approach: Deploy ARPAO pattern (scripts/arpao_orchestrator.py) for the static solver. Each night the K-Search tree evolves primitive parameters and strategy thresholds. Feed winning mutations into both Static and Paper tracks.
   Effort: 1 week setup; then autonomous

27-WEEK MILESTONE TIMELINE
--------------------------
Week 1-2  (Apr 28 – May 11):  Paper Track Sprint
  - Final paper edit + supplementary materials
  - Reproducibility package (MIT license, Dockerfile, README)
  - Run score_draft.py → target >= 90/100
  - Submit Paper Track early if portal opens
  DELIVERABLE: Submission-ready paper artifact

Week 3-4  (May 12 – May 25):  DSL Expansion Phase (Static)
  - Audit ARChitects DSL (open-source) for primitives not in arc_solver.py
  - Port 20-30 high-yield primitives (object containment, symmetry axis, mirror, tiling patterns)
  - Run ablation_study.py on expanded set; expect >5% solve rate
  DELIVERABLE: New primitive library + ablation report

Week 5-6  (May 26 – Jun 8):  LLM Fallback Integration (Static)
  - Gemma-4 / Qwen2.5-Coder local inference for program sketch generation
  - Gate: only accept if alignment score == 1.0
  - Evaluate on hardest 50 tasks; measure delta
  DELIVERABLE: Hybrid solver (DSL + LLM fallback)

Week 7-8  (Jun 9 – Jun 22):  Interactive Consolidation (ARC-AGI-3)
  - Merge 6 prototype agents into unified compound loop
  - Implement game-type router (click / sequential / puzzle)
  - V-Model gate: run on all 25 public demos; produce scorecard
  - If score > 0, submit to Milestone #1 (June 30 deadline)
  DELIVERABLE: Unified agent + Milestone #1 submission (or NO-GO decision)

Week 9-10 (Jun 23 – Jul 6):  JEPA World Model Training (Interactive)
  - Collect transition trajectories from 25 demos via experiential_agent
  - Train ARCWorldModel (test_arc_jepa.py) on transition data
  - Replace tabular world model with neural predictor
  - Measure state-prediction accuracy; if >70%, integrate into agent
  DELIVERABLE: Neural world model checkpoint

Week 11-12 (Jul 7 – Jul 20):  Static Leaderboard Push
  - Submit hybrid solver to Kaggle static competition
  - Monitor leaderboard; autoresearch overnight on underperforming tasks
  - Gate: if solve rate < 3%, pivot to LLM-heavy strategy
  DELIVERABLE: Kaggle static submission with confirmed score

Week 13-14 (Jul 21 – Aug 3):  Interactive Leaderboard Push
  - Deploy JEPA-augmented agent to interactive evaluation
  - Run ARC-AGI-3 demos with neural world model + compound loop
  - Autoresearch on game-type routing thresholds via ARPAO
  DELIVERABLE: First confirmed interactive score

Week 15-16 (Aug 4 – Aug 17):  Cross-Track Synthesis
  - Feed interactive learnings (game mechanics) into DSL primitive library
  - Reverse: use DSL symmetry primitives to improve JEPA state representation
  - Publish intermediate paper / technical report (builds Paper Track credibility)
  DELIVERABLE: Synced primitive library + interim report

Week 17-18 (Aug 18 – Aug 31):  Scale & Stress Test
  - Scale static solver to full 4,000 task training set
  - Stress test interactive agent on all demos + synthetic variants
  - Run autoresearch daemon (thermal executor) for 24/7 optimization
  DELIVERABLE: Stress-test report + optimized checkpoints

Week 19-20 (Sep 1 – Sep 14):  Novelty Injection
  - Target hardest 10% of tasks with novel approaches:
    - Neural program synthesis (NeuroGolf transformer variants)
    - Kaggle compound orchestration for multi-agent voting
  - Evaluate on held-out validation split
  DELIVERABLE: Novel-approach candidate set

Week 21-22 (Sep 15 – Sep 28):  Integration & Validation
  - Combine best static approaches into single compound loop
  - Combine best interactive approaches into unified agent
  - Run full validation suite; ensure MIT-licensed repo is public
  DELIVERABLE: Final integrated submission artifacts

Week 23-24 (Sep 29 – Oct 12):  Final Ablation & Paper Update
  - Run full ablation on final static solver (4k tasks)
  - Update Paper Track draft with final numbers, figures, tables
  - Generate figure1_compound_loop.png and any new diagrams
  - Final score_draft.py pass; target 95/100
  DELIVERABLE: Final paper draft + final static solver version

Week 25-26 (Oct 13 – Oct 26):  Submission Window (Static + Interactive)
  - Make Kaggle submissions for both tracks
  - Monitor leaderboard; autoresearch on marginal improvements
  - Buffer week for re-submission if bugs found
  DELIVERABLE: Locked-in leaderboard scores

Week 27    (Oct 27 – Nov 2):  Buffer & Final Polish
  - Paper Track final submission (if separate portal)
  - Static + Interactive any last-minute fixes
  - Competition lock-in; no new experiments
  DELIVERABLE: All 3 tracks formally entered

RISK MITIGATION
---------------
| Risk | Impact | Mitigation |
|------|--------|------------|
| ARC-AGI-3 milestone #1 deadline too close (Jun 30) | High | Treat Week 7-8 as go/no-go spike; if no score > 0, deprioritize interactive and double down on static |
| DSL expansion yields < 2pp gain | Medium | Fallback to LLM-heavy strategy earlier (Week 5-6) |
| Local LLM inference too slow for Kaggle | Medium | Pre-generate program sketch cache offline; load at runtime |
| JEPA training diverges / overfits | Medium | Keep tabular world model as fallback; use ensemble |
| Paper rejected due to low novelty score | Low | DRAFT_v2 already scores ~83/100; novelty claims are structural (metacognition as first-class) |

IMMEDIATE ACTION ITEMS (THIS WEEK)
----------------------------------
1. Run static solver ablation with current 33 primitives on full 4,000 training tasks to establish exact baseline
2. Merge 6 ARC-AGI-3 agent files into unified agent module; delete dead prototypes
3. Run score_draft.py → log current score; iterate to 90+
4. Set up ARPAO cron (`*/20 * * * *`) for overnight autoresearch on static solver
5. Run V-Model gate on all 25 public demos to get quantified baseline for interactive track

DEFINED METRICS (WEEKLY DASHBOARD)
----------------------------------
- static_solve_rate_1k: target 5% by Week 6, 6% by Week 12
- static_solve_rate_4k: target 4.5% by Week 17
- interactive_games_solved: target >= 1 by Week 8, >= 10 by Week 16
- interactive_efficiency: target >= 25% median human by Week 16
- paper_draft_score: target 90 by Week 2, 95 by Week 24
- autoresearch_experiments_nightly: target >= 5 per night
- ksearch_best_solve_rate: track in ~/.cohezion-research/ksearch/arc_static.json
