---
type: audit
title: SurrealDB + Obsidian Vault Audit
date: 2026-06-07
trigger: user request "audit of surrealdb and obsidian vault as part of the loop"
scope: SurrealDB (namespaces/dbs/tables/counts/health) + cohezion-vault (notes, frontmatter, staleness)
status: report-only (non-destructive per orphan policy — flag + propose wiring, never delete)
companion: HOOK_TRIGGER_AUDIT_2026-06-07.md
---

# SurrealDB + Obsidian Vault Audit — 2026-06-07

## 1. SurrealDB (port 8001, node ACTIVE, QUERY_TIMEOUT 30s, ~210 MB)

**Namespaces:** `cohezion` (default), `uap`, `bmad`.
**`cohezion/main`: 53 tables.** Populated highlights:

| Table | Count | Note |
|---|---|---|
| vmodel_gate | 2245 | V-model audit trail — large, healthy |
| experiment_runs | 14 | autoresearch results |
| **learning** | 14 | ⚠ see drift below |
| **learnings** | 11 | ⚠ canonical-by-convention (harness `learnings:…`, this session's retro record landed here ✓) |
| **compound_learnings** | 2 | ⚠ third overlapping table |
| agent_journey | 3 | |
| session_registry | **0** | SCP — no live remote sessions registered |
| session_bus | **0** | SCP — empty bus |
| universe_node | 0 | empty |
| journey_knowledge | 0 | empty |

### Findings
- **F1 (drift, verify — do NOT merge blind):** three overlapping learning tables —
  `learning`(14) / `learnings`(11) / `compound_learnings`(2). Per non-destructive-wiring
  policy these are *hazards to verify*, not redundancies to merge. Convention + harness point
  to **`learnings`** as canonical; recommend consolidating the other two INTO it (integrate
  first, empty husk removed as a consequence) after confirming no distinct consumers.
- **F2 (liveness):** `session_registry`/`session_bus` empty. Expected if no Telegram remote
  steering is active right now, but the SCP loop can't be exercised without a registered
  session — worth a periodic "is the bus reachable + has ≥0 stale rows" check, not an alarm.
- **F3 (coverage gap):** `INFO FOR DB` on `uap`/`bmad` returned a non-dict (empty db or
  different shape) — not inventoried this pass. Flag for a deeper namespace sweep.

## 2. Obsidian vault — `~/vaults/cohezion-vault` (12,395 .md)

| Metric | Value |
|---|---|
| Total notes | 12,395 |
| Knowledge notes (excl. plugin source) | 10,455 |
| Plugin-source `.md` (3d-graph + hyperdim-viz) | ~648 — **inflate the count; not knowledge** |
| **Missing YAML frontmatter** | **2,802 / 10,455 = 26%** |
| Modified last 7d / 30d | 3,511 / 3,574 (very active) |
| Largest dirs | wiki 2978, daily 795, _bmad 708, docs 285, cortex 282, cerebellum 200, hippocampus 104, learnings 71 |

### Findings
- **F4 (compliance):** **26% of knowledge notes lack YAML frontmatter** — the vault +
  research-defaults convention requires it for discoverability/`vault_find_relevant_context`.
  Non-destructive remediation: a frontmatter-backfill pass (add `type`/`date` stubs), never
  deletion.
- **F5 (metric hygiene):** plugin-source dirs (`cohezion-3d-graph-plugin`, `hyperdim-viz-plugin`,
  ~648 `.md`) inflate vault counts and frontmatter stats — exclude them from vault health metrics.
- **F6 (RESOLVED — intentional migration, not drift):** the UAP research dirs
  (`/home/mike-anderson/UFO_Release_01/`) were **moved to Google Drive 2026-05 to free local
  space** (confirmed on Drive, owner `manderson240@gmail.com`: mission-report PDFs/txts,
  `uap-data.csv`). `research-defaults.md` updated to point at the Google Drive MCP instead of the
  dead local path. The SurrealDB `uap` namespace (structured entities) is separate and unaffected.

## 3. Cross-cutting quality finding (sycophancy gate)
- **F7:** `AutoDQA.evaluate()` rejects **empty** non-answers but **ACCEPTS flattery-only**
  output (`"Great question! You're absolutely right…"` → `accept=True`). Harness **I6**
  ("AUTODQA must reject sycophantic outputs") is **under-tested** — its check only feeds the
  empty string. Real gap: no substance/flattery discriminator. (See §4 wiring C.)

## 4. Recommended wiring — make this audit recurring ("as part of the loop")
All additive, gated, non-destructive:
- **A — harness invariant `surrealdb_vault_health`** in `harness_check.py`: ✅ **IMPLEMENTED
  2026-06-07** as **DV1** (SurrealDB reachable + `learning*` fragmentation flag — currently WARNs
  on `learning(14)/learnings(11)/compound_learnings(2)`) and **DV2** (vault frontmatter compliance
  ≥ 70%, sampled). Both WARN-only so they never break the harness when services are down. The
  companion hook-audit invariant **HT1** (warmup hook can't load a big model = OOM guard) landed
  in the same pass. Re-runs every `harness_check.py`.
- **B — frontmatter-backfill** pass for the 2,802 non-compliant notes (stub `type`/`date`),
  + add plugin-source dirs to the vault metric-exclude list.
- **C — strengthen the sycophancy gate (F7):** ✅ **IMPLEMENTED 2026-06-07.**
  `cohezion.compound.autodqa.is_sycophantic` discriminator + a post-verdict guard in
  `AutoDQA.evaluate()` now reject flattery-without-substance while sparing a substantive answer
  that opens with praise (discriminating test included). I6 invariant widened to feed a
  flattery sample. 19/19 AutoDQA tests pass; I4 six-types intact.

No data changed by this report.
