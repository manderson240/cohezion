# PRE-REGISTRATION — routebench-grounded

**Committed BEFORE any result exists. Git timestamp is the evidence.**
Design: Claude Fable 5 (consulted 2026-07-25). Execution: local inference only, $0, one AMD Strix Halo box.

---

## Research question

When a routing eval's ground truth is **measured by execution** instead of **asserted by
specification**, and its prompts are drawn from a **diverse generator** instead of **templates**, how
much of the router's claimed capability survives — and can the observed 95%→52% collapse be
additively decomposed into those two instrument defects?

**Secondary:** does *any* learnable routing signal exist above a ~20-regex baseline once the eval
instrument is honest — or should the learned router be deleted?

## Why this question

Four failures observed in 48h are ONE phenomenon: **the error of the measurement instrument exceeded
the effect size being measured.**

| # | Failure | Instrument defect | Detectable by clean stats? |
|---|---|---|---|
| 1 | single-seed ablation 42% → 5-seed 25% (chance) | seed variance | YES (hygiene) |
| 2 | 70-pair threshold optimum refuted at 501 pairs | sample size | YES (hygiene) |
| 3 | router 92.9%/95.4% CI[93.2,97.3] → 51.6% CI[49.1,54.1] | **generator diversity** | **NO** |
| 4 | asserted labels agree with execution ~37-46% | **label provenance** | **NO** |

Failures 3 and 4 are the interesting ones: the CI in #3 was *correct* and the eval was still wrong by
43 points, because the generator and the label source are both **upstream of the split**. No amount
of statistical rigour downstream can detect them.

**Novel contribution:** the *decomposition* — how many points of the collapse come from label
provenance vs generator diversity, and whether they interact. Requires both an execution-grounded
labeller and matched template/diverse prompt sets over the same task.

## Design

### Ground-truth protocol ("measured" label)
Execute each prompt on NPU (`llama3.2-1b-FLM`), iGPU (`Gemma-4-E4B-it-GGUF`), CPU
(`Gemma-4-E2B-it-GGUF`), one heavy job at a time (N3 discipline). Reference = strongest local tier.
Label = **cheapest tier whose answer matches the reference** (nomic-embed cosine ≥ 0.58, the CA1
threshold validated on 501 pairs 2026-07-24). No match ⇒ `cloud`.

**Scope of the claim, stated up front:** labels measure *"cheapest tier sufficient relative to the
best this system can do locally"* — NOT objective correctness. That is precisely the quantity the
router must predict in deployment, so the benchmark has deployment validity even where the reference
model is objectively wrong. We do not claim universality.

### The 2×2 instrument grid (primary result)
The **frozen** predictive-coding router evaluated in all four cells:

| | Asserted labels (spec) | Measured labels (execution) |
|---|---|---|
| **Template prompts** | A — anchor, expect ≈95% | C |
| **Diverse prompts** | B — anchor, expect ≈52% | D — **reality** |

- diversity effect = A − B · provenance effect = A − C · interaction = A − B − C + D
- **A and B are replication anchors.** If they do not reproduce prior numbers within CI, STOP.

### Arms (evaluated in Cell D conditions)
1. **Keyword baseline (~20 regexes) — the null model, run FIRST.** Everything must beat it.
2. Frozen predictive-coding router.
3. Trajectory-retrieval baseline: k=25 NN over stored journey embeddings → majority tier.
4. (Morning, if labels land) Unsloth LoRA on a ~1B model trained on measured labels, 5 seeds.

### Reporting
All numbers = 5-seed means with 95% bootstrap CIs. Echo-contaminated prompts (generator repeating
spec text) are **detected, counted and reported** — never silently dropped.

## Pre-registered criteria

- **Gate 0 (runs FIRST, may end the experiment).** Re-measure 100 prompts twice. If test–retest label
  agreement **< 80%**, the ground truth is too noisy to support any downstream claim, and the
  registered conclusion becomes: *"the measurement protocol, not the router, is the bottleneck."*
  That is a legitimate publishable outcome, not a failure to be worked around.
  No arm-vs-arm gap smaller than the measured label-noise floor may be claimed.
- **H1 (instrument dominates model).** CONFIRMED if (A − D) ≥ 20 points AND both main effects ≥ 5
  points with non-overlapping CIs. **FALSIFIED if (A − D) < 10 points** — the collapse was mostly
  something else and this decomposition story is wrong.
- **H2 (learnability).** CONFIRMED if the best learned arm beats the keyword baseline in Cell D by
  **≥ 5 points with non-overlapping 95% CIs**. **FALSIFIED if the CIs overlap ⇒ pre-registered
  decision: DELETE the learned router from Cohezion**, keep regexes plus continuous measured-label
  monitoring, and say so plainly in the writeup.
- **Discriminating check on the benchmark itself.** Shuffle training labels and retrain one seed. If
  the shuffled-label model scores materially above keyword/chance level, the pipeline **leaks**
  (memorisation / near-duplicate prompts across the split) and **all learnability results are void**.

## Honest risks

1. **Circularity:** ground truth is agreement with the strongest local tier, which is not an oracle.
   Guarded by the explicit scope statement above, Gate 0 (stochastic noise floor), and the rule that
   no effect below the noise floor is claimed.
2. **The "diverse" pool is one generator's idea of diversity** — a fifth instance of the same disease,
   one level up. Guard: report embedding dispersion and category coverage for BOTH pools, so the
   diversity axis is a *measured property*, not a label. The shipped artifact is the **labeller**;
   the prompt pool is explicitly replaceable.
3. **Not claimed:** generalisation beyond routing, beyond this tier fleet, or transfer of any trained
   arm. One task, fully instrumented, decided honestly.

## Both endings are publishable
- H2 confirmed → "replaced the router with a 1B classifier trained on measured labels, beating the baseline by N points."
- H2 falsified → "showed our learned router was statistically indistinguishable from 20 regexes, and deleted it."

**The design decides which is true, not the author.**
