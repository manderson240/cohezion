# Kaggle Master Battle Plan — 2026-09-28 (Opus 5.5 consult)

Grounded in `scripts/kaggle/sentinel_status.json` (live ledger), `src/cohezion-sentinel/src/main.rs`,
`~/cohezion-labs/casmi26/RECON.md`, and memory notes `kaggle-endgame-audit-20260927`,
`validate-the-proxy-against-the-scored-outcome`, `biohub-motion-relink-destroys-ilp-edges`,
`decompose-composite-metric-gains-into-factors`. **[USER]** = action the user must take (CLI
submit / web-UI selection is blocked for agent sessions).

## Corrections to the brief (these change the decisions)

| Brief says | Ledger / memory says |
|---|---|
| A Kaggriculture upload "queue-resets #56622866" | Live pair = 56622866 (GM41, 00:03:49) + 56622857 (SOTA2945, 00:03:44). A new upload evicts the **older** one, SOTA2945, not GM41. |
| Dutch auction / Day-25 patch is an untested option | Already ladder-tested 3x: v5 1315.3, v6 1343.8, v7 1232.9 — our three worst recent files. |
| Biohub is competing for top 3 | Money line was 0.967 on 09-22; at 0.946 we were rank ~1025/3806. |
| ARC-AGI-3 baseline is 0.07 | Best is v15 **0.26** (56175303). Since then: 0.24 → 0.15 → 0.08 → 0.07. The byte-exact v15 restore (v20) scored 0.21 → **LB noise ≈ ±0.05** at this level. |
| RSNA calibration submissions are progress | ROC-AUC is invariant to any per-label monotone transform. Per-label calibration (v14 monotonicity) cannot move the metric. v19 "Dirichlet" can only move it if it mixes labels (off-diagonal W); check whether it does. The 4 identical 0.940 scores are the same kernel version submitted 4× and prove nothing. |

## Priority order

0. **Sentinel: already disarmed, verify it stays that way.** All three submit paths in `main.rs`
   are guarded by flags that exist: `biohub_v21_submitted.flag`, `rsna_v19_submitted.flag`,
   `arc3_v1_submitted.flag` (in `scripts/kaggle/`). The source has no Kaggriculture submit path.
   Risk: a recompiled binary with a new flag name re-arms it (it double-submitted Biohub and
   quad-submitted RSNA on 09-27). **Do not delete these flags. Do not add auto-submit for any
   competition before its deadline.** An agent-shell `pgrep` cannot confirm the process state;
   [USER] check with `ps aux | grep sentinel` from a real terminal.
   **Other submitters:** a grep for submit call sites across `scripts/`, `src/` and `~/cohezion-labs`
   finds **no file that targets `kaggriculture`**. The 00:03 UTC 09-28 uploads (56622857, 56622866)
   were the manual restore recommended in `docs/research/claude_fable_consultation_20260927.md`.
   `scripts/kaggle/gemma4_kernel/submit_at_midnight_utc.py` targets Gemma4, not this portfolio.
   [USER] still run `crontab -l` and `systemctl --user list-timers`, since scheduled jobs aren't visible from
   an agent shell. Until that's done, the freeze is a policy, not an enforced guarantee.
1. Kaggriculture — freeze (no work).
2. Biohub — explicit final selection [USER], then stop.
3. RSNA — build real 5-fold OOF (24 days).
4. CASMI26 — local re-ranker (77 days; highest long-horizon leverage).
5. ARC-AGI-2 local verifier suite + paper track.

---

## 1. Kaggriculture — 100% upload freeze until close. No exceptions for strategy patches.

**The math.** Between GM41 (56449933, 2138.5) and the 09-28 restores we uploaded 8 files. **0 of 8**
out-rated it on the ladder, including v3, which claimed "100% local win rate vs SOTA2945" and landed at 1862.4. By the
rule of three, the 95% upper bound on "a new file beats our best" is ≈ 3/8 = 0.375, and the point
estimate is 0. The local panel's correlation with ladder rating was never validated (the n=3 reading
was retracted as incommensurable). So no local result producible in 40 h can raise that probability
above the cost: an upload swaps a 2119.5-proven agent (SOTA2945) for an unproven one restarting at
600. EV of any upload < 0.

