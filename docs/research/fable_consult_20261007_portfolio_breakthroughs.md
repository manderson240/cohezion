# Fable consult 2026-10-07 — portfolio breakthroughs, grounded

**Author:** Claude Fable 5.1, headless, read-only. Nothing submitted, pushed, or edited outside this file.
**Sources read:** `~/cohezion-labs/KAGGLE_INDEX.md` (synced 2026-10-06), `scheduled/slot_audit.md` (2026-10-07 23:24Z),
`consult4_20261006/fable_strategy.md` (live CLI pulls 2026-10-06), `kaggle-october-loops.md` v3.1, `KAGGLE_GEMMA4_COORDINATION.md`,
`rsna-knee/ARM_LEDGER.md`, `ENVEDA_PLAN_20260930.md`, `arc-agi-2/ARC_TTT_STATUS.md`, `ARC_AGI2_IMPROVEMENT_PLAN.md`,
the v30 ARC-3 notebook, the local `arc_agi` 0.9.1 SDK (`scorecard.py`), `scripts/kaggle/*` daemons, `scheduled/gemma_ladder.py`,
`scheduled/presubmit_gate.py`, `kaggle_submit.py`, `ascension_orchestrator.py`.
**Not verifiable from this session:** live leaderboards (Kaggle CLI and SurrealDB calls required approval), daemon liveness
(`pgrep` is pid-namespace-blind in the sandbox: UNKNOWN, not absent), the official NFL BDB 2027 page (JS-rendered).

---

## 0. The brief's premises vs. what is measured

| Track | Brief said | Measured (source) | Consequence |
|---|---|---|---|
| ARC-AGI-3 | "Rank 1 is 19.45%", we 0.12–0.25, target >0.35 | Scale is 0–100. Leader **55.89**, 5th **38.33**, open-source Milestone-2 baseline **25.8 ± 3.9**. We **0.26** (v15), rank ~2341/3881. v30 scored **0.12**, v29 0.16 (index; consult4; slot audit) | ">0.35" is +0.09 points = ~100 ranks. The real ladder is 0.26 → 25.8 (fork) → 38 (prize). |
| ARC-AGI-2 | "Top-10 cutoff 33.89%, +2.08% = 2–3 tasks" | 33.89 is the **public notebook's score**, rank ~23. 8th (last prize) = **48.33**. We 31.81 = that fork, rank 239. Our DSL attempt-2 injections measured **−1.25 / −0.69** (v13, v14). TTT lane: 0/120 local | No +2.08 gap exists. 2.08% of 240 tasks is 5 tasks, not 2–3. Status is banked-no-further-spend. |
| RSNA | "Podium ~0.957, gap +0.014" | 10th = **0.960**; efficiency top-3 0.957–0.959 with fast runtimes. We 0.943 = public speedy-raptors fork (ref 56477886); every patch v20–v28 scored ≤0.943 (v26 0.939, v27 0.942). Diverse arm fold-0 gate **FAIL** (OOF 0.867, needs 0.90). 26.6 GPU-h expire 2026-10-10 | Gap to a prize is +0.017 with 15 days and no OOF for the stack. |
| Enveda | "~0.335, Top-10 0.383, Rank 1 0.425" | Best is now **0.42** (the public 0.421 fork, ref 56920135). 5th = **0.443**, leader **0.478**. Our own v10–v17 rerankers: 0.288–0.335 | The 4-channel/GBDT/tautomer stack is a weaker re-derivation of the public stack. The 0.42 fork is the base. |
| Gemma 4 | (no score given) | We **0.10** (anchor). Leader 0.24, 2nd–4th **0.18**, 0.17 ×14. Prize = 37/18/10K top-3 | The only board where a config change reaches a prize zone. |
| NFL BDB 2027 | "starter verified" | Notebook has 7 cells, loads no tracking data, computes no metric, and its header already asserts "+38.4%" | Nothing is verified yet; the headline claim precedes the data. |
| Daemons | "feed breakthroughs back" | `ascension_orchestrator` submits with `kernel_version=1` by default; 5 identical RSNA and 3 identical Enveda submissions pending today; presubmit gate PASSed with evidence `"test"` | The feedback loop currently burns slots and records self-declared predictions. Fix before adding research. |

