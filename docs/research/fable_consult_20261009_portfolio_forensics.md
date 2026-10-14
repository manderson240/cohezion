# Fable consult 2026-10-09 — portfolio forensics, four dialectics, grounded

**Author:** Claude Fable 5.1, read-only. Nothing submitted, pushed, or edited outside this file.
**Live sources pulled this session (Kaggle CLI, 2026-10-09 ~21:00 UTC):** submissions and leaderboards for RSNA,
Enveda, ARC-AGI-2, ARC-AGI-3, Gemma 4; our RSNA v30 kernel source (`manderson240/cohezion-rsna-knee-sota-ensemble`);
the Enveda 0.421 fork source; `dfranzen/arc-agi-3-milestone-2-solution`; `verracodeguacas/gemma-4-agent-budget-fit-single-agent`.
**Local sources:** `~/cohezion-labs/scheduled/slot_audit.md` (2026-10-08), `rsna-knee/ARM_LEDGER.md`, `casmi26/RECON.md`,
`ENVEDA_PLAN_20260930.md`, `gemma4-devagent/local_eval/{REPORT,AB_NOTES,NOTES}.md`, `scheduled/gemma_ladder.py`,
`KAGGLE_GEMMA4_COORDINATION.md`, the 2026-10-07 consult (`fable_consult_20261007_portfolio_breakthroughs.md`).
**Not verifiable here:** Kaggle discussion pages (JS-rendered; Topic 746792 could not be read), the Gemma 4 deadline
(CLI call denied), GPU quota remaining.

---

## 0. The brief's premises against what is measured today

| Track | Brief said | Measured 2026-10-09 | Consequence |
|---|---|---|---|
| RSNA | 0.940, "v30 currently grading"; target 0.964 | **v30 scored 0.939** (ref 57012270, 14:43 UTC). Best is still **0.943** = the verbatim public fork (ref 56477886). v19→v30: 12 patched variants, **0 above 0.943**. Top: three-way tie at **0.964**, 10th ≈ 0.962. 13 days left. | The gap to a prize is +0.019 to +0.021. Every post-hoc patch has been ≤ 0 on the board. |
| Enveda | 0.415 "v19 SOTA", ends **Oct 28**, target 0.484 | v19 = **0.415** (57007704) is *below* the 0.421 fork; v18 = 0.407. Deadline is **2026-12-14** (66 days). Leader 0.484, 2nd 0.481, then a gap to 0.459. 5th moved 0.443 → 0.457 in three days. | Ten weeks, not three. Every knob turned on the fork so far has lost. Board resolution ≈ ±0.02 (§2.1), so 0.415 vs 0.421 is noise; 0.484 vs 0.421 is not. |
| ARC-AGI-2 | 31.81, v15 grading; target 88.06 | v15 **pending** (56961835). The "LB 33.89" fork reruns scored **26.39** and **28.47** (same recipe, different seeds). Best 31.81 (56409554). | Seed band of the public recipe is 26–34; 31.81 is a lucky draw of it. Attempt-2 DSL injection measured −1.25 / −0.69. |
| ARC-AGI-3 | 0.25, "v10 queued" | Lineage is monotone **down**: 0.26 (v15) → 0.24 → 0.16 → 0.12 → **0.10** (v30 rerun, 56981979). Leader **59.17**, 5th 40.97, 11th 37.98. | Each "SOTA" variant scored lower than the one before. The open-source Milestone-2 solution (25.8 ± 3.9) runs an INT4 Qwen3.8-Flash-Next on an RTX Pro 6000 with SGLang; it is not a CPU agent. |
| Gemma 4 | "needs a 512-token thinking budget, colocated prompts, free tool calls" | Anchor **0.10** (thoughts off). `thinking_on` (4096 budget, 8192 out) → **0.08**. "Zero-Budget Thinking + Colocated" → **0.00** (config failure class), its successor pending. Leader 0.24 ×2, 3rd 0.22, 0.20 ×7. | No measurement supports a 512-token budget. A 0.00 is a crash, not a quality reading. The public-board noise is ±2 tasks ≈ ±0.034, so no single read distinguishes 0.08 from 0.10. |
| NFL BDB 2027 | kinematic metrics | Entered (136 teams), deadline 2027-01-06. No local working directory exists; the starter notebook (per the Oct 7 consult) loads no data and already asserts "+38.4%". | Nothing is built. It is a writeup competition judged by club analysts. |

