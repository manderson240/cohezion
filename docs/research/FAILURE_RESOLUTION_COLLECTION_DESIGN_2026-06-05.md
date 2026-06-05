---
title: Failure-Resolution Data Collection — Experimental Design
date: 2026-06-05
status: DESIGN (pre-registered analysis; collection foundation built, production wiring pending)
author: Claude Code (V-model audit loop)
depends_on: docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md
---

# Collecting `(failure_class, resolving_strategy, outcome)` to make the recursive-trace gate decidable

## 0. Why this exists + what changed (honesty note)

The recursive-trace value gate returned **UNPROVEN** because no `(failure_class, fixing_strategy)`
corpus exists. Confirmed 2026-06-05 by searching **both** layers:
- **Filesystem:** grep for `solving_strategy|fixing_strategy|resolved_by` → only the new `core.py`.
- **SurrealDB db=main (53 tables):** best case **N=1** usable triple (one `mycelium_patterns` row:
  `bwrap-missing-bind → safe-env.sh → recoverable`). `agent_journey`=3 rows, `compound_learnings`=2,
  `traces`=0. No `mutation`/`quality`/`heal`/`fail` table. SkillMutationQueue & AutoDQA support
  `persist=True` but have **never accumulated rows** (persist defaults off).

**Artifact-under-test changed (stated explicitly).** The original gate tested a specific hand-map
(`latency→semantic_remap`, …). Those four "healer strategies" are **string labels with no
implementation anywhere** — so that exact map is untestable. This design **swaps the artifact**: from
"is *my* hand-map right?" to the more general, real question **"in cohezion's real remediation loops,
is the resolving strategy statistically dependent on the failure class?"** A KEEP here means
*recursive-trace's premise holds in cohezion*; it does not resurrect the specific phantom map.

## 1. The value question, made non-circular

Recursive-trace's only claim over flat autoresearch: **conditioning candidate selection on the
typed failure-class beats ignoring it.** Formalized over real resolved pairs `(fc, rs)`:

- **Marginal ordering (fair baseline = autoresearch + dedup + global success rates):** try strategies
  in order of overall success frequency `P(rs)`.
- **Failure-conditional ordering (recursive-trace):** try strategies in order of `P(rs | fc)`.
- **Value = expected-attempts-to-first-success is lower under conditional than marginal.** Equivalent
  to: `rs` is statistically **dependent** on `fc`. If independent (`P(rs|fc)=P(rs)`), recursive-trace
  is *exactly* autoresearch-with-a-dedup-cache → **RETIRE**.

**This is non-circular** because `P(fc, rs)` is estimated from **real outcomes the code did not
generate** — not from any map we wrote. Independence is fully expressible in the data; the gate CAN
return RETIRE.

### 1.1 Significance: label-permutation null ($0, honest)

Dependence must be *real*, not small-sample noise. Pre-registered test:
1. Compute the real attempt-reduction `Δ = E_attempts[marginal] − E_attempts[conditional]` from the
   empirical joint.
2. Shuffle the `rs` labels across all pairs (destroys any fc→rs link), recompute `Δ_shuf`. Repeat
   2000×.
3. **KEEP** (for that domain) iff `Δ > 0` **and** `Δ` exceeds the **95th percentile** of the shuffled
   `Δ_shuf` (p<0.05) **and** the domain has ≥ `N_min` pairs with ≥ `K_min` distinct failure-classes.
   **RETIRE** iff `Δ` is within the shuffled null. **UNPROVEN** iff below the volume floor.

Pre-registered floors: `N_min = 60` pairs/domain, `K_min = 3` distinct failure-classes,
≥ 2 distinct strategies observed. (Tunable only *before* data — recorded here.)

## 2. Domains (all three — analyzed SEPARATELY, never pooled)