**Why the freeze doesn't lose match volume.** The final Bradley-Terry run uses **all episodes between
active agents across the whole competition** (host, thread #732931), and games run ~2 weeks past
09-30. Both live agents are climbing (1583.9 / 1446.4 from 600 in ~24 h) and have ~16 days left to
converge toward their historical 2138/2119.

**Only upload trigger (escalate to user, don't act):** an active agent shows ERROR/timeout episodes
in `kaggle competitions submissions -c kaggriculture` / its episode list. That's a defect signal. A
strategy idea is not.

**Honest outlook:** a lifetime peak of 2224.6 vs a top-10 line of ~2920 is a ~700-point gap. At 2220.9
we were rank ~1327/9862. Expected finish ≈ rank 1,200–1,500, no prize. Move all build lanes off this
competition. Caveat: GM41 = 56449933 was matched by timestamp (file 02:04, upload 02:06 UTC 09-22),
not byte-proven.

## 2. Biohub — lock and verify (ends 09-29 23:59 UTC)

Metric (read from the scorer): `adj_J = max(0, J·(1 − 0.1·(N_pred − N_est)/N_est))` + 0.1·division_jaccard,
clipped below at 0 and **not capped above**.

**Final verification checklist**
1. **[USER] Select finals explicitly in the web UI.** Don't rely on auto-select.
   - Slot 1: **56433510** (V7, 0.946) *or* 56452965 (V8, 0.946). They're the same lineage, so pick one.
   - Slot 2: **56263700** (V6 run79 fork, 0.944). It's a different lineage, which hedges against a
     public/private reshuffle. Two near-identical 0.946 files buy almost no private-LB diversity.
2. Confirm both selected refs are `COMPLETE` with a numeric score (the sentinel's CSV parse wrote
   `"SubmissionStatus.COMPLETE"` into `public_score` for some rows, so read the CLI directly).
3. Confirm no new Biohub submissions appear after the flags were written (last is 56621668, 23:25 UTC 09-27).
4. Stop. At a +0.021 gap to the money line with <28 h left, there's no lever. The +0.062
   association lever needs GPU validation and several submissions.

**The "zero-risk" post-processing ideas, assessed:**
- *Drop zero-degree nodes (tracks of length 1):* this removes no edges, so **J doesn't change**.
  The whole gain comes from lowering N_pred, which means it's the node-only, metric-shaped component. Our own decomposition
  rule (`decompose-composite-metric-gains-into-factors`) says not to ship on a node-only gain.
  Magnitude ≈ 0.1 × (fraction of isolated nodes) × J, about +0.003 if 3% of nodes are isolated. That's worth a
  few ranks, not money. If you still want it: compute `edge_only` / `node_only` on the 8 GT stems
  (`data/gt_official/`). Expect edge_only == 0 exactly, and never select it as a final.
- *Length ≥3 filter:* **harmful.** It deletes true single-edge tracks (real TP edges).
- *Mitotic daughter divergence threshold:* **closed by measurement.** There are 7 GT divisions across 8 videos,
  and the best case recovers ≈1 division ≈ +0.002. The instrument can't rank it.

## 3. RSNA Knee — real 5-fold OOF (ends 10-22; 0.943 → 0.957 needs +0.014)

**The math first.** Mean-of-12 AUC depends only on the within-label ranking of the final score.
Only changes to **cross-model combination** (which members, their weights, rank vs logit averaging)
or to **member quality** can move it. Stop spending submissions on calibration. Per-label weights fit
without OOF have underperformed twice already (v11 0.938, v15 0.941 vs the 0.943 fork).

**Step-by-step (budget ≈ 30 GPU-h/week × 3.4 weeks ≈ 100 GPU-h, minus ARC reserve):**
1. **Inventory (0 GPU-h).** In `~/cohezion-labs/rsna-knee/fork-speedy-raptors-0922/`, list every blend
   member of the 0.943 fork: which have public training code, which are weights-only. Only retrainable
   members can have OOF. Weights-only members are trained on all data, so their OOF would leak.
2. **Freeze one split (0 GPU-h).** Group by patient (not study, not image), multilabel-stratify on the 12
   labels, 5 folds. Publish `folds.csv` as a private Kaggle dataset so every kernel uses identical folds.
3. **Time one fold before budgeting (≈2–4 GPU-h).** Train fold 0 of the strongest retrainable member at the
   fork's own resolution and config. Read wall time from the kernel log's `time` field, not the launch clock.
   Budget = folds × members × measured fold time. Stop and re-scope if it exceeds ~70 GPU-h.
4. **Train members fold by fold.** One kernel per (member, fold-pair). Save `oof_{m}_f{k}.npy` (patient-indexed)
   plus `test_{m}_f{k}.npy`. Assert the weight-loading precondition (`missing == unexpected == 0`) before any
   long run. This is the Biohub warm-start lesson.
5. **Blend on OOF with nested CV.** The outer loop holds out 1 fold. The inner loop fits weights on the other 4 folds' OOF.
   - Parameterise per-label weights as softmax(θ) on the simplex.
   - Maximise mean AUC with Nelder-Mead (few params: 3–5 members), or with a pairwise logistic surrogate
     `Σ_{i∈pos, j∈neg} log σ(s_i − s_j)` on subsampled pairs, then report exact AUC.
   - Compare rank-average vs logit-average combination.
   - **Adopt a weighting only if the nested-CV gain exceeds 2× the fold-to-fold std.** Nothing "guarantees"
     a monotone AUC gain. Nested CV is how you avoid fitting noise, which is what v11/v15 did.
6. **Join with the public 0.943 blend.** It has no OOF, so treat it as one member with a single scalar
   weight α ∈ {0.3, 0.5, 0.7}, chosen by 2–3 LB submissions. That's the only LB probing the plan needs.

**Backbone selection method (not recalled winners).**
- Candidate families: 2.5D slice CNNs (CoAtNet/ConvNeXt/EfficientNetV2), a 3D volumetric model,
  and frozen foundation features (DINOv2 / RadImageNet) + a MIL head. The fork already contains CoAtNet, Raptor, and DINOv2.
- Choose by measurement: per label, compute the OOF Spearman correlation between members. Among members
  whose OOF AUC is within 0.005 of the best, add the one with the lowest correlation.
- Check the top public notebooks' member lists before training anything new.

**Honest odds:** our own ensembles have never scored above 0.941. The 0.943 came from forking a public
notebook, so the cheapest first step is re-scanning the *current* top public RSNA notebooks for newer
members. ~20 LB submissions moved us +0.003. +0.014 needs a genuinely new, orthogonal, strong
member. Treat Gold as a stretch and Silver-protection as the base case.

## 4. Enveda CASMI26 — local CPU re-ranker (ends 12-14; 0.328 → top-10 0.383)

**Step 0: pool-recall oracle (do this before any re-ranker work).** On the GroupKFold hold-out, measure the
fraction of molecules whose true IK14 is **anywhere** in the candidate pool, split by simulated class 1/2/3.
MRR ≤ recall. If current MRR is already close to recall, re-ranking cannot reach 0.383, and the lever is
**targeted candidate generation** for the 39% novel class.

**Constraints from RECON.md that the pipeline must respect:**
- **No blind isomer expansion.** PubChem-isomer expansion hurt (0.52 → 0.35, dilution). Targeted additions
  did help: the ladder went 0.151 library-only → 0.245 with COCONUT/analog propagation → 0.336. Add candidates only when
  CV shows a recall gain that outweighs the dilution.
- Hidden test is 16% class 1 (library) / 45% class 2 (PubChem/COCONUT) / 39% class 3 (novel).
- CV = GroupKFold on inchikey14, with a timsTOF-weighted held-out set.
- The submission unit is `molecule_id` (≤25 SMILES). Fuse the ~3 spectra per molecule before ranking.
- RDKit 2026.03.6 segfaults when iterating ExplicitBitVect. Use `GetFingerprintAsNumPy` /
  `DataStructs.ConvertToNumpyArray` / `ToBitString` only.
- First confirm which pipeline produced 0.328. `fork_out/` holds the analog-baseline fork (09-17); verify
  before rebuilding.

**Zero-cost gain to check first:** collapse candidates to unique InChIKey14 **before** taking the top 25.
Stereoisomers that share an IK14 waste slots, and MRR only credits the first hit.

**Pipeline (16 Zen 5 cores; parallelise over molecules with `multiprocessing`, 400 test molecules is trivial;
CV is the cost):**
1. *Formula / precursor gate.* Derive tolerance from data:
   `tol = quantile(|precursor_mz_error_ppm|, 0.995)` over timsTOF rows with sane precursors (drop the
   corrupt `precursor_mz > 5000` rows). Use it as a **soft** penalty `−½(ppm/σ)²`. Hard-drop only when a
   candidate fails every plausible adduct (multimers are 11% of train).
2. *Channels per (spectrum, candidate):* binned cosine against the candidate's library spectra (class 1);
   fingerprint log-likelihood from a spectra→FP predictor (class 2/3); ppm penalty; source prior.
3. *Fusion across spectra of one molecule:* z-score each channel within the molecule's candidate list,
   average across spectra, combine with learned weights. Run RRF (k tuned on CV, start at 10, not 60:
   the lists are short) as a robust alternative. Pick by CV MRR, not by preference.
4. *Weight fitting:* coordinate ascent on mean MRR@25 over CV molecules. The weights are few and the metric is
   non-differentiable. Add `max_cos × channel` interactions so library-matched molecules trust the cosine.

```python
import numpy as np

PROTON = 1.007276
ADDUCT = {"[M+H]+": (1, PROTON), "[M+Na]+": (1, 22.989218), "[M-H]-": (1, -PROTON),
          "[2M+H]+": (2, PROTON), "[2M+Na]+": (2, 22.989218)}          # (k, delta), |z| = 1

def ppm_err(mz_obs, M, adduct):
    k, d = ADDUCT[adduct]
    exp = k * M + d
    return (mz_obs - exp) / exp * 1e6

def spec_vec(mz, inten, prec_mz, bin_w=0.01):
    keep = mz < prec_mz - 0.5                       # drop precursor region
    b = np.round(mz[keep] / bin_w).astype(np.int64)
    ub, inv = np.unique(b, return_inverse=True)
    v = np.bincount(inv, weights=np.sqrt(inten[keep]))
    return ub, v / (np.linalg.norm(v) or 1.0)

def cosine(a, b):                                   # a, b = spec_vec outputs (sorted unique bins)
    _, ia, ib = np.intersect1d(a[0], b[0], assume_unique=True, return_indices=True)
    return float(a[1][ia] @ b[1][ib])

POP = np.array([bin(i).count("1") for i in range(256)], np.uint8)
def tanimoto(q, C):                                 # q (B,), C (N,B) packed uint8 (np.packbits)
    inter = POP[C & q].sum(1, dtype=np.int32)
    union = POP[C | q].sum(1, dtype=np.int32)
    return inter / np.maximum(union, 1)

def fp_loglik(p, Cbits):                            # p (F,) predicted bit probs, Cbits (N,F) bool
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return Cbits @ np.log(p) + (~Cbits) @ np.log1p(-p)

def z(x):
    s = x.std()
    return (x - x.mean()) / (s if s > 1e-9 else 1.0)

def fuse_scores(per_spec_feats, w):                 # list[S] of (N,F) -> (N,)
    Z = np.stack([np.column_stack([z(f[:, j]) for j in range(f.shape[1])])
                  for f in per_spec_feats])
    return Z.mean(0) @ w

def rrf(per_spec_scores, k=10):
    return sum(1.0 / (k + 1 + np.argsort(np.argsort(-s))) for s in per_spec_scores)

def top25_unique_ik14(scores, ik14):                # ik14: (N,) object array
    seen, out = set(), []
    for i in np.argsort(-scores):
        if ik14[i] not in seen:
            seen.add(ik14[i]); out.append(i)
            if len(out) == 25: break
    return out

def mrr25(ranked_ik14, true_ik14):
    for r, k in enumerate(ranked_ik14, 1):
        if k == true_ik14: return 1.0 / r
    return 0.0
```

Caveats in the recipe: fixed 0.01-Da bins split peaks that sit on a bin edge. If CV shows it matters,
switch to tolerance matching (±10 ppm, greedy). The FP predictor (2.5M-spectrum corpus → Morgan bits) is
the differentiation play in RECON.md. Train it timsTOF-weighted and evaluate its bit-AUC on the
GroupKFold hold-out before wiring it into the ranker.

## 5. ARC Prize — AGI-2 local validation + paper track

**Zero-false-prune suite (no Kaggle submissions).**
- For every AutoHarness verifier / prune rule, run it on the **ground-truth outputs** of all public
  training and evaluation tasks.
- Invariant: accept rate on GT == 100%. A single rejection is a false prune: the rule would discard a
  correct answer. Report it with the task id.
- Also report prune power: the rejection rate on the model's wrong candidates.
- Then score pass@2 on the public eval set with the rule on vs off, same seeds.
- A rule ships only with 0 false prunes **and** a positive pass@2 delta.

**Explain the fork gap first.** Check first whether 33.89 is the source notebook's own score or just the
#10 LB line (memory records it as the #10 line). If it's the source's score, 31.81 (ours) sits below it. Reproduce the source
byte-exact and score it locally before crediting any delta to our additions.

**ARC-AGI-3:** submissions v15–v25 are inside ±0.05 LB noise. Stop auto-submitting. If you resubmit, use
v15 byte-exact.

**Paper track (1,500 words). [USER] fetch the actual rubric before writing:**
`kaggle competitions pages -c arc-prize-2026-paper-track --content --page-name Evaluation`. The
blueprint below isn't matched to verified judge criteria, and arXiv:2603.03329 is **unverified**
(not fetched here). No blueprint can guarantee ≥4.5/5.

1. *Problem & claim (~200 w):* candidate verification as a cheap filter for LLM program/answer search on ARC-AGI-2.
2. *Method (~400 w):* AutoHarness verifiers. Formal statement: if a rule R is D4-equivariant
   (R(g·x, g·y) = R(x, y) for all g ∈ D4) and D4-TTA voting is used, filtering commutes with the
   augmentation. Prove it in a few lines, and state which rules satisfy it.
3. *Evaluation (~450 w):* false-prune rate on all public GT outputs (target 0), prune power, pass@2
   ablation on the public eval set, cost per task. Give the base as "public 33.89 notebook" honestly. The
   solver is a fork, and the contribution is the verifier layer.
4. *Negative results (~250 w):* v10 Poincaré beam 0.00; ARC-AGI-3 sequence inside LB noise; what that
   says about LB-driven iteration.
5. *Limits & reproducibility (~200 w):* code link, seeds, compute.