The slot audit's own headline (v3 loops doc): **24 of 30 submissions last week scored below our existing best; 0 beat it.**
The binding constraint is not algorithms. It is unmeasured variants entering scarce daily slots. Every recommendation
below is shaped as *measure locally → gate → one submission*.

---

## 1. Portfolio expected value, ranked (what to do this week)

1. **Gemma 4** — queue `thinking_on` as the next ladder rung (measured lever: 17.8% → 37–40% locally, thread 746250; our anchor runs thoughts OFF). 0 GPU, 1 slot/day, prize zone 0.18 reachable.
2. **Daemon repair** (section 8) — stops the slot burn that has cost 24 slots in 7 days. 0 GPU, no slot.
3. **Enveda** — Class-2 candidate generation + fingerprint model + learned ranker on the 0.42 base (section 5). 70 days, ~4 GPU-h per training run, the only long-horizon track where the top is reachable by engineering.
4. **Gemma paper track** ($35K, no accuracy criterion, "Best New Resource" fits the ladder + slot auditor + local eval harness). Due Nov 12.
5. **ARC paper track** ($75K guaranteed pool, due Nov 9) — document the 33.89-lineage submission plus measured negatives honestly.
6. **NFL BDB 2027** — a writeup competition; start the actual analysis (section 7). Due Jan 6.
7. **ARC-AGI-3** — build the local RHAE harness first (section 2); no submission until a local run beats v15's local number. Fork the open-source milestone only if G4 quota is otherwise idle.
8. **RSNA** — freeze at 56477886; optionally the 0.944 fork on expiring quota Oct 8–9; no more patches.
9. **ARC-AGI-2** — select the 33.89 fork rerun as a final if it scores ≥31.81; stop variants.

---

## 2. ARC-AGI-3 — the scoring rule makes the current agent class unwinnable; here is what wins on CPU

### 2.1 What is actually scored
Local SDK (`arc_agi/scorecard.py:121-136`, the exact code the Kaggle offline mode runs):

```
level_score = min(100, 100 * baseline_actions / actions_taken)   if level completed
            = 0                                                   otherwise
env_score   = mean(level_scores)       # over ALL levels of the game, uncompleted = 0
```

The 2026 competition metric per arcprize.org is RHAE = (human_actions / ai_actions)², i.e. the same ratio **squared**
(the local SDK 0.9.1 is linear; both are monotone in actions, so a local harness ranks candidates correctly but
under-predicts the penalty). The human baseline is the second-best of ten first-time players.

Local game `vc33` has 7 levels with baselines `[7, 18, 44, 61, 131, 34, 152]` (447 actions total). Our notebook caps
each game at **150 actions and never tracks level boundaries**. Consequences, by arithmetic:

- Spending 150 actions on level 1 (baseline 7) and completing it: level score 4.7 (linear) / 0.2 (squared); game
  score ≤ 0.67 / 0.03 because the other six levels are 0. That is the mechanism behind 0.26.
- Reaching 35 requires completing most levels at ≤ 1.7× human actions (squared rule). That is goal inference from the
  first frames, not search. The open-source Milestone-2 solution does it with an LLM (Qwen3.8-Flash-Next, RTX Pro 6000)
  and lands at 25.8 ± 3.9.

**Verdict:** macro-action compilation, BFS affordance traversal, cellular-automaton recognition and goal-distance
shaping all *reduce actions within a level the agent already understands*. None of them creates understanding. On CPU
without a model, the realistic ceiling is low single digits from "click" games whose first levels are cheap. Say so
in the paper; do not restart the score chase (September verdict, re-confirmed by v27–v30: 0.11–0.25, then 0.12).

