---
type: audit
status: report-only
date: 2026-10-23
checkout: /home/mike-anderson/dev/cohezion
branch: security/codeql-wave2
head: d3cb21249
scope: 130 modified tracked files + 90 untracked paths = 220 paths
inputs:
  - deterministic inventory (groups.json; whitespace-only / ruff-format-of-HEAD check matched 0 files)
  - classifier output per group (src_modified 31, scripts_modified 88, other_modified 11, untracked 90)
  - verifier output per group (10 disagreements, 4 pattern re-tests)
writes_performed: none (this file only; no state-changing git command was run)
---

# Main checkout reconcile plan — 2026-10-22 dirty tree

## Summary

1. **220 paths classified, every one in exactly one table below**: 130 modified tracked files (124 unique edits, 5 byte-identical to commits on other branches, 1 inventory row mislabelled "deleted" that is really a dirty nested repo) plus 90 untracked paths.
2. **COMMIT-TO-BRANCH: 3** — `scripts/stealthskater_ingest.py` and `AGENT-SURFACES.md` on `security/codeql-wave2`; `docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md` on a branch cut from `land/tgl-graph-20260918`.
3. **ARCHIVE: 67** — unique bytes with no home branch (GEMS scratch, Kaggle kernels, FLUME explainer toolchain, Sweep-A drafts already superseded on `fix/port-service-wt-fixes` / `fix/hidden-import-cycles`, intermediate Kaggle versions).
4. **DISCARD-AFTER-APPROVAL: 120** — 83 files of the 2026-09-17 model-pin sed sweep (Sweep B, conflicts with landed migration 2421551cb), 27 untracked files byte-identical to `ollama_lemonade_kaggle_push` commits or zero-byte shell accidents, 6 pasted copies of other branches' blobs, 4 generated artifacts (timestamps / regenerable registries).
5. **LEAVE: 23** — harmless docstring-only Sweep-A notes, 9 bwrap sandbox placeholders that must survive the session, half-units that need a sibling (paper-track README/paper.md, graphrag test), AGENTS.md mixed hunks.
6. **UNSURE: 7** — each has a stated settle condition; none is safe to commit or discard today (EventBus usage consumer wiring, kanban credential env override, Sweep-B src pins, graphrag singular tables, GRPO tokenizer injection).

Verdict counts: COMMIT-TO-BRANCH 3 + ARCHIVE 67 + DISCARD-AFTER-APPROVAL 120 + LEAVE 23 + UNSURE 7 = **220**.

Verifier disagreements resolved by evidence: 5 verdict changes (genesis_persistence.py, genesis_schema.surql, triune_engine.py, registry/skill_registry.json, check_status_8001.py → see "Verifier disagreements"), 1 upgrade (docs/plans tgl → COMMIT-TO-BRANCH), 4 evidence-only corrections with verdict unchanged.

---

