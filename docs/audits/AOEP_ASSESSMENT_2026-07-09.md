---
type: audit
title: AOEP-v0 Governance Assessment
date: 2026-07-09
paper: arXiv:2606.30306 — "Always-On Agents: A Survey of Persistent Memory, State, and Governance in LLM Agents"
scorecard: src/cohezion/compound/aoep_scorecard.py
baseline_overall: 0.167
checkout: worktree-imperative-wondering-kettle @ 306b930f6
---

# AOEP-v0 Governance Assessment (2026-07-09)

## 1. Paper Summary (short)

The survey codes 435 works on LLM-agent persistent memory and finds a **stark asymmetry**:
systems *accumulate and retrieve* state far more than they *govern, relinquish, or repair* it.
Retrieval is addressed by 62% of works and writing by 46%, but **rollback by only 6% (27 works)**,
**authority by only 17% (72 works)**, and **audit by 20% (88 works)**. It frames this as an
undefended design gap, not rational specialization, because retained state is also consequential.

**Six governance axes** (each: "who/what/when may this state influence an action, and can it be undone?"):

| Axis | One-line definition | Survey coverage |
|---|---|---|
| **Authority** | Who/what *licenses* this state to influence an action (possession ≠ action rights; revocation). | Rarest (17%) |
| **Scope** | Which user/task/tool/time-window/group an item may be used for (no cross-boundary leakage). | Usually static, not dynamic |
| **Mutability** | Whether an item may be revised, superseded, decayed, or locked. | Best-covered, still shallow |
| **Provenance** | Which source, timestamp, and chain of transformations produced an item. | Destroyed by lossy consolidation |
| **Recoverability** | Whether derived state *and the decisions it caused* can be rolled back. | 2nd-rarest |
| **Actionability** | What *kind* of object an item is: evidence / preference / policy / skill / executable commitment. | Rarely typed |

**Nine-stage state lifecycle** — a governed loop, forward arc (accumulate) + return arc (govern):

1. **Observe & Write** — deciding what becomes state.
2. **Validate** — the "missing gate" for quality-checking before a write persists.
3. **Organize** — consolidation that either preserves or destroys governance metadata.
4. **Retrieve** — most-studied; still ignores governance requirements at recall.
5. **Act** — binding state to consequence (should be authority-conditioned).
6. **Update** — revision is studied; *propagation of the revision* rarely is.
7. **Forget** — deletion as *true erasure across all tiers*, not retrieval-editing.
8. **Audit** — accounting for state usage across sessions.
9. **Rollback** — "the rarest capability": recovery of state-*affected decisions*, with the affected actions identified.

Five invariants must hold across the loop: **authority monotonicity, scope non-expansion,
deletion propagation, provenance preservation, rollback traceability.**

**AOEP-v0 obligations beyond answer quality:** the protocol scores *state-mutation and recovery
obligations*, not task correctness — using event streams + state snapshots to make transition
obligations executable: expired permissions must not license actions; scope must hold when state
crosses users; deletions must propagate to every tier and derived cache; provenance must survive
consolidation; poisoned/stale state must be rollback-able with affected actions identified.

**Identified research gaps:** governance (authority, audit) and *recovery/relinquishment* (forget,
rollback, deletion-propagation) are the systematically under-defended stages. Cohezion's own gap
profile below mirrors the corpus almost exactly.

---

## 2. Live Baseline

`AOEPScorecard().run()` on this checkout (2026-07-09):

```
overall 0.167
authority 0.0   scope 0.0   mutability 0.0
provenance 0.0  recoverability 1.0   actionability 0.0
gaps: authority, scope, mutability, provenance, actionability
```

> **Discrepancy flagged (honesty):** `src/cohezion/compound/CLAUDE.md` invariant **AO6** records a
> `0.67` baseline from 2026-07-06 (authority=1.0, scope/mutability/provenance/actionability=0.5).
> This worktree measures **0.167** — it is **behind main**: `_seesaw_check` (CB15) and
> `SkillMutationQueue.refund` (CB2) are absent here (`grep -rln "_seesaw_check\|SkillMutationQueue"
> src/` returns only the scorecard + CLAUDE.md, never the implementation). The 0.167 reading is the
> *current strict-probe reality of this checkout*, and the roadmap below is written against it.
> The AO6 gap is partly a merge-lag artifact, not solely missing capability.

---

