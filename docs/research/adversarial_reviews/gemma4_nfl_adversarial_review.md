## Forensic Adversarial Audit & Podium Playbook

### 1. Google Gemma 4 Developer Agent ($65k) + Paper Track ($35k)

**Assumption:** SWE-bench-style tool agent using Gemma 4 as backbone.

#### Adversarial Audit — What Kills Most Teams
- **Public test overfitting:** Hidden tests are often modified/added. Passing public tests is necessary but not sufficient. Winners optimize for general patch correctness, not public-test memorization.
- **Weak validation:** Random splits leak across repos/issues. Use **leave-one-repo-out** or time-based splits; track per-repo performance.
- **Context stuffing:** Dumping entire repo into context destroys performance. Retrieval quality is a top separator.
- **Fragile tool harness:** Bash timeouts, file-path errors, git state corruption silently kill runs. Podium teams build retry logic and state recovery.
- **Single-shot attempts:** One patch per issue rarely wins. Inference scaling + execution feedback is the biggest podium differentiator.

#### Top Winning Strategies — Agent Track
- **Fine-tune Gemma 4 on agent trajectories:** Use public SWE-bench trajectories or synthetic rollouts; supervised fine-tuning or DPO on successful tool-use sequences. Distill from stronger models if allowed.
- **Scaffold:** ReAct loop with tools: `ripgrep`, file read/edit, `git diff`, bash with timeout, test runner. Add a compact **repo map** at start.
- **Retrieval:** BM25 + code embeddings over chunks; rerank by issue text; include imports, tests, and nearby files. Keep context under ~15–20k tokens.
- **Inference scaling:** Sample **N=8–32 candidate patches** per issue. Execute tests; keep patches that pass. If none pass, run iterative repair using test output as feedback. Final selection via minimal diff, test pass, and self-consistency.
- **Minimal, general patches:** Do not edit tests. Avoid repo-specific hacks. Prefer small diffs that fix root cause.
- **Tool reliability:** Use timeout wrappers, checkpoint git state before edits, auto-rollback on failed runs.

#### Top Winning Strategies — Paper Track
- Focus on **one high-leverage component**: retrieval, memory, self-repair, or multi-agent orchestration.
- Provide **ablations** and **failure taxonomy**; open-source code and reproducible evaluation.
- Show gains on a hidden-like split, not just public SWE-bench.

---

### 2. NFL Big Data Bowl 2027 ($100k, Spatio-Temporal Tracking)

**Note:** 2027 theme not public; patterns below hold across prior Big Data Bowl tasks.

#### Adversarial Audit — What Kills Most Teams
- **Leakage:** Using frames after the event, play outcome in features, or player labels that encode target. Hidden test is different games/weeks — leakage fails catastrophically.
- **Random split validation:** Must group by **game_id/week** and use time-based splits. Random play splits give inflated scores.
- **Distribution shift:** Hidden games have different teams, players, coordinators. Overfitting to known player IDs or team tendencies hurts.
- **Raw tracking noise:** Missing frames, swapped player IDs, coordinate drift. Winners invest heavily in cleaning, interpolation, and normalization.
- **Metric mismatch:** Optimize directly for the competition metric (e.g., cross-entropy/BCE, rank-based). Calibrate probabilities.

#### Top Winning Strategies
- **Feature engineering at key moments:** Snap, handoff, throw, catch, tackle. Build play-level tabular features:
  - Speeds, accelerations, angles, distances to ball/nearest defender, separation, orientation.
  - Voronoi area, convex hull, blocker-defender matchups, route combinations, formation/motion.
- **Model stack:** LightGBM/XGBoost/CatBoost with monotonic constraints + a small LSTM/Transformer embedding of player trajectories. **Ensemble GBDT + NN** via rank averaging or weighted log-loss.
- **Validation:** Group by game_id; use adversarial validation to detect shift; track per-week performance.
- **Post-processing:** Isotonic/Platt calibration, clipping, enforce known football constraints.
- **Podium pattern:** Strong domain features + GBDT + one trajectory NN + diverse ensemble + rigorous grouped CV.

---

### Bottom Line
- **Gemma Agent:** Retrieval quality, fine-tuned tool use, and massive inference-time sampling with execution feedback win. Paper track rewards focused ablations and open code.
- **Big Data Bowl:** Clean, leakage-free features + grouped validation + GBDT/NN ensemble win. Deep learning alone rarely beats strong domain features on tracking data.