## 1. COMMIT-TO-BRANCH (3)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `scripts/stealthskater_ingest.py` | Authored in this checkout on `security/codeql-wave2` before 2026-09-15 08:23:48 (docstring: "caught by multi-perspective review, 2026-09-14"). In no ref: `git log --all -S'def sanitize_record_id(raw: str) -> str:'` empty; origin/main has neither sanitize_record_id nor the neuron rename (last touched a61564940, 2026-08-10). | Injection hardening of SurrealDB backtick-quoted record ids built from external wiki page names — same signature as the branch's wave-2 commits b3fc1ad82/bccb006af (SSRF allowlist, argv-list exec, path containment) — plus the `neurons` → `neuron` ghost-table fix. Verifier confirmed the script writes to db **vault** (header `surreal-db: vault`), and db vault has `neuron` and no `neurons`, so the fix is correct where it runs. | medium (changes id normalisation and write target; both verified) |
| `AGENT-SURFACES.md` | Adds two ownership rows (`src/cohezion/competitions/**`, `submissions/**` → @research-daemon). `git log --all -S` on the exact row: nothing. The file has exactly one commit in all history, 75283314a 2026-09-15 on this branch. | Path only ever changes on this branch. Verifier ran `scripts/ci/check_agent_surfaces.py` against HEAD's map: exit 1, UNOWNED for `submissions/arc-paper-track/README.md` and `src/cohezion/competitions/arc/advanced_grid_reasoner.py` (tracked at HEAD); worktree map exits 0. `.github/workflows/agent-surfaces.yml` runs the checker on changed paths, so any commit touching those trees fails CI until the rows land. Purely additive, two lines. | low |
| `docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md` | Untracked /spec plan; frontmatter line 5: "landed as land/tgl-graph-20260918". That local branch exists: 5 commits, all 2026-09-18, based on 455ffbb2a (the plan's own §0 baseline); subjects carry the plan's labels (72716c190 "(R1a)", c59111187 "(R1-R3)", f35058139 "(R4/R5)", 87df29547 "(P5)"); adds the files the plan prescribes (`src/cohezion/flume/goal_graph.py`, `scripts/ci/loop_doc_mirror_check.py`). Plan file itself in no ref; branch has no remote. | Resolved from ARCHIVE (classifier never checked the branch the plan names). Commit on a new branch cut from `land/tgl-graph-20260918` so the plan travels with the work it describes; also keep an archive copy because that branch is local-only. | low |

## 2. ARCHIVE (67)

Archive root for every row: `archives/2026-10-23-main-checkout-reconcile/<original relative path>`. Tracked files are **copied** (working copy + `git diff HEAD` patch); untracked paths are **moved**.

### 2a. src_modified (12)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `src/cohezion-physics-core/src/lib.rs` | Snapshot of `ollama_lemonade_kaggle_push` work: `-S'fn zobrist_hash_grid(grid: Vec<Vec<u8>>, seed: u64)'` hits only 551651584 (2026-10-13); `git diff 551651584 -- lib.rs` = 46 lines, all modules that commit ADDS. mtime 2026-09-28. | Strict subset of the committed version and does not build alone: declares `mod kaggriculture_sim; mod biohub_tracker;` whose .rs files exist only in 551651584 (wt has only untracked vmodel_verifier.rs). Not byte-identical → archive; branch supersedes. | low |
| `src/cohezion/agi/recursive_learning.py` | Variant of `ollama_lemonade_kaggle_push`: `git diff 86e203558 -- path` (2026-10-16) = 37 lines: two extra imports + ruff wrapping. mtime 2026-10-16 11:19, hours after that commit. | Committed 86e203558 is the cleaner twin; wt adds ActionReceipt/IntentStack/JanusGovernor imports with ruff F401 on ActionReceipt. Depends on untracked recuris_memory.py / harness_protocol.py / hippocam_memory.py (all committed in 86e203558). Archive; branch supersedes. | low |
| `src/cohezion/cache/semantic_cache.py` | Sweep A (mtime 2026-09-15). `-S'def _flush_dimension_mismatch'` hits d88df6d9e then 5f4cc9149 (both 2026-10-22, only on `refs/prefetch/remotes/origin/fix/port-service-wt-fixes`); diff vs d88df6d9e = 19 lines of checked_statements plumbing. | Exact helper was committed in d88df6d9e then REPLACED by 5f4cc9149 ("keep other-width L2 entries; switch the similarity view instead") — the wt approach was reviewed and superseded on that branch. | low |
| `src/cohezion/compound/compound_health_oracle.py` | Sweep A. `git diff 240944001 -- path` (2026-10-22, port-service-wt-fixes) = 27 lines of pure ruff wrapping; verifier: byte-identical after `ruff format`. 13a6f1fd4 then refines it. | Semantically identical to committed 240944001 and already refined by 13a6f1fd4. Committing would duplicate/conflict. | low |
| `src/cohezion/flume/vae_encoder.py` | Sweep A. `-S'class _CheckpointSequentialEncoder'` hits f9e566afe + f561257b5 (2026-10-22, port-service-wt-fixes); diff vs f9e566afe = 45 lines (17 code lines) inside the degeneracy probe. | Committed branch version is the refined form (repo-root checkpoint path, ep20 artifact, fail-closed degeneracy gate, mypy-clean stub). Archive the draft. | low |
| `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | Prepends L255/L256 (2026-09-11 Kaggle content, matching untracked docs/retrospectives/2026-09-11-*.md). `-S'Learning 256: Kaggle Simulation Eviction'` across all refs: empty. `ollama_lemonade_kaggle_push` carries DIFFERENT L255/L256 (2026-09-14) and runs to L575. | Content exists nowhere in history, but its numbering collides with the branch that owns this file's growth. Keep under archives/ for renumbering into that ledger. | low |
| `src/cohezion/knowledge_graph/genesis_schema.surql` | Sweep A. Only line 202 (`training_data_summary` view) changed to `FROM journey_transition`; same file still has `DEFINE TABLE journey_transitions SCHEMAFULL` (line 29) and all fields ON the plural table (31-40). No ref carries the edit. | **Resolved UNSURE → ARCHIVE.** Internally inconsistent: the view would read a table the schema never defines. Live db genesis: `journey_transition` = 0 rows, `journey_transitions` = 33. Archive with genesis_persistence.py. | low |
| `src/cohezion/persistence/genesis_persistence.py` | Sweep A. `-S'f"CREATE journey_transition SET "'` across refs: empty. 516923fe8 (2026-09-20, origin/main + chore/portfolio-coherence) rewrote the file keeping PLURAL `journey_transitions`, adding checked_statements and tests/persistence/test_genesis_persistence.py (absent on this branch). | **Resolved UNSURE → ARCHIVE.** Module sets `SURREAL_DB = "genesis"` (line 28); the 43,031 singular rows in db main belong to another writer. In db genesis the plural table holds this module's 33 rows; the wt comment claiming the plural write "evaporated" is false for its own target. Keep bytes only for the `ORDER BY t` observation (schema defines `t`, not `timestamp`) to port onto main's version. | low |
| `src/cohezion/persistence/obsidian_mcp.py` | Sweep A import-cycle break. e75588eb4 (2026-09-22, `remotes/origin/fix/hidden-import-cycles`) made the same TYPE_CHECKING move; diff vs it = 13 lines (two comment lines). | Code-identical to the committed branch version; only comment text differs. Archive; branch supersedes. | low |
| `src/cohezion/persistence/surreal_logger.py` | Sweep A ("Import-cycle break (2026-09-14)", pickaxe empty). e75588eb4 contains the same TYPE_CHECKING fix; diff = 18 lines of comment wording. | Superseded by the reviewed version on fix/hidden-import-cycles. | low |
| `src/cohezion/registry/skill_registry.json` | Generated by `scripts/ci/sync_skill_registry.py` (ensure_ascii=False, sorted). Key-level: HEAD 235, wt 345, +110/-0/0 changed; 8d3265bb6 (2026-10-19, ollama_lemonade_kaggle_push) has 358 keys, 0 only-in-wt. mtime 2026-10-16. | **Resolved DISCARD → ARCHIVE.** Verifier: 95 of the 345 shared entries differ in value from 8d3265bb6 (branch entries carry `name`), and 43 of the 110 new entries cite skill files absent from this tree (all present in `git ls-tree 8d3265bb6`) — so the file was generated from the branch's tree state and the sync script run here cannot reproduce it. Not byte-identical to any commit → earlier snapshot, archive by the lib.rs standard. | low |
| `src/cohezion/reliability/semantic_cache.py` | Sweep A ("Deferred import (2026-09-14)", pickaxe empty). e75588eb4 applies the same lazy import of get_vault_logger; diff = 21 lines of comment wording. | Superseded by the committed cycle-break branch. | low |

### 2b. scripts_modified (3)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `scripts/ops/submit_arc3_when_ready.py` | wt is v14 ("Affordance Rarity SearchAgent"), dirty before 2026-09-15 08:23:48. Only -S hit for the v14 message is 551651584 (2026-10-13, ollama_lemonade_kaggle_push), which REPLACED it: 551651584^ is v18, 551651584 is v24; origin/main is v16. | Superseded intermediate on both lines; committing would regress VERSION/MSG. Its hardened poll loop (240x15s, try/except, `uv run --with kaggle`) never landed but v24 reworked the loop differently. Keep bytes for reference. | low |
| `scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb` | Local Kaggle iteration saved 2026-09-15 18:04:11 (27 → 31 cells). Not in any ref (`--find-object` none; ricecakar / `def augment(` / JIT room guard absent everywhere). **Verifier correction:** the v8-v13 line (48794ef97, b9d0368b5, 2aa79010b) is NOT on origin/main — it lives only on ollama_lemonade_kaggle_push / agent-179* / find_previous_kaggle_work. origin/main's last commit on this notebook is e9869f425 (2026-09-12); HEAD's copy equals fe6735b10, 438 lines behind it. | Pre-v8 intermediate layered on a pre-e9869f425 base; competition deadline 2026-10-22 has passed. Unique cells (augment/predict helpers, CPU fallback, JIT guard, CoatNet 0.75/0.80) worth keeping as bytes, not committing. Anyone landing RSNA v13 later must take it from the Kaggle branch, not main. | low |
| `scripts/kaggle/rsna_sota_ensemble/kernel-metadata.json` | Rewritten 2026-09-15 18:04:11 with the notebook (json.dump indent=1, no trailing newline). Semantic change: one added dataset_source `ricecakar/rsna-knee-band32-ours`, in no ref; origin/main == HEAD for this file. | Pair of the archived notebook; competition closed. Keep with it. | low |

### 2c. untracked (52)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `.claude/rules/codegraph.md` | mtime 2026-09-18. Tracked on origin/main (blob 01821b4939, added by b3342cf18) but NOT on this branch; wt blob 577701685d matches no commit and is an OLDER draft (lacks --dry-run and vault-artifact paragraphs; 3+/6- vs main). | Superseded by origin/main's version; as an untracked file it will block merging main into this branch ("untracked file would be overwritten"). Archive the draft; the tracked version arrives via merge. | low |
| `.kaggle_arc3_work/` | 18 files, all 2026-09-15: ARC-AGI-3 autoharness kernel cell dumps + remote_v18 notebook/log/parquet. No history; `remote_v18_out/submission.parquet` is byte-identical to `~/cohezion-labs/arc-agi-3/keepalive/commit_out/submission.parquet`. | Kaggle scratch belonging in ~/cohezion-labs; competition closed. Keep bytes. | low |
| `acf_analysis.py` | 2026-09-20 GEMS (DrivenData) rasterio/GBM-importance scratch; no -S hit anywhere; no byte twin under ~/dev/drivendata. | Wrong repo (GEMS home is ~/dev/drivendata/gems); unique. | low |
| `arc3_macro_action_compiler.py` | 2026-10-13 standalone ARC-AGI-3 macro-action compiler (pure stdlib). No path/blob history. | Unique Kaggle work at repo root; belongs in ~/cohezion-labs. | low |
| `atwater_response.json` | 2026-09-19 LLM "Tanya Atwater digital twin" GEMS research response. No history. | GEMS research scratch in the wrong repo. | low |
| `dem_fault_features.json` | 2026-09-17 GEMS DEM feature research JSON. No history. | GEMS research scratch. | low |
| `docs/audits/PROMPT_AUDIT_2026-10-06.diff` | 2026-10-06 proposed CLAUDE.md/rules hunks (companion to the .md; applied: none). No history. | Unique unapplied proposal; keep with the .md. | low |
| `docs/audits/PROMPT_AUDIT_2026-10-06.md` | 2026-10-06 configuration prompt audit (96 findings, 21 hunks, applied: none). No branch carries the path. | Unique report; could go on a docs branch later but no branch evidences it. | low |
| `docs/build_explainer.py` | 2026-09-18 builds docs/cohezion_flume_explainer.html from the marimo notebook. No history. | FLUME explainer toolchain; archive as a set. | low |
| `docs/cohezion_flume_explainer.html` | 2026-09-18 235KB HTML generated by build_explainer.py. No history. | Generated but it is the deliverable; keep with its generator. | low |
| `docs/cohezion_flume_notebook.py` | 2026-09-18 marimo notebook (explainer source). No path history. | Unique doc source. | low |
| `docs/decode_explainer.py` | 2026-09-18 helper extracting notebookCode from the HTML. No history. | Explainer toolchain set. | low |
| `docs/extract_explainer.py` | 2026-09-18 explainer helper. No history. | Explainer toolchain set. | low |
| `docs/inspect_nb.py` | 2026-09-18 notebook inspection helper. No history. | Explainer toolchain set. | low |
| `docs/triage/` | One file, `2026-09-15-dirty-tree-triage.md`: the previous session's reconciliation record for the Sept-15 dirty tree. No history. | Direct evidence for this reconciliation; proper home is the vault reports dir. | low |
| `event_bus.json` | 2026-09-20 "gems-oom-recovery" event payload (memory snapshot during the GEMS OOM). No history. | Incident record from GEMS work. | low |
| `features_detailed.py` | 2026-09-20 GEMS feature script hard-coded to /home/mike-anderson/dev/drivendata/gems/data. No history. | GEMS scratch in the wrong repo. | low |
| `features_final.py` | 2026-09-20 GEMS feature script (make_valid_mask etc.); produced analysis_output.txt. No history. | GEMS scratch. | low |
| `features_vectorized.py` | 2026-09-20 GEMS vectorized feature script. No history. | GEMS scratch. | low |
| `gems_band_analysis.py` | 2026-09-20 GEMS band analysis. No history. | GEMS scratch. | low |
| `gems_dem_strategy.json` | 2026-09-17 LLM research JSON. No history. | GEMS research scratch. | low |
| `gems_dw_tversky_strategies.json` | 2026-09-17 LLM research JSON on DW-Tversky strategies. No history. | GEMS research scratch. | low |
| `gems_method_research.json` | 2026-09-17 LLM research JSON. No history. | GEMS research scratch. | low |
| `gems_pipeline_research.json` | 2026-09-17 LLM research JSON. No history. | GEMS research scratch. | low |
| `gems_research findings.json` | 2026-09-17 LLM research JSON (space in filename; different content from the underscore sibling). No history. | GEMS research scratch. | low |
| `gems_research_findings.json` | 2026-09-17 LLM research JSON. No history. | GEMS research scratch. | low |
| `gems_winning_strategy.md` | 2026-09-17 GEMS submission strategy note (references drivendata-repo paths). No history. | GEMS note in the wrong repo. | low |
| `hermes-cron-rootcause-2026-09-17.md` | 2026-09-17 Hermes cron outage root-cause record. No history; vault has a derived skill but not this file. | Unique incident record; home is the vault reports dir. | low |
| `isacks_gems_response.json` | 2026-09-19 LLM "Isacks" GEMS response. No history. | GEMS research scratch. | low |
| `learn/` | 8 files, `learn/claude-api/*.py`, 2026-10-21: Anthropic SDK lesson scripts generated by the claude-api skill. No history. | Personal tutorial scripts, not project code. | low |
| `ml-competition-submission/` | 4 md files 2026-09-17..20: skill draft (DW-Tversky metric + references). Not installed anywhere; no history. | Unique GEMS-derived skill draft; install into the vault skills dir if wanted. | low |
| `scripts/hotswap_model.sh` | 2026-09-15 task-shaped hotswap prototype via Lemonade OmniRouter. No history. Superseded by src/cohezion/inference/hotswap.py (feat/trace-goal-loop-*) and scripts/npu_hotswap.py (ollama_lemonade_kaggle_push). | Unique but superseded prototype. | low |
| `scripts/kaggle/agent_security_kernel/make_paper_track_cover.py` | 2026-09-15 matplotlib script producing submissions/arc-paper-track/cover_image.png. No history. | Paper-track tooling; belongs with the kit in ~/cohezion-labs. | low |
| `scripts/kaggle/arc2_v6_tta24_kernel/` | 2 files 2026-09-15 (kernel-metadata.json + notebook). No history. | Kaggle kernel snapshot; competition closed. | low |
| `scripts/kaggle/arc2_v8_synth_lora_kernel/` | 2 files 2026-09-16. No history. | Kaggle kernel snapshot. | low |
| `scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent-v19.ipynb` | 2026-09-15 v19 next to the tracked unversioned notebook. No history; Sept-15 triage doc lists it as real uncommitted work. | Kaggle kernel version; scoring harness lives in ~/cohezion-labs/arc-agi-3. | low |
| `scripts/kaggle/kaggriculture_smoke_v5.py` | 2026-09-15 Kaggriculture v5 smoke test. No history. | Kaggle scratch; belongs in ~/cohezion-labs/kaggriculture. | low |
| `scripts/kaggle/rsna_efficiency_fast/` | 2 files 2026-09-16 (metadata + 188KB notebook). No history. | Kaggle kernel snapshot. | low |
| `scripts/kaggle/rsna_sota_ensemble/monitor_all_inflight.py` | 2026-09-14 803-byte in-flight kernel monitor. No history. | Kaggle ops scratch; low value, keep bytes. | low |
| `scripts/model_hotswap_router.py` | 2026-09-15 task-class → model router prototype paired with hotswap_model.sh. No history; superseded by the hotswap modules. | Unique but superseded prototype. | low |
| `src/cohezion/agi/info_density.py` | 2026-09-15 compression-ratio info-density helper with its own test. No history; no importer at HEAD. | Unique never-wired module; keep with tests/unit/test_info_density.py. | low |
| `src/cohezion/competitions/biohub_cell/V6_LINEAGE.md` | 2026-09-15 lineage note for the Biohub v6 kernel. No history; the branch keeps the kernel under scripts/kaggle/biohub_v6/ without this note. | Unique Kaggle lineage doc; competition closed. | low |
| `src/cohezion/competitions/biohub_cell/kernel-metadata-v6.json` | 2026-09-15 kernel metadata. Not byte-identical to anything in history. | Small unique Kaggle metadata; keep with V6_LINEAGE.md. | low |
| `src/cohezion/inference/strix_halo_hybrid_router.json` | mtime 2026-10-01; path tracked on ollama_lemonade_kaggle_push (added by 551651584) but wt bytes match no commit. **Verifier correction:** wt is `"version": "1"`, model_name `user.StrixHalo-Cohezion-Router`; tip is version 2 with a different model_name; `git diff --stat` vs tip = 156 deletions, 0 insertions (strict subset). | Unique bytes, older than the branch's first version. Archive rather than discard. | low |
| `src/cohezion/inference/task_router.py` | 2026-09-15; no path history; no importer in src/scripts/tests. | Unique never-wired prototype. | low |
| `submissions/arc-paper-track/PAPER_TRACK_SUBMISSION.md` | 2026-09-16 manual submission kit for the ARC Prize paper track. No history; ~/cohezion-labs holds a different kit. | Unique ARC submission artifact; belongs in ~/cohezion-labs. | low |
| `submissions/arc-paper-track/cover_image.png` | 2026-09-15 PNG generated by make_paper_track_cover.py. No history. | Generated but cheap to keep with its kit. | low |
| `submissions/arc-paper-track/writeup.md` | 2026-09-15 "Deterministic Verifiers Replacing LLM Calls at Inference" writeup. No history; labs has later V19 writeups with different content. | Unique submission text. | low |
| `submissions/kaggriculture/` | One file main_v5_day3fork.py (75KB, 2026-09-15), byte-identical to ~/cohezion-labs/kaggriculture/agent_v5_live.py — which is itself untracked there ("??"). | Preserved in labs but in no commit anywhere, so archive rather than discard. | low |
| `sykes_response.json` | 2026-09-19 LLM "Sykes" GEMS response. No history. | GEMS research scratch. | low |
| `tests/unit/test_info_density.py` | 2026-09-15 tests for info_density.py. No history. | Keep paired with info_density.py. | low |
| `tharp_response.json` | 2026-09-19 LLM "Marie Tharp digital twin" GEMS response. No history. | GEMS research scratch. | low |

## 3. DISCARD-AFTER-APPROVAL (120)

### 3a. src_modified (4)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `src/cohezion/agents/generated/skill_0_agent.py` | Header `# Generated from SKILL_0_PRIME v1.0 at 2026-09-14T17:07:45` stamped by src/cohezion/core/config_templates.py:164 (`time.strftime`). Committed blob (9fdf40f58, 2026-09-12) differs only in that timestamp. | 1-line timestamp churn from a daemon regeneration; body byte-identical to HEAD (verifier-confirmed after stripping the header line). | low |
| `src/cohezion/agents/generated/skill_1_agent.py` | Same regeneration event (identical timestamp). Committed blob a29ac9e30 in 9fdf40f58. | Timestamp-only churn of a generated file. | low |
| `src/cohezion/knowledge_graph/health_log.json` | Runtime artifact written by src/cohezion/healing/_core.py (HEALTH_LOG_PATH). Only `timestamp` changed (2026-08-27 → 2026-09-14T17:01:34). | Generated, timestamp-only churn; HEAD blob is the content. | low |
| `src/cohezion/skills/skill_registry.json` | Generated by `scripts/sync_skill_registry.py` (json.dump sort_keys, default ensure_ascii → the `\u` re-escaping). wt = HEAD's 96 + 10 new (6 AMD_*, AUTOHARNESS_PRIME, KAGGLE_GRANDMASTER_ASCENT_PRIME, NO_AI_SLOP_PRIME, SURREALDB_DATAMESH_PRIME), 0 changed. mtime 2026-10-02. | Regenerable and already stale: NO_AI_SLOP_PRIME points at a file that does not exist; the 5 AMD_* entries point into the amd/skills-repo gitlink. Verifier: 9 of 10 sources exist on disk (untracked or inside the gitlink), regenerable via rglob over SKILLS_DIR — DISCARD stands. Re-run the sync script on the landed skill set. | low |

### 3b. scripts_modified (83)

Sweep B (82 files): all share mtime 2026-09-17 10:11:51 to the second (scripted sed); mapping `qwen3.5:397b-cloud` → `kimi-k3:cloud`, `deepseek-v4-flash:0731-cloud` → `deepseek-v4-flash:cloud`, and (verifier refinement) bare `qwen3.5:397b` → `kimi-k3:cloud`, bare `deepseek-v4-flash:0731` → `deepseek-v4-flash:cloud`. In NO ref (`git log --all -S'"model": "kimi-k3:cloud"' -- scripts/ops` hits only unrelated 551651584/fe6735b10; origin/main still carries the old ids in all 82; `--find-object` on each working blob: nothing). CONFLICTS with landed migration 2421551cb (2026-09-22, origin/main): canonical successors are `kimi-k2.7-code:cloud` and `deepseek-v4.1-flash:cloud`; 2421551cb states `deepseek-v4-flash:cloud` is itself retired and origin/main's registry has no such id. Shared origin for every row below unless stated: "Sweep B sed 2026-09-17 10:11:51; in no ref; origin/main unchanged."

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `scripts/adversarial_review_oscillation.py` | Sweep B | Pure model-id rename, 0 non-rename lines; conflicts with 2421551cb successor map. Regenerate from the registry successor map. | low |
| `scripts/capella_probe.py` | Sweep B | Pure rename; conflicts with 2421551cb. | low |
| `scripts/datamesh_land_scanner.py` | Sweep B; `-S'(kimi-k3:cloud, 2026-08-14)'`: no commits | Sweep over-reach: rewrites a dated review attribution "(qwen3.5:397b, 2026-08-14)" to kimi-k3:cloud, falsifying history; also targets retired deepseek-v4-flash:cloud. | low |
| `scripts/experiments/bleeding_edge_research_sprint.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/arc3_adversarial_fleet_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/audit_and_patch_thinking_timeouts.py` | Sweep B | Pure rename. | low |
| `scripts/ops/audit_competition_metadata_leverage.py` | Sweep B (verifier re-test sample) | Pure rename (3 lines). | low |
| `scripts/ops/audit_ml_acceleration_opportunities.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/autonomous_evolution_supervisor.py` | Sweep B | Pure rename. | low |
| `scripts/ops/benchmark_model_harness_affinity_matrix.py` | Sweep B (verifier re-test sample) | Pure rename (3 lines). | low |
| `scripts/ops/benchmark_ollama_cloud_models.py` | Sweep B; origin/main already lists kimi-k3:cloud separately | Rename (5 lines) produces duplicate kimi-k3 entries in a benchmark roster. | low |
| `scripts/ops/cloud_adversarial_bughunt.py` | Sweep B | Pure rename. | low |
| `scripts/ops/cloud_multiperspective_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_all_ollama_cloud_models.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_cloud_bleeding_edge_improvements.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_cloud_competition_architectures.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/consult_cloud_defect_class.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_fresh_cloud_models.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_kaggle_next_breakthroughs.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_matsumoto_enc_audit.py` | Sweep B (verifier re-test sample) | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_and_local_bleeding_edge.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_bleeding_edge_advisors.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_deep_exploration.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_fix.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_grand_advisors.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_kanban_crm.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_on_nous_research.py` | Sweep B | Rename incl. retired deepseek-v4-flash:cloud (absent from origin/main registry). | low |
| `scripts/ops/consult_ollama_cloud_targeted_audits.py` | Sweep B | Pure rename. | low |
| `scripts/ops/consult_ollama_cloud_thinking_models.py` | Sweep B | Pure rename. | low |
| `scripts/ops/day1_arc_ttc_scaling_engine.py` | Sweep B | Pure rename (4 lines). | low |
| `scripts/ops/debug_qwen_arc_task.py` | Sweep B | Rename in a qwen-specific debug script (name now mismatches content). | low |
| `scripts/ops/debug_qwen_full_print.py` | Sweep B | Rename in a qwen-specific debug script. | low |
| `scripts/ops/debug_qwen_raw.py` | Sweep B | Rename in a qwen-specific debug script. | low |
| `scripts/ops/debug_qwen_thinking.py` | Sweep B | Rename in a qwen-specific debug script. | low |
| `scripts/ops/deep_dive_dogfood.py` | Sweep B; `-S'qwen3.5:397b-cloud' -- path` shows only additions fe6735b10/645424494/b840a19e6 | Pure rename (5 lines). | low |
| `scripts/ops/dird_37_matrix_synthesis.py` | Sweep B | Pure rename. | low |
| `scripts/ops/direct_cloud_bughunt.py` | Sweep B | Pure rename. | low |
| `scripts/ops/dual_fleet_multiperspective_review.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/enrich_daemons_with_cloud.py` | Sweep B | Pure rename. | low |
| `scripts/ops/execute_overnight_bbq_worker.py` | Sweep B | Pure rename. | low |
| `scripts/ops/execute_pipeline_sprint_sequence.py` | Sweep B | Pure rename. | low |
| `scripts/ops/execute_thenoise_iterative_evolution.py` | Sweep B (verifier re-test sample) | Pure rename. | low |
| `scripts/ops/finalize_fanout_report.py` | Sweep B | Pure rename. | low |
| `scripts/ops/gaia_cloud_adversarial_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/grand_13_model_cloud_adversarial_review.py` | Sweep B; origin/main already has 3 kimi-k3 entries | Rename (6 lines) incl. retired deepseek-v4-flash:cloud; duplicates kimi-k3 lanes in the 13-model roster. | low |
| `scripts/ops/grand_breadth_depth_fanout_sprint.py` | Sweep B | Pure rename (6 lines, 4 task entries). | low |
| `scripts/ops/grand_multiperspective_adversarial_deep_review.py` | Sweep B; origin/main already has 3 kimi-k3 entries | Rename (6 lines) incl. retired id; duplicates kimi-k3 lanes. | low |
| `scripts/ops/grand_multiperspective_shoulders_matsumoto_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/grand_unified_tri_silicon_cloud_audit.py` | Sweep B; origin/main already has 3 kimi-k3 entries | Rename (6 lines) incl. retired id; duplicates kimi-k3 lanes. | low |
| `scripts/ops/local_multiperspective_research_reviewer.py` | Sweep B | Pure rename. | low |
| `scripts/ops/master_hybrid_fleet_optimizer.py` | Sweep B (verifier re-test sample) | Pure rename. | low |
| `scripts/ops/master_matrix_parallel_explorer.py` | Sweep B | Pure rename. | low |
| `scripts/ops/master_tri_delegate_adversarial_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/multi_cloud_swarm_matrix_sprint.py` | Sweep B | Pure rename. | low |
| `scripts/ops/multi_model_micrograph_comparison.py` | Sweep B | Pure rename. | low |
| `scripts/ops/multiperspective_cloud_adversarial_review.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/multiperspective_code_review.py` | Sweep B | Single rename to retired deepseek-v4-flash:cloud (successor deepseek-v4.1-flash:cloud); targets a dead model. | low |
| `scripts/ops/multiperspective_diff_review.py` | Sweep B | Only deepseek-v4-flash:0731-cloud → retired id (2 lines). | low |
| `scripts/ops/multiperspective_gaia_orchestrator.py` | Sweep B | Pure rename. | low |
| `scripts/ops/ollama_cloud_adversarial_frontier_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/ollama_cloud_adversarial_review.py` | Sweep B | Pure rename. | low |
| `scripts/ops/ollama_cloud_multiperspective_adversarial_review.py` | Sweep B | Pure rename (7 lines). | low |
| `scripts/ops/prove_anytime_compute_maximization.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/prove_ollama_cloud_fleet.py` | Sweep B | Rename incl. retired deepseek-v4-flash:cloud. | low |
| `scripts/ops/query_cloud_reviewers_clean.py` | Sweep B | Pure rename. | low |
| `scripts/ops/query_qwen397b_direct.py` | Sweep B | Rename in a qwen397b-specific script (filename contradicts content). | low |
| `scripts/ops/refactor_codebase_for_simplicity.py` | Sweep B | Pure rename. | low |
| `scripts/ops/remediate_adversarial_gaps_hybrid.py` | Sweep B | Rename incl. retired deepseek-v4-flash:cloud. | low |
| `scripts/ops/research_arxiv_2606_12683_agi_asi.py` | Sweep B | Pure rename. | low |
| `scripts/ops/research_bleeding_edge_silicon_strategies.py` | Sweep B | Pure rename. | low |
| `scripts/ops/research_terminal_mermaid_graphics.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/silicon_model_optimization_research.py` | Sweep B | Pure rename. | low |
| `scripts/ops/solve_with_qwen397b_thinking.py` | Sweep B | Rename in a qwen397b-specific script. | low |
| `scripts/ops/test_frontier_cloud_coder_on_arc.py` | Sweep B | Pure rename. | low |
| `scripts/ops/test_qwen397b_arc.py` | Sweep B | Rename in a qwen397b-specific script. | low |
| `scripts/ops/verify_and_validate_with_ollama_cloud.py` | Sweep B | Pure rename. | low |
| `scripts/ops/verify_dsh_deepseek_harness_integration.py` | Sweep B | Single rename to retired deepseek-v4-flash:cloud; targets a dead model. | low |
| `scripts/ops/verify_dual_substrate_proof.py` | Sweep B | Pure rename (3 lines). | low |
| `scripts/ops/verify_ollama_cloud_datamesh_inference.py` | Sweep B | Rename (5 lines) incl. retired id; bare-id map produced a duplicated `kimi-k3:cloud / kimi-k3:cloud` docstring. | low |
| `scripts/ops/verify_ollama_cloud_live_execution.py` | Sweep B | Rename (4 lines) incl. retired id. | low |
| `scripts/ops/verify_qwen_code_datamesh_integration.py` | Sweep B | Pure rename. | low |
| `scripts/ops/verify_true_multimodal_vision_feedback_loop.py` | Sweep B | Rename claims kimi-k3 "with vision capability" — an unverified attribute carried over from the qwen text. | low |
| `scripts/ci/lint_baseline.txt` | Generated by `ruff_ratchet.py --update` in this checkout before 2026-09-15 08:23:48 (pre-commit autostash reflog). Value 1170 in no ref; origin/main is at 905 via c79014385 (2026-10-22) and ba72b0b64. | Generated artifact (header: "measured-by: ruff_ratchet.py --update"); stale 1170 superseded by 905. Re-run the ratchet after rebasing. | low |

### 3c. other_modified (6)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `pi/git/github.com/tmustier/pi-extensions` (real path `.pi/git/github.com/tmustier/pi-extensions`) | Nested git repo (gitlink 160000 a6839e57c, no .gitmodules mapping). git status shows ` m` (dirty content), NOT a deletion — the inventory's DELETED-IN-WORKTREE / `M ` label is wrong. Inside: one file, `extending-pi/skill-creator/scripts/validate_skill.py`, pure ruff reformat (line-length 100, pyproject.toml:188) from the post-edit-lint hook. | Formatter artifact on vendored upstream code; the parent cannot commit it (gitlink records only the inner commit, unchanged). Restore via `git -C <nested> checkout --`. | low |
| `cloud-vault-mcp/src/mcp_server/surrealdb_sync.py` | wt blob 9f9d93734 byte-identical to 13710806c (2026-09-19, origin/main; not an ancestor of HEAD). HEAD == merge-base copy; this branch never touched the file; `git diff origin/main -- path` = 0. | The working tree holds origin/main's newer version of a file this branch never changed. Discard restores HEAD; the content returns on rebase/merge onto origin/main. | low |
| `scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent.ipynb` | wt blob 5dba184ce byte-identical to e9869f425 (2026-09-12, origin/main; also 846572b59). Not an ancestor of HEAD; HEAD's copy is this branch's own a4315dc4d v13. | Content exists verbatim on origin/main (v15). Discard restores v13, which will be resolved toward origin/main at merge time regardless; nothing unique in the working tree. | low |
| `src/cohezion/platform/admission_gate.py` | wt blob d43385c9f byte-identical to 409e043b7 (2026-10-16, ollama_lemonade_kaggle_push); that branch has since changed the file again in 209d1d3c9 (2026-10-19, 17-line diff). HEAD == merge-base == origin/main. | Already-superseded intermediate from another branch; keeping it risks landing the stale version over the newer fix. Imports the untracked aperture_guard.py (6x) — discard the pair together. | low |
| `src/cohezion/skills/AUTOHARNESS_PRIME.md` | wt blob 916516f96 byte-identical to 551651584 (2026-10-13) and to the ollama_lemonade_kaggle_push tip (0-line diff). HEAD == origin/main == merge-base. | Live tip version on the branch it will land from. Nothing unique. | low |
| `tests/mycelium/generated_test_dummy.py` | wt holds the unformatted one-liner `def test_more(): pass` (blob f3f4bf3fe), byte-identical to 551651584 and seven earlier commits back to c00702919 (2026-05-02); HEAD holds the ruff-formatted form from 4c3423ab1. | Generated fixture oscillating between generator output and formatter output; pre-commit ruff rewrites it to HEAD's form on any commit anyway. | low |

### 3d. untracked (27)

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `)\n        if tk and head.startswith(tk) and len(tk)<len(head) or (tk and tk==head.strip(*` | Zero-byte file, mtime 2026-10-20 09:02; name is a fragment of Python source — a shell quoting accident. Content = empty blob e69de29bb2. | Empty shell-redirect artifact. | low |
| `**2026-10-15` | Zero-byte, mtime 2026-10-15 17:40; markdown bold token leaked into a shell command. | Empty shell accident. | low |
| `--nets` | Zero-byte, mtime 2026-10-21 15:29; a CLI flag written as a redirect target. (Instrument note: `git hash-object` parses the name as a flag; use `./--nets`.) | Empty shell accident. | low |
| `.obsidian/` | 21 `*-graph.json` files, all byte-identical to the 8f712a8bd tree (2026-07-30); deliberately untracked by 2a0813a15 (ancestor of HEAD); HEAD's .gitignore no longer matches them. | Daemon-generated graph exports already preserved in history at 8f712a8bd. | low |
| `=2026.2.0` | Zero-byte, mtime 2026-10-22 16:59; an unquoted `pkg>=2026.2.0` redirect. | Empty shell accident. | low |
| `analysis_output.txt` | 2026-09-20 captured stdout/stderr of running features_final.py (numpy RuntimeWarnings). No history. Verifier: regeneration inputs exist (features_final.py + gems data tifs + submissions/gbm_model_v1.json). | Generated run log, regenerable from its (archived) producer. | low |
| `anatomical_copula_coupling.py` | Byte-identical (blob a01dc56067) to 551651584:scripts/kaggle/rsna_speedy_raptors/anatomical_copula_coupling.py on ollama_lemonade_kaggle_push. | Misplaced root-level duplicate; exists at its proper path in 551651584. | low |
| `docs/__marimo__/` | marimo auto-generated session cache for docs/cohezion_flume_notebook.py (2026-09-18). | Regenerated whenever the notebook is opened. | low |
| `docs/retrospectives/2026-09-11-kaggle-offensive-and-surrealdb-maximization.md` | Byte-identical (sha256 3807ef68…) to `~/vaults/cohezion-vault/retros/<same name>`. **Verifier: a commit CAN be named** — the vault is a git repo and holds the identical blob 449695a72f at HEAD, committed 4a7960b84 (2026-10-13). | Exact duplicate of the vault's committed copy. | low |
| `scripts/jobs/storage_headroom_guard.sh` | Byte-identical (blob d4016c1640) to 551651584 and to the ollama_lemonade_kaggle_push tip. | Exists in history. | low |
| `scripts/kaggle/name_that_llm/` | 3 files, each byte-identical to a commit on ollama_lemonade_kaggle_push: build_starter_notebook.py = 86e203558 (tip), the .ipynb = 86e203558 (tip moved on at 76f859b9e), kernel-metadata.json = 2e76d79c9 (tip moved on at 022ccce39). | Stale snapshot; everything is in history. | low |
| `scripts/ops/master_longhorizon_goals_recursive_learning_refactor.py` | Byte-identical (blob 7d8f5c1bcb) to 551651584 and the branch tip. | Exists in history. | low |
| `scripts/ops/vmodel_compound_trace_refactor.py` | Byte-identical (blob f9576ba785) to 551651584 and the branch tip. | Exists in history. | low |
| `src/cohezion-physics-core/src/vmodel_verifier.rs` | Byte-identical (blob d65b2df8aa) to 551651584 and the branch tip. The modified lib.rs (ARCHIVE) declares `mod vmodel_verifier`. | Exists in history; discard together with the lib.rs decision (archive lib.rs first). | medium |
| `src/cohezion/agi/recuris_memory.py` | Byte-identical (blob 7e619eab0d) to 86e203558 and the branch tip. Imported by the modified recursive_learning.py (ARCHIVE). | Exists in history; discard only after recursive_learning.py is archived+restored or the wt import breaks. | medium |
| `src/cohezion/competitions/biohub_cell/cohezion-biohub-v6.ipynb` | Byte-identical (blob ee04d7e530) to e9be42add:scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb (2026-09-18, origin/ollama_lemonade_kaggle_push). **Verifier correction:** the later a99613aaf delta is 132+/1-, not "3 lines" — irrelevant to the decision. | Exists in history at its proper path. | low |
| `src/cohezion/compound/harness_protocol.py` | Byte-identical (blob f3e765bd4c) to 86e203558 and the branch tip (defines ActionReceipt/HarnessContextProtocol imported by the modified recursive_learning.py). | Exists in history; couple with the recursive_learning.py decision. | medium |
| `src/cohezion/compound/vmodel_compound_graph_system.py` | Byte-identical (blob baced51fe4) to 551651584; branch tip (955d529cc, 2026-10-17) is 48 lines newer. | Older snapshot already in history. | low |
| `src/cohezion/gaia/` | One file strix_evaluator_agent.py, byte-identical (blob d399b52819) to 551651584 and the branch tip. No importer in the working tree. | Exists in history. | low |
| `src/cohezion/inference/aperture_guard.py` | Byte-identical (blob f49f02ce33) to 86bdd9b2d / 24d2bef41 and the branch tip; DELETED at the tip of origin/fix/admission-aperture-guard by 10b6687eb ("thin gate"). Imported 6x by the modified admission_gate.py (DISCARD). | Exists in history and retired upstream; discard together with admission_gate.py. | medium |
| `src/cohezion/kaggle/` | One file stateless_npu_agent.py, byte-identical (blob 65150e8a54) to 2e76d79c9; branch has 5+ later commits on it (tip differs by 38 lines). | Stale older snapshot already in history. | low |
| `src/cohezion/knowledge_graph/hippocam_memory.py` | Byte-identical (blob c455d10bf0) to 86e203558 and the branch tip (defines IntentStack/JanusGovernor imported by the modified recursive_learning.py). | Exists in history; couple with recursive_learning.py. | medium |
| `src/cohezion/skills/AMD_GAIA_ORCHESTRATION_PRIME.md` | Byte-identical (blob 40e558ad5e) to 551651584; tip (d25dbfaee, 2026-10-18) is 34 lines newer. | Older snapshot already in history. | low |
| `src/cohezion/skills/KAGGLE_GRANDMASTER_ASCENT_PRIME.md` | Byte-identical (blob e42700dce8) to 551651584 and the branch tip. | Exists in history. | low |
| `src/cohezion/skills/SURREALDB_DATAMESH_PRIME.md` | Byte-identical (blob 6a38597c93) to 551651584 and the branch tip. | Exists in history. | low |
| `tests/unit/test_longhorizon_goals_recursive_learning.py` | Byte-identical (blob 617ee2af48) to 551651584 and the branch tip. | Exists in history. | low |
| `tests/unit/test_recuris_hippocam_hcp.py` | Byte-identical (blob 230548cd3d) to 86e203558 and the branch tip. | Exists in history. | low |

## 4. LEAVE (23)

No commands. These stay as they are until the stated condition.

| Path | Origin | Rationale | Risk |
|---|---|---|---|
| `src/cohezion/agi/kaggle_autoharness.py` | Sweep B (mtime 2026-09-17 10:11:51). Pickaxe empty. Last path commit 98756fad1 (2026-08-26). | All three changed lines are docstrings; no behaviour change. Rides with the Sweep B decision. | low |
| `src/cohezion/compound/self_improvement_orchestrator.py` | Sweep A docstring note ("grep-verified 2026-09-14"); pickaxe empty. | Docstring-only: removes the phantom JOURNEY_STEP route claim. | low |
| `src/cohezion/data_mesh/multi_session_sanitization_gateway.py` | Sweep A docstring note; pickaxe empty. | Docstring-only correction (drops the false JOURNEY_STEP intercept claim). | low |
| `src/cohezion/flume/evo_visualizer.py` | Sweep A; `-S'_resolve_output_path'` empty across refs. | Anchors the CWD-relative `.obsidian/...` output onto ~/vaults/cohezion-vault; the untracked repo-root `.obsidian/` is the symptom it fixes. No conflicts. Pair with viz_bridge.py when a branch is chosen for the 09-14 sweep. | low |
| `src/cohezion/flume/loop_goal_refactor_engine.py` | Sweep A docstring note (3 lines); pickaxe empty. Path heavily rewritten on land/tgl-graph-20260918 (809-line divergence). | Docstring-only; will trivially conflict with the tgl-graph branch if that lands first. | low |
| `src/cohezion/inference/smart_oom_governor.py` | Sweep B, one docstring line. 55434a168 (ollama_lemonade_kaggle_push) recalibrates this file. | Single docstring token swap; rides with Sweep B. | low |
| `src/cohezion/learning/ouroboros.py` | Sweep A; `-S'guard is removed: no'` empty. | Removes an `event_type != "training_step"` guard on analyze_audio_telemetry; no caller and no test at HEAD, so behaviourally inert today. | low |
| `src/cohezion/universe/triune_engine.py` | Sweep A ("Import-cycle break (2026-09-14)"); pickaxe empty. e75588eb4 on fix/hidden-import-cycles breaks the same persistence↔universe cycle from the surreal_logger side without touching this file. | **Resolved COMMIT-TO-BRANCH → LEAVE.** After e75588eb4, persistence imports universe only under TYPE_CHECKING, so triune_engine's eager import is no longer on any cycle; the branch's own hidden_import_cycle_scan.py did not flag this edge. Harmless annotation-only edit, but redundant — the bar for committing it to that branch is not met. | low |
| `src/cohezion/universe/viz_bridge.py` | Sweep A; same `_resolve_output_path` helper as evo_visualizer.py; pickaxe empty. | Anchors `.obsidian/3d-graph-data.json` to the vault. No conflicts; pair with evo_visualizer.py. | low |
| `scripts/maintenance/check_status_8001.py` | Authored here before 2026-09-15 08:23:48; `agent_journeys` → `agent_journey`. In no ref. | **Resolved COMMIT-TO-BRANCH → LEAVE.** The script constructs `SurrealClient(url="ws://localhost:8001/rpc")` with no database kwarg, and SurrealClient defaults to database=`vault` (surreal_client.py:349) where neither table exists — all three queries still fail after the edit. Settle: add `database="main"` (agent_journey = 19,430 rows there), run the script, then commit both changes together. | low |
| `AGENTS.md` | Four hunks, two origins: (1) the 109-line `<!-- BEGIN amd-skills:local-ai-use -->` block is byte-identical to 75d66ff49 on ollama_lemonade_kaggle_push (template-generated, :13305 substituted); (2) `qwen3.5:397b-cloud` → `kimi-k3:cloud` ×2, `crontab.example` → `config/crontab.example`, `scripts/fleet_lock.py` → `scripts/fleet_sentry.py` exist in no commit (3c073e53a adds kimi-k3 in a different row only). | Not committable as one unit: re-committing the amd block here would duplicate a managed block at merge; the three doc fixes are correct (targets exist at HEAD) but have no evidencing branch. When landing the doc fixes, drop the amd hunk and commit the other three on a fresh docs branch, not here. | low |
| `submissions/arc-paper-track/README.md` | Full rewrite dated "as of 2026-09-15": deadline 2026-11-09, Kaggle Writeup format, points at untracked writeup.md / cover_image.png / PAPER_TRACK_SUBMISSION.md. In no ref; every branch with the path still has the OLD README. | Deadline-bearing ARC Prize paper-track prep that only makes sense with its untracked siblings (archived above). Commit as one unit on a kaggle/arc-paper-track branch (or move to ~/cohezion-labs per the Kaggle rule). Coupled to the AGENT-SURFACES.md `submissions/**` row. | medium |
| `submissions/arc-paper-track/paper.md` | Single added first line: SUPERSEDED-by-writeup.md banner. In no ref. **Verifier note:** ollama_lemonade_kaggle_push's paper.md is a different document (150-line diff, dated 2026-08-25), not merely unbannered. | Meaningless without the README rewrite and writeup.md; keep with that unit. | low |
| `tests/knowledge_graph/test_graphrag_engine.py` | Assertion `"synapses"` → `"synapse"` + docstring. In no ref. Pairs with the UNSURE graphrag_engine.py edit; HEAD's engine still emits `<-synapses<-neurons`. | Half of a two-file fix; either half alone breaks test_hybrid_search_includes_connections. Land together with graphrag_engine.py on a fix branch. Verifier: the test's claim that the plural tables "never held rows" is false for `synapses` (570 ghost rows, all in/out = null). | medium |
| `.bash_profile` | Zero-byte bwrap placeholder, mtime 2026-10-23 07:43 (this session); untracked by 194b8a5c7. | Per bwrap-worktree-recovery rule: deleting re-bricks Bash; keep until session end, never stage. | low |
| `.bashrc` | Zero-byte bwrap placeholder. | Sandbox bind-mount placeholder; dies with the session. | low |
| `.gitconfig` | Zero-byte bwrap placeholder. | Never stage. | low |
| `.idea` | Zero-byte bwrap placeholder FILE (not dir). | Never stage. | low |
| `.profile` | Zero-byte bwrap placeholder. | Never stage. | low |
| `.ripgreprc` | Zero-byte bwrap placeholder. | Never stage. | low |
| `.vscode` | Zero-byte bwrap placeholder FILE. | Never stage. | low |
| `.zprofile` | Zero-byte bwrap placeholder. | Never stage. | low |
| `.zshrc` | Zero-byte bwrap placeholder. | Never stage. | low |

## 5. UNSURE (7)

No commands. Each row names what settles it.

| Path | Origin | Rationale / settle condition | Risk |
|---|---|---|---|
| `src/cohezion/__main__.py` | Sweep A (mtime cluster 2026-09-15 08:23:48). `-S'register_usage_consumer'` empty; no ref ever added llm_usage_consumer.py. No path commits since 42b5c6745. | Adds `await register_usage_consumer()` to the boot path, depending on the UNTRACKED `src/cohezion/inference/llm_usage_consumer.py` (100 lines, parses, zero tests). Prerequisites exist at HEAD (usage_log.record_usage, EventType.LLM_CALL/LLM_RESPONSE) and the vocabulary has no consumer today, so plausible but unverified and in the startup sequence. **Settle:** `python -m cohezion` boot smoke with the untracked module + a test; then commit both on a new fix branch off origin/main. docs/triage/2026-09-15-dirty-tree-triage.md already called this pair "real uncommitted work" five weeks ago. | medium |
| `src/cohezion/data_mesh/kanban_bridge.py` | Sweep A ("review flagged (2026-09-14)"); `-S'def _surreal_basic_auth'` empty. f1253f4a7 (origin/main) kept the hardcoded `root:root`; this branch's own a1fa550e1 ("CodeQL wave-2 hardening") ADDS three more `base64.b64encode(b"root:root")` constants elsewhere. | Replaces a hardcoded credential with SURREAL_USER/SURREAL_PASS env overrides — the CodeQL hardcoded-credentials class this branch is nominally about, yet the branch's own commit contradicts it. **Settle:** decide whether a credential-rotation tranche (memory: .env leak, ROTATE ALL) owns this plus the three a1fa550e1 sites; commit together there. | medium |
| `src/cohezion/inference/model_card_profiles.py` | Sweep B (mtime 2026-09-17). `-S'"kimi-k3:cloud": ModelProfile('` empty. wt vs e9869f425 = 114 lines. | Renames the registry KEY `qwen3.5:397b-cloud` → `kimi-k3:cloud` while keeping its 64k/8192 profile: old-key lookups KeyError and the numbers may not match kimi-k3. Live Ollama confirms the old model is gone, but fb51e91e0 ("register 20 cloud models", ollama_lemonade_kaggle_push) re-registered the roster independently. **Settle:** diff this pin set against fb51e91e0's roster and pick one source of truth for all of Sweep B. | medium |
| `src/cohezion/inference/unified_hybrid_router.py` | Sweep B. `-S'TaskClass.CODING: "kimi-k3:cloud"'` empty. Path rewritten since on port-service-wt-fixes (370-line divergence) and ollama_lemonade_kaggle_push (677-line divergence). | Four code lines: CODING pin → kimi-k3:cloud (now duplicating DEEP_REASONING, stale "397B" comment), TIER_2_ROSTER, ULTRA_FAST_DRAFT tag, sampling-options branch. Verifier: `tests/unit/test_unified_hybrid_router.py:56` (unmodified) asserts coding → `"qwen3.5:397b-cloud"`, so the retarget breaks a committed test. **Settle:** pick the branch that owns the router and re-apply the pin sweep there with the test updated. | medium |
| `src/cohezion/knowledge_graph/graphrag_engine.py` | Sweep A. `-S'<-synapse<-neuron AS incoming'` empty; no path commits since 882dd2997. Paired with tests/knowledge_graph/test_graphrag_engine.py (LEAVE). | Live vault db: `neuron` = 39,725 rows, `neurons` absent (HEAD's `FROM neurons` can never return rows), `synapse` = 9,792 vs ghost `synapses` = 570 rows all with in/out = null. Directionally right and the verifier confirms the classifier's settle condition (ghost rows are not real edges) is now met — but no branch has this signature. **Settle:** commit engine + test together on a new `fix/graphrag-singular-tables` branch off origin/main, with the test docstring corrected (the plural table did hold 570 null rows). | medium |
| `src/cohezion/rl/grpo_trainer.py` | mtime 2026-09-21; self-dated "Real implementation (2026-09-19)"; pickaxe empty; no path commits since d5d695cd3. | Replaces torch.randn log-prob placeholders with a real forward pass, but requires an injected `self._tok` that NO caller sets, so every `_compute_log_probs` call now raises RuntimeError; tests/wiring/test_grpo_trainer_wired.py does not exercise these methods. **Settle:** add tokenizer injection to the factory plus a test that fails on the old randn stub; otherwise archive. | medium |
| `src/cohezion/inference/llm_usage_consumer.py` | 2026-09-14 untracked; no commit in any branch has the path. Registered by the modified `__main__.py` (line 959). | Load-bearing dependency of the `__main__.py` edit; shares its fate: same commit if that hunk is committed, archive if dropped. Settled by the `__main__.py` row. | medium |

---

## Verifier disagreements

Ten disagreements across the four groups. Resolved where the evidence is decisive; the final verdict shown is the one used in the tables above.

| # | Path | Classifier | Verifier | Evidence | Final |
|---|---|---|---|---|---|
| 1 | `src/cohezion/persistence/genesis_persistence.py` | UNSURE — singular table is the only one in db main (43,031 rows) but contradicts 516923fe8; settle the canonical name first | ARCHIVE — the edit is wrong for the DB this module writes to and already superseded on origin/main | `SURREAL_DB = "genesis"` at line 28 (header surreal-db at 45, 62) → db main is irrelevant. Live db genesis: `journey_transition` = 0, `journey_transitions` = 33. genesis_schema.surql:29-40 defines only the plural table. 516923fe8 keeps `CREATE journey_transitions` (lines 127/217/219/231) + tests/persistence/test_genesis_persistence.py (absent here). Pickaxe empty. | **ARCHIVE** (decisive: the wt comment is false for its own target DB) |
| 2 | `src/cohezion/knowledge_graph/genesis_schema.surql` | UNSURE — contradictory counts; count both genesis tables | ARCHIVE — one-line edit internally inconsistent with the same file | Only line 202 changed to `FROM journey_transition`; lines 29-40 still DEFINE the plural table and fields. db genesis: singular 0 rows, plural 33. No ref carries the edit. | **ARCHIVE** (decisive) |
| 3 | `src/cohezion/universe/triune_engine.py` | COMMIT-TO-BRANCH fix/hidden-import-cycles — back-edge of a cycle that branch addresses | LEAVE — redundant with the branch's own fix; the branch's instrument did not flag this edge | At e75588eb4, surreal_logger.py and obsidian_mcp.py import `cohezion.universe.triune_manifold` only under `if TYPE_CHECKING:`; persistence/__init__.py imports only those two. So persistence has no runtime edge back into universe and triune_engine's eager import is on no cycle. The branch's commit changed 13 files without touching triune_engine.py; its hidden_import_cycle_scan.py (present at e75588eb4, absent at HEAD) did not flag it. | **LEAVE** (decisive on "belongs there": no; optional confirmation = run e75588eb4's scan against a tree with HEAD's triune_engine.py) |
| 4 | `src/cohezion/registry/skill_registry.json` | DISCARD — regenerable; wt keys strict subset of 8d3265bb6 | ARCHIVE — subset claim is key-level only; not regenerable from this tree | 95 of 345 shared entries differ in value from 8d3265bb6 (branch entries carry `name`); 43 of the 110 new entries cite skill files absent here but present in `git ls-tree 8d3265bb6`, so the file was generated from the branch's tree. Blob matches no commit. | **ARCHIVE** (decisive by the classifier's own lib.rs standard; low risk either way) |
| 5 | `scripts/maintenance/check_status_8001.py` | COMMIT-TO-BRANCH security/codeql-wave2 — correct ghost-table fix verified against db main/genesis | UNSURE → LEAVE — fix incomplete where the script runs | Line 18: `SurrealClient(url="ws://localhost:8001/rpc")`, no database kwarg; surreal_client.py:348-349 defaults database=`vault`, no env override. INFO FOR DB ns=cohezion db=vault: no agent_journey*; `SELECT count() FROM agent_journey` on vault → "table does not exist". db main: agent_journey = 19,430. The classifier verified against the wrong database. | **LEAVE** (decisive: committing it commits an unverified claim; settle = add `database="main"`, run, commit both) |
| 6 | `scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb` | ARCHIVE — "origin/main moved past it: 48794ef97 v8, b9d0368b5, 2aa79010b v13" | ARCHIVE stands, evidence wrong: none of those commits is on origin/main | `git merge-base --is-ancestor` → no for all three; they live on ollama_lemonade_kaggle_push / agent-179* / find_previous_kaggle_work only. origin/main's last notebook commit is e9869f425 (2026-09-12), with 0.85 but no 0.75; HEAD == fe6735b10, 438 lines behind. ricecakar in no ref. | **ARCHIVE** (unchanged; origin text corrected in the table) |
| 7 | `docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md` | ARCHIVE — not in feat/trace-goal-loop-* or any branch; no plan-registration reference | COMMIT-TO-BRANCH land/tgl-graph-20260918 (+ archive copy, branch is local-only) | Frontmatter line 5 names the branch; branch exists locally with 5 commits on 2026-09-18 from 455ffbb2a (the plan's §0 baseline) whose subjects carry the plan's R1a/R1-R3/R4-R5/P5 labels and which add the plan's prescribed files (goal_graph.py, loop_doc_mirror_check.py). Unlanded (rev-list origin/main.. = 5), no remote ref. | **COMMIT-TO-BRANCH** on a new branch cut from land/tgl-graph-20260918, plus archive copy (decisive: classifier never checked the named branch) |
| 8 | `docs/retrospectives/2026-09-11-kaggle-offensive-and-surrealdb-maximization.md` | DISCARD — "not in any git commit (so no commit to name)" | DISCARD stands; a commit CAN be named | ~/vaults/cohezion-vault is a git repo; `git -C ~/vaults/cohezion-vault log -1 -- retros/<name>` = 4a7960b84 (2026-10-13); HEAD blob 449695a72f == hash-object of the repo copy. | **DISCARD-AFTER-APPROVAL** (unchanged; provenance now commit-anchored) |
| 9 | `src/cohezion/inference/strix_halo_hybrid_router.json` | ARCHIVE — "differ from tip by 203 lines (both version 2)" | ARCHIVE stands; origin description wrong | wt is `"version": "1"`, model_name `user.StrixHalo-Cohezion-Router`; tip is version 2 with a different name; diff --stat vs tip = 156 deletions / 0 insertions; cmp differs at byte 17. | **ARCHIVE** (unchanged; origin corrected) |
| 10 | `src/cohezion/competitions/biohub_cell/cohezion-biohub-v6.ipynb` | DISCARD — byte-identical to e9be42add; "3-line diff vs a99613aaf" | DISCARD stands; delta misstated | `git diff --stat e9be42add a99613aaf -- scripts/kaggle/biohub_v6/<nb>` = 132 insertions, 1 deletion. Identity to e9be42add is what matters. | **DISCARD-AFTER-APPROVAL** (unchanged) |

Non-disagreement verifier findings folded into the tables: Sweep B src rows — `tests/unit/test_unified_hybrid_router.py:56` asserts the old id (supports UNSURE); graphrag — ghost `synapses` rows all null (settle condition met, still no home branch); other_modified — `-S'kimi-k3:cloud' -- AGENTS.md` does hit 3c073e53a but in a different row (wt replacement still in no commit); inventory row `pi/git/github.com/tmustier/pi-extensions` is `.pi/...` with status ` m`, not a deletion.

---

## Recurring patterns

1. **Sweep A — 2026-09-14 "consumption audit" cluster (22 of 31 src files share mtime 2026-09-15 08:23:48, one restore/copy event; comments self-date to 2026-09-14).** Path-limited `git log --all -S` is negative for every signature (instrument control: the same pickaxe found positives for lib.rs, recursive_learning.py, cache/semantic_cache.py). Sub-themes: docstring-only phantom-consumer corrections (LEAVE), TYPE_CHECKING cycle breaks (ARCHIVE — superseded by e75588eb4 on fix/hidden-import-cycles, 2026-09-22), live-table-name corrections (graphrag UNSURE; genesis ARCHIVE — wrong for its DB), vault-anchored output paths (LEAVE), env-overridable SurrealDB auth (UNSURE), EventBus usage-consumer wiring (UNSURE), semantic-cache flush / health-oracle synthesis / VAE checkpoint loader (ARCHIVE — all four re-done and committed in refined form on `refs/prefetch/remotes/origin/fix/port-service-wt-fixes`, 2026-10-22; `git fetch origin` materializes it). The working-tree copies are earlier drafts of what that branch holds.
2. **Sweep B — 2026-09-17 10:11:51 model-pin sed (83 files: 4 src + 79 scripts).** Verifier re-tested 5 uncited scripts and all 4 src files: every hunk is a pure substitution under the same map, 146 kimi-k3 lines added / 146 qwen3.5:397b removed, no kimi-k3 additions outside the cluster. Factually motivated (live Ollama /api/tags has kimi-k3:cloud and deepseek-v4-flash:cloud, not qwen3.5:397b-cloud) but no ref carries it, it conflicts with the landed successor map in 2421551cb, it falsifies dated attributions, and it breaks test_unified_hybrid_router.py:56. One decision for all 83: discard the 79 scripts + lint_baseline, LEAVE the 2 docstring-only src files, UNSURE the 2 code-bearing src files pending a single source of truth (fb51e91e0's roster vs 2421551cb).
3. **Pre-commit autostash timestamp 2026-09-15 08:23:48** = reflog `75283314a HEAD@{2026-09-15 08:23:48}: reset: moving to HEAD` between commits 75283314a (08:20) and dc4d672de (08:29), both HEAD ancestors. The mtime is a bound, not authorship: Sweep A's 22 files plus lint_baseline.txt, check_status_8001.py, submit_arc3_when_ready.py and stealthskater_ingest.py were all already dirty before that moment.
4. **`ollama_lemonade_kaggle_push` snapshot (19 untracked + 3 modified + 2 other_modified = 24 paths).** Byte-identical to blobs in 551651584 / 86e203558 / 2e76d79c9 / e9be42add / 86bdd9b2d / 409e043b7, several already superseded at the branch tip. That branch (antigravity worktree, 203 commits ahead of origin/main, unmerged, also on remotes/origin) is the durable home; the main checkout received stale copies. Verifier re-tested 9 uncited untracked files — none on the branch tip — so the pattern is correctly scoped. Couplings are real: recursive_learning.py ↔ recuris_memory/harness_protocol/hippocam_memory; admission_gate.py ↔ aperture_guard.py; lib.rs ↔ vmodel_verifier.rs. Order of operations: archive the modified half, restore HEAD, then remove the untracked half.
5. **origin/main copies pasted into a behind branch (2 files: surrealdb_sync.py, arc3 notebook).** HEAD is 24 ahead of stale local main but merge-base with origin/main is 347909e51; both files vanish on rebase/merge. Verifier re-tested all 119 uncited src/scripts paths: 0 match origin/main or the ollama tip, so this is confined to the cited files.
6. **Generated artifacts and formatter noise (10 paths).** Timestamp stamps (skill_{0,1}_agent.py, health_log.json), regenerable registries (skills/skill_registry.json), ruff line-length-100 reformat leaking into a vendored nested repo (pi-extensions), generator-vs-formatter oscillation (generated_test_dummy.py), ruff_ratchet baseline (lint_baseline.txt), marimo cache, daemon graph exports (.obsidian/), run log (analysis_output.txt). Verifier re-tested the formatter pattern on 5 uncited src files: all are real content edits, not formatter noise.
7. **Wrong-repo scratch (GEMS 20 paths, Kaggle 11+ paths, learn/ tutorials, incident notes).** Per `~/.claude/rules/kaggle-portfolio.md` Kaggle work belongs in ~/cohezion-labs; GEMS home is ~/dev/drivendata/gems; incident records belong in the vault. Blob-existence probe over all 144 individual files confirms none of these is secretly in history.
8. **Half-units that must land together (3 clusters).** ARC paper-track session 2026-09-15 (README rewrite + paper.md banner + untracked writeup/cover/kit + AGENT-SURFACES.md `submissions/**` row); graphrag singular tables (engine + test); EventBus usage consumer (`__main__.py` + llm_usage_consumer.py).
9. **Zero-byte accidents and sandbox placeholders (13 paths).** 4 unquoted shell redirects (`--nets`, `=2026.2.0`, `**2026-10-15`, a Python fragment) and 9 bwrap bind-mount placeholders created 2026-10-23 07:43 by this session (must survive until session end).

---

## Approval blocks

Conventions: run from `/home/mike-anderson/dev/cohezion`; `ARCH=archives/2026-10-23-main-checkout-reconcile`; every git command below either reads state, creates a new ref, or adds a child commit — none rewrites shared history, none pushes. Blocks are ordered; **B must run before C3**, and **C3 before C2** for the coupled pairs. Before any block: `git status --porcelain | wc -l` should read 220-ish and `git rev-parse --short HEAD` must print `d3cb21249`.

### Block A — COMMIT-TO-BRANCH (3 paths, two sub-blocks; approve each with one yes)

**A1 — `security/codeql-wave2` additions (2 files), on a new branch cut from the current HEAD so the shared branch tip is untouched:**

```bash
cd /home/mike-anderson/dev/cohezion
git switch -c reconcile/codeql-wave2-additions security/codeql-wave2   # new branch at d3cb21249; working tree untouched
git add -- scripts/stealthskater_ingest.py
git commit -m "fix(scripts): sanitize SurrealDB record ids in stealthskater ingest and write to the live neuron table" \
  -m "Backtick-quoted record ids built from external wiki page names are now normalised through sanitize_record_id(); the ingest targets the live \`neuron\` table in db vault (the plural \`neurons\` does not exist). Caught by multi-perspective review 2026-09-14."
git add -- AGENT-SURFACES.md
git commit -m "feat(ci): own submissions/** and src/cohezion/competitions/** in the agent write-surface map" \
  -m "scripts/ci/check_agent_surfaces.py exits 1 (UNOWNED) for submissions/arc-paper-track/README.md and src/cohezion/competitions/arc/advanced_grid_reasoner.py against HEAD's map; these two additive rows close the gap so the fail-closed checker in .github/workflows/agent-surfaces.yml passes for changes under those trees."
git switch security/codeql-wave2   # return; the two files are now clean here too? NO — they are committed on reconcile/*, so they show as modified again on this branch. See note.
```

Note on the last line: do **not** switch back. Stay on `reconcile/codeql-wave2-additions` for the remainder of the blocks (it is at the same commit plus two, so every other path's classification is unchanged), or skip the final `git switch` entirely. Landing: open a PR from `reconcile/codeql-wave2-additions` into `security/codeql-wave2` (or straight to main after the branch's own landing) through the normal gates.

**A2 — trace-goal-loop plan onto a new branch cut from `land/tgl-graph-20260918`, without checking that branch out (plumbing only; the working tree and current branch are not touched):**

```bash
cd /home/mike-anderson/dev/cohezion
ARCH=archives/2026-10-23-main-checkout-reconcile
P=docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md
mkdir -p "$ARCH/docs/plans" && cp -- "$P" "$ARCH/$P"            # archive copy (branch is local-only)
BASE=$(git rev-parse land/tgl-graph-20260918)
BLOB=$(git hash-object -w -- "$P")
TREE=$( export GIT_INDEX_FILE="$(mktemp)"; git read-tree "$BASE" >/dev/null; \
        git update-index --add --cacheinfo "100644,$BLOB,$P" && git write-tree; rm -f "$GIT_INDEX_FILE" )
COMMIT=$(git commit-tree "$TREE" -p "$BASE" -m "docs(plans): register the trace -> goal -> loop graph consolidation plan" \
          -m "Plan frontmatter names this branch ('landed as land/tgl-graph-20260918'); the branch's five 2026-09-18 commits (R1a, R1-R3, R4/R5, P5) implement it from the plan's §0 baseline 455ffbb2a.")
git update-ref refs/heads/reconcile/tgl-graph-plan "$COMMIT" 0000000000000000000000000000000000000000   # create only; fails if the ref already exists
git log --oneline -1 reconcile/tgl-graph-plan && git ls-tree reconcile/tgl-graph-plan -- "$P"
```

After A2 the untracked plan file is still in the working tree; it is removed by C2 (its bytes are now in both the archive and the new branch).

### Block B — ARCHIVE (67 paths; one yes)

Tracked files (15) are **copied** with a patch; untracked paths (52) are **moved**. Nothing here calls `git checkout` — the HEAD-restore of the 15 tracked files is C3.

```bash
cd /home/mike-anderson/dev/cohezion
ARCH=archives/2026-10-23-main-checkout-reconcile
mkdir -p "$ARCH"
printf '%s\n' "$ARCH/" >> .git/info/exclude   # keep the archive out of git status without editing tracked .gitignore (optional)

# B1 — tracked ARCHIVE rows: copy working copy + save the diff (15 files)
while IFS= read -r p; do
  mkdir -p "$ARCH/$(dirname "$p")"
  cp -- "$p" "$ARCH/$p"
  git diff HEAD -- "$p" > "$ARCH/$p.patch"
done <<'EOF'
src/cohezion-physics-core/src/lib.rs
src/cohezion/agi/recursive_learning.py
src/cohezion/cache/semantic_cache.py
src/cohezion/compound/compound_health_oracle.py
src/cohezion/flume/vae_encoder.py
src/cohezion/knowledge_graph/KEY_LEARNINGS.md
src/cohezion/knowledge_graph/genesis_schema.surql
src/cohezion/persistence/genesis_persistence.py
src/cohezion/persistence/obsidian_mcp.py
src/cohezion/persistence/surreal_logger.py
src/cohezion/registry/skill_registry.json
src/cohezion/reliability/semantic_cache.py
scripts/ops/submit_arc3_when_ready.py
scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb
scripts/kaggle/rsna_sota_ensemble/kernel-metadata.json
EOF

# B2 — untracked ARCHIVE rows: move (52 paths; directories move whole)
while IFS= read -r p; do
  mkdir -p "$ARCH/$(dirname "$p")"
  mv -- "$p" "$ARCH/$p"
done <<'EOF'
.claude/rules/codegraph.md
.kaggle_arc3_work
acf_analysis.py
arc3_macro_action_compiler.py
atwater_response.json
dem_fault_features.json
docs/audits/PROMPT_AUDIT_2026-10-06.diff
docs/audits/PROMPT_AUDIT_2026-10-06.md
docs/build_explainer.py
docs/cohezion_flume_explainer.html
docs/cohezion_flume_notebook.py
docs/decode_explainer.py
docs/extract_explainer.py
docs/inspect_nb.py
docs/triage
event_bus.json
features_detailed.py
features_final.py
features_vectorized.py
gems_band_analysis.py
gems_dem_strategy.json
gems_dw_tversky_strategies.json
gems_method_research.json
gems_pipeline_research.json
gems_research findings.json
gems_research_findings.json
gems_winning_strategy.md
hermes-cron-rootcause-2026-09-17.md
isacks_gems_response.json
learn
ml-competition-submission
scripts/hotswap_model.sh
scripts/kaggle/agent_security_kernel/make_paper_track_cover.py
scripts/kaggle/arc2_v6_tta24_kernel
scripts/kaggle/arc2_v8_synth_lora_kernel
scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent-v19.ipynb
scripts/kaggle/kaggriculture_smoke_v5.py
scripts/kaggle/rsna_efficiency_fast
scripts/kaggle/rsna_sota_ensemble/monitor_all_inflight.py
scripts/model_hotswap_router.py
src/cohezion/agi/info_density.py
src/cohezion/competitions/biohub_cell/V6_LINEAGE.md
src/cohezion/competitions/biohub_cell/kernel-metadata-v6.json
src/cohezion/inference/strix_halo_hybrid_router.json
src/cohezion/inference/task_router.py
submissions/arc-paper-track/PAPER_TRACK_SUBMISSION.md
submissions/arc-paper-track/cover_image.png
submissions/arc-paper-track/writeup.md
submissions/kaggriculture
sykes_response.json
tests/unit/test_info_density.py
tharp_response.json
EOF
find "$ARCH" -type f | wc -l   # expect 15 copies + 15 patches + the untracked file count (+1 plan copy from A2)
```

Follow-ups outside this plan (no approval needed here, noted for routing): the Kaggle subset of the archive can be relocated to `~/cohezion-labs/`, the GEMS subset to `~/dev/drivendata/gems/`, and `docs/triage/`, `hermes-cron-rootcause-*.md`, `event_bus.json` to `~/vaults/cohezion-vault/reports/`.

### Block C — DISCARD-AFTER-APPROVAL (120 paths) — **destructive, needs explicit yes**

Each sub-block is its own yes. C1 and C3 use `git checkout --` (the only block that does); C2 uses `rm`. Nothing is recoverable from the working tree afterwards — but every C1/C3 path's HEAD content is by definition in git, every C2 path's bytes are in a named commit (or are empty), and B has already archived the coupled modified halves.

**C1 — tracked DISCARD rows (93 paths: 4 src + 83 scripts + 6 other). Restores HEAD's blob for each:**

```bash
cd /home/mike-anderson/dev/cohezion
git checkout -- \
  src/cohezion/agents/generated/skill_0_agent.py \
  src/cohezion/agents/generated/skill_1_agent.py \
  src/cohezion/knowledge_graph/health_log.json \
  src/cohezion/skills/skill_registry.json \
  scripts/ci/lint_baseline.txt \
  scripts/adversarial_review_oscillation.py \
  scripts/capella_probe.py \
  scripts/datamesh_land_scanner.py \
  scripts/experiments/bleeding_edge_research_sprint.py \
  scripts/ops/arc3_adversarial_fleet_review.py \
  scripts/ops/audit_and_patch_thinking_timeouts.py \
  scripts/ops/audit_competition_metadata_leverage.py \
  scripts/ops/audit_ml_acceleration_opportunities.py \
  scripts/ops/autonomous_evolution_supervisor.py \
  scripts/ops/benchmark_model_harness_affinity_matrix.py \
  scripts/ops/benchmark_ollama_cloud_models.py \
  scripts/ops/cloud_adversarial_bughunt.py \
  scripts/ops/cloud_multiperspective_review.py \
  scripts/ops/consult_all_ollama_cloud_models.py \
  scripts/ops/consult_cloud_bleeding_edge_improvements.py \
  scripts/ops/consult_cloud_competition_architectures.py \
  scripts/ops/consult_cloud_defect_class.py \
  scripts/ops/consult_fresh_cloud_models.py \
  scripts/ops/consult_kaggle_next_breakthroughs.py \
  scripts/ops/consult_matsumoto_enc_audit.py \
  scripts/ops/consult_ollama_cloud_and_local_bleeding_edge.py \
  scripts/ops/consult_ollama_cloud_bleeding_edge_advisors.py \
  scripts/ops/consult_ollama_cloud_deep_exploration.py \
  scripts/ops/consult_ollama_cloud_fix.py \
  scripts/ops/consult_ollama_cloud_grand_advisors.py \
  scripts/ops/consult_ollama_cloud_kanban_crm.py \
  scripts/ops/consult_ollama_cloud_on_nous_research.py \
  scripts/ops/consult_ollama_cloud_targeted_audits.py \
  scripts/ops/consult_ollama_cloud_thinking_models.py \
  scripts/ops/day1_arc_ttc_scaling_engine.py \
  scripts/ops/debug_qwen_arc_task.py \
  scripts/ops/debug_qwen_full_print.py \
  scripts/ops/debug_qwen_raw.py \
  scripts/ops/debug_qwen_thinking.py \
  scripts/ops/deep_dive_dogfood.py \
  scripts/ops/dird_37_matrix_synthesis.py \
  scripts/ops/direct_cloud_bughunt.py \
  scripts/ops/dual_fleet_multiperspective_review.py \
  scripts/ops/enrich_daemons_with_cloud.py \
  scripts/ops/execute_overnight_bbq_worker.py \
  scripts/ops/execute_pipeline_sprint_sequence.py \
  scripts/ops/execute_thenoise_iterative_evolution.py \
  scripts/ops/finalize_fanout_report.py \
  scripts/ops/gaia_cloud_adversarial_review.py \
  scripts/ops/grand_13_model_cloud_adversarial_review.py \
  scripts/ops/grand_breadth_depth_fanout_sprint.py \
  scripts/ops/grand_multiperspective_adversarial_deep_review.py \
  scripts/ops/grand_multiperspective_shoulders_matsumoto_review.py \
  scripts/ops/grand_unified_tri_silicon_cloud_audit.py \
  scripts/ops/local_multiperspective_research_reviewer.py \
  scripts/ops/master_hybrid_fleet_optimizer.py \
  scripts/ops/master_matrix_parallel_explorer.py \
  scripts/ops/master_tri_delegate_adversarial_review.py \
  scripts/ops/multi_cloud_swarm_matrix_sprint.py \
  scripts/ops/multi_model_micrograph_comparison.py \
  scripts/ops/multiperspective_cloud_adversarial_review.py \
  scripts/ops/multiperspective_code_review.py \
  scripts/ops/multiperspective_diff_review.py \
  scripts/ops/multiperspective_gaia_orchestrator.py \
  scripts/ops/ollama_cloud_adversarial_frontier_review.py \
  scripts/ops/ollama_cloud_adversarial_review.py \
  scripts/ops/ollama_cloud_multiperspective_adversarial_review.py \
  scripts/ops/prove_anytime_compute_maximization.py \
  scripts/ops/prove_ollama_cloud_fleet.py \
  scripts/ops/query_cloud_reviewers_clean.py \
  scripts/ops/query_qwen397b_direct.py \
  scripts/ops/refactor_codebase_for_simplicity.py \
  scripts/ops/remediate_adversarial_gaps_hybrid.py \
  scripts/ops/research_arxiv_2606_12683_agi_asi.py \
  scripts/ops/research_bleeding_edge_silicon_strategies.py \
  scripts/ops/research_terminal_mermaid_graphics.py \
  scripts/ops/silicon_model_optimization_research.py \
  scripts/ops/solve_with_qwen397b_thinking.py \
  scripts/ops/test_frontier_cloud_coder_on_arc.py \
  scripts/ops/test_qwen397b_arc.py \
  scripts/ops/verify_and_validate_with_ollama_cloud.py \
  scripts/ops/verify_dsh_deepseek_harness_integration.py \
  scripts/ops/verify_dual_substrate_proof.py \
  scripts/ops/verify_ollama_cloud_datamesh_inference.py \
  scripts/ops/verify_ollama_cloud_live_execution.py \
  scripts/ops/verify_qwen_code_datamesh_integration.py \
  scripts/ops/verify_true_multimodal_vision_feedback_loop.py \
  cloud-vault-mcp/src/mcp_server/surrealdb_sync.py \
  scripts/kaggle/arc3_autoharness_kernel/arc-agi-3-autoharness-agent.ipynb \
  src/cohezion/platform/admission_gate.py \
  src/cohezion/skills/AUTOHARNESS_PRIME.md \
  tests/mycelium/generated_test_dummy.py
# the nested vendored repo (parent gitlink unchanged; restore inside it):
git -C .pi/git/github.com/tmustier/pi-extensions checkout -- extending-pi/skill-creator/scripts/validate_skill.py
```

Then regenerate what the sweep was trying to do, on a proper branch: `git switch -c chore/model-pin-successors origin/main` and apply the 2421551cb successor map (`qwen3.5:397b-cloud` → `kimi-k2.7-code:cloud`, `deepseek-v4-flash:0731-cloud` → `deepseek-v4.1-flash:cloud`) — out of scope for this plan.

**C3 — restore HEAD for the 15 tracked ARCHIVE rows (run only after Block B has copied them):**

```bash
cd /home/mike-anderson/dev/cohezion
test -f archives/2026-10-23-main-checkout-reconcile/src/cohezion-physics-core/src/lib.rs.patch || { echo "run Block B first"; exit 1; }
git checkout -- \
  src/cohezion-physics-core/src/lib.rs \
  src/cohezion/agi/recursive_learning.py \
  src/cohezion/cache/semantic_cache.py \
  src/cohezion/compound/compound_health_oracle.py \
  src/cohezion/flume/vae_encoder.py \
  src/cohezion/knowledge_graph/KEY_LEARNINGS.md \
  src/cohezion/knowledge_graph/genesis_schema.surql \
  src/cohezion/persistence/genesis_persistence.py \
  src/cohezion/persistence/obsidian_mcp.py \
  src/cohezion/persistence/surreal_logger.py \
  src/cohezion/registry/skill_registry.json \
  src/cohezion/reliability/semantic_cache.py \
  scripts/ops/submit_arc3_when_ready.py \
  scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb \
  scripts/kaggle/rsna_sota_ensemble/kernel-metadata.json
```

**C2 — untracked DISCARD rows (27 paths; `rm`, run after C1 and C3 so the coupled imports are already gone from the tree) plus the plan file now held by A2:**

```bash
cd /home/mike-anderson/dev/cohezion
# zero-byte shell accidents (names start with '-', '*' or '=' — always pass './' or '--')
find . -maxdepth 1 -type f -size 0 \( -name ')*' -o -name '**2026-10-15' -o -name '--nets' -o -name '=2026.2.0' \) -print   # review the 4 names first
find . -maxdepth 1 -type f -size 0 \( -name ')*' -o -name '**2026-10-15' -o -name '--nets' -o -name '=2026.2.0' \) -delete
# generated / already-in-history
rm -r -- .obsidian docs/__marimo__ scripts/kaggle/name_that_llm src/cohezion/gaia src/cohezion/kaggle
rm -- \
  analysis_output.txt \
  anatomical_copula_coupling.py \
  docs/retrospectives/2026-09-11-kaggle-offensive-and-surrealdb-maximization.md \
  scripts/jobs/storage_headroom_guard.sh \
  scripts/ops/master_longhorizon_goals_recursive_learning_refactor.py \
  scripts/ops/vmodel_compound_trace_refactor.py \
  src/cohezion-physics-core/src/vmodel_verifier.rs \
  src/cohezion/agi/recuris_memory.py \
  src/cohezion/competitions/biohub_cell/cohezion-biohub-v6.ipynb \
  src/cohezion/compound/harness_protocol.py \
  src/cohezion/compound/vmodel_compound_graph_system.py \
  src/cohezion/inference/aperture_guard.py \
  src/cohezion/knowledge_graph/hippocam_memory.py \
  src/cohezion/skills/AMD_GAIA_ORCHESTRATION_PRIME.md \
  src/cohezion/skills/KAGGLE_GRANDMASTER_ASCENT_PRIME.md \
  src/cohezion/skills/SURREALDB_DATAMESH_PRIME.md \
  tests/unit/test_longhorizon_goals_recursive_learning.py \
  tests/unit/test_recuris_hippocam_hcp.py
rmdir docs/retrospectives 2>/dev/null || true
# A2 artefact (bytes now on reconcile/tgl-graph-plan and in the archive)
test -s archives/2026-10-23-main-checkout-reconcile/docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md && rm -- docs/plans/2026-09-18-trace-goal-loop-graph-consolidation.md
```

### Block D — LEAVE (23 paths)

No commands. After A–C the remaining `git status` noise should be exactly: 9 Sweep-A/B docstring-or-path src files, check_status_8001.py, AGENTS.md, the two paper-track files, test_graphrag_engine.py, and the 9 zero-byte dotfiles (which must not be deleted while any Claude Code session is open here).

### Block E — UNSURE (7 paths)

No commands. Settle conditions are in table 5; each resolves into a new `fix/*` branch off origin/main (usage consumer; graphrag singular tables + test; GRPO tokenizer injection), a credential tranche (kanban_bridge + the three a1fa550e1 sites), or the Sweep-B source-of-truth decision (model_card_profiles + unified_hybrid_router + their test).

### Expected end state (verification, read-only)

```bash
git status --porcelain | grep -v '^?? \.\(bash_profile\|bashrc\|gitconfig\|idea\|profile\|ripgreprc\|vscode\|zprofile\|zshrc\)$' | wc -l   # expect 21 (14 LEAVE tracked/other + 7 UNSURE), of which 1 is untracked (llm_usage_consumer.py)
git log --oneline -2 reconcile/codeql-wave2-additions; git log --oneline -1 reconcile/tgl-graph-plan
find archives/2026-10-23-main-checkout-reconcile -type f | wc -l
```

---

## Root cause

Sessions worked directly in the shared main checkout because desktop worktree creation is broken on Claude Code 2.1.293 (see `~/.claude/rules/bwrap-worktree-recovery.md` and memory `claude-w-broken-on-2-1-276-git-dir-sentinel`): every session that could not get an isolated worktree landed its edits, Kaggle kernels, GEMS scratch and branch snapshots in `/home/mike-anderson/dev/cohezion`, on whatever branch happened to be checked out (`security/codeql-wave2` since September). `docs/audits/COHERENCE_AUDIT_2026-10-22.md` **F6 — Branch and worktree debt** on branch `chore/portfolio-coherence` measured the symptom a day earlier ("The main checkout itself sits on `security/codeql-wave2`, 21 commits ahead and 56 behind main, with 131 modified files, 9 tracked dotfiles showing as deleted … and 687 untracked files. A reviewer who clones sees none of this, but every agent session that starts here does.") and proposed the hygiene steps (prune merged locals and worktrees, restore dotfiles); this plan is the per-path reconciliation F6 left implicit. The 9 zero-byte dotfiles in the LEAVE table are the same bwrap defect's placeholders, created by this session, and are the reason F6 saw "tracked dotfiles showing as deleted" on 2026-10-22.

## Done when

All 220 paths have been acted on per their block (A committed on two `reconcile/*` branches, B archived under `archives/2026-10-23-main-checkout-reconcile/`, C restored/removed after an explicit yes, D untouched, E resolved on their own branches), and `git status` in the main checkout shows only the 23 LEAVE paths plus the 7 UNSURE paths until those are settled.

## Count check

| Verdict | src_modified | scripts_modified | other_modified | untracked | Total |
|---|---|---|---|---|---|
| COMMIT-TO-BRANCH | 0 | 1 | 1 | 1 | **3** |
| ARCHIVE | 12 | 3 | 0 | 52 | **67** |
| DISCARD-AFTER-APPROVAL | 4 | 83 | 6 | 27 | **120** |
| LEAVE | 9 | 1 | 4 | 9 | **23** |
| UNSURE | 6 | 0 | 0 | 1 | **7** |
| **Group total** | **31** | **88** | **11** | **90** | **220** |

Modified tracked: 31 + 88 + 11 = 130 (matches the inventory's 130; the inventory's "1 deleted in the worktree" is the mislabelled `.pi/git/github.com/tmustier/pi-extensions` nested-repo row, counted here under other_modified DISCARD; the "5 whose content already exists in other commits" are surrealdb_sync.py, the arc3 notebook, admission_gate.py, AUTOHARNESS_PRIME.md and generated_test_dummy.py, all in table 3c). Untracked: 90 (matches). Each path appears in exactly one table: 3 + 67 + 120 + 23 + 7 = 220.