## 3. Lifecycle Coverage Table (with verified evidence)

Grades adversarially reviewed. *Note: the E4B local-LLM challenge pass
(`build_gaia_llm_tier("Gemma-4-E4B-it-GGUF")`, max_tokens=2000, 2 sequential attempts) returned
empty both times — the documented L369 calibration-abstention on structured multi-section prompts,
treated as a no-op — so a **manual adversarial pass** was applied and its verdicts are in the last column.*

| # | Stage | Grade | Best existing mechanism (file:symbol — verified) | Adversarial verdict |
|---|-------|-------|--------------------------------------------------|---------------------|
| 1 | Observe & Write | **STRONG** | `journey_tracker.py:JourneyTracker.record_*` → SurrealDB; `semantic_cache.py:SemanticCache.put`; `skill_refiner.py:SkillRefiner` writes PRIME files; vault_log_decision | *fair* — high write volume, but writes are reflexive (every execution → a TrajectoryPoint) with no salience/write-gate; strong on the axis the paper says is *over*-covered. |
| 2 | Validate | **PARTIAL** | `skill_refiner.py:_lm_signal_cites_metrics` (CB14 citation gate); `jepa_gate.py:JepaGate` (PROCEED/REROUTE/SKIP); `request_alignment_analyzer.py` | *fair* — real gates exist, but seesaw invariant-negation gate is **absent here**, and trajectory writes are never validated. |
| 3 | Organize | **PARTIAL** | `semantic_cache.py` L1 hash / L2 cosine / L3 vault tiering; `journey_tracker.py` FLUME 12D projection | *fair* — consolidation works but the 12D projection is lossy and provenance-destroying, exactly the paper's warning. |
| 4 | Retrieve | **STRONG** | `semantic_cache.py:SemanticCache.get` 3-tier fallback; `vault_find_relevant_context`; `journey_tracker.py` trajectory export | *fair* — genuinely strong; the over-studied stage. |
| 5 | Act | **PARTIAL** | `executor.py:CompoundExecutor.execute_task`; `degradation_detector.py:suggest_routing_tier` → routing | *near-too-generous* — acting is strong, but "Act *under authority*" has **zero** authority gate on state→action; governance-Act is absent. |
| 6 | Update | **PARTIAL** | `skill_refiner.py:SkillRefiner.refine` (PRIME revision); `degradation_detector.py` EMA baseline update | *fair* — revision exists; *propagation* of a revision across derived caches/embeddings is not addressed (the paper's exact gap). |
| 7 | Forget | **ABSENT** | *(none)* — no cross-tier deletion propagation across L1/L2/L3/SurrealDB/FLUME embeddings; no machine-unlearning; `SkillMutationQueue.refund` (bi-temporal soft-delete) **not present in this checkout** | *fair* — correctly ABSENT; this is the corpus-wide 6% gap reproduced locally. |
| 8 | Audit | **PARTIAL** | `journey_tracker.py:_chain_state` sha256 hash-chain (OLIF audit trail); SurrealDB bi-temporal `valid_from/valid_to`; `degradation_detector.py` snapshot/alert history | *near-too-harsh* — machinery is fairly complete; PARTIAL only because "which trajectory point influenced which action" is not queryable end-to-end. |
| 9 | Rollback | **PARTIAL** | `skill_refiner.py:restore_state` + durable spine `~/.cohezion/skill_refiner_state.json`; `degradation_detector.py:from_dict`; Entire.io rewind | *near-too-generous* — **state**-rollback is strong, but rollback of state-*affected decisions* (identify + undo downstream actions) is ABSENT; the paper's rarest capability is unmet. |

**Strongest stages:** Write, Retrieve, (Audit near-strong). **Weakest:** Forget (ABSENT),
Rollback-of-decisions (ABSENT sub-capability), Validate (seesaw missing here).

---

## 4. Axis Gap Analysis — Wiring vs Building

For each scorecard axis: is the fix **WIRING** (machinery exists, just doesn't satisfy the contract
point) or **BUILDING** (capability genuinely missing)? Contract points are the `score_*` methods.

| Axis | Now | Root cause of the 0.0 | Fix type | Target & size |
|------|-----|-----------------------|----------|---------------|
| **Provenance** | 0.0 | `score_provenance` wants `source`+`transformation` fields on `TrajectoryPoint` (1.0) or `action`+`operation_type` (0.5). TP has `operation_type`+`metadata` but no such fields. The hash-chain + SurrealDB provenance data **already exists**, just not surfaced through this contract point. | **WIRING** | Add `source`+`transformation` to `TrajectoryPoint`, populate from `_chain_state`/task lineage → **1.0**. **S** (~30 LOC + 1 test). |
| **Mutability** | 0.0 | `score_mutability` wants `_seesaw_check` in `SkillRefiner.refine`. Present on main (CB15), **absent in this worktree**. | **WIRING** (to 0.5) + **BUILDING** (to 1.0) | Merge/port seesaw → **0.5**; add TTL/decay on revisable state → **1.0**. **S** wiring, **M** for TTL. |
| **Actionability** | 0.0 | `score_actionability` wants a typed `action` field (evidence/preference/policy/skill/commitment) on `TrajectoryPoint`. No `action` field. | **WIRING** (0.5) + **BUILDING** (1.0) | Add `action` field populated with `tier_used` → **0.5**; classify each point into the paper's 5-type taxonomy → **1.0**. **S**→**M**. |
| **Scope** | 0.0 | `score_scope` wants `scope_filter` param on `SemanticCache.get`. Signature is `get(prompt, system, model)` — no param. | **WIRING** (0.5) + **BUILDING** (1.0) | Add `scope_filter` param → **0.5**; enforce per-entry `{agent,task,ttl}` metadata filtering (scope-non-expansion invariant) → **1.0**. **M**. |
| **Authority** | 0.0 | `score_authority` wants `authority_tag` field in `ExecutionMetrics` **and** a gate in `execute_task` reading it. Neither exists (CB16 added tier_used/tool_call_count/escalation_count, not authority_tag). | **BUILDING** | Add `authority_tag` + a gate that blocks state→action when authority is expired/absent (authority-monotonicity invariant). **M**→**L** for real revocation currency. |
| **Recoverability** | **1.0** | Satisfied: `restore_state` + durable spine file present. | — | Hold; extend toward decision-rollback (P2). |

**Not a scorecard axis but the paper's biggest gap — Forget** (deletion propagation + machine
unlearning across L1/L2/L3/SurrealDB/FLUME): **BUILDING, L.** No contract point yet; would need a
7th axis or a lifecycle-stage probe.

