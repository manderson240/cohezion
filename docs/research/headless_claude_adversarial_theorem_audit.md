# Headless Claude Adversarial Audit of Cohezion Kaggle Theorems
**Audited At**: 2026-10-07 02:48:15 UTC  
**Auditing Models**: Headless `claude-opus-5-5` & `claude-sonnet-5-5` via CLI (`claude -p`)  
**Core Question**: *Are our theorems the RIGHT theorems for the problems they were supposed to solve? If they were, why aren't we at the top of the leaderboards?*

---

## 1. Cynical Kaggle Grandmaster Audit (Claude Opus)
# Diagnosis: four theorems, each aimed at the wrong target

Throughout, **[file]** means I checked it on disk in `~/cohezion-labs`, and **[inf]** means it is my judgment.

## Q1. Why these are toy abstractions

All four make the same mistake. Each theorem proves something true about a quantity the leaderboard doesn't score.

| Theorem | What it optimizes | What the metric scores |
|---|---|---|
| T1 RSNA | Log-loss on an `Abnormal` column | **Macro AUC over 12 columns, with no `Abnormal` column** [file] |
| T2 ARC-2 | Zero false positives on the demo pairs | Exact match on the test output, within 2 attempts |
| T3 ARC-3 | Probability of never repeating a state | **`(human_actions / ai_actions)²`**, so every wasted move costs quadratically [file: memory `arc-agi3-scoring-efficiency-pivot`] |
| T4 CASMI | A spectrum-to-spectrum similarity function | MRR@25 over a candidate list, where **84% of test molecules have no reference spectrum** [file: `casmi26/RECON.md`] |

**ARC-AGI-3 (T3).** Under that metric, "escapes deadlock with probability 1" is a promise to spend an unbounded number of moves, and the score charges for each one squared. Cycle avoidance is exploration, and exploration is exactly what the formula punishes. The proof also fails in practice:
- **[inf]** Hashing raw frames makes cycle detection pointless if the frame contains a step counter or animation, because every state then looks new.
- **[inf]** Hash collisions were never the problem. The hard part is deciding which frames count as the same state, inferring the goal, and finding the shortest solving sequence.
- Your own memory note already says the agent needs to plan the shortest path over a transition graph, not explore indefinitely. The theorem formalizes the behavior that note rejected.

**ARC-AGI-2 (T2).** First, the drop may not be real:
- The index records the public recipe at **30.56** (submission 55981444) [file]. That sits inside your "degraded" range of 30.28–30.97.
- I can't find 31.81 anywhere in the arc-agi-2 docs [file], so it may be a single lucky run. On about 120 tasks, 1.5 points is 1–2 tasks, which is within rerun variance.
- Before explaining a degradation, rerun the baseline twice to measure that variance.

If the drop is real, the mechanism is slot displacement **[inf]**:
- Zero false positives on the demos means the filter never rejects a program that fits them. Programs that fit the demos but get the test wrong are exactly what a hand-written DSL produces on ARC-AGI-2.
- Each such program takes one of your two attempts away from a correct vote by the test-time-training model.
- `ARC_AGI2_IMPROVEMENT_PLAN.md` already recorded five DSL/pattern submissions at **0.00** and concluded "will stay 0.00" [file]. You added a component measured at zero to a model scoring 31%, and it took attempts away from the model.

## Q2. RSNA Knee: the theorem's target column isn't scored

- **The column doesn't exist.** `train.csv` and the submission both have exactly 12 labels: ACL, MCL, the two menisci, three OA columns, Effusion, Synovitis, Baker's, Contusion, Fracture [file]. `max(p_Abnormal, max_k p_k)` writes a probability nobody reads.
- **Log-loss optimality doesn't apply.** Macro AUC only cares about the order within each column [file: `fable_rsna.md:11`]. Your submission values are already rank fractions (k/9) [file]. "Rank averaging gives 1.000 nats" is a log-loss problem, and under AUC rank averaging is the correct move. That argument was answering a metric you aren't scored on.
- **The numbers in your prompt are stale.** The index says we are at **0.943**, rank 763/5332, and the leader is at **0.964**. The gap is 0.021, not 0.015.

The real problem, from the files:
1. **We don't have a model of our own.** The 0.943 is an inference-only fork of a public graph. Our ConvNeXt arm plateaued at OOF **0.867** after three attempts (0.841, then 0.867, flat from epoch 4) and failed the gate [file: `ARM_LEDGER.md`]. Whatever separates 0.943 from 0.964 is something we haven't built.
2. **The labels are the bottleneck.** Training labels are LLM-extracted from Spanish free-text radiology reports, quantized to 5 soft levels, with only 58 gold-labeled studies [file]. Label noise caps every model trained on them.
3. **The gap is concentrated in a few columns.**
   - A 0.021 gain in macro AUC equals about 0.25 of AUC summed across the 12 columns. That is roughly **+0.06 on each of the four weak labels** (Lateral OA, MCL, PF OA, Fracture, which sit at 0.83–0.85 out-of-fold) [file plus arithmetic].
   - What 0.96 teams likely do differently **[inf, a hypothesis]**: cleaner report-label extraction, models that look at the right views and slices for each finding, and ensembles of several diverse models. The only file evidence is the S75 member CV range of 0.896–0.915.