**Slot burn since the Oct 7 consult:** 10 submissions across five boards, **0 improvements**. RSNA v28 was submitted
four times on Oct 7 with identical 0.940 scores, then v29 twice and v30 once (all 0.939). The orchestrator defects
D1/D2 named on Oct 7 (version-1 default, no idempotency) are still producing identical-score duplicates. That remains
the binding constraint of the portfolio, ahead of any algorithm.

---

## 1. RSNA Knee — podium is not reachable in 13 days; here is the arithmetic and the one measured probe left

### 1.1 Empirical Physicist — what the metric can and cannot see
Thirteen scored columns (`ACL, MCL, Medial Meniscus, Lateral Meniscus, Medial OA, Lateral OA, PF OA, Effusion,
Synovitis, Baker's, Contusion, Fracture, Abnormal`), mean of per-column ROC-AUC. The v30 post-processing chain
(kernel cell 26) is:

1. logit-space blend of CoAtNet vs transformer ranks, per-label weight ≈ 0.60;
2. "clinical covariance shrinkage" `logit += 0.035 · prior_boost`;
3. prevalence-margin clipping;
4. per-column percentile rank;
5. **Abnormal := clip(0.40·abn + 0.35·max_k p_k + 0.25·noisy_or(p))** ("Soft Kolmogorov").

**Invariant R1 (rank invariance).** For any strictly increasing `f`, `AUC(f∘s) = AUC(s)`. Steps 2–4 are
per-column monotone maps of a single score, therefore **exactly null** on the metric (step 2 only mixes columns
through the prior term at α = 0.035, which is inside the tie-break regime). Step 5 is the only operation in the
chain that can move the board, and it moves **one column of thirteen**, so its effect is bounded by
`|ΔAUC_Abnormal| / 13`. Measured: the Kolmogorov family (v22, v24, v29, v30) scores 0.939 against the base 0.943.
The sub-finding heads rank "abnormal" *worse* than the Abnormal head on the rows where they disagree. Delete step 5.

**Invariant R2 (resolution).** Hanley–McNeil at AUC ≈ 0.94 with a few hundred positives per column gives a
per-column SE ≈ 0.006–0.010; averaged over 13 weakly-correlated columns ≈ 0.003. The spread 0.939–0.943 across
v19–v30 is one SE. The gap to 0.962 is roughly seven SE. Patching cannot cross it; only a new reader can.

### 1.2 Formal Topologist — what the "0.949 single CoAtNet" intel actually implies
I could not read Topic 746792. What can be checked: our stack already attaches
`dreaddevelopment/raptor-knee-native384`, `raptor-knee-native384dense` and
`mattiaangeli/rsna-knee-coat-resgated-ep10-top3` — native-384 crops and a CoAtNet are *already in* the 0.943 graph.
"Anatomical mirroring TTA" is laterality normalisation: a left knee is a right knee under
`(sagittal: slice-order reversal, i.e. medial↔lateral) × (coronal/axial: width flip)`. The stack applies this
**at cache time** (`normalise_laterality`, cell 9), so every model sees a canonical side. Averaging predictions over
`{identity, mirror}` at test time is only valid if the model was **trained** with mirror augmentation; otherwise the
mirrored volume is a contralateral-knee out-of-distribution input. That is a training-side property of the public
weights we do not own. The intel describes a training recipe, not a post-processing lever, and 0.949 would sit
outside the top 100 on today's board.

### 1.3 Game-Theoretic Strategist — the only expected-value-positive move
The top of the board (thread 745861, Oct 7 consult §4): LLM-relabelled report targets (host-permitted; the
`pilkwang/rsna-knee-llm-labels` dataset is already attached to our kernel), own 2.5D/MIL readers, 5 folds,
rank-blended 15–30 % into the public stack. Our one attempt (ConvNeXt-T, soft labels, ARM_LEDGER) plateaued at
**OOF 0.867 against a 0.90 gate** over epochs 4–9 — a label/recipe ceiling, not under-training. A credible retry is
15–20 GPU-h per fold-set with no OOF for the public stack to blend against, and 13 days. Expected board delta:
≈ +0.002 (starkhushi precedent: blending a sub-0.90 arm produced 0.936).

**Decision:** freeze at 56477886. The single remaining *measured* probe is the one ARM_LEDGER already names:
blend fold-0 SWA weights at rank weight 0.2 into the 0.943 kernel, **one** slot, with the prediction written
*before* submission: `pred ≤ 0.945`. Above 0.943 → folds 1–4 are justified; otherwise the arm is dead and the GPU
quota goes to Enveda, where ten weeks remain.