Pooling domains would recreate the causal-attribution trap (routing's weak causal link contaminating
quality-gate's). Each domain is tagged and scored independently; the gate emits a per-domain verdict.

| Domain | failure_class | strategy (action) | outcome (success) | hook point | causal match | volume |
|---|---|---|---|---|---|---|
| **quality_gate** | `output_type` / `verdict.reason` | tier that produced the accepted output (npu/igpu/cpu/cloud) | gate `accept` | `compound/autodqa.py:evaluate` + `inference/quality_eval.py` | strong (stronger tier fixes quality) | HIGH (every task) |
| **skill_mutation** | typed skill-failure reason | `mutation_type`/patch kind | `approved` vs `refund/rejected` | `compound/skill_mutation_queue.py:approve/refund` | strong, discrete | LOW (rare) |
| **routing** | degraded metric (`duration` only — see caveat) | chosen tier | metric returned to baseline | `compound/degradation_detector.py:check_degradation`+`suggest_routing_tier` | weak except `duration` | MED |

**Routing caveat (pre-registered):** `cache_hit_rate`/`coherence`/`token_efficiency` are computed
*upstream* of tier dispatch — rerouting cannot recover them. Only `duration` is causally rerouteable.
So routing pairs are collected **only for `duration`**; a routing RETIRE is reported as "tier is not
the lever for metric X," NOT as a recursive-trace refutation. This prevents an uninformative RETIRE
masquerading as a real one.

## 3. Ground-truth without circularity (the collection protocol)

The hard tension: non-circular ground truth needs **real events**; injected failures = experimenter
sets the oracle = circularity reborn. Resolution per the chosen "all event sources":

- **live** (primary): real/representative tasks flow through the fleet; failures emerge organically;
  the strategy that *actually* produced the accepted/approved/recovered outcome is recorded. Tagged
  `source=live`.
- **passive** (zero-intervention subset of live): organic production failures during normal use.
- **replay** (bootstrap volume): historical metric/quality traces re-scored offline, tagged
  `source=replay` so the gate can weight or exclude them. Replay NEVER sets the oracle — it only
  re-derives outcomes from recorded real signals.

**Counterfactual note:** live logging sees only the strategy actually chosen, not what *other*
strategies would have done. For the conditional-vs-marginal metric this is acceptable: we measure
`P(rs|fc)` over *successful resolutions*, which is exactly the quantity the mechanism would exploit.
Where the escalation chain tries multiple tiers before success (quality_gate does), we get the full
*tried-order + which one resolved* — richer than single-shot.

## 4. Collection VIABILITY is unconfirmed — and is a user/environment fact, not a code fact

**The load-bearing open question is not validity but viability: will real pairs ever be generated?**
A pair needs a real failure followed by a real resolution — which requires a *workload* that exercises
the hook (AutoDQA reject→escalate, a skill mutation, a `duration` degradation). This is the mirror of
the circularity risk: there, an experiment that could not fail; here, an experiment that may not *run*.

Two things follow, both pre-registered:

1. **Do NOT synthesize a "representative task batch" to manufacture volume.** If we invent the batch,
   we choose which failures occur — experimenter control over the failure distribution, the same bias
   class the permutation null exists to avoid. The only clean volume source is **organic traffic**.
2. **Viability cannot be settled from the codebase.** Whether a failure-generating workload exists is a
   fact about the deployment (e.g. this box currently runs a Claude Code audit loop, **not** cohezion's
   `CompoundExecutor`/AutoDQA — so quality_gate volume may be *zero*, not "high"). It is therefore an
   explicit **user question**, asked before any production wiring: *is there a real workload that drives
   tasks through AutoDQA / mutations / degradations — or do we instrument one specific known-failing flow
   as the deliberate (still-organic, not experimenter-chosen) event source?*

Honest status: **apparatus built + analysis validated; collection viability UNCONFIRMED.** We do not
claim "ready to collect" until a real event source is identified.

## 5. Schema (unified, domain-tagged) + sink

One JSON line per resolution, appended to `~/.cohezion-research/logs/resolution_log.jsonl` (a path the
gate already scans):

```json
{"ts": "...", "domain": "quality_gate", "failure_class": "code",
 "strategy": "cpu", "success": true, "source": "live",
 "tried_order": ["igpu","cpu"], "task_hash": "..."}
```

`record_resolution(...)` (in `cohezion.recursive_trace.resolution_log`) is the single writer all three
hook points call. The gate's `_extract_pair` is extended to read `domain` + `success` and to count
only `success=true` pairs.

## 6. Build status (this design's foundation)

- **Built + tested now:** `resolution_log.record_resolution/read_resolutions`; the upgraded
  `recursive_trace_gate.py` (per-domain conditional-vs-marginal lift + permutation null); discriminating
  tests for both. The analysis is validated on **clearly-labeled synthetic pairs** (to prove the metric
  separates dependent from independent data — NOT to fake a verdict).
- **Pending (gated on the §4 viability question, NOT on more building):** the three one-line
  `record_resolution` calls in AutoDQA / SkillMutationQueue / DegradationDetector. Wiring is deferred
  until a real organic event source is confirmed — otherwise the loggers would sit on a flow nothing
  exercises and the gate would return UNPROVEN forever.

## 7. Pre-registered decision rule (summary)

Per domain D with ≥ N_min live(+replay) pairs:
- **KEEP(D)** iff conditional ordering beats marginal (`Δ>0`) at permutation-p < α_corrected.
- **RETIRE(D)** iff `Δ` within the permutation null (failure-class ⊥ resolving-strategy in D).
- **UNPROVEN(D)** iff below volume floor.
- **Multiple-comparison correction (pre-registered):** because the overall rule is KEEP-if-any, the
  per-domain threshold is **Bonferroni-corrected**: `α_corrected = 0.05 / (#testable domains)`. Without
  this, testing 3 domains inflates family-wise error to ~14%. (Equivalently: pre-commit to the single
  highest-volume domain and test only it at α=0.05.)
- Overall recursive-trace verdict = KEEP iff **any** causally-valid domain returns KEEP at α_corrected;
  RETIRE iff all causally-valid domains with sufficient volume return RETIRE; else UNPROVEN.