### 2.2 The one thing to build: a local RHAE harness as the L14 gate
`~/cohezion-labs/arc-agi-3/ARC-AGI-3-Agents/.venv` already has `arc_agi 0.9.1` + `arcengine 0.9.3` and **25 offline
games** under `environment_files/`. `test_v28_local.py` runs them but prints only steps/levels, not the score. Make the
score the artifact:

```python
# arc3_local_rhae.py  (run in the ARC-AGI-3-Agents venv)
import json, arc_agi
from arcengine import GameState
arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir="./environment_files")
card = arcade.create_scorecard()
rows = []
for i, info in enumerate(arcade.get_environments()):
    env = arcade.make(info.game_id, scorecard_id=card)
    agent = AGENT_CLASS(info.game_id, seed=i * 100)
    obs, level_start, levels = env.reset(), 0, 0
    per_level = []
    for step in range(MAX_ACTIONS_PER_GAME):
        if obs is None or obs.state in (GameState.WIN, GameState.GAME_OVER): break
        act, data = agent.choose_action(obs)
        obs = env.step(act, data=data)
        if obs and obs.levels_completed > levels:          # level boundary: reset the per-level counter
            per_level.append(step + 1 - level_start); level_start = step + 1; levels = obs.levels_completed
    base = info.baseline_actions or []
    lin = [min(100, 100 * b / a) for a, b in zip(per_level, base)] + [0] * max(0, len(base) - len(per_level))
    sq  = [min(100, 100 * (b / a) ** 2) for a, b in zip(per_level, base)] + [0] * max(0, len(base) - len(per_level))
    rows.append({"game": info.game_id, "levels": levels, "per_level_actions": per_level,
                 "score_linear": sum(lin) / max(1, len(base)), "score_rhae": sum(sq) / max(1, len(base))})
sc = arcade.close_scorecard(card)
json.dump({"games": rows, "mean_linear": sum(r["score_linear"] for r in rows) / len(rows),
           "mean_rhae": sum(r["score_rhae"] for r in rows) / len(rows), "sdk_total_actions": sc.total_actions},
          open("rhae_local.json", "w"), indent=1)
```

Gate (append to `presubmit_gate.py` evidence rules, section 8): an ARC-3 submission requires `rhae_local.json` for the
exact notebook cell, with `mean_rhae` ≥ the v15 agent's `mean_rhae` on the same 25 games. v15 is the first thing to
run through this harness, because its 0.26 is the only board number we have and it is the calibration anchor.

### 2.3 Agent changes that are consistent with the metric (in order of expected lift per action)
1. **Per-level action accounting and a per-level budget.** Track `obs.levels_completed`; when actions in the current
   level exceed `k × median(baseline)` with `k = 3` (if `info.baseline_actions` is populated at competition time; else
   a fixed 60), abandon the game. This does not raise that level's score (already 0) but reclaims wall-clock for games
   the agent can finish. Invariant: `len(per_level_actions) == obs.levels_completed` at game end.
2. **Deterministic-replay Go-Explore inside one game.** The environments are deterministic. Archive cells keyed by the
   Zobrist hash with `(levels_completed, -actions_to_reach, action_prefix)`. "Return" = `RESET` + replay the prefix.
   This is real Go-Explore (the current class is a greedy rarity walker with cycle penalties; the name is aspirational).
   Cost model: every replayed action counts against the score, so return-to-cell is only worth it when the frontier
   cell is strictly better in `levels_completed`. Use it to *finish* a level found by exploration with the minimal
   known prefix, not to explore. Invariant: after `RESET` + replay, `hash_frame(obs.frame) == archived_hash`
   (discriminating test: a non-deterministic or mis-replayed prefix fails it).
3. **Minimal-prefix compression after a level completes.** Once a level is solved with prefix `p`, run BFS over the
   recorded transition graph for that level to find the shortest action path to the winning frame; on the *next*
   attempt of that game (if the harness allows a RESET without ending the game) replay the shortest path. On Kaggle
   each game is played once, so this only helps if the gateway lets a RESET restart the level with the action count
   preserved; measure it locally before relying on it.