### 1.4 Hardware & Systems Sentry
Stop the duplicate submissions first (Oct 7 §8.2 repairs 1–2). Four identical 0.940 refs on Oct 7 and three
identical 0.939 refs on Oct 8–9 each cost a 6–8 h L4 scoring rerun. The kernel's own fingerprint check
(`check_fingerprint`, tolerance 0.002) is good engineering; it is also why the chain cannot drift upward — every
member is pinned to someone else's trained weights.

---

## 2. Enveda CASMI26 — the step function is Class-2 recall, and the board is noisier than the brief assumes

### 2.1 Empirical Physicist — decompose the metric before touching features
MRR@25 over ~400 molecules, InChIKey14 match. The LB-probed class mix (RECON, thread 741659) is
**16 % Class 1 / 45 % Class 2 / 39 % Class 3**.

**Invariant E1 (class decomposition).** `MRR = Σ_c π_c · MRR_c`. If Class 1 is "solved" at MRR ≈ 0.90, it
contributes **0.144**. Our 0.421 therefore implies `MRR_{2∪3} = (0.421 − 0.144)/0.84 ≈ 0.33`. If Class 3 (not in
PubChem, de novo only) is near zero, then **`MRR_2 ≈ 0.277/0.45 ≈ 0.62`** today, and the leader's 0.484 needs
`MRR_2 ≈ 0.76`. Class 1 is 16 % of the prize; nothing done to it moves the board again.

**Invariant E2 (recall ceiling).** `MRR_2 ≤ recall@25(candidate set)` on Class-2 queries. A ranker cannot promote a
structure that is not in the pool. The Oct 7 measurement request (recall@25/@100 of formula-matched
PubChem/COCONUT candidates on InChIKey14-disjoint held-out train structures) has **not been run**; there is no
number in `ENVEDA_PLAN`. Run it before any ranker work. RECON also records that *unconstrained* pool expansion
hurt (0.52 → 0.35 on a fold), so the lever is tight formula gating, not a bigger pool.

**Invariant E3 (resolution).** Reciprocal rank has variance ≈ 0.15 at these operating points; at n = 400,
SE(MRR) ≈ √(0.15/400) ≈ **0.019**. v18/v19 (0.407/0.415) versus the fork (0.421) are inside one SE. The ranker
knobs the fork's author tuned on the public board are themselves fitted to that noise. Gate everything on the
structure-disjoint fold, never on the board.

**Invariant E4 (train/test shift).** Test spectra have a median of 230 peaks against a train median of 42; "82 %
of peaks below the 1 % floor" is this shift. Any intensity floor applied at inference must be the same transform
the fingerprint model saw in training. The FPNets in the 0.421 fork are other people's models with their own
preprocessing; re-filtering their input without retraining is a silent distribution shift. Spectral-entropy
similarity (Li et al. 2021) handles this intrinsically — entropy-weighted intensities down-weight low-intensity
peaks without a hard threshold.

### 2.2 Formal Topologist — the exact formulation
Two-stage retrieval with a class-conditional gate, trained so the model has *seen* Class-2 conditions:

```
q = (precursor m/z, adduct, CE, peaks)                     one query = one molecule (spectra merged by m/z binning)
lib_max(q)  = max modified-cosine over the training library (the v7 engine, now a feature)
g(q)        = P(class 1 | lib_max, n_peaks, precursor) — logistic fit on the fold with simulated classes

Candidate set C(q):
  M_neutral  = (m/z − m_adduct) · z        for adducts {[M+H]+, [M+NH4]+, [M+Na]+, [M−H2O+H]+, [M+K]+, [2M+H]+}
  F(q)       = formulas within ±5 ppm of M_neutral satisfying the seven golden rules (C,H,N,O,P,S; RDBE ≥ 0)
  C_lib(q)   = top-K library structures by modified cosine                      (Class-1 path)
  C_db(q)    = PubChem ∪ COCONUT ∪ LOTUS structures with formula ∈ F(q),         (Class-2 path)
               capped at N by log1p(PubChem SID count) popularity, N ≤ 200
  C(q)       = C_lib ∪ C_db,  deduped on InChIKey14 after RDKit tautomer canonicalisation

Score(q, c) = LambdaMART(φ(q, c)),  group = q, label = [InChIKey14(c) == truth]
  φ: Tanimoto(FP̂(q), ECFP4(c)) for FP̂ from a fingerprint MLP trained on the COMPETITION train set;
     spectral-entropy similarity to the ICEBERG/GLACIER forward-predicted spectrum of c;
     explained-intensity fraction under in-silico bond cleavage (below);
     count of matched diagnostic neutral losses; ppm error; formula-match flag; log1p(popularity);
     lib_max; g(q); |C(q)|; rank of c within its source list.
Final list  = RRF( our ranker, the 0.421 fork's lists ; k tuned on the fold ), top-25 after InChIKey14 dedupe.
```