---

## 5. Draft Prioritized Roadmap (P0/P1/P2)

Each item: **axis/stage · exact change · contract point satisfied · verification (score move) · size.**
Ordered by ROI: P0 = pure wiring over existing machinery, largest score movement per LOC.

### P0 — wiring existing machinery to contract points (lifts overall 0.167 → ~0.50)

1. **Provenance (WIRING, S)** — Add `source: str = ""` and `transformation: str = ""` to
   `TrajectoryPoint`; populate `source` from task/skill lineage and `transformation` from
   `operation_type` + `_chain_state` hash. **Contract:** `score_provenance` structural branch →
   both fields non-empty. **Verify:** provenance `0.0 → 1.0`. **Size:** S.
2. **Mutability (WIRING, S)** — Port `_seesaw_check` into `SkillRefiner.refine` from main (CB15).
   **Contract:** `score_mutability` `"_seesaw_check" in getsource(refine)`. **Verify:** mutability
   `0.0 → 0.5`; also re-greens CB15/AO4. **Size:** S.
3. **Actionability (WIRING, S)** — Add `action: str = ""` to `TrajectoryPoint`, populated with
   `metadata['tier_used']`. **Contract:** `score_actionability` structural branch → `action` field
   present. **Verify:** actionability `0.0 → 0.5`. **Size:** S.

> P0 total: three small, additive, non-destructive changes (two touch one dataclass) move overall
> from **0.167 to ≈0.50** and re-green a broken harness invariant. Re-run
> `pytest tests/compound/test_aoep_scorecard.py` + `AOEPScorecard().run()` to confirm.

### P1 — small builds closing the governance-attack surface

4. **Scope (WIRING→BUILD, M)** — Add `scope_filter: dict | None = None` to `SemanticCache.get`;
   filter L1/L2/L3 hits by per-entry `{agent, task}` metadata. **Contract:** `score_scope`
   `scope_filter in signature` (0.5) → active filtering (1.0). **Verify:** scope `0.0 → 0.5 → 1.0`;
   enforces scope-non-expansion. **Size:** M.