4. **Click games: component-rarity is already the right prior; add change-detection.** Score a click by
   `|frame_t+1 − frame_t|_0` (number of changed cells); keep a per-game bandit over component classes (color, size
   bucket) with reward = changed-cells and a bonus for `levels_completed` increments. Avoid re-clicking a component
   that produced zero change. This is the cheapest "affordance graph" and it is measurable.
5. **Drop** `rng.random() < 0.35` random clicks while movement actions exist (v30 line in step 1 of `choose_action`):
   under RHAE, a random action is a guaranteed loss.

Everything above is CPU-only, pure Python, and fits the 10-concurrent-CPU-session model: run the 25 local games
with 10 seeds each in parallel sessions, aggregate `rhae_local.json`, and only the best seed-config goes to the
single daily slot.

---

## 3. ARC-AGI-2 — there is no +2.08 gap to extract; there is a final-selection decision

- 31.81 is the LB33.89 recipe (Qwen3-4B SFT139 + per-task LoRA, D4 + colour permutation voting, constrained DFS
  decode) with the author's defaults; its seed variance on identical settings is 28–34 (our Sep-3 measurement). The
  difference between 31.81 and 33.89 is inside that band.
- **Attempt-2 DSL injection is net negative by construction.** The recipe's `attempt_2` is the second vote cluster
  from the model's own augmentation ensemble. Replacing it with a DSL guess helps only on tasks where the DSL is right
  and the model's second cluster is wrong; our DSL measured 0/120 locally, so the first set is empty while the second
  is not. Measured on the board: −1.25 (v13), −0.69 (v14). The "non-destructive" invariant is non-destructive to
  `attempt_1` only.
- TTT improvements with real marginal lift exist (more augmentations per task, longer per-task LoRA, 2-pass
  self-consistency) but they are throughput-bound on L4×4 inside 12 h, and our own TTT lane was 30× too slow
  (~2,000 s/task on T4). The NVARC/TRM regime at 48–84 is a different model class.
- **Action:** let ref 56897895 / 56920228 (the fork rerun) score; if ≥31.81 select it as one of the two finals. Stop
  v12–v15-style variants. Spend the remaining effort on the ARC paper (Accuracy criterion gets a small lift from
  33.89 vs 31.81; the honest Theory/Progress sections are where points come from).

---

## 4. RSNA — the +0.017 is not bridgeable by TTA or cross-planar attention in 15 days; here is why, and the one honest probe

- Targets are five columns: `acl_tear, meniscus_tear, abnormal, fracture, tendon_injury`
  (`verify_submission_invariants.py:160`). Metric: mean column-wise ROC-AUC. Each column is ranked **independently**.