**In-silico bond cleavage (the "substructure" signal that generalises to Class 2).** For candidate `c`, enumerate
fragments by breaking ≤ 2 acyclic single bonds and ≤ 1 ring bond pair (MetFrag depth 2); for each fragment formula
`f` and hydrogen shift `h ∈ {−2..+2}`, a peak is *explained* if `|m/z_peak − (mass(f) + h·m_H + m_adduct)| ≤ 5 ppm`.
Score = Σ_explained `I_peak^0.5 · w(depth)` / Σ `I_peak^0.5`. Intensity to the power ½ is the standard variance
stabiliser; it also demotes the noise floor without a hard cut (E4). Cache fragment trees per InChIKey14 — the same
candidate recurs across queries.

**Why the fold design matters more than the model.** GroupKFold on InChIKey14, and for every held-out molecule
*remove its spectra from the library* the Class-1 path searches. Without that removal the fold is all Class 1,
the ranker learns `lib_max` is everything, and the board (84 % Class 2/3) punishes it — which is the shape of every
v10–v19 result (0.288–0.335 for our own rerankers).

### 2.3 Game-Theoretic Strategist — where the prize line will be
The 5th place moved +0.014 in three days; by Dec 14 a prize position will likely need ≥ 0.50. The top two are
0.02+ clear of the pack, consistent with one qualitatively different component (my read: a fingerprint model
trained on the 2.5 M competition spectra plus a real Class-2 ranker, i.e. the formulation above). Being inside the
pack at 0.45 is worth little; the build has to target 0.50, which needs `MRR_2 ≈ 0.80`. That is a candidate-recall
problem first (E2) and a ranker problem second.

**Licence guardrail (prize-clean path).** NIST-derived data is disqualifying (thread 744470). Several datasets in
the fork chain (`ahmedberatozer/casmi26-*`) carry "Other, non-commercial" terms with unresolved eligibility
(thread 745072). PubChem is public domain; COCONUT/LOTUS are CC0/CC-BY — verify the exact tag on each Kaggle
dataset before attaching. Train the fingerprint model and the ranker on `train.parquet` and the public-domain
candidate sources only; keep the fork as a *fusion partner*, not a dependency, so that a 0.48+ entry can be
defended.

### 2.4 Hardware & Systems Sentry — what runs where, at $0
- Candidate recall measurement, formula enumeration, fragment-tree caching, fold construction: CPU, local,
  pyarrow row-group reads (RECON: full-column reads need ~550 s; row-group iteration stays RAM-light).
- Fingerprint MLP: binned spectrum (0.01 Da, 50–1000 m/z, log1p) ⊕ neutral-loss channel → 2048-bit ECFP4, BCE with
  bit-prevalence weights; T4×2, ~4 h. Report per-bit AUC and Tanimoto(pred, true) on the disjoint fold.