## Q3. CASMI26: you can't rerank a molecule that isn't in your candidate list

The 0.420 notebook combines these stages [file: `enveda/fork_v4n`]:
- a pool of about 710,000 candidate structures, plus a PubChem tier searched by precursor mass;
- a fingerprint network and a LightGBM ranker;
- ICEBERG/GLACIER predicted spectra, used to separate candidates with the same formula;
- a **PubChem popularity prior**, `log1p(SIDs) + log1p(PubMed ids)`;
- reciprocal-rank fusion of two engines.

What Theorem 4 ignored:
1. **The prior.** P(structure | spectrum) ∝ P(spectrum | structure) · P(structure). The theorem models only the first term. When MS2 can't tell isomers apart, which is common, the prior decides, and in that notebook's own table the popularity prior was the first step to beat the 0.399 reference (0.404).
2. **84% of test molecules have nothing to compare against.** By the LB-probed split, 45% are in PubChem/COCONUT and 39% are novel, with no reference spectrum [file]. A spectrum-to-spectrum similarity can only score the 16% that are library hits. Isomers get separated by predicted spectra, which your theorem has no part in.
3. **Your "diagnostic fragments" are mostly noise.** Test spectra have a median of 230 peaks against 42 in train [file]. A low-abundance tail on timsTOF is mostly noise and interference, so giving it a non-zero gradient amplifies noise.
4. **The candidate list caps the score, not the scorer.** Your own recon recorded that expanding the PubChem isomer pool dropped the score from 0.52 to 0.35 [file]. A better similarity function cannot raise MRR when the right answer isn't in the list.
5. **"Strictly monotonic with JSD" is true by construction.** Entropy similarity is essentially 1 − JSD, so the property proves nothing.

I could not find the code for our own 0.288 reranker; the only entropy code in `casmi26/` is in forks and the fingerprint trainer [file]. So point 4 is inference: if it scored a smaller or different candidate pool than the 0.420 pipeline, recall explains most of the loss.

`★ Insight ─────────────────────────────────────`
- Every theorem was "sound" because it fixed its own objective. The first line of any competition proof should be the scoring function, copied from the metric code.
- Kaggle gaps live in the data and the candidate lists (labels, recall, priors), not in the scoring function at the end.
- A component measured at 0.00 (the ARC DSL) or with no consumer (the `Abnormal` column) is dead. Proving it optimal doesn't bring it back.
`─────────────────────────────────────────────────`

## One cheap check per competition

- **RSNA:** probe single labels on the leaderboard: submit real predictions for one weak column and constants for the rest, then recover that column's AUC as `(12·LB − 11·0.5)`. That shows where the 0.021 actually is. One slot per label; nothing launched.
- **CASMI:** add entropy similarity as one more LightGBM feature on the 0.420 base and compare MRR with and without it on the same data. If it adds nothing, drop the theorem.
- **ARC-2:** rerun the plain baseline twice. If the spread covers 30.3–31.8, there was never a degradation to explain.
- **ARC-3:** count the actions of every win under `(h/a)²`. Any part of the agent whose purpose is exploring more should be removed.

Nothing was submitted, trained, or delegated for this. It used only reads of local files, in keeping with quota-conservative mode.

---

## 2. Discrete Synthesis & RL Theorist Audit (Claude Sonnet)
`★ Insight ─────────────────────────────────────`
Both "theorems" are true as stated, but they bound the wrong quantity. Theorem 2 is sound on demos but says nothing about test-time generalization. Theorem 3 guarantees coverage when the goal needs identification.
`─────────────────────────────────────────────────`

This is pure analysis. I haven't run anything against the repo or the LB logs, so every causal claim below is a hypothesis with a stated way to falsify it. Numbers marked "toy" rest on assumed parameters.

## Part 1: ARC-AGI-2, why a "sound" filter can hurt

### 1.0 The filter is vacuous on exactly the programs that matter

Let I be any invariant (χ, D4 class, component count). If p is consistent with the demos, p(x_i)=y_i, then I(p(x_i))=I(y_i) holds automatically. So "0 false positives on demos" and ">10⁴ contraction" are both true, and neither can change which demo-consistent programs survive. The filter only prunes programs that were already going to fail the demos. That makes it a speedup claim. The accuracy-relevant quantity is the generalization of the survivors to the test input, which the theorem never touches. This is the "claim aimed at the wrong half of the input space" failure from `verification-depth.md` §1.