- **The Kolmogorov projection is metric-neutral at best.** `abnormal := max(abnormal, max_k p_k)` changes only the
  `abnormal` column's ordering. It raises AUC iff the sub-finding heads rank abnormal studies better than the abnormal
  head on exactly the rows where they disagree. That is an empirical question answerable only with OOF predictions,
  and the stack has none (it is inference-only over other teams' weights, ARM_LEDGER). It is not a validity
  requirement of the metric; keep it only if it passes a measured gate.
- Pure intra-column rank normalisation is a no-op for AUC (rank-invariant) except where it breaks ties; the v20→v27
  swings (0.939–0.943) are therefore slice-count and blend-weight effects plus non-determinism at the 0.001 level
  (consult4 §3). Each patch cost a slot and a 6–8 h scoring rerun.
- What the top does (thread 745861): LLM-relabelled report targets (host-permitted), own 2.5D/MIL readers, 5 folds,
  rank-blend 15–30% into the public stack. Our arm skipped relabelling and plateaued at OOF 0.867 across epochs 4–9:
  label noise, not under-training. A credible retry is ~15–20 GPU-h for maybe +0.002 → still rank ~250.
- Cross-planar 3D attention and TTA: both are *training-side* changes needing OOF to tune; with no OOF, no training
  recipe that passes its own gate, and 26.6 expiring GPU-hours, they cannot be validated before Oct 22.
- **Action:** freeze at 56477886 (0.943); optionally run the goodpjw2008 0.944 fork verbatim on Oct 8–9 expiring
  quota and submit once if the commit run reproduces 0.944; cancel the four duplicate v28 pendings' successors by
  fixing the orchestrator (section 8). Do not blend the fold-0 arm (consult4 Decision B, unchanged).

---

## 5. Enveda CASMI26 — the step function is candidate generation, not ranking features

Metric: MRR@25 over ~400 molecules, correct = same InChIKey14 after tautomer canonicalisation. Hidden class mix:
Class 1 (library-reachable by spectral similarity), Class 2 (PubChem/COCONUT only), Class 3 (de novo).

- Our v7 analog engine returns training-set structures ⇒ it can only score Class 1. The 0.42 public fork pools
  PubChem/COCONUT candidates + FPNet fingerprint model + LightGBM + forward predictors + RRF (consult4). Spectral
  entropy contrastive ranking, neutral-loss trees and substructure-fingerprint embeddings are all **ranker features**;
  a ranker cannot promote a candidate that is not in the pool. First measure recall.

### 5.1 Two offline measurements before any build ($0, CPU)
1. **Class attribution of the 0.42 output:** fraction of our correct top-1/top-25 hits whose structure has a training
   spectrum. If ~all, Class 2 is the whole gap.
2. **Candidate recall@25/@100 on held-out train structures** (InChIKey14-disjoint folds): formula enumeration from
   precursor m/z under adducts `[M+H]+, [M+NH4]+, [M+Na]+, [M−H2O+H]+` at ±5 ppm (the v15 lesson: a Gaussian mass
   penalty inside a pre-filtered isobar window is noise, but the *window* itself must be tight), candidates from the
   `prvsiyan/coconut-casmi26-candidates` + PubChem tiers already attached to the kernel. If recall@100 < 0.6 the
   ranker is not the bottleneck.

### 5.2 The build (D1–D45 of the 68 days left)
- **Fingerprint model:** binned spectrum (0.01 Da bins, 50–1000 m/z, log1p intensity) ⊕ neutral-loss channel
  (precursor − fragment) → MLP → ECFP4 2048-bit multi-label BCE, trained on the 2.5M train spectra on T4×2 (~4 h).
  Loss weighting by bit prevalence; report per-bit AUC and Tanimoto(pred, true) on the structure-disjoint fold.
- **Features per (query, candidate):** Tanimoto(pred FP, cand FP); max modified-cosine to the nearest library analog
  of the candidate (the v7 engine, reused as a feature); ICEBERG forward-prediction cosine where available;
  `log1p(PubChem count)` popularity prior; precursor ppm error; number of matched diagnostic neutral losses; formula
  match flag; spectral entropy similarity (Li et al. 2021) between query and predicted spectrum.
- **Ranker:** LightGBM `lambdarank`, group = query, label = InChIKey14 match, trained on structure-disjoint folds so
  the model learns Class-2 behaviour. Gate: local MRR@25 on the disjoint fold must beat the 0.42 fork's local MRR on
  the same fold (write both numbers in the evidence line).
- **Fusion:** reciprocal-rank fusion of (new ranker, 0.42 fork) — RRF is robust to score-scale mismatch and is what
  the 0.421 lineage does; tune `k` on the fold, not on the board.
- **Top-25 diversity:** dedupe by InChIKey14 after canonicalisation before filling 25 slots (the v18 "guaranteed
  25-slot completeness" must be post-dedupe or it wastes slots on tautomers).
- **Licence guardrail:** the 0.421 lineage uses `ahmedberatozer/casmi26-*` ("Other, non-commercial"); eligibility is
  unresolved (thread 745072; NIST data is disqualifying per 744470). Build the fingerprint model on the competition
  train set so our stack is prize-clean if we approach 0.44.

---

## 6. Gemma 4 — the only board with a reachable prize zone; the lever is already known

- Measured (thread 746250, 129-task local eval): thinking OFF 17.8% vs ON 37–40%; graph tools no benefit (21/21
  semantic searches empty); 25 vs 50 tool calls = −14 tasks; temp 0.4–1.0 tie. Thread 745059: `include_thoughts` in
  adk_submission 0.2.12 *disables* reasoning. **Our anchor runs thoughts OFF.**
- Time: ~120 tasks run sequentially inside 12 h ⇒ ≤ 6 min/task is the binding constraint; local 6-min cap scored
  28.7% vs 41.9% at 15 min, which compresses the board toward 0.17–0.18.
- **"Token-insulated action verification" and "deterministic tool compilation", answered concretely:** in this
  harness the agent is a config (agent.yaml, prompts, sampling.yaml, eval_config.yaml); there is no harness code of
  ours running inside the sandbox. Loop and timeout traps are prevented by budget fields and prompt invariants, not by
  an AutoHarness:
  1. `eval_config.yaml`: `max_time_minutes` 6–7, `max_tool_calls` 50–60, `max_turns` 30; the harness extracts the
     `git diff` even without `submit_patch`, so a time-out with an edit in place still scores.
  2. Prompt invariants (already in the ladder as `edit_early`, `pacing_status`, `edit_escaping`): first `edit_file`
     by tool call 6; `get_status()` every ~8 calls; stop exploring at 70% budget; `old_string` 3–5 exact lines, no
     escaping.
  3. Prune `search_similar_code` and `get_code_subgraph` from `tools:` (context overflow, no measured benefit).
- **Ladder order:** `thinking_on` (new variant: `include_thoughts`/thinking enabled with summaries) → `prune_graph_tools`
  → `task_timeout_budget` 6–7 min → `more_calls` (pending 56884361 already) → temp. Adopt only at ≥ best + 0.01.
- Paper track: the ladder log + slot auditor + `local_eval/` harness + the measured failure taxonomy (eval_config miss
  → 60-min default → three 0.00s; blank-score outage; `include_thoughts` inversion) is a "Best New Resource" entry.

---

## 7. NFL Big Data Bowl 2027 — metrics that score on all three rubric axes

Caveat: the official page could not be fetched; the starter notebook's own fields (`quick_pressure`, `player_get_off`,
`combine_results.csv`, organizer topic 746678) establish the pass-rush/pass-protection theme with combine tracking.
Historically BDB is judged by NFL club analysts on Football Score, Data Science Score, Report/Writeup and
Visualisation, roughly equal weight; the writeup is capped (~2,000 words) and must be reproducible from the notebook.

**First, remove the unsupported claim.** The notebook header asserts "+38.4% in predicting Quick Pressure Rate" before
any data is loaded. Judges read that as fabrication. Replace with the hypothesis and fill the number from the model.

### 7.1 Metric design (compute these, then let the data decide the headline)
- **Get-off burst** (in-game): from the snap frame, `a_0.5 = (s(t0+0.5) − s(t0)) / 0.5` and the integral of
  acceleration over the first 1.0 s; target `player_get_off` directly. Combine analogue: 10-yard split and the first
  0.5 s of the 40 at 10 Hz. This is the cleanest transfer pair.
- **Angular burst** `dθ/dt`: rate of change of rusher heading `dir` (unwrapped) in the first 1.5 s after the snap,
  and in the 3-cone drill at the cone turns. Smooth with a Savitzky–Golay filter (window 5, order 2) before
  differentiating; report sensitivity to the window.
- **Time-to-closest-approach (TCA)** to the QB and its derivative; `v_closing = (v_rusher · r̂)`; the notebook's
  function is right but needs the QB's velocity too (relative velocity), and a guard for `v_closing ≤ 0`.
- **Pocket control share:** Voronoi/Dirichlet tessellation of the pocket polygon (QB ± tackles' outside shoulders,
  LOS to QB depth) at each frame; rusher's share of pocket area within 1.0 s of the snap. Bounded in [0,1], robust to
  field position, and visualisable.
- **Matchup-adjusted dominance:** fit `quick_pressure ~ get_off_burst + dθ/dt + Voronoi_share + TCA_slope +
  (1|rusher) + (1|blocker) + (1|game)` as a mixed-effects logistic model. The random effects separate player skill
  from scheme/opponent; report the rusher random-effect posterior as the "dominance" rating with credible intervals.
- **Combine → game transfer:** regress the rusher random effect on combine kinematics with position as a fixed effect;
  report partial R² per combine feature. The honest result may be modest; the writeup wins on soundness, not size.

### 7.2 Statistical soundness checklist (what analysts look for)
- Train on 2023–2024 weeks, validate on a held-out season/weeks; cluster bootstrap by game for CIs; calibration plot
  and Brier alongside AUC; empirical-Bayes shrinkage of per-player rates toward the position mean with the sample
  size shown; a null model (position-only) as the baseline every claim is measured against.
- Visuals: one animated play (Voronoi share evolving), one calibration plot, one shrinkage plot (raw vs shrunk rates),
  one combine-vs-game scatter with CIs. Four figures, each answering one question.

---

## 8. Daemon feedback — the loop is currently harmful; repair before feeding it

### 8.1 Confirmed defects (read from the code today)
- **D1 — every orchestrated submission is kernel version 1.** `ascension_orchestrator.submit_notebook` never passes
  `-v`; `kaggle_submit.py:254-259` then sets `kernel_version=1` ("to ensure valid CreateCodeSubmission request").
  Prediction (falsifiable tomorrow): the five pending RSNA "v28" refs 56920108…56921662 and the three pending Enveda
  "v18" refs will score identically to each other and equal to those kernels' version-1 outputs, not to v28/v18.
- **D2 — no idempotency.** `submitted` is an in-memory flag; a `FAILED` return (e.g. IV&V printout after a successful
  API call) sets `all_done=False` and the 20-s loop re-submits; two orchestrator instances (headless swarm +
  sentinel) double it. Result today: 5 RSNA + 3 Enveda duplicates in one UTC day.
- **D3 — the pre-submit gate accepts any non-empty string as evidence** and the predicted score is self-declared.
  Today's log: `PASS: arc-prize-2026-arc-agi-2 predicted 33.89 vs best 31.81; evidence: test`. The gate cannot block
  what it was built to block.
- **D4 — the research engine bakes false premises into its prompts** (`sprint_arc2_theorems`: "target >= 33.89% Top
  10 solo"), `query_ollama` concatenates `thinking` into the answer so a reasoning-only reply counts as success, and
  `FlumeManifoldAuditor` embeds the *hypothesis text* via SHA-256, so its "drift" and "HIHO coherence" are functions
  of the string, not of any competition quantity. `audit_cases` hard-codes `predicted=0.35` for ARC-3. This is how the
  brief's wrong numbers were produced and then confirmed.
- **D5 — the brief's `kaggle_discussion_learner.py` and `scientific_digital_twins.py` are not scripts.** They are
  modules (`cohezion.researcher.kaggle_discussion_learner`, `cohezion.competitions.scientific_digital_twins`) driven
  by `mine_kaggle_discussions.py` and `autonomous_experiential_research_loop.py`. The twins' `evaluate_next_step`
  returns fixed advice strings; `reason_with_ollama_cloud` targets `deepseek-v4-pro:cloud`, which returned empty on
  2026-09-30 even for "say pong" (broken instrument, not a verdict).
- **D6 — the sentinel polls but consumes nothing.** `master_24_7_kaggle_sentinel.run_cycle` writes score changes to
  SurrealDB and `sentinel_status.json`; no daemon reads the slot audit or the lessons file to change behaviour.

### 8.2 Repairs (small, each with a discriminating test)
1. `kaggle_submit.py`: remove the `kernel_version=1` default; when `-v` is absent resolve the **latest** version via
   `api.kernels_list_versions` (or `kernels status` output) and print it; refuse to submit if it cannot be resolved.
   Test: calling without `-v` against a kernel with 28 versions must pass `kernel_version=28`, never 1.
2. `ascension_orchestrator.py`: persist a ledger `{competition: {kernel: {version: ref}}}` to disk; before
   submitting, list `competitions submissions` and skip if a submission for that (kernel, version) exists in any
   status; one process lock (`fcntl.flock`) so two instances cannot both submit. Test: a second call with the same
   (kernel, version) is a no-op.
3. `presubmit_gate.py`: require the evidence string to name an existing artifact path (`rhae_local.json`,
   `metrics_f0.json`, an OOF CSV, or a public kernel URL with its board score) and require `pred <= measured` read
   from that artifact where it carries a number. Test: evidence `"test"` → BLOCK.
4. `bleeding_edge_research_engine.py`: delete the fixed premises from every sprint prompt and inject the current
   `slot_audit.md` + `KAGGLE_INDEX.md` sections as the premise; treat `response == ""` as failure regardless of
   `thinking`; drop the manifold audit from the loop or re-implement it over a real quantity (predicted − scored
   history per competition). Test: a prompt must contain today's best/leader numbers, not literals.
5. Make the sentinel a **consumer**: on each newly scored submission, compare to the prediction logged by the gate
   and append the `(pred, scored, error)` triple to `KAGGLE_LESSONS.jsonl` as `kind: outcome` (L13 already does the
   outcome half; the gate's prediction is the missing half of the learning signal).

### 8.3 What "feed breakthroughs back" should mean after the repair
Each competition gets one measured local instrument (ARC-3: `rhae_local.json`; Enveda: disjoint-fold MRR@25; Gemma:
ladder log; RSNA: none until an OOF exists; ARC-2: `_score_local.py` on the 120 eval tasks; NFL: held-out-season AUC
and Brier). The research daemons may propose variants; only a variant whose instrument number beats the current best
may enter a slot, and the sentinel records prediction vs outcome. That closes the loop the brief asked for without
burning slots.

---

## 9. Immediate execution order for the swarm (next 72 h)

| # | Owner | Action | Gate / evidence | Cost |
|---|---|---|---|---|
| 1 | Claude | Patch D1 + D2 in `kaggle_submit.py` / `ascension_orchestrator.py`; stop any running orchestrator | tests in §8.2 green; no new duplicate refs tomorrow | 0 |
| 2 | ladder | Add `thinking_on` variant to `gemma_ladder.py` VARIANTS at index `next_idx`; let the daily task submit | board score ≥ 0.11 adopts | 1 slot |
| 3 | agy | Enveda §5.1 measurements (class attribution, candidate recall) on CPU | two numbers in `ENVEDA_PLAN` | 0 |
| 4 | agy | ARC-3: run v15 and v30 through `arc3_local_rhae.py` on the 25 local games, 3 seeds each | `rhae_local.json` for both; v15 must rank above v30 or the harness is wrong | 0 |
| 5 | Claude | Patch D3 (gate evidence must be an artifact) | `"test"` → BLOCK | 0 |
| 6 | Claude | Read the fork rerun's ARC-2 score when it lands; select finals | ≥31.81 → final | 0 |
| 7 | agy | NFL: load tracking + combine data in the starter, compute get-off burst and TCA on one week, delete the "+38.4%" header | notebook runs end-to-end on Kaggle CPU | 0 |
| 8 | — | RSNA: nothing except the optional 0.944 verbatim fork on Oct 8–9 | commit run reproduces 0.944 | ≤8 GPU-h |

Sources for the live numbers: `~/cohezion-labs/consult4_20261006/fable_strategy.md` §0 (CLI pulls 2026-10-06 19:00 UTC),
`~/cohezion-labs/scheduled/slot_audit.md` (2026-10-07 23:24Z), `~/cohezion-labs/KAGGLE_INDEX.md` (2026-10-06).
ARC-AGI-3 scoring: `arc_agi/scorecard.py` (local SDK) and https://arcprize.org/competitions/2026/arc-agi-3 (RHAE).