- RDKit: 2026.03.6 segfaults on `ExplicitBitVect` → numpy iteration (RECON); use `GetFingerprintAsNumPy` only.
- One submission per *fold-gated* candidate; the evidence line must carry both fold MRRs (ours and the fork's).

### 2.5 Recipe — the recall measurement that gates everything (CPU, run first)

```python
# casmi26/measure_recall.py — recall@K of formula-gated candidates on an InChIKey14-disjoint fold.
# Answers E2 before any ranker is built. Expect: if recall@100 < 0.6, the ranker is not the bottleneck.
import numpy as np, pandas as pd, pyarrow.parquet as pq
from rdkit import Chem
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

PPM = 5.0
ADDUCTS = {"[M+H]+": 1.007276, "[M+NH4]+": 18.033823, "[M+Na]+": 22.989218,
           "[M+K]+": 38.963158, "[M-H2O+H]+": -17.003288, "[M-H]-": -1.007276}

def neutral_mass(mz: float, adduct: str, z: int = 1) -> float | None:
    d = ADDUCTS.get(adduct)
    return None if d is None else (mz - d) * z

def formula_index(cands: pd.DataFrame) -> dict[str, set[str]]:
    """{formula: {inchikey14,...}} over the candidate DB (PubChem tier + COCONUT), built once and cached."""
    out: dict[str, set[str]] = {}
    for f, k in zip(cands["formula"], cands["inchikey14"]):
        out.setdefault(f, set()).add(k)
    return out

def exact_mass_of(formula: str) -> float:
    from rdkit.Chem import Descriptors
    return Descriptors.ExactMolWt(Chem.MolFromSmiles(formula)) if formula.startswith("C") and False else _mass(formula)

def _mass(formula: str) -> float:
    import re
    M = {"C": 12.0, "H": 1.0078250319, "N": 14.0030740052, "O": 15.9949146221, "P": 30.97376151, "S": 31.97207069,
         "F": 18.99840320, "Cl": 34.96885271, "Br": 78.9183376, "I": 126.904468}
    return sum(M[e] * (int(n) if n else 1) for e, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula))

def candidates_for(mz: float, adduct: str, fidx: dict[str, set[str]], fmass: dict[str, float]) -> set[str]:
    m = neutral_mass(mz, adduct)
    if m is None:
        return set()
    tol = m * PPM * 1e-6
    hits: set[str] = set()
    for f, fm in fmass.items():                    # fmass is {formula: exact_mass}; pre-sorted bisect in production
        if abs(fm - m) <= tol:
            hits |= fidx[f]
    return hits

def recall_at(fold_rows: pd.DataFrame, fidx, fmass, ks=(25, 100, 500)) -> dict[int, float]:
    got = {k: 0 for k in ks}
    for r in fold_rows.itertuples():
        hits = candidates_for(r.precursor_mz, r.adduct, fidx, fmass)
        n = len(hits)
        for k in ks:                                # recall@K is an upper bound: assumes a perfect ranker inside the pool
            got[k] += int(r.inchikey14 in hits and n <= k) + int(r.inchikey14 in hits and n > k) * (k / n)
    return {k: got[k] / len(fold_rows) for k in ks}
```

The `n > k` branch credits `k/n` — the expected recall of a *random* ranker inside an oversized pool — so the
number reported is honest about dilution, which is the failure RECON measured (0.52 → 0.35).

---

## 3. ARC-AGI-2 — a selection decision, not a synthesis problem

**Invariant A1 (verified-program injection).** A DSL program may replace a model vote only if it reproduces
**every** training pair of the task exactly. A train-verified program has high test precision (ARC-1-style DSLs:
70–90 %); an unverified one has the DSL's base rate, which we measured at **0/120** locally. The recipe's
`attempt_2` is the model's second augmentation-vote cluster, with non-zero precision. Replacing it with an
unverified guess is a strict loss: v13 −1.25, v14 −0.69. "Non-destructive" was true of `attempt_1` only.

**Invariant A2 (seed band).** The LB-33.89 recipe's own reruns scored 26.39 and 28.47 this week; our 31.81 is a
draw from the same 26–34 band. There is no +2 to extract; there is nothing to lose by stopping.

**Action.** When v15 (56961835) scores: select 56409554 (31.81) as one final, and the better of {v15, 56920228}
as the other. No further variants. The paper track ($75 K pool, due Nov 9) is where this board still pays: an
honest Theory/Progress section with the measured negatives (A1, A2) is exactly what the Accuracy-plus-Writeup
rubric rewards.

---

## 4. ARC-AGI-3 — the scoring rule, the timeout trap, and the one step-function available

### 4.1 Empirical Physicist — what is scored (local SDK `scorecard.py`, confirmed Oct 7)
```
level_score = min(100, 100·(baseline/actions)^p)   if the level is completed, p = 1 (local SDK) or 2 (RHAE, board)
env_score   = mean over ALL levels, uncompleted = 0
```
Only *completed* levels earn anything; an incomplete level is 0 regardless of exploration quality.

**Invariant G1 (credit is per level, so the budget must be per level).** Spending 150 actions on a 7-action level
earns 4.7 (linear) or 0.2 (squared) and zeroes the other six. That is the whole mechanism behind 0.26 → 0.10:
every v16–v30 change added *search* (Zobrist anti-cycle, BFS macro-actions, Go-Explore archives) and none added
*goal inference*, so each variant spent more actions per level and completed no more levels.

### 4.2 Hardware & Systems Sentry — the timeout trap, read from the open-source harness
Franzen's notebook (`## 0. Harness patch`, 9,914 lines) states two facts about the Kaggle runtime we had not
written down:

1. *"Kaggle might cancel the run if no action is done in some timeframe"* — the harness starts and issues a
   `RESET` **before** the model backend is ready. There is an **idle watchdog**. A CPU agent that pauses for a long
   BFS between actions is the TOPAS failure shape (36 % local → 11.67 % board): the board run was killed or timed
   out mid-game, so every unfinished level became 0.
2. *"Pin arc_agi's cached `level_reset_only` before its client is built (RESET keeps the level)."* — `RESET`
   restarts the **current level**, not the game. That makes deterministic Go-Explore *return* cheap: return =
   `RESET` + replay of the within-level prefix.

**Invariant G2 (liveness).** Emit an action at least every `T_idle` seconds (choose 20 s; measure the real limit
once locally against the gateway with a deliberate stall). Any planner must be *anytime*: `choose_action()` returns
the best known action when its slice expires. Invariant test: a planner given a 60 s stall budget still produces an
action within `T_idle`.

**Invariant G3 (wall clock).** With G games and total budget W, allocate `w_g = 0.9·W / G` initially and
re-allocate unused time from finished/abandoned games to games showing level progress. Easiest-first: play each
game to a probe budget of 60 actions; rank games by `levels_completed / actions`; invest in the top of that order.
This is a knapsack over games where the value of a game is its completed-level mass, and it is the only
"affordance search policy" that is consistent with the metric.

### 4.3 Formal Topologist — the CPU ceiling and the honest fork
Macro-action compilation, BFS over affordance graphs, cellular-automaton detection and distance shaping all
reduce actions *within a level the agent already understands*; none creates understanding. Reaching 35 requires
completing most levels at ≤ 1.7× human actions under the squared rule, i.e. goal inference from the first frames.
On CPU without a model the realistic ceiling is low single digits from click-games with cheap first levels.

The one step-function on this board is the open-source Milestone-2 solution (public notebook, 25.8 ± 3.9):
INT4 Qwen3.8-Flash-Next served by SGLang with a draft model on `NvidiaRtxPro6000`, bundled wheels and models as
datasets, `ProgressPace` (expected future level weights conditional on completing the current level — a learned
version of G3), `NoopRepeatGuard` (blocks (state, action) pairs that produced no change; 512 states × 16 actions per
level). Running it verbatim would move us from 0.10 to ~25 (rank ≈ 30–50, outside prize but a paper-track
foundation). Preconditions: G4 quota, the `kaggle-blackwell-handshake` skill, and a licence check on the bundled
sources (`dfranzen/taaf-kaggle-source-bundle-copy`) before any derivative work.

### 4.4 Recipe — per-level accounting + anytime liveness (pure Python, drop-in for the current agent)

```python
# arc3_budget.py — wraps any choose_action() with G1/G2/G3 invariants. CPU only.
import time
from collections import defaultdict

class LevelBudget:
    """Per-level action accounting with abandonment and an idle watchdog."""
    def __init__(self, baseline_actions: list[int] | None, k: float = 3.0, fixed: int = 60, t_idle: float = 20.0):
        self.base = baseline_actions or []
        self.k, self.fixed, self.t_idle = k, fixed, t_idle
        self.level, self.level_start, self.per_level = 0, 0, []
        self.last_emit = time.monotonic()

    def cap_for(self, level: int) -> int:
        return int(self.k * self.base[level]) if level < len(self.base) else self.fixed

    def on_step(self, step: int, levels_completed: int) -> bool:
        """Return True to ABANDON the game (current level over budget). Keeps len(per_level)==levels_completed."""
        if levels_completed > self.level:
            self.per_level.append(step + 1 - self.level_start)
            self.level_start, self.level = step + 1, levels_completed
        self.last_emit = time.monotonic()
        return (step + 1 - self.level_start) > self.cap_for(self.level)

    def must_emit(self) -> bool:                      # G2: never go silent
        return time.monotonic() - self.last_emit > 0.8 * self.t_idle

def rhae(per_level: list[int], base: list[int], p: float = 2.0) -> float:
    done = [min(100.0, 100.0 * (b / a) ** p) for a, b in zip(per_level, base)]
    return (sum(done) + 0.0 * (len(base) - len(done))) / max(1, len(base))

class GameScheduler:
    """G3: easiest-first knapsack over games under a wall-clock budget W."""
    def __init__(self, games: list[str], W: float, probe_actions: int = 60):
        self.W, self.t0, self.probe = W, time.monotonic(), probe_actions
        self.progress = defaultdict(lambda: (0, 1))  # game -> (levels, actions)
        self.order = list(games)

    def rank(self):
        self.order.sort(key=lambda g: -self.progress[g][0] / self.progress[g][1])

    def remaining(self) -> float:
        return 0.9 * self.W - (time.monotonic() - self.t0)
```

Usage contract: run every game to `probe_actions` first, call `rank()`, then spend `remaining()` on the ordered
list; the per-game `LevelBudget.on_step` abandons a game whose current level exceeds `k×baseline`. Discriminating
test: a game with baselines `[7, 18]` and an agent that cannot finish level 1 must be abandoned at action 21, and
`per_level == []`. Calibrate `k` on the 25 local games against v15 through the `arc3_local_rhae.py` harness from the
Oct 7 consult (still unbuilt — nothing named `rhae` exists under `arc-agi-3/`).

---

## 5. Gemma 4 Developer Agent — the only board with a reachable prize, and the brief's thinking premise is unmeasured

### 5.1 Empirical Physicist
- `thinking_on` (4096 budget, 8192 out) scored **0.08** against the 0.10 anchor; public-board noise is ±2 tasks of
  58 ≈ ±0.034 (stated by the budget-fit author from repeated identical submissions; consistent with our ladder's
  `ADOPT_MARGIN = 0.034`). The two reads are indistinguishable. "Thinking on helps" (thread 746250, local 17.8 → 37–40 %)
  and "thinking on scored 0.08" are not in conflict; one board read cannot see a 2× local effect through ±0.034.
- "Zero-Budget Thinking + Colocated Prompts" → **0.00**. On this board 0.00 is the crash class (`eval_config`
  miss → 60-min default; undeclared tools raising in ADK; schema rejects), per `KAGGLE_GEMMA4_COORDINATION`. It
  carries no information about thinking budgets. Its successor (56982619) is pending; expect another 0.00 unless the
  cause was found and written down.
- No measurement anywhere in our files supports a **512**-token thinking budget. The local harness cannot even
  enforce `thinking_budget` on llama.cpp (NOTES divergence 2), so it was never tested locally either.

**Invariant M1 (two reads per rung).** With SE ≈ 0.034 per read and one slot per day, adoption at `≥ best + 0.034`
on a single read has a ~16 % false-adopt rate and a much larger false-reject rate on a true +0.03 effect. Any rung
whose first read is within ±0.034 of the anchor gets a **second identical submission** before the ladder moves on.

### 5.2 Formal Topologist — the measured public configuration
The budget-fit kernel's settings are chosen from 129 local runs at scorer speed, and the author reports a scored
run that finished under 12 h:

| Setting | Our anchor (v5 lineage) | Budget-fit | Author's measured reason |
|---|---|---|---|
| `max_time_minutes` | 3–5 | **8** | ~half of eventual fixes are not in the file at 4 min |
| `max_tool_calls` | 25→60 | **28** | runs still exploring after many calls almost never succeed |
| `timeout_seconds` | 120 | **240** | the scorer's pytest uses the same value; `requests` suites need ~100 s, so a *correct* patch can be scored as a failure at 120 s |
| `max_output_tokens` | 3072–16384 | **8192** | vLLM refuses prompt + output > 32,768 |
| `thinking_budget` | 1024–4096 | **4096**, thoughts on | — |
| prompt rule | edit by call 6 | **edit by call 12** | no edit by call 12 → 87 % fail |
| graph tools | declared | declared, **prompt-discouraged** | exact-id only, usually empty; undeclared-but-advertised raises in ADK |

The `timeout_seconds = 240` row is the one our ladder has never varied and is a plausible *mechanism* for a
scored-as-failed correct patch — it is a scorer-side effect, which is why it does not show up in local pass-rates.

### 5.3 Game-Theoretic Strategist
Prize zone today: 0.24 / 0.24 / 0.22; seven teams at 0.20. The anchor is 0.10. No single-knob rung closes +0.12;
the measured public configuration is the candidate that could. Submit the budget-fit configuration **verbatim**
as the next rung (one slot), with the prediction `0.12–0.18` written first; if the first read is ≥ 0.134 adopt it
as the new anchor and resume single-knob rungs from there (M1 applies). Keep the ladder's `prune_graph_tools`
removed (declared tools must stay declared; the prompt does the discouraging).

### 5.4 Hardware & Systems Sentry
The local harness measures (a) non-empty applicable patch within budget, (b) finish-reason distribution,
(c) relative deltas — not absolute pass-rate (REPORT "Calibration verdict"). Its last A/B was aborted on router
contention (AB_NOTES). Use it only for (a) and (b) on the budget-fit config before submission: the one thing it can
catch is a config that produces zero edits, which is the 0.00 class.

---

## 6. NFL Big Data Bowl 2027 — build the instrument before the claim

Nothing exists locally. The Oct 7 consult §7 metric design stands; the brief's three quantities, with the invariants
that make them defensible to club analysts:

- **0.5 s burst acceleration.** Tracking is 10 Hz. Use the provided speed field `s`, not differenced `x, y`:
  `a_0.5 = (s(t0+0.5) − s(t0)) / 0.5` from the snap frame, plus the 1.0 s integral. Invariant: computed from `s`,
  with a Savitzky–Golay smoother (window 5, order 2) applied first and the window sensitivity reported.
- **Jerk.** A third derivative at 10 Hz amplifies white noise by ω³; raw jerk is noise. Define jerk only on the
  SG-smoothed acceleration and report it as a *rate-of-change of burst*, bounded to the first 1.5 s. If the
  held-out AUC does not improve over burst alone, drop it — a kinematic quantity that is not predictive is a
  liability in the Football Score column.
- **Dynamic Voronoi containment.** Static Voronoi of the pocket polygon (QB ± tackles' outside shoulders, LOS to QB
  depth) is a share in [0, 1]. "Dynamic" = velocity-shifted influence (Fernandez & Bornn pitch control): each
  player's seed is `x + v·τ` with τ = 0.5 s and an influence radius that grows with speed. Clip to the pocket
  polygon; report the rusher's share at 0.5 s and 1.0 s and its slope.
- **Model.** Mixed-effects logistic `quick_pressure ~ burst + Δθ/dt + share + TCA_slope + (1|rusher) + (1|blocker)
  + (1|game)`; the rusher random effect is the rating, with credible intervals, shrunk by sample size. Null model =
  position only. Train 2023–2024, validate on held-out weeks; Brier and calibration plot beside AUC.

The headline "+38.4 %" in the starter notebook must be deleted until a number comes out of the held-out season.

---

## 7. Cross-portfolio invariants (the four dialectics applied to the loop itself)

1. **Empirical:** every board has a measured noise floor — RSNA ≈ 0.003, Enveda ≈ 0.02, Gemma ≈ 0.034,
   ARC-2 seed band 26–34. A variant whose predicted delta is below the floor does not get a slot.
2. **Topological:** per-column monotone post-processing is null under AUC (R1); a ranker is bounded by candidate
   recall (E2); only completed levels score (G1); an unverified program never overrides a vote (A1). These are
   theorems about the metrics, not opinions about models — they rule out most of the v19–v30 / v13–v15 / v16–v30
   lineages *before* submission.
3. **Game-theoretic:** the prize lines move. Enveda's 5th rose +0.014 in three days; Gemma's 3rd is 0.22. Target
   the line at the deadline, not today's.
4. **Systems:** the duplicate-submission defect is still live (RSNA ×4 on Oct 7, ×3 on Oct 8–9). Until
   `kaggle_submit.py` resolves the latest kernel version and the orchestrator keeps a (kernel, version) ledger with
   a process lock, every other recommendation here is competing for slots with a bug.

## 8. Execution order (next 72 h)

| # | Track | Action | Pre-written prediction / gate | Cost |
|---|---|---|---|---|
| 1 | Daemons | Land D1 + D2 (latest-version resolution, idempotent ledger + `flock`); stop any running orchestrator | no identical-score duplicate refs tomorrow | 0 |
| 2 | Gemma | Submit the budget-fit configuration verbatim as the next rung | pred 0.12–0.18; adopt at ≥ 0.134; second read if within ±0.034 | 1 slot |
| 3 | Enveda | Run §2.5 recall measurement on a disjoint fold (CPU) | numbers in `ENVEDA_PLAN`; decide ranker vs. candidates | 0 |
| 4 | Enveda | Start the competition-train fingerprint MLP (T4×2, ~4 h) only if recall@100 ≥ 0.6 | per-bit AUC + Tanimoto on the fold | ~4 GPU-h |
| 5 | RSNA | Delete the Abnormal mixing (R1); optionally the arm blend at 0.2, one slot, pred ≤ 0.945 | > 0.943 → folds 1–4; else freeze | ≤ 1 slot |
| 6 | ARC-3 | Build `arc3_local_rhae.py`; wrap v15 with §4.4; measure k ∈ {2, 3, 4} on 25 games × 3 seeds | `mean_rhae` ≥ v15's before any slot | 0 |
| 7 | ARC-2 | Read v15; select finals (31.81 + best other) | none | 0 |
| 8 | NFL | Create `~/cohezion-labs/nfl-bdb-2027/`, load one week, compute burst + share, delete the "+38.4 %" | notebook runs end-to-end on Kaggle CPU | 0 |