### 1.1 Counterexample A: directional physics (equivariance is not free)

If the filter augments demos with D4 images (gx, gy), or demands I-invariance under g, it assumes f∘g = g∘f for all g∈D4. The true symmetry group is H(f) = {g : f∘g = g∘f}.

- **Gravity.** Take f↓ on 3×3 with a single cell at (0,1), so f↓(x) puts it at (2,1). Let R be the 90° CW rotation, (r,c)→(c,2−r).
  - The augmented demo is (Rx, R f↓(x)): cell (1,2) → cell (1,0). That is "fall left".
  - The true f↓(Rx) puts the cell at (2,2).
  - So f↓ fails its own augmented demos. In general R f↓ R⁻¹ = f←, so H(f↓) = {id, horizontal flip}, which is Z₂ and not D4.
  - Result: the true program is rejected, and the solver falls back to a wrong program or to nothing.
- **Chirality.** For a "rotate clockwise" task with T=R, the flip F gives F R F⁻¹ = R⁻¹ ≠ R. All four det=−1 elements of D4 break equivariance.
- **Euler constant-Δ overfit.** Take the task "close the gap in the C-shape", where each C has χ=1 and each ring has χ=0.
  - Every demo has one object, so the filter learns "Δχ = −1".
  - The true law is Δχ = −(#objects). A test input with 2 gaps has Δχ=−2, so the filter rejects the correct output.
  - Invariants that scale with object count look constant when all demos have one object.

H(f) is not identifiable from demos alone. Equivariance is a prior, and treating it as a hard constraint makes P(reject f*) = 1 on every task where H(f)≠D4.

### 1.2 Counterexample B: N_train = 2–3

Let there be m candidate invariants, and let a spurious one hold on a random demo pair with probability q.

- **Posterior that an invariant is real.** P(real | N demos) = π / (π + (1−π) q^N). With prior π=0.1 and q=0.3:
  - N=2 gives 0.55, so 45% of "invariants" are coincidences.
  - N=3 gives 0.80.
  - N=5 gives 0.97.
- **Toy model.** With m=40 and q=0.3, the expected number of spurious invariants is λ = m q^N: 3.6 at N=2, 1.1 at N=3, 0.1 at N=5.
  - Each one kills f* on the test with probability about 1−q.
  - P(f* survives) ≈ exp(−λ(1−q)), which is 0.08 at N=2, 0.47 at N=3 and 0.93 at N=5.
  - Real invariants are correlated, so the magnitudes are illustrative. The monotone blow-up as N shrinks is the robust part.
- **Hypothesis space.** An Occam bound needs N·b ≥ log₂|P| + log₂(1/δ), where b is the effective bits per demo. For ARC, b is small because many programs agree on near-identity grids, so N=2–3 leaves a demo-consistent set that still disagrees on the test.

### 1.3 Why that becomes a leaderboard regression: the swap arithmetic

Suppose DSL answers displace incumbent answers. Then

Δscore ∝ |W_inc ∩ R_dsl| − |R_inc ∩ W_dsl|

where W and R are the sets of tasks answered wrong and right. The DSL fires on structurally easy tasks, which are exactly where the neural or TTT incumbent is already right. The gain set (incumbent wrong, DSL right) is therefore small, and the loss set (incumbent right, DSL overfit and wrong) is not.

Also, 31.81 → 30.28 is about 1.5 pts. If the LB is about 120 tasks, that is roughly 2 task-equivalents. The 30.28–30.97 spread shows run-to-run variance of about 0.7 pts, and the binomial SE at p≈0.3 and n=120 is about 4 pts. **The regression may be indistinguishable from noise**, so settle that before explaining it.

### 1.4 Correct formulation

1. **Symmetry as model selection.** Treat H ≤ D4 (10 subgroups) as a latent variable with a prior and Bayes factors, not an assumption. Use symmetry only to canonicalize or augment the search, and never to reject a final candidate. If augmentation is used, verify augmented consistency per candidate p via H(p), and fall back to the unaugmented demos when it fails.
2. **Invariants as soft likelihoods.** Weight each invariant by the posterior above, w_j = P(real | N), and never use a hard cut.
3. **Arbitrate, don't replace.** Let the DSL take an attempt slot only when it fits all demos and either disagrees with the incumbent or the incumbent's confidence is below τ. Pass@2 makes this cheap.
4. **Tests that would falsify me.** Run these on existing logs:
   - Per-task confusion matrix of DSL-fired vs incumbent-correct.
   - H(f*) distribution over known training solutions.
   - Leave-one-demo-out: infer invariants from N−1 demos and measure how often they hold on the held-out demo. That is the spurious rate directly.

## Part 2: ARC-AGI-3, why cycle evasion isn't a solver

### 2.1 What Theorem 3 proves, and what it doesn't

- **The collision bound.** Zobrist gives pairwise collision 2⁻⁶⁴. Over n states, P(any collision) ≈ n²/2⁶⁵. For this to be below 10⁻¹⁵ you need n ≲ 190. At n=10⁶ it is about 3×10⁻⁸. This is minor, because collisions are not the bottleneck.
- **The "probability 1" claim has hidden preconditions.**
  - It needs a strongly connected state graph. Counterexample: s0→s1 (sink) and s0→s2 (frontier). The policy enters s1 with probability ≥ 1/|A|, and from there P(escape) = 0.
  - It fails on irreversible transitions. A reset restores connectivity, but only at the cost of actions.
  - It fails in the other direction too. If the hashed frame includes timers, animation, score bars or distractors, every frame is "novel" and cycles are never detected. The hash needs a bisimulation-quotiented abstraction, not the raw pixels.
- **It is a coverage guarantee, not a goal guarantee.** Novelty-seeking is optimal for max E[#distinct states], and that objective is independent of R. The hitting probability of the goal set G is about |G|/|S| per new state, so E[T] ≈ |S|/|G|. For 64×64×16-colour frames, |S| is astronomical, and even for a factored object abstraction it grows exponentially in the number of independent objects.

### 2.2 Concrete counterexample: Lights Out

A game on k=25 toggles has a state graph that is the Cayley graph of Z₂²⁵, with 3.4×10⁷ states and one goal.

- Perfect cycle-free frontier exploration finds the goal in about 2²⁴ expected new states.
- The dynamics are linear over GF(2). Probe each action once (k actions), read off the action matrix, and solve by Gaussian elimination. That is about k+1 effective actions.
- The gap between 2k and 2²⁴ is the difference between model identification and state-space coverage. It is also directly relevant to an action-efficiency score, where wasted actions are the cost.

### 2.3 The right formulation

Treat the problem as Bayesian program induction over a deterministic game, with exploration costed against exploitation.

1. **Hypothesis space.** θ = (T_θ, G_θ) is a transition program plus a goal predicate, with prior 2^{−|θ|}. The posterior is b_t(θ) ∝ 2^{−|θ|} Π 1[T_θ(s_i,a_i)=s_{i+1}].
2. **Objective.** Minimize E[T] = E[T_identify] + E[T_execute]. The information-theoretic floor is T_identify ≥ H(θ)/max_a I(θ; s′ | a). Novelty-seeking reaches this only incidentally.
3. **Exploration policy.** Choose a_t = argmax_a I(θ; s′ | b_t, s_t, a), which for deterministic hypotheses is the entropy of the predicted next-state distribution. Switch to exploit when the expected plan-cost reduction from one more probe is below 1 action. A practical approximation is Thompson/posterior sampling: sample θ ~ b_t, plan in that world, act, then update.
4. **Mistake bound.** In the realizable deterministic case, a halving-style learner makes at most log₂|Θ| wrong predictions, so the cost is the description length of the game in bits and not |S|.
5. **Abstraction (affordance value iteration).**
   - Segment frames into objects (connected components with colour, shape and position) and learn per-object affordances Aff(o,a) = effect type.
   - Run optimistic value iteration (R-max/UCB-VI) on the abstract MDP: V_{n+1}(s) = max_a [ r̂ + γ Σ T̂ V_n ], with unknown (s,a) pairs set to V_max.
   - That directs exploration to unknown pairs that could matter, and PAC sample complexity scales with |S_abs||A|, not the pixel space.
6. **Goal-directed search.** Run A*/greedy best-first with h_g(s) as the object-space distance under goal hypothesis g, weighted by its posterior.
   - Before the first score event there is no reward, so the goal prior must come from perceptual cues.
   - After the first completion G is largely identified. If levels within a game share mechanics, which I believe they do but haven't re-verified, that cost amortizes.
7. **Subgoal decomposition (options).** Find bottleneck states B (doors, keys, gates) via cut or betweenness structure and plan over the option graph.
   - For m sequential subgoals with local branching b, cost falls from about b^m to about m·b.
   - Detect subgoal events from frame-diff discontinuities.

### Ablations that would settle this on our data

- Fraction of hash-distinct states that are animation-only.
- Goal-hitting time vs coverage time of the current agent.
- Number of actions to identify the mechanics with and without information-gain probing.

I can implement the leave-one-demo-out spurious-invariant measurement and the DSL-vs-incumbent confusion matrix as a first falsification pass if you want them run.

---

## 3. Executive Synthesis & Root Cause Summary
- **The Core Flaw**: Proving asymptotic properties of post-processing filters (monotonicity, cycle avoidance, entropy metrics) does not create predictive signal. It only conditions or prunes existing signal.
- If the underlying representation or retrieval library is weak or hallucinating, mathematically optimal post-processing will only optimally project noise.