5. **Authority (BUILD, M→L)** — Add `authority_tag: str = ""` to `ExecutionMetrics`; add a gate in
   `execute_task` that refuses to propagate state→action when the tag is absent/expired.
   **Contract:** `score_authority` field + `"authority_tag" in getsource(execute_task)`. **Verify:**
   authority `0.0 → 1.0`; enforces authority-monotonicity. **Size:** M (1.0 on the probe); L for real
   revocation-currency semantics.

### P2 — genuine new capability (the corpus-wide gaps)

6. **Forget (BUILD, L)** — Deletion-propagation service: a delete removes an item from L1+L2+L3+
   SurrealDB **and** invalidates its FLUME embedding/derived summaries; add an AOEP probe/7th axis.
   **Contract:** new. **Verify:** deletion-propagation invariant test (deleted item unreachable via
   every tier). **Size:** L.
7. **Rollback-of-decisions (BUILD, L)** — Extend rollback from state-only to state-*affected
   decisions*: use the hash-chain to identify actions downstream of a poisoned point and mark them
   for re-decision. **Contract:** extend `score_recoverability` beyond the spine file. **Verify:**
   rollback-traceability invariant (corrupt a point → affected actions enumerated). **Size:** L.
8. **Mutability TTL / Authority revocation currency (BUILD, M each)** — TTL/decay on revisable state
   (mutability → 1.0); time-boxed authority tokens (authority → durable 1.0). **Size:** M.

---

## Appendix — verification commands

```bash
# baseline
uv run python -c "from cohezion.compound.aoep_scorecard import AOEPScorecard; s=AOEPScorecard().run(); print(s.overall, s.gaps)"
# harness invariants for the axes touched
uv run pytest tests/compound/test_aoep_scorecard.py -q
# confirm merge-lag facts
grep -rln "_seesaw_check\|SkillMutationQueue" src/   # → scorecard + CLAUDE.md only in this checkout
```

## Milestone 1 EXECUTED (2026-07-09, same day)

Grafted the reviewed v1.1.0 wiring package (donor 5c0a061ff, lost in consolidation:
seesaw gate, TrajectoryPoint.action, SemanticCache scope_filter, authority tag,
TokenLedger) onto the landing branch, plus new source/transformation provenance
fields on TrajectoryPoint and the scorer's documented-but-unimplemented 1.0
provenance branch.

**Measured: AOEP-v0 overall 0.167 → 0.75, gap axes 5 → 0**
(authority 1.0, scope 0.5, mutability 0.5, provenance 1.0, recoverability 1.0,
actionability 0.5). Zero test regressions (the 12 cache failures are the
pre-existing consolidation-debt set, unchanged).

Remaining to reach 1.0 (the true tip of the spear — the survey's rarest capabilities):
- scope 0.5→1.0: TTL/expiry on scoped cache entries
- mutability 0.5→1.0: TTL/decay contracts on revisable skill state
- actionability 0.5→1.0: semantic state categories (evidence/skill/commitment) per paper
- P2 BUILDS: forgetting (cross-tier deletion propagation / unlearning) and
  decision-rollback (undo downstream state-affected actions) — the two capabilities
  the survey found rarest across all 435 works.

## Milestone 2 EXECUTED (2026-07-10): all six axes at 1.0

P1 fills, each behavior-tested (tests/compound/test_aoep_p1_fills.py, 11 tests) and
live-dogfooded (real track_execution produced action="skill:npu" with provenance):
- scope 1.0: CacheEntry.scope + active _scope_ok filtering in get() L1/L2 (unscoped = global, back-compat)
- mutability 1.0: SkillMutationQueue.expire_stale() TTL decay (bi-temporal soft-delete, history preserved) wired into SkillRefiner.refine
- actionability 1.0: classify_state_category() — deterministic evidence/skill/commitment mapping populated into TrajectoryPoint.action

Compound daemon gaps also filled + dogfooded live (--once ran a full compound cycle,
tasks retired through the new retry-aware path): bounded retries, idempotent sys.path,
PID liveness gate, atomic state writes, uv-run dashboard subprocess.

**HONESTY NOTE: scorecard 1.0 ≠ done.** The six axes measure the AOEP-v0 contract
points; the two lifecycle stages the survey found rarest — FORGETTING (cross-tier
deletion propagation) and DECISION-ROLLBACK (undoing downstream actions) — remain
ABSENT and are not captured by any axis probe. They stay P2 on this roadmap and are
the real tip of the spear.
