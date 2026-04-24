---
title: "Cohezion Vault Decisions — Distillate (Top 20)"
date: 2026-04-23
campaign: synthetic-sniffing-panda Ω7
distillator: bmad-distillator
compression_target: lossless
source_file_count: 20
total_source_lines: 10672
distilled_lines: 1679
compression_ratio: 6.36:1
---

# Vault Decisions Distillate

## Reading guide

This distillate is reconstruction-faithful: any reader (human or LLM) can use it instead of loading the 20 source docs into context. Each entry preserves identity, options, decision, rationale, trade-offs, and reversal cost. Source paths cited per entry; full prose reachable via Source links.

Method: lossless compression. Strip filler prose; preserve every concrete number, file path, schema definition, function signature, named entity, decision criterion. Bullet lists replace paragraphs. Code excerpts retained only where exact text is load-bearing (schemas, function signatures, hard-to-reconstruct algorithms).

## Index

1. **/dev Brownfield Overhaul** — Reorganize 210GB /dev tree into Anthropic-Universes-ready portfolio with non-destructive moves, multi-agent coordination, and 6 phases (Class A/B/C concurrency).
2. **12D Graph + SurrealDB Integration** — Build custom Obsidian plugin for 12-dimensional knowledge graph backed by SurrealDB; rejects 3D plugins / RDBMS / file-JSON alternatives.
3. **Log Mining Adversarial Review** — Reject original 647-session log mining plan after finding 7 critical flaws; pivot to 98-session pilot with manual labeling.
4. **Compound Engineering Meta-Learning Expansion** — Turn one-shot log mining into continuous feedback loop with 4-tool MCP suite, weekly cron, COHESION integration; 12-month roadmap.
5. **Phase 4 Retrospective + Phase 5-7 Overnight Plan** — Phase 4 finished 47% under estimate via "Implementation First"; commit to 5-agent overnight Phase 5-7 build of decision intelligence layer.
6. **Phase 2 Final Completion Summary** — All 3 tracks (SurrealDB schema, Entire.io daemon, Lessons linking) delivered in 12h vs 20-22h estimate, 142/142 tests passing.
7. **Model Wrangler Strategy** — Daily-driver specialist role for proactive local-LLM monitoring, same-day benchmarking, aggressive 24h swap cycles, monthly fine-tuning.
8. **12D Graph Refined Plan (Specialist-Driven)** — Refine 12D graph plan around 7 named specialists with explicit responsibilities; surpass InfraNodus on 6 axes.
9. **Ollama MCP Server** — Build dedicated MCP server for Ollama model management instead of duplicating logic across scripts.
10. **MCP Infrastructure Architecture** — Two-server topology (Cloud Vault MCP HTTP:8360 with 30 tools + Ollama MCP stdio with 5 tools) brokering Claude Code → Vault/SurrealDB/Ollama/Sheets.
11. **Framework-Driven Prioritization** — Apply ROI/meta-concepts framework to rank 8 pending initiatives; Sheets Pipeline Phase 3 wins on 365x annual ROI.
12. **Autonomous Context Hooks Guide** — Two-phase pre/post hooks load relevant vault notes before AI agents respond and save results back, across Claude Code, OpenCode, Gemini CLI.
13. **Claude Log Mining Architecture** — Original 4-phase plan to mine 299MB of Claude logs (647 prompts) for patterns / antipatterns / alignment metrics. Superseded by adversarial review (#3).
14. **Canvas-Driven Compound Engineering** — Use Obsidian Canvas as cognitive amplifier for top-down knowledge linking; 6-phase plan replacing bottom-up algorithmic matching.
15. **Phase 2 Wave 2 Execution Strategy** — Deploy codification framework (PRIME skill + CLAUDE.md) to accelerate Track B kickoff; 4-stream parallel execution.
16. **Token-Efficient Compound Engineering Roadmap** — One-month roadmap (4 phases) systematizing canvas-driven manual linking pattern across vault enrichment.
17. **Phase 6C Semantic Contradiction Detection** — Implement Ollama-embedding-based contradiction detection between 88 decisions × 44 lessons; 10x faster than performance targets.
18. **Phase 2 Schema Design (Agent Reasoning + Cascades)** — Add `agent_reasoning` node type plus `CHALLENGES_LESSON` and `RELATES_TO_DECISION` edge types to capture WHY behind decisions.
19. **Phase 2 Completion Approved for Production** — Formal sign-off authorizing immediate production deployment of Phase 2 (3 tracks, 142/142 tests, $0 cost, 1.5h deployment window).
20. **Obsidian Best Practices for AI Agents** — Synthesized AI-agent conventions for Obsidian: atomic notes, bidirectional linking, frontmatter standards, query patterns, anti-patterns.

---

## Decisions

### 1. /dev Brownfield Overhaul — Anthropic Universes Role

- **Date**: 2026-04-17
- **Status**: PENDING (approval deferred at time of doc)
- **Owner**: Claude Code session pid-320136 (worktree dynamic-prancing-cookie)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/decisions/2026-04-17-dev-brownfield-overhaul-plan.md`

**Context**

Goal: rework `/home/mike-anderson/dev/` (210 GB, 30 top-level entries) so an Anthropic reviewer for "Research Engineer, Universes" ($500K–$850K, agentic training environments + RL + sandboxing + ML infra) can walk it top-down in 60 seconds. Cohezion (99 GB flagship) has world-class work but lives on `isolated/session-oom-modularity` with 180 root-level markdowns, no LICENSE, dirty tree. 97 GB of duplicate Cohezion variants clutter the root. Portfolio-worthy work sits next to stray artifacts and external forks. Zero data loss required; every "removal" is a `mv` into a manifested archive with documented restore commands.

**Options considered**

- Archive location:
  - `~/cohezion-archives/` — cross-directory; rejected for confusion.
  - "leave in place" — fails 60s review test; rejected.
  - **(chosen)** `~/dev/.archive/` — same-disk atomic `mv`, sits next to manifest, one-command reversible.
- LICENSE: **Apache 2.0 (chosen)** — matches Anthropic's own OSS convention (anthropic-cookbook, anthropic-tools); explicit patent grant matters for physics/ML codebase.
- Cohezion depth:
  - "Surface tidy" only — minimal but lowest ceiling; rejected.
  - "Deep restructure with branch surgery" — high risk, executes branch ops; rejected.
  - **(chosen)** "Organize + propose branch strategy" — highest ceiling, zero added risk; staged commits respect git-operations.md (no push); branch strategy is a written proposal user executes manually.

**Decision**: chose `~/dev/.archive/` + Apache 2.0 + organize-and-propose. Execute as 6 phases (0..5) tagged by concurrency class A/B/C.

**Rationale**

- Reviewer-first framing: a 60-second top-down read is the test that matters; everything else (history preservation, branch hygiene) serves that.
- Same-disk `mv` is atomic and reversible; copy-then-delete is not. `.archive/` adjacent to `MANIFEST.md` + `RESTORE.sh` keeps reversibility one command away.
- Apache 2.0 is the lowest-friction OSS license that matches the prospective employer's own conventions; MIT lacks the explicit patent grant.
- "Organize + propose" maximizes upside with zero downside: staging commits is allowed by git-operations.md; pushing is not. User retains full discretion on branch strategy.

**Concurrency model: 3 active writers + 3 op classes**

| Class | Examples | Safe under concurrency? | Quiet window? |
|---|---|---|---|
| A. Always-safe (additive) | New files at non-existent paths (`/dev/README.md`, `LICENSE`, MANIFEST.md, RESTORE.sh, sidecars) | Yes | None |
| B. Top-level relocation (`mv`) | `mv` of top-level `/dev/*` into `.archive/` or `forks/` | Only if `lsof` empty + no CWD inside + no service config inside | Light user confirmation |
| C. Cohezion-internal mutation | `git mv` of root MDs in cohezion/, edit `.gitignore`, stage commits | NO during concurrent Gemini/other-Claude writes | Strict — pause Gemini + other Claude + autoresearch |

Active writers at planning time: this Claude session (pid 210583); Gemini CLI (node pid 13848 + 6 helpers, CWD `/dev/cohezion`); apparent second Claude session (10 bash+node PIDs); Lemonade-backed agents (`lemond` 208327, `llama-server` 208510 serving DeepSeek-R1-Qwen3-8B on :8002); osv-scanner (read-only); long-running services (uvicorn, overture-proxy.mjs, surreal :8001, ollama).

Coordination: write `/home/mike-anderson/dev/.OVERHAUL_COORDINATION.md` per phase (visible declaration, not kernel-enforced). Convention-based; Class A safe regardless, Class B uses `lsof` preflight, Class C gated on explicit user confirmation.

**AGENT_STATUS.md design (persistent multi-agent register)**

Complementary to COORDINATION.md (overhaul-only, transient): `cohezion/AGENT_STATUS.md` is a rolling register of every active agent across time, enforced by harness hooks. To avoid corruption from many writers on one MD, each agent writes only its own `cohezion/.agent-status.d/<session-id>.json` (atomic single-writer); aggregator script reads all JSONs and renders the MD in one pass. Schema fields: `agent`, `session_id`, `pid`, `cwd`, `model`, `started_at`, `last_update`, `status`, `intent`, `todos`, `last_tool_call`, `paths_exclusive`, `handoff_notes`. Hooks: SessionStart→start, UserPromptSubmit→prompt (preserve intent unless goal-setting), PostToolUse→tool (rate-limited 1/10s), Stop/SessionEnd→end. Conditional execution: only fire when CWD's `git rev-parse --show-toplevel` resolves to cohezion or its worktrees. Gemini/Lemonade discoverable via `ps -ef` passive scan. Aggregator runs <100ms, idempotent, atomic write (.tmp+mv). Prune: `last_update`>24h && not active → archive; >1h && active → flag stale. .gitignore: live MD + `.agent-status.d/`, but commit `AGENT_STATUS.README.md` + `.gitkeep` + scripts in `tools/agent-status/`.

**Phases**

- **Phase 0 (Class A, ~10 min)**: Write `COORDINATION.md` + `.archive/preflight.sh` (helper printing `lsof +D`, `ps -ef` CWD scan, git lock status, Lemonade/Ollama agent activity, GREEN/YELLOW/RED verdict). No existing files touched.
- **Phase 1 (Class A, ~20 min)**: Scaffold chassis. New files: `/dev/README.md` (4 sections: Flagship/Portfolio/Forks/Archive, each project gets 2-line desc + "why for Universes" tag); `.archive/` + `MANIFEST.md` + `RESTORE.sh`; `forks/README.md`; `/dev/.claude/CLAUDE.md` (workspace SOP); `cohezion/AGENT_STATUS.README.md` + `.agent-status.d/.gitkeep` + `tools/agent-status/{render_agent_status,agent-status-update}.sh`.
- **Phase 1b (Class A, ~25 min)**: Claude Code config optimization. Sub-phases: 1b.1 snapshot settings.json (.bak), 1b.2 `/release-notes-audit` → `optimization-proposal-<date>.md` (Low=batch apply, Medium=per-item, High=report only — respects `check-settings-size.sh` gate), 1b.3 `/insights` or `Skill('fewer-permission-prompts')` → top-N read-only allowlist proposal, 1b.4 hook audit (4 hooks for AGENT_STATUS + audit 13 existing scripts: check-settings-size, format-on-edit, on-permission-denied, post-bash-cleanup, post-compact-context, pre-bash-check, protect-files, repo-health-check, validate-agent-files, version-watch, warn-sensitive-commands), 1b.5 apply via `Skill('update-config')` with change-log.md, 1b.6 propagate summary to `/dev/.claude/CLAUDE.md`.
- **Phase 2 (Class B, ~15 min)**: Run `preflight.sh` per target. 2a: 5 orphaned worktree dirs → `.archive/cohezion-orphan-worktrees/{gemma4,session-56,session-57,spec-fix-technical-debt,worktree-registry}` (history is in cohezion/.git/, safe to mv). 2b: stale clones → `.archive/cohezion-standalone-clones/{cohezion-archive-stale-main,cohezion-backup-bare-20260407}` — manifest **flags bare-repo backup as containing unique commits on `feature/2026-tip-of-the-spear`, DO NOT prune**. 2c: 9 stray dirs → `.archive/stray/`. 2d: 5 upstream-only forks (A2UI, amrvac, WarpX, cs249r_book, CAID) → `forks/`. Final top level: 11 entries (down from 30).
- **Phase 3 (Class A, ~20 min)**: Add `UNIVERSES_RELEVANCE.md` sidecar to autoresearch-amd, geak, reference-kernels, aimo-progress-prize-3, le-wm; `CONTRIBUTIONS_FROM_THIS_FORK.md` to aiter (may be empty). observer-patch-holography flagged in `/dev/README.md` only. Revised from "append to README" to "new sidecar" to stay Class A.
- **Phase 4 (Class C, ~60-90 min)**: STRICT preflight (Gemini paused, other Claude paused, autoresearch stopped, services may stay). Capture `git status --short` baseline; halt if drifts. 4a: add `cohezion/LICENSE` Apache 2.0. 4b: 180 root markdowns → `cohezion/docs/{sessions,learnings,archive}/INDEX.md` via `git mv`. Keep ≤8 at root (README.md, CLAUDE.md, LICENSE, CONTRIBUTING.md, SECURITY.md, MEMORY.md, HARDWARE_PROFILE_PRIME.md, configs). 4c: declutter (output dirs → `runs/<date>/`, logs → `logs/`, `birdclef_baseline.pth` → `models/`, 185 root JSON → `configs/`/`data/`/`runs/` per pattern). 4d: tighten `.gitignore` for `*.handoff.md`, `.pi/HANDOFF-*.md`, `.worktrees/`, `AGENT_STATUS.md`, `.agent-status.d/` (with `!.gitkeep`). 4e: themed staged commits (chore(root): relocate sessions; chore(license): add Apache; chore(gitignore): catch handoff). **No push.** 4f: write `cohezion/docs/BRANCH_STRATEGY_PROPOSAL.md` with 3 options:
  - A. Merge `isolated/session-oom-modularity` → main (squash) — Low risk, **recommended**.
  - B. Cherry-pick cleanup to new main-based branch — Medium, per-commit triage.
  - C. Stay on isolation branch, document why — None, acceptable if intentional.
- **Phase 5 (Class A, ~15 min)**: Verification checklist (`ls /dev/` ≤12 entries, `cohezion/*.md` ≤8, `LICENSE` exists, `RESTORE.sh --dry-run-all` works, sidecars exist on portfolio projects, `pytest --co` succeeds), finalize `/dev/README.md`.

**Trade-offs accepted**

- We give up speed (3-3.5 hours total, gated on user-declared quiet windows).
- We give up "clean history": staged commits and proposal-only branch surgery — user must execute branch ops manually.
- We give up some auto-coverage on Gemini/Lemonade agents (passive `ps` scan only).

**Reversal cost**: low. `RESTORE.sh --all` undoes Phase 2; `git checkout HEAD~N -- <path>` undoes pre-push file moves; settings.json `.bak` files restore harness config; LICENSE is additive (delete file).

**Depends-on / informs**

- Depends on: git-operations.md (read-only by default), check-settings-size.sh hook gate.
- Informs: future Anthropic-application portfolio packaging; sets convention for AGENT_STATUS multi-agent register.

---

### 2. 12D Graph Visualization + SurrealDB Integration Plan

- **Date**: 2026-02-09
- **Status**: proposed (design phase)
- **Owner**: vault team (multi-specialist)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-09-12d-graph-surrealdb-integration.md`

**Context**

Vault reached 123 wiki-links across 66 papers; 21 concepts cross-linked. Standard 3D graph plugins inadequate for richer multi-dimensional exploration. Need backend supporting native graph + embeddings + real-time subscriptions.

**Options considered**

- Standard 3D graph plugin — single spatial view, insufficient analytical axes; rejected.
- Traditional RDBMS — no native graph, poor relationship perf; rejected.
- File-based JSON graph — not scalable for real-time subscriptions; rejected.
- **(chosen)** Custom 12D graph plugin (Obsidian) + SurrealDB backend.

**Decision**: build custom 12D graph plugin powered by SurrealDB.

**Rationale**

- 12 distinct analytical dimensions cover spatial(X/Y/Z), temporal, domain clustering, connectivity density, conceptual depth, citation impact, recency, cross-domain bridging, user interest, semantic similarity, completion status, agent-journey affinity.
- SurrealDB advantages: native graph relationships, multi-model (docs+relations+graph queries), real-time subscriptions, full-text search, spatial indexing, embeddings, GraphQL+SurrealQL.
- Confidence 0.85; 60h estimated implementation across 5 phases.

**The 12 dimensions and their visual encoding**

| Dim | Default axis | Visual encoding | Filter control |
|---|---|---|---|
| 1. X position | Domain cluster | X position | Domain selector |
| 2. Y position | Connectivity | Y position | Min/max links |
| 3. Z position | Temporal | Z position | Date range |
| 4. Domain affinity | Color | Node color hue | Domain filter |
| 5. Depth level | Size | Node radius | Theory↔Applied |
| 6. Citation impact | Glow | Glow intensity | Min citations |
| 7. Recency | Opacity | Node alpha | Age filter |
| 8. Cross-domain | Edge thickness | Connection width | Bridge score |
| 9. User interest | Animation | Pulse rate | Interaction count |
| 10. Semantic sim | Edge color | Connection hue | Similarity threshold |
| 11. Completion | Border | Outline style | Enrichment % |
| 12. Agent affinity | Particles | Particle count | Relevance score |

**Architecture stack**

```
Obsidian Vault (markdown) → Vault Watcher → Cloud Vault MCP (Python: VaultOps + Graph Builder + Embeddings + SurrealDBSync)
  → SurrealDB (nodes: papers/concepts/tags/authors; edges: links/citations/similarity/domains; live queries)
  → Obsidian Plugin (TS/React + WebGL/Three.js, 12 dimensional sliders, real-time SurrealDB subscriptions, 12D→3D projection)
```

**Implementation plan**

- Phase 1 (Wk 1-2) SurrealDB integration: install (Docker/binary), schema for papers/concepts/domains, relationship types (LINKS, CITES, BELONGS_TO, SIMILAR_TO), bulk import 84 papers + 21 concepts, file-watcher real-time sync.
- Phase 2 (Wk 2-3) Dimensional computation: static dims (`compute_temporal_dimension`, `compute_connectivity_dimension`, `compute_domain_dimension`, `compute_conceptual_depth`); dynamic dims (`compute_semantic_similarity` via OpenAI/Anthropic embeddings, `compute_agent_affinity` from agent context); user-interaction tracking for Dim 9.
- Phase 3 (Wk 3-5) Plugin development: `npm init obsidian-plugin cohezion-12d-graph`; deps `three @react-three/fiber @react-three/drei surrealdb.js zustand`; structure `src/{main.ts, graphView.tsx, db/{surrealClient.ts,queries.ts}, viz/{GraphRenderer.tsx,NodeRenderer.tsx,EdgeRenderer.tsx,projectionEngine.ts}, controls/{DimensionSliders.tsx,AxisSelector.tsx,FilterPanel.tsx}, settings/SettingsTab.tsx}`. ProjectionEngine maps selected dim indices to X/Y/Z * 100 scale.
- Phase 4 (Wk 5-6) Advanced: recommendations ("you might like"), agent-journey integration (track goals in SurrealDB, highlight Dim 12, show agent path over time), collaborative (multi-user annotations, shared dim views), export (JSON/GraphML, network analysis).

**SurrealDB schema (key fields, abbreviated)**

```sql
DEFINE TABLE paper SCHEMAFULL;
DEFINE FIELD title|file_path|content|tags|date ON paper TYPE string|string|string|array|datetime;
DEFINE FIELD dim_spatial_{x,y,z}|dim_temporal|dim_connectivity|dim_depth|dim_citations|dim_recency|dim_bridging|dim_interest|dim_completion ON paper TYPE float|int;
DEFINE FIELD dim_domain ON paper TYPE array<string>;
DEFINE FIELD dim_similarity|dim_agent_affinity ON paper TYPE object;
DEFINE TABLE links TYPE RELATION FROM paper TO concept;
DEFINE TABLE cites|belongs_to|similar_to TYPE RELATION FROM paper TO {paper|domain|paper};
DEFINE INDEX idx_paper_{date,tags,connectivity} ON paper FIELDS {date,tags,dim_connectivity};
```

**Risks & mitigations**

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| SurrealDB perf with large graphs | High | Med | Index opt, pagination, clustering |
| 12D projection UX complexity | Med | High | Clear defaults, guided tours, presets |
| Plugin compat | Med | Low | Test multiple Obsidian versions |
| Real-time sync lag | Low | Med | Debouncing, background sync |
| Embeddings API cost | Med | Med | Cache embeddings, batch, local models |

**Alternative incremental path** (if 12D too ambitious initially): Phase 1-Lite 4D (X domain, Y connectivity, Z temporal, color completion); Phase 2-Lite 8D (+ size/opacity/edge thickness/glow); Phase 3-Full 12D.

**Trade-offs accepted**

- We give up immediate delivery (6-7 weeks to production for full 12D).
- We give up reuse of mature plugins; building from scratch.
- We give up 12D projection clarity (humans can only see 3D; mitigated via dynamic projection, secondary visual encoding, dimensional sliders).

**Reversal cost**: medium. SurrealDB+plugin is additive; can be disabled and graph reverts to Obsidian native. Vault data unaffected (markdown is source of truth).

**Depends-on / informs**

- Informs Decision #8 (specialist-driven refined plan), Decision #10 (MCP infra), Decision #17 (semantic contradiction detection uses same Ollama embed pipeline), Decision #18 (Phase 2 schema design extends this).

---

### 3. Claude Log Mining Plan — Adversarial Review (REJECT)

- **Date**: 2026-02-10
- **Status**: critical-flaws-identified (severity HIGH)
- **Owner**: Claude (self-adversarial review of own prior plan)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-log-mining-adversarial-review.md`

**Context**

A prior plan (Decision #13) proposed 4-wave systematic mining of `~/.claude/` logs (claimed 647 sessions, $0.75 budget). Adversarial review applied before execution.

**Verdict**: PLAN HAS CRITICAL FLAWS — DO NOT EXECUTE AS DESIGNED. Would lead to ~90% wasted effort ($0.75 → $0.08 actual value), meaningless patterns from bad data, false confidence in broken classifier, MCP tool giving misleading recommendations.

**Seven critical flaws**

1. **Sample size catastrophe** — Plan claims 647 sessions; reality: 127 debug logs exist, 98 usable (15% of claimed). Debug logs are recent/specific only, not retroactive. Can't extract 10-15 patterns from 3 successful sessions; statistical significance destroyed.
2. **Broken outcome classifier** — Of 98: 3 success (3.1%, ABSURDLY LOW), 19 partial, 70 failure (71.4%, ABSURDLY HIGH), 6 unknown. The 3 "successes" are massive 67-106K-token sessions with 250+ tool calls (likely thrashing). Logic `error_count > 5 → failure` and `tool_calls > 0 && error_count == 0 → success` measures absence of logged errors, not actual goal completion.
3. **Error count meaninglessness** — Avg 42.6 errors/session because `re.findall(r'\[ERROR\]', sample)` counts all `[ERROR]` lines including non-fatals, expected misses, retries, warnings.
4. **Debug logs missing conversation content** — Plan assumes extractable user prompts beyond display string, Claude responses, reasoning. Reality: only operational metadata reliable; some buried `Message N [META]:` content; not structured transcript; not Claude's reasoning.
5. **Haiku quality assumptions** — With 3 successes and broken labels, Haiku will hallucinate patterns ("keep prompts concise like 'UV', 'Proceed'" — wrong). 100 sessions vs claimed 647.
6. **Token cost underestimation** — Real cost ~3.2x: Wave 2 $0.50→$1.20 (passing all 98 + debugging + re-running after fixes); Wave 3 $0.25→$0.80 (full context per session, refinement iters); Wave 4 $0→$0.40 (test runs each costing Haiku $0.01); total $0.75→$2.40.
7. **MCP tool integration complexity** — Plan said 120 min, $0; real: ~375 min ($0.40). Breakdown: Ollama integration 30min, SurrealDB cosine search 60min, pattern matching 90min, Haiku NL suggestions 45min, testing 120min, docs 30min.

**Alternatives considered**

- **A. ABANDON** — Save $2.40 + 11h; miss meta-learning opportunity. Verdict: viable if no better.
- **B. MANUAL REVIEW** — Human reads 98 sessions (2h), labels (2h), extracts 5-7 patterns (2h), writes vault (1h) = 7h, $0, HIGH quality, HIGH accuracy, no scalability/embeddings. Verdict: BETTER than current plan.
- **C (chosen). REDESIGN** — Pilot study on 98 sessions, manual labeling (8h), fix error counting (2h dev), reduced Wave 2 (3 agents on 40 sessions, 45min, $0.40), reduced Wave 3 (98 sessions scoring, 30min, $0.20), SKIP Wave 4. Total: 11.75h human + 1.75h AI, $0.60. Deliverable: validated *hypotheses* (not patterns), documented limitations.
- **D. CONTINUOUS COLLECTION** — Implement enhanced logging now (4h), collect 500+ sessions over 6 months, run full analysis later. Do **in parallel with C**.

**Decision**: redesign as Alternative 3 pilot (primary) + Alternative 4 continuous collection (secondary in parallel).

**Rationale**

- Sample size is unfixable retroactively; accept 98 sessions; promise hypotheses not patterns.
- Manual labeling beats Haiku on broken-classifier data; humans know which prior tasks actually succeeded.
- Filter error counting to FATAL/CRITICAL/exception-traces; weight by severity; ignore expected.
- Reduce scope: 20 best + 20 worst sessions to Haiku, 3-5 hypotheses, human validation before accept.
- Skip MCP tool (defer until validated patterns exist); manual vault lookup interim.
- In parallel: enhance logging today (capture full conversation, post-session satisfaction rating, task-completion signal) to enable proper analysis in 6 months at 500+ sessions.

**Self-critique (what Claude did wrong)**

- Assumed data availability without verification.
- Optimistic token estimates (no 2-3x safety margin).
- No data quality checks first (designed before running indexer).
- Overpromised deliverables (10-15 patterns from 3 successes is absurd).
- Ignored MCP integration complexity.
- **Violated "Implementation First" principle**: designed full 4-wave architecture (~68K tokens), 680-line decision doc, complete execution plan — without running `/tmp/log_indexer.py` (2 min) to validate data exists. Token waste: 68K-20K = 48K tokens (71% wasted).

**Trade-offs accepted**

- We give up promised deliverable (10-15 patterns → 3-5 hypotheses).
- We give up speed (5h → 10h).
- We give up MCP tool (deferred).
- We give up impressive scope (647 sessions → 98 pilot).

**Reversal cost**: low. Pilot can be expanded into full plan after 6 months of continuous collection yields 500+ sessions.

**Depends-on / informs**

- Supersedes Decision #13 (claude-log-mining-architecture).
- Informs Decision #4 (compound engineering meta-learning) which adopted the redesigned approach + continuous-collection insight.
- Meta-lesson: validate data availability BEFORE designing complex systems.

---

### 4. Compound Engineering — Meta-Learning System Expansion

- **Date**: 2026-02-10
- **Status**: proposed (priority high)
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-compound-engineering-meta-learning.md`

**Context**

After successful pilot mining with 5 success hypotheses + 5 anti-patterns extracted from Claude logs, recognize the infrastructure is reusable. This isn't just log analysis — it's a feedback loop for AI improvement.

**Options considered**

- One-time analysis — misses ongoing learning potential; rejected.
- Manual pattern updates — not scalable; rejected.
- **(chosen)** Expand into continuous meta-learning loop with cron + 4 MCP tools + COHESION integration.

**Decision**: roll log mining into continuous learning loop with MCP tool suite, integrated into agent orchestration (COHESION). Confidence 0.88.

**Six compound-engineering opportunities, prioritized**

1. **Continuous learning loop** (HIGH IMPACT). Cron weekly Sunday 2am: `/home/mike-anderson/.claude/hooks/weekly_pattern_refresh.sh` — index new sessions, Haiku-label (~$0.10 per 50), if 50+ new sessions re-extract, compare patterns, if confidence shift >20% update vault, generate `inbox/` insight summary. Economics: ~100 sessions/wk × $0.002 = $0.20/wk = $10.40/yr; ROI: 10-20% token savings = $50-100/yr savings.
2. **MCP tool suite — pre/mid/post analysis** (VERY HIGH IMPACT). 4 tools:
   - **`analyze_prompt_effectiveness(prompt)`** — Pre-flight; Ollama embed → SurrealDB similar-prompt search → anti-pattern check → returns `{success_probability, similar_successful_prompts, warnings, suggestions, estimated_tokens}`. $0.01/call (Haiku).
   - **`detect_session_thrashing()`** — Mid-session every 100 tools; counts tools/errors/tokens vs thresholds (500 tools, 30% errors); returns `{thrashing_detected, current_tools, current_errors, error_rate, recommendation}`. $0 (local).
   - **`suggest_prompt_refinement(current_prompt, context)`** — Post-failure or on request; rewrites with explicit tasks/file paths. $0.01.
   - **`generate_session_retrospective()`** — Post-session; analyzes tokens/tools/errors/outcome vs patterns, generates Markdown retro. $0.02.
   - Total suite: 4 weeks dev each (16w), $0.04/session = $4/mo = $48/yr; 20% token savings → $100-200/yr → 2-4× ROI.
3. **Pattern library evolution** (MEDIUM). Phase 1 (mo 1-6) validation at scale; Phase 2 (mo 6-12) fine-grained patterns by task-type/project-type/temporal; Phase 3 (yr 2) auto-generate, auto-deprecate, version (v1/v2/v3); Phase 4 (yr 2+) export, share, benchmark, publish.
4. **Cross-project application** (HIGH). Apply to other Cohezion projects, other AI systems (GPT-4, Gemini), multi-user (anonymized). Generalize log indexer + pattern extraction model-agnostic.
5. **COHESION framework integration** (HIGHEST IMPACT). 5 integration points:
   - A. Agent persona templates with validated `prompt_patterns: {success_factors, avoid}`.
   - B. Pre-flight prompt analysis in `Task()` tool — if `success_probability < 0.6`, suggest refinement.
   - C. Mid-session thrashing detection every 100 tool calls → pause + ask user.
   - D. Post-session learning: auto-retrospective + vault update + pattern confidence update.
   - E. Economic optimization: track token cost per pattern, recommend efficient approaches.
   - 6-week timeline.
6. **Research & publication** (MEDIUM, high visibility). Title: "Token-Efficient Meta-Learning for LLM Prompt Optimization"; venues NeurIPS Workshop, ACL Workshop, ArXiv. Open-source `claude-log-mining` repo.

**Phased roadmap**

| Phase | Timeline | Effort | Cost |
|---|---|---|---|
| A. Foundation | 2 weeks | 1w dev | baseline |
| B. MCP Tools | 6 weeks | 4w dev | $48/yr | 2-4× ROI |
| C. Integration | 6 weeks | 4w dev | — | 20-30% session improvement |
| D. Validation | 3 months | $10/mo | — | statistical validity |
| E. Publication | 6 months | 2w writing | — | visibility/citations |
| **Total** | **12 months** | **~10w dev + $500/yr** | — | transformative |

Break-even: after Phase C (14 weeks).

**Critical decisions**

- B vs C priority: **B iterative** (build one tool → integrate → iterate). Faster feedback; lower risk of unused tools.
- Continuous logging scope: **enhanced** (full conversation + 1-5 satisfaction rating + task-completion yes/no/partial; skip screen recordings).
- Open-source timing: **after Phase D validation** — pilot results too preliminary to publish.

**Trade-offs accepted**

- We give up speed of one-off analysis; commit to multi-month roadmap.
- We give up specialization (cross-project generalization adds complexity).
- We give up keeping methodology proprietary (planned open-source).

**Reversal cost**: low for individual tools (each phase cleanly separable); medium for COHESION integration (touches Task tool, agent personas).

**Depends-on / informs**

- Depends on Decision #3 (adversarial review redesign), Decision #10 (MCP infrastructure), Decision #9 (Ollama MCP).
- Informs cross-decision theme: vault-first compounding learning.

---

### 5. Phase 4 Retrospective + Phase 5-7 Overnight Compound Engineering Plan

- **Date**: 2026-02-14
- **Status**: proposed (overnight execution scheduled)
- **Owner**: vault-architect (lead) + 5 specialist agents
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-14-phase-4-retrospective-and-phase-5-overnight-plan.md`

**Context**

Phase 4 (Decision Analysis UI) finished 47% under estimate (5h vs 9.5h, 105K vs 200K tokens) using "Implementation First" template-copy pattern. Solo execution beat 5-agent team (no coordination overhead). 13/13 success criteria met. 142 tests passing. Now plan Phases 5-7 to add the intelligence layer.

**Options considered**

- Wait for user feedback before Phase 5 — delays competitive advantage; rejected.
- Single-agent sequential — wastes parallel capacity; rejected.
- Plan-heavy approach — Phase 4 proved lean execution wins; rejected.
- **(chosen)** Execute Phases 5-7 overnight as unified compound-engineering cycle with 5-agent parallel execution.

**Decision**: launch 5-agent overnight session; minimum-viable Phase 5 + 6A + 6B guaranteed; 6C + 7 as bonus. Confidence 0.85. 8-hour window 2026-02-14 → 2026-02-15.

**Phase 4 lessons captured**

- L1: Implementation First > lengthy planning. 2,600-line plan vs 5h solo execution; template reuse cut dev 47%.
- L2: Token economics drive strategy. Planning ~5K tokens vs execution 105K; full execution cheaper than "plan well then fail once".
- L3: Autonomous single-agent > coordinated team for bounded tasks. 5-agent overhead (30min coord + 20min/turn comms) lost to 5h solo.
- L4: Caching enables scale without infrastructure. LRU 50 items / 5min TTL / 90%+ hit rate → 88-decision search <50ms.
- L5: Debounce + non-blocking concurrency = real responsiveness. 100ms debounce + background dim computation → <500ms paper ingestion.

**Phase 5: Integration (2-3h, solo lead)**

- 5.1 (30 min) Decision ribbon icon + `Ctrl+Shift+D` shortcut.
- 5.2 (45 min) Unified paper-decision navigation: click paper in 3D → populate Decision Explorer; click decision → highlight papers in 3D; breadcrumb Paper→Decision→Cascade→Related; modal sync.
- 5.3 (60 min) Cascade network overlay in 3D; toggle "Show decision cascades"; edge color by impact (critical=red, significant=orange, minor=gray); maintain >30 FPS.
- 5.4 (30 min) Settings panel: visibility toggle, cascade depth slider 1-5, confidence threshold, reasoning-type filter.

**Phase 6: Compound Engineering — Decision Intelligence (4-6h, 3-agent parallel)**

- **6A. Automated reasoning chain inference** (inference-engineer, 2h, 200 LOC). For decisions missing chains: extract 88 existing chains, identify type patterns (research/pattern/intuition/convention by keyword), Ollama-embed decision text → find 3 closest existing → use their reasoning_type distribution to generate chain (3/3 research → 4-5 research steps; 2/3 pattern → hybrid). Store as "inferred" with confidence=0.6, log for human review. Output: 30-40 chains.
- **6B. Cascade impact computation — 2nd/3rd order effects** (graph-engineer, 2.5h, 250 LOC). Load 88 decisions + 148 cascade rels; build dep graph; for each decision compute Level 1 (A→X), Level 2 (A→B→X), Level 3 (A→B→C→X), conflict chains, support chains; aggregate impact score. Store `decision_impacts(source, target, depth, type, score)`. BFS to depth 5; precomputed once/session, cached in SurrealDB. Output: complete impact graph 88 × 5 depths.
- **6C. Contradiction detection via semantic similarity** (validation-engineer, 1.5h). Embed all 88 decisions and 44 lessons; build 88×44 similarity matrix; pairs >0.7 → extract opposing concepts (NLP), classify (contradicts/undermines/requires_review), severity by (decision confidence × lesson importance × similarity)/3. Tag `detection_method='semantic'`. Output: 20-40 additional contradictions beyond the 25 manually linked. (See Decision #17 for completion record.)
- **6D. Decision quality scoring** (analytics-engineer, 1h, 150 LOC). Score = `(confidence×0.4) + (alts/5×0.2) + (assumptions/3×0.1) + (no-contradictions×0.2) + (reasoning diversity×0.1)`. High-quality (>0.85) = trust; 0.6-0.85 = useful with caveats; <0.6 = experimental.

**Phase 7: Operational Intelligence Dashboard (4-6h, 2-agent parallel)**

- **7A. Decision health dashboard** (dashboard-engineer, 2h). 6 metrics: confidence histogram, reasoning-type pie, contradiction-rate trend line, quality-score sortable table, decision velocity bar, impact distribution donut. Chart.js or D3, 30s refresh, PDF export.
- **7B. Cascade impact timeline + recommendation engine** (reasoning-engineer, 2-3h, 200 LOC). Timeline view (chronological cascade resolution); recommendation triggers on new paper ingestion (Ollama-embed → find similar papers → query decisions referencing them → recommend reconsidering Decision X). Notification: "2 recommendations based on new paper".

**5-agent parallel execution plan**

| Wave | Hours | Lead (Phase 5) | Agent 1 | Agent 2 | Agent 3 | Agent 4 | Agent 5 |
|---|---|---|---|---|---|---|---|
| 1 | 0-2.5h | 5.1+5.2 | 6A setup | 6B alg | 6C semantic setup | — | — |
| 2 | 1.5-4h | 5.3+5.4 | 6A complete | 6B complete | — | 7A start | — |
| 3 | 3.5-7h | integrate Phase 5 | — | — | 6C complete | 7A complete | 7B start |
| Wrap | 7-8h | all integration testing + 60 LOC docs each + commit |

Expected: 10-15h serial → 6-8h wall (40-50% compression). 2,200 LOC, 400/1000/800 by phase.

**Risk mitigation overnight**

- Pre-written task specs (no live discussion).
- Inference during off-peak; cache results.
- Pre-warm Ollama (first batch slow); embed in background.
- Lead does UI; others do inference (real parallelism, not blocked).
- Clear file ownership per agent (no merge conflicts).
- Plan for 8h not 12h; quality > speed.

**Trade-offs accepted**

- We give up daytime user-feedback loop; commit to 8h overnight + morning checkpoint.
- We give up some Phase 6C/7 if behind; minimum viable is Phase 5 + 6A + 6B.
- We give up the "manual review" intermediate step (auto-inferred chains tagged for later validation).

**Reversal cost**: low. Each phase outputs are additive; can disable inferred chains (filter `tag=inferred`), recompute cascades on demand, rollback dashboard module.

**Depends-on / informs**

- Depends on Decision #2 (12D graph), Decision #17 (semantic contradiction completes 6C), Decision #18 (Phase 2 schema design provides reasoning chain table).
- Informs subsequent Phases 8-10 (real-time notifications, multi-team sync, automated reasoning audits).

---

### 6. Phase 2 Final Completion Summary — All Tracks Done, Production Ready

- **Date**: 2026-02-13
- **Status**: completed
- **Owner**: integration-engineer (Track B), data-graph-specialist (Track A), vault-architect (Track C)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-13-phase-2-final-completion-summary.md`

**Context**

Phase 2 launched 2026-02-12 with 3 parallel tracks. All success criteria met across all tracks. 100% test pass rate, 0 blockers, on-time delivery, production-ready. Sign-off decision.

**Options considered**

- (only) Sign off Phase 2 with all 3 tracks complete, 100% tests, 0 blockers. Confidence 1.0. No alternatives rejected (formal completion sign-off).

**Decision**: Phase 2 complete. All tracks production-ready. Authorized for immediate deployment.

**Track scorecards**

| Track | Component | Est | Actual | Compression | Tests | Coverage |
|---|---|---|---|---|---|---|
| A | SurrealDB Reasoning Schema | 12h | 7.5h | 37.5% | 73/73 | 95% |
| B | Entire.io Sync Daemon | 7-8h | 4h | 51% | 44/44 | 92.5% |
| C | Lessons Phase 2 Linking | 1-2h | 0.5h | 75% | 25 cross-links 100% valid | — |
| **Phase 2** | — | **20-22h** | **12h** | **40-45%** | **142/142** | **94.2%** |

**Track A — SurrealDB Agent Reasoning Schema**

- Files: `cloud-vault-mcp/src/mcp_server/{agent_reasoning.py, agent_reasoning_queries.py, agent_context_schema_phase2.sql}`.
- 3 MCP tools: `record_reasoning()`, `record_challenge()`, `record_cascade()`.
- 4 query patterns: `root_cause_analysis()`, `contradiction_detection()`, `cascade_impact()`, `high_confidence_reasoning()`.
- 1 new node type (`agent_reasoning`); 4 new edge types (`informs_reasoning`, `challenges_lesson`, `cascades_to`, `validates_decision`); 7 perf indexes.
- 1500+ LOC; <200ms avg perf (3.5× target); 0 Phase 1 breaking changes.
- Tests: 26 tool + 27 query + 20 integration = 73/73.

**Track B — Entire.io Sync Daemon**

- Files: `cloud-vault-mcp/src/mcp_server/{entire_sync_daemon.py 183 LOC, entire_ops.py 94 LOC, entire_main.py 103 LOC}` + `entire-io-sync.service` systemd.
- 5 CLI commands: `start` (configurable polling), `status`, `dlq` (dead letter list), `retry`, `test` (validate setup).
- AsyncIO event loop polls git every 300s; WorkQueue (SQLite) idempotency; DeadLetterQueue (SQLite) failure recovery; EntireOps parses commit metadata (agent_id, outcomes, metrics, status).
- Data flow: git → poll → parse → check WorkQueue → if new: create Vault note → record SurrealDB → mark queue.
- Systemd: auto-restart, ResourceLimits 256M RAM / 50% CPU, Security ProtectSystem=strict + ProtectHome=yes, syslog logging.
- 380+ LOC; all ops <100ms; 0 dup processing.
- Tests: 25 unit (entire_ops) + 19 integration = 44/44.
- Operations runbook: 600+ lines (`patterns/entire-io-sync-daemon-operations.md`).

**Track C — Lessons Phase 2 Linking**

- 25/25 cross-links established, 100% accuracy, 0 broken refs.
- SurrealDB: 25 lesson↔decision bidirectional rels; query <100ms.
- Vault wiki-links + backlinks functional. Decision→Lesson→Paper relationships complete.

**Cross-track integration**

- Track A → Track B: B records to `agent_logs` nodes from A schema. No conflicts.
- Track B → Track C: B daemon writes daily notes; C lessons enrich them. Bidirectional rels established.
- All tracks: SurrealDB hub. A reasoning + B operational + C linked lessons = complete operational tracking system.

**Lessons learned**

- Pattern 1: Parallel-track execution scales (3 tracks, 40-45% combined compression).
- Pattern 2: Local services enable $0 delivery (SurrealDB + Ollama, no cloud).
- Pattern 3: Comprehensive testing reduces risk (142/142 enables confident compression).
- Pattern 4: Production-first design beats feature bloat (Track B: 380 LOC + 5 CLI commands + systemd from day 1).

**Trade-offs accepted**

- We give up scope flexibility (committed to 3 tracks; all delivered).
- We give up potential cloud-managed convenience (chose local services for $0).

**Reversal cost**: low. Each track independently deployable/rollbackable. Track A schema migrations reversible; Track B systemd disable; Track C cross-links removable from SurrealDB.

**Depends-on / informs**

- Depends on Decision #18 (Phase 2 schema design).
- Informs Decision #19 (deployment authorization), Decision #5 (Phase 4 retro feeds back into compound learning).

---

### 7. Model Wrangler Strategy — Local LLM Lifecycle Management

- **Date**: 2026-02-09
- **Status**: proposed (specialist role addition)
- **Owner**: TBD (Specialist #6 in 12D Graph project team)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-09-model-wrangler-strategy.md`

**Context**

Local LLM ecosystem releases 3-5 quality models per week. Reactive monitoring loses 10-20% performance gains and cost reductions. Need dedicated continuous-monitoring role.

**Options considered**

- Reactive monitoring — miss new models, stay on slower; rejected.
- Quarterly reviews — miss 10+ releases per cycle; rejected.
- **(chosen)** Dedicated Model Wrangler role: daily monitoring, same-day benchmarking on major releases, aggressive 24h swap cycles, monthly fine-tuning. Confidence 0.90.

**Decision**: add Model Wrangler as DAILY DRIVER specialist.

**Rationale**

- Volatile fast-moving ecosystem rewards proactive monitoring; punishes drift.
- Same-day benchmarking on major releases (4h critical / 24h major / 48h minor / weekend experimental) means decisions made on fresh data.
- Aggressive swap cycle (24h if ≥10% improvement OR critical fix) keeps production current.
- Monthly fine-tuning on COHEZION-specific data closes generic-model accuracy gap.

**Responsibilities**

1. **Daily monitoring (9am)**: Hugging Face Trending top-20, Ollama library updates, LM Studio Discord #model-releases, Reddit /r/LocalLLaMA last 24h, Papers with Code leaderboards (MMLU, HumanEval), Twitter/X (@ollama, @huggingface, @MetaAI, @MistralAI), GitHub watch (llama.cpp, ollama, transformers), Discord (LocalLLaMA, Ollama, LM Studio). Automated alerts via RSS/webhooks → daily digest script.
2. **Benchmarking** — COHEZION-specific suites:
   - Suite A. Gap analysis: 20 sample papers, accuracy vs Claude Opus ground truth, speed, false-positives, cost.
   - Suite B. Semantic similarity: 100 paper pairs vs human ratings, Pearson r correlation, ms/embedding, dim size.
   - Suite C. Agent journey affinity: 10 contexts × 84 papers, precision@5, speed, context sensitivity.
3. **Selection criteria** (weighted): Accuracy 40% (≥70%), Speed 30% (<2s real-time), Resource 20% (<16GB RAM), Context 10% (≥8K).
4. **Swap decision**: improvement = `(Δaccuracy×0.4) + (Δ1/speed×0.3) + (Δresource×0.2) + (Δcontext×0.1)`; swap if ≥10% OR critical fix.
5. **Swap process**: bench new → compare → prepare → update `ai_config.yaml` → integration test 5 papers → deploy → monitor 24h → rollback if issues → document in `daily/2026-XX-XX-model-swap-{old}-to-{new}.md`.
6. **Fine-tuning** monthly when accuracy <70% / repeated FPs / poor vault-specific concept understanding / new domain added. Dataset: 500 examples from vault + Claude Opus labels covering gap analysis + similarity + affinity. Pipeline: generate `finetuning.jsonl` → Modelfile (`FROM llama3.2:8b ADAPTER ./finetuning.jsonl`) → `ollama create cohezion-llama -f Modelfile` → benchmark → deploy if ≥80%.

**Model registry**

- Tier 1 production: nomic-embed-text v1.5 (embeddings, 274MB, 50ms/doc, 0.85), llama3.2:8b (gap analysis, 4.7GB, 2s/20 papers, 72%), mistral:7b (quick, 4.1GB, 500ms, 68%), llama3.2:70b (deep, 40GB, 20s, 88%).
- Tier 2 candidates: qwen2.5:14b (8GB, 75% — faster + better than llama3.2:8b), phi-4:14b (testing), gemma-2:9b (queued), deepseek-r1:7b (queued).
- Tier 3 experimental: aya-expanse:8b (multilingual), solar-pro:22b (claims SOTA reasoning).

**SurrealDB monitoring schema**

```sql
CREATE TABLE model_performance SCHEMAFULL;
DEFINE FIELD {model_name, version, task, accuracy, speed_ms, ram_mb, timestamp};
```

**Automation tools**

- `benchmark_model.py`: run all 3 suites, store JSON, auto-recommend if `should_swap_model` true.
- `swap_model.sh`: pull → integration test → backup config → sed replace → restart → 60s monitor → health check → rollback on fail. <5 min target.

**Division of responsibilities** (with AI Features Specialist)

- Model Wrangler owns: selection, swapping, fine-tuning, monitoring.
- AI Features Specialist owns: algorithm design, integration, accuracy reporting.

**Rollback triggers**: accuracy drop >5%, speed regression >50%, crashes/loops, user complaints about quality. <5 min rollback.

**Trade-offs accepted**

- We give up stability-of-known-version (aggressive swap creates churn).
- We give up generic model robustness (fine-tuning narrows to vault domain).
- We give up developer time (~100h/year on monitoring + benchmarking + swaps + fine-tuning).

**Reversal cost**: low for individual swaps (<5 min rollback); medium for fine-tuning (need to retrain); high for full deprecation of role (loss of monitoring discipline).

**Depends-on / informs**

- Depends on Decision #9 (Ollama MCP), Decision #10 (MCP infrastructure).
- Informs Decision #2 (12D graph) and Decision #8 (refined plan, where Model Wrangler is Specialist #7).

---

### 8. 12D Graph System — Refined Implementation Plan (Specialist-Driven)

- **Date**: 2026-02-09
- **Status**: proposed
- **Owner**: 7-specialist team (assembled)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-09-12d-graph-refined-plan.md`

**Context**

Refines Decision #2 around explicit specialist roles. Goal: surpass InfraNodus on 6 axes (BC, topical clustering, Force Atlas layout, Claude gap analysis, AI research questions, dynamic graphs) while adding COHEZION-signature features (Agent Journey Mode, compound engineering workflows, session-state integration).

**Options considered**: implicit ("monolithic vs specialist-driven"). Chose specialist-driven.

**Decision**: assemble 7-specialist team and execute in parallel.

**Rationale**

- 12D vs InfraNodus 3D = 4× richer dimensional space.
- Agent Journey Affinity (Dim 12) = signature feature InfraNodus lacks.
- Real-time vault↔SurrealDB sync (Dim 9 user interest captured live).
- Hybrid AI architecture: Claude Opus designs, local LLMs execute, Claude Sonnet reviews, Claude Haiku does real-time gap checks.
- Reasoning extracted by chain analyzer with 0.6 confidence, type=research (the doc was inferred-mode); explicit comparison to InfraNodus framing.

**InfraNodus features → COHEZION enhancements**

| InfraNodus | COHEZION enhancement |
|---|---|
| Betweenness centrality (BC), 3D | BC across 12 dims, weighted by agent journey affinity |
| Louvain topical clustering | Multi-dim clustering: domain tags + semantic sim + temporal proximity |
| Force-Atlas 2D/3D | 12D Force-Atlas with configurable projection to 3D |
| Claude gap analysis | Opus designs strategy; local LLMs execute on 100+ papers; suggests missing papers + research directions |
| GPT-4 research questions | Context-aware: current agent task + vault gaps + dimensional position |
| Real-time graph updates | Bidirectional sync (vault ↔ SurrealDB), file watcher, live 3D updates |

**12 dimensions** (mapped to InfraNodus equivalents)

| # | Purpose | InfraNodus equivalent | COHEZION innovation |
|---|---|---|---|
| 1-3 | Spatial X/Y/Z | Force-Atlas | Configurable projection from 12D |
| 4 | Temporal | none | Track knowledge evolution |
| 5 | Domain clustering | Topical clusters | Multi-domain bridging detection |
| 6 | Connectivity density | BC | Weighted by connection strength |
| 7 | Conceptual depth | none | Theory ↔ application |
| 8 | Citation impact | none | Track which papers cite this |
| 9 | Recency/relevance | none | Time-decay weighted |
| 10 | Cross-domain bridging | gap analysis | Interdisciplinary opportunities |
| 11 | User interest | none | Heat map of user attention |
| 12 | Agent journey affinity | none | **COHEZION SIGNATURE** |

**Specialist team**

1. **SurrealDB Specialist** (COMPLETE) — schema, query opt, UPSERT; production-ready bidirectional sync.
2. **12D Math/Geometry Specialist** (TO SPAWN) — 12D→3D projection, Force-Atlas in higher dims, PCA/t-SNE, validate dimensional independence.
3. **Obsidian Plugin Specialist** (TO SPAWN) — manifest.json/main.ts/settings, SurrealDB WS client, Three.js scene + render pipeline, Obsidian command palette.
4. **UI/UX Specialist** (TO SPAWN) — dimensional control panel (axis mapping/filters/sliders), node/edge visual encoding, search/filter, Agent Journey Mode UI, accessibility.
5. **AI Features Specialist** (TO SPAWN) — hybrid Claude+local-LLM architecture, BC (NetworkX), semantic similarity (sentence-transformers → local), Agent Journey Affinity scoring (Claude designs, local LLM scores in real-time).
6. **Google Sheets Specialist** (TO SPAWN) — SheetsBridge sync (12D metrics to Sheets for external analysis), enrichment status tracking, automated workflows (Sheet row → Vault note → SurrealDB → 3D Graph), dashboard metrics.
7. **Model Wrangler Specialist** (TO SPAWN, DAILY DRIVER) — see Decision #7. Daily 9am digest, 4h critical / 24h major bench, same-day emergency swaps, weekly dataset refresh, monthly retraining, real-time SurrealDB metrics + Slack alerts, <5min rollback.

**COHEZION-optimized features**

- **Agent Journey Mode** (signature) — track agent active concepts (task desc + recent messages), embed comparison to paper embeddings, real-time 3D filter, GPT-4 contextual suggestions ("Papers you might need: scaling-agent-systems.md").
- **Compound engineering workflows** — `agent_journey` table tracks active agents + focus concepts; `agent_collaboration` edges show dependencies; color-coded clusters per agent; timeline slider for activity over time.
- **Session state integration** — VaultMemoryBridge reads `daily/` notes; parses current phase + active tasks + branch; updates `dim_agent_journey_affinity` real-time.
- **Gap analysis** beyond InfraNodus — multi-dim gap detection across 12 dims (Temporal, Cross-Domain, Conceptual Depth, Citation Impact). Hybrid AI: (1) Opus plans strategy, (2) local LLMs execute (sentence-transformers embed 84 papers, dim distributions, outlier detect), (3) Sonnet reviews ("are these gaps meaningful?"), (4) Haiku real-time checks per new paper.
- **Live dimensional recomputation** — file watcher detects edit → SurrealDB updates → dimensional engine recomputes (e.g., wiki-link added → dim_connectivity 5→8, dim_cross_domain 0.2→0.7, dim_recency 0.5→1.0) → WebSocket push → Three.js smooth transition.

**Trade-offs accepted**

- We give up monolithic build speed; commit to coordination overhead of 7 specialists.
- We give up purely-local processing (Claude Opus design phase requires API).
- We give up first-mover simplicity for differentiation vs InfraNodus.

**Reversal cost**: medium. Each specialist's work is modular; can drop specialists if priorities shift. Hybrid AI design lets us swap Claude tiers for cheaper alternatives.

**Depends-on / informs**

- Depends on Decision #2 (base 12D plan) + Decision #7 (Model Wrangler).
- Informs Decision #5 (Phase 4 / 5-7 — UI built on this foundation), Decision #17 (semantic contradiction uses same Ollama embeddings).

---

### 9. Ollama MCP Server — Model Management as Infrastructure

- **Date**: 2026-02-09
- **Status**: implemented (16h actual vs 18h estimate)
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-09-ollama-mcp-server.md`

**Context**

Multiple one-off scripts (`gap_analysis_poc.py`, `generate_embeddings.py`, `chunk_papers.py`) duplicate Ollama API logic. No shared context window management. Model selection scattered. Not reusable.

**Options considered**

- Continue scattered scripts — duplicated logic, not reusable; rejected.
- Use Ollama API directly from each tool — no context mgmt, manual model selection; rejected.
- **(chosen)** Build reusable MCP server centralizing context, model selection, batching as infrastructure. Confidence 0.92.

**Decision**: build dedicated `ollama-mcp` server. Confidence 0.92.

**Rationale**

- Single source of truth: one place to optimize Ollama interactions; bug fixes propagate to all clients.
- Auto context window mgmt (chunking) eliminates per-script handling.
- Model selection logic encoded once; auto-select by task type + content length + quality preference.
- Reusable across Claude Code, agents, scripts, web UI.

**Architecture**

```
/home/mike-anderson/dev/cohezion/ollama-mcp/
├── src/
│   ├── server.py           # FastMCP server
│   ├── context_manager.py  # Context window mgmt
│   ├── model_selector.py   # Auto-select
│   ├── batch_processor.py  # Request batching
│   └── memory_manager.py   # RAM optimization
└── pyproject.toml
```

**MCP tools (5)**

1. **`ollama_query(prompt, model='auto', context='auto', max_tokens=1000)`** — auto-chunks if prompt > model context; auto-loads model with optimal keep-alive; unloads LRU model if RAM >80%; returns consolidated response.
2. **`ollama_embed(text, cache=True)`** — uses nomic-embed-text always-loaded; SurrealDB-cached optional; batch-processes if list.
3. **`ollama_batch(prompts, model='auto', batch_size=5)`** — combines into batches, single API call per batch, parsed back out.
4. **`ollama_select_model(task, content_length=0, quality='balanced')`** — task `embeddings` → `nomic-embed-text`; `gap_analysis` + `length>30000` → `deepseek-r1:7b` (32K ctx) else `qwen3:8b`; `reasoning` + `quality=best` → `deepseek-r1:7b` else `qwen3:8b`.
5. **`ollama_status()`** — JSON with loaded models (name, size_mb, context_window, until), RAM (total/used/percent), perf (requests_today, avg_latency_ms).
6. (also) **`ollama_preload(models, keep_alive='60m')`** — pre-load to avoid first-request latency.

**Integration with Claude Code** via `~/.claude/config.json` `mcpServers.ollama` entry.

**Trade-offs accepted**

- We give up per-script optimization flexibility (centralized = standardized).
- We give up speed of adding script-local quirks (must add to MCP server, used by all).

**Reversal cost**: low. Scripts can revert to direct Ollama calls; MCP server is additive.

**Depends-on / informs**

- Informs Decision #10 (MCP infrastructure topology), Decision #2 / #8 (12D graph uses Ollama MCP for embeddings + gap analysis), Decision #17 (semantic contradiction uses Ollama MCP), Decision #4 (compound engineering uses for embed + select).

---

### 10. MCP Infrastructure Architecture

- **Date**: 2026-02-10
- **Status**: active
- **Owner**: platform team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/cortex/mcp-infrastructure-architecture.md`

**Context**

Document the MCP server topology: how Claude Code IDE talks to local services (Ollama, SurrealDB, Sheets, Vault).

**Decision** (architectural reference, not a decision-with-alternatives): two-server topology.

1. **Cloud Vault MCP** — HTTP server on port 8360, exposes 30 tools across 7 categories.
2. **Ollama MCP** — Stdio-based (no port), exposes 5 tools.

**Topology diagram (text rendering)**

```
Claude Code IDE
   │ MCP protocol
   ├──────────────┬──────────────┐
   ▼              ▼              ▼
Cloud Vault MCP  Ollama MCP    (others)
HTTP :8360       stdio
   │              │
   │ HTTP         │ HTTP
   ├──┬───┬───┬───┤
   ▼  ▼   ▼   ▼   ▼
 Vault SurrealDB Sheets Ollama Memory
                       :11434
                       28+ models
```

**Cloud Vault MCP tool inventory (30 tools)**

- `vault_*` (10): read_file, write_file, search_vault, list_directory, get_metadata, update_metadata, create_note, delete_note, move_note, watch_file.
- `compound_*` (4): research_topic, enrich_paper, cross_reference_concepts, analyze_gap.
- `sheets_*` (5): get_all_rows, read_range, update_row, batch_update, update_vault_note_column.
- `surrealdb_*` (5): query, import_papers, import_concepts, create_index, get_schema.
- `teleport_*` (6): submit_task, get_result, list_tasks, update_status, archive_result, cleanup.
- `memory_*` (3): store, retrieve, list_memories.
- `health_*` (1): /health endpoint.

**Ollama MCP tool inventory (5)**

- `ollama_query, ollama_embed, ollama_batch, ollama_status, ollama_select_model`.

**Cloud Vault MCP file structure**

```
cloud-vault-mcp/
├── src/mcp_server/
│   ├── server.py               # Main MCP server
│   ├── vault_operations.py     # 10 vault tools
│   ├── compound_operations.py  # 4 compound tools
│   ├── sheets_bridge.py        # Sheets integration
│   ├── surrealdb_sync.py       # Graph DB sync
│   ├── health.py               # Health endpoint
│   └── ollama_client.py        # Calls to Ollama MCP
├── benchmarks/benchmark_runner.py
└── tests/*.py
```

**Cloud Vault MCP config (27+ env vars)**

- Core paths: `VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault`, `MCP_HOST=0.0.0.0`, `MCP_PORT=8360`.
- Ollama: `OLLAMA_ENABLED=true`, `OLLAMA_URL=http://localhost:11434`, `OLLAMA_TIMEOUT=30`.
- SurrealDB: `SURREALDB_ENABLED=true`, `SURREALDB_URL=http://localhost:8000`.
- Sheets: `SHEETS_ENABLED=true`, `GOOGLE_CLOUD_PROJECT=cohezion-477604`.
- Monitoring: `HEALTH_CHECK_TIMEOUT=5`, `LOG_LEVEL=INFO`.

**Ollama MCP file structure**

```
ollama-mcp/
├── src/mcp_server/
│   ├── server.py
│   ├── ollama_client.py    # HTTP to Ollama service
│   ├── model_selector.py   # Smart model picking
│   ├── context_manager.py  # Token budget
│   └── error_handler.py    # Graceful degradation
├── benchmarks/
└── tests/
```

**Model selection logic (example)**

```python
def select_model(task_type, content_length):
    if task_type == "embed": return "nomic-embed-text:latest"
    if content_length > 100_000: return "phi4-256k:latest"
    elif content_length > 10_000: return "qwen2.5-coder:14b"
    else: return "qwen3:8b"
```

**Available models (28)**

- Fast 8B: qwen3:8b, deepseek-r1:7b
- Balanced 14B: qwen2.5-coder:14b, phi4:latest
- Long context 256K: phi4-256k:latest
- Embeddings: nomic-embed-text:latest
- Other: 23 additional (llama, mistral, neural-chat, ...)

**Ollama service endpoints**

- `GET /api/tags` (list models)
- `POST /api/generate {model, prompt, stream:false}`
- `POST /api/show {name}`
- `POST /api/embed {model, input}`

**SurrealDB schema** (papers/concepts/links)

```surql
TABLE papers {title, abstract, authors, published, tags, file_path, concepts}
TABLE concepts {name, definition, primary_sources, related_concepts, papers}
TABLE links {from_paper, to_concept, link_type, created_at}
```

**Trade-offs accepted**

- We give up single-server simplicity (two MCPs to maintain).
- We give up cross-server transactions.

**Reversal cost**: medium. Tools could be merged into single MCP if desired; but separation reflects ownership boundaries (vault vs inference).

**Depends-on / informs**

- Depends on Decision #9 (Ollama MCP), Decision #2 (SurrealDB integration).
- Informs all subsequent MCP-tool-based work (Decision #4 MCP suite, Decision #17 contradiction detection).

---

### 11. Framework-Driven Prioritization

- **Date**: 2026-02-10
- **Status**: in-progress
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-framework-driven-prioritization.md`

**Context**

8+ pending initiatives; need systematic prioritization. First application of [[meta-learning]], [[roi-analysis]], [[template-reuse]] frameworks.

**Options considered**

- Opinion-based prioritization — biased, unrepeatable; rejected.
- Random picking — no strategic direction; rejected.
- **(chosen)** Apply ROI framework to evaluate each candidate by Investment (time, tokens, risk), Returns (savings, qualitative), ROI Trajectory (immediate / per-use / N-uses), Reuse potential, Break-even.

**Decision**: rank initiatives by computed ROI; pick top.

**Pending work queue (8)**

1. Event-Driven Sheets Pipeline Phase 3 (testing, deployment) — ACTIVE.
2. 3D Graph Visualization (Phase 3 target 2026-02-14).
3. 12D Graph Phase 6 (iteration + cluster analysis).
4. Ollama MCP Phases 2-4 (context caching, optimization).
5. Apply Lessons v2 (selective enrichment).
6. Fix 28 papers with YAML parsing errors.
7. Update .gitignore for cohezion repo (14M+ untracked files).
8. SurrealDB graph queries (orphans, gaps, opportunities).

**ROI scorecards**

| # | Candidate | Investment | Returns/Use | Trajectory | Reuse | Break-even |
|---|---|---|---|---|---|---|
| 8 | SurrealDB graph queries | 20-30 min, 4-5K tokens, low risk | 10-20K tokens saved (manual analysis avoided) | Immediate; 3-4× per query; 30-40× over 10 runs | HIGH | 1 run |
| 2 | 3D Graph Viz | 30 min – 2h, 5-20K tokens, MED risk (compat/perf) | 0 tokens (passive viewing) | 2× visual convenience one-time | LOW | Never (no token savings) |
| 1 | Sheets Pipeline Phase 3 | 2-3h, 15-25K tokens, low risk | 20-30K tokens/day (autonomous research) | Day 7 break-even; Day 30 30×; Day 365 365× | VERY HIGH | 1 day |
| 4 | Ollama MCP P2-4 | 3-4h, 20-30K tokens, MED risk | 100-200 tokens/inference | 100 inferences break-even; 1K = 5×; 10K = 50× | HIGH | 150-200 calls |
| 5 | Apply Lessons v2 | 1-2h, 8-12K tokens, low risk | 0 tokens (quality only) | Qualitative only | LOW | N/A |
| 6 | Fix 28 YAML errors | 30-60 min, 3-5K tokens, low | 0 (enables other work) | Unblocks SurrealDB queries | NONE | only via blocked work |
| 7 | Update .gitignore | 5-10 min, 500-1K tokens, none | Repo hygiene | One-time fix | NONE | N/A |

**Decision**: pick **Sheets Pipeline Phase 3** (highest computed ROI: 365× annual). Document rejected alternatives + rationale.

**Rationale**

- ROI math cuts through opinion bias.
- Sheets Pipeline Phase 3 has highest compounding return (autonomous = continuous savings) with lowest implementation risk (Phase 1-2 already proven).
- 3D Graph Viz formally rejected: no compound effect, vault size (144 nodes) too small for meaningful 3D clustering anyway.
- YAML fix only valuable if it blocks higher-ROI work — defer to when SurrealDB queries hit it.

**Trade-offs accepted**

- We give up "fun" projects (3D viz) for compounding work (Sheets pipeline).
- We give up immediate visual polish for autonomous infra value.

**Reversal cost**: none for re-prioritization (frameworks reusable).

**Depends-on / informs**

- Establishes ROI-framework precedent; informs all subsequent prioritization (Decision #4 roadmap, Decision #5 Phase 4 retro).

---

### 12. Autonomous Context Hooks for AI Agents

- **Date**: 2026-03-04
- **Status**: complete
- **Owner**: cohezion vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/cortex/Autonomous-Context-Hooks-Guide.md`

**Context**

AI agents (Claude Code, OpenCode, Gemini CLI) responded without vault context and didn't save results back. Knowledge graph awareness lost; vault enrichment manual.

**Decision** (architecture/configuration reference): two-phase hook system across all 3 supported agents.

**Architecture**

- **Phase 1 (Pre-operation)**: User prompt → hook intercepts → extract query → search vault → load 5-10 relevant notes → inject context → AI responds. Injection format: original prompt + `📚 Obsidian Vault Context (Auto-loaded)` block + per-note `## NoteName` + `**Tags:** ... **Related:** [[other-notes]]` + content + closing `**Instructions:** Reference context with [[Note Name]], link new concepts`.
- **Phase 2 (Post-operation)**: AI response → hook intercepts → save to session cache → extract permanent notes from `##` headings → update daily note → create backlinks. Daily-note format: `### Session: claude-12345` + Time + Type + Duration + Context loaded count + Permanent notes created + Files list with backlinks.

**Installation**

- Claude Code: `cp dev/cohezion/.claude/hooks/vault-context-*.py ~/.claude/hooks/`.
- OpenCode: `cp dev/cohezion/.opencode/hooks/*.sh ~/.opencode/hooks/`.
- Gemini CLI: `cp dev/cohezion/.gemini/hooks/*.py ~/.gemini/hooks/`.
- chmod +x all.

**Configuration files**

- Claude Code `~/.claude/vault-context.json`: `{enabled, vault_path, auto_load, auto_save, context_limit:10, default_tags:["#anthropic-portfolio"]}`.
- OpenCode `~/.opencode/vault-context.json`: `{enabled, vault_path, auto_save}`.
- Gemini CLI `~/.gemini/vault-context.json`: `{enabled, vault_path}`.

**Test command**

```
python dev/cohezion/src/cohezion/hooks/vault_context_loader.py pre \
  --session-id test-123 --query "anthropic portfolio" --limit 5
```

**Configuration options**

- Core: `enabled` (bool), `vault_path` (str auto-detect), `auto_load` (true), `auto_save` (true), `context_limit` (10), `default_tags` (array).
- Advanced: `extract_permanent_notes` (true), `update_daily_note` (true), `create_backlinks` (true), `min_section_length` (100), `context_cache_dir` (`/tmp/cohezion-context-cache`).

**Workflow examples**

- Portfolio planning: pre-hook loads `[[cohezion]] [[agent-architecture]] [[tool-use]]` → Claude responds → post-hook caches conv, extracts "Timeline" section as permanent note, updates daily note, creates backlinks. Vault enriched with new timeline knowledge linked to existing portfolio.
- Multi-turn session continuity: turn 1 loads transformer/NN/semantic-search; subsequent turns inherit cached context; cumulative knowledge.

**Trade-offs accepted**

- We give up agent independence (always-on hook adds latency + load).
- We give up control of context selection (heuristic search may miss).
- We give up storage cleanliness (cache dir grows).

**Reversal cost**: trivial. `enabled: false` in config disables; hook scripts can be deleted.

**Depends-on / informs**

- Depends on Decision #10 (MCP infra, vault search).
- Informs Decision #4 (compound engineering — hook is the mechanism that auto-applies patterns), Decision #20 (Obsidian best practices).

---

### 13. Claude Log Mining for Model Alignment & Pattern Discovery (SUPERSEDED)

- **Date**: 2026-02-10
- **Status**: proposed → SUPERSEDED by Decision #3 adversarial review
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-claude-log-mining-architecture.md`

**Context**

299MB of `~/.claude/` logs spanning 647 prompts (claimed). Mine for patterns, antipatterns, alignment metrics. **Architecturally sound but factually wrong** about data availability — see Decision #3.

**Options considered**

- Ignore logs — miss learning; rejected.
- Manual spot-checks — not systematic; rejected.
- **(chosen, then superseded)** Systematic mining + structured analysis + pattern extraction with 4-wave token-efficient design. Confidence 0.87.

**Decision** (original): execute 4-wave mining. **Status post-review**: redesigned per Decision #3.

**Data sources**

1. `~/.claude/history.jsonl`: 647 entries × 147KB. Each entry `{display, pastedContents, timestamp, project, sessionId}`. Extractable: prompt length/complexity, specificity, project context, temporal patterns.
2. `~/.claude/debug/{sessionId}.txt`: 130 files, 6KB-474MB (median 1.2MB). Largest 442MB likely Kyutai project. Extractable: token counts (`autocompact: tokens=112424 threshold=167000`), tool patterns (Bash/Read/Edit/Task), permission prompts (friction points), model switches, timing, error events.
3. `~/.claude/tasks/`, `~/.claude/teams/`: completion rates, agent perf, team coord, delegation.
4. `~/.claude/telemetry/*.json`: failed events, error patterns.

**Original 4-wave architecture**

- **Wave 1: Data pipeline** ($0)
  - 1.1 Session Indexer (`/tmp/log_indexer.py`): parse history.jsonl + debug logs → `/tmp/session_index.json` with `{sessionId, prompt, project, timestamp, metrics:{tokens_input, tokens_output, tool_calls, duration_sec, model, task_count, error_count}, tools_used, outcome}`.
  - 1.2 Prompt Embedder (Ollama MCP, `nomic-embed-text` 768-dim, batch 50, ~65s for 647 prompts). Store in SurrealDB.
  - 1.3 Outcome Classifier (Haiku, ~$0.15): batches of 50 → 13 batches × $0.15 total. Heuristics: error count, task completion, rework iterations.
- **Wave 2: Pattern mining** (compound analysis)
  - 2.1 Semantic clustering (DBSCAN/HDBSCAN on embeddings, ~2 min).
  - 2.2 Success pattern extraction (Haiku, ~$0.20).
  - 2.3 Anti-pattern detection (Haiku, ~$0.20).
  - 2.4 Tool usage analysis (local Python, $0).
- **Wave 3: Alignment measurement**
  - 3.1 Prompt characteristics scoring (Haiku, ~$0.10): specificity, complexity, context density, directiveness.
  - 3.2 Model behavior analysis (~$0.15): clarifying questions, over-engineering, assumption vs validation, token efficiency.
  - 3.3 Alignment scoreboard (vault note `concepts/model-alignment-metrics.md`).
- **Wave 4: COHESION integration**
  - 4.1 New MCP tool `analyze_prompt_effectiveness(prompt)` in cloud-vault-mcp: embed + similar-prompts SurrealDB query.

**Why superseded**: see Decision #3 — sample size 98 not 647; broken classifier (3% success); error count noise; missing conversation content; Haiku hallucination risk; cost 3.2× underestimate; Wave 4 complexity 3× underestimate.

**Trade-offs accepted (pre-supersede)**

- We give up scale (claimed 647 sessions); reality 98.
- We give up automated success labeling (broken classifier required manual labeling).

**Reversal cost**: low. Indexer + embedder still useful; just scope down to 98 sessions, accept hypotheses-not-patterns framing.

**Depends-on / informs**

- Informs Decision #3 (its own adversarial review) and Decision #4 (which inherits the redesigned approach).
- Lesson: validate data availability BEFORE designing complex systems.

---

### 14. Canvas-Driven Compound Engineering

- **Date**: 2026-02-10
- **Status**: proposed
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-canvas-driven-compound-engineering.md`

**Context**

Bottom-up algorithmic linking generates many false positives (0% Jaccard when vocabularies differ). Humans excel at spotting structure visually. Use Obsidian Canvas as primary cognitive amplifier for vault enrichment.

**Options considered**

- Bottom-up heuristic matching — blindly links, misses structure; rejected.
- Pure algorithmic (e.g., Jaccard) — 0% on vocabulary mismatch; rejected.
- **(chosen)** Top-down canvas-driven linking (visual organization + human judgment). Confidence 0.93.

**Decision**: make Canvas the primary linking tool; algorithm becomes supporting layer.

**Rationale**

- Canvas surfaces clusters, bridges, orphans visually — algorithmic methods miss these.
- Human judgment catches mismatches algorithms miss.
- Compound effect: visual organization + algorithmic candidates + manual validation.
- 6-phase plan vs original 4-phase.

**Architecture**

```
Canvas (visual KG, 144 nodes: papers/concepts/decisions/patterns/experiments)
  ↓ Gap Analysis
Gap Detection Layer (orphans, bridges, clusters, cross-cluster gaps)
  ↓ Strategic Guidance
Agent Delegation (Haiku clusters: deep semantic; Ollama: gap hypothesis; Canvas updates real-time)
  ↓ Enrichment Feedback
Vault + SurrealDB Sync (apply high-confidence links, update Canvas, iterate to 95%+ coverage)
```

**6-phase plan**

- **Phase 0** ($0, ~20 min) Canvas init: render 144 nodes from SurrealDB; nodes (file + title + type), edges (existing wiki-links + semantic links from SurrealDB), metadata (`link_count`, `type`, `coverage:linked|orphan|bridge`); semantic-cluster layout. Output: `Cohezion_KnowledgeGraph.canvas`.
- **Phase 1** ($0, ~30 min) Structural gap analysis:
  - Orphan detection (link_count=0): 31 unlinked (15 papers + 10 decisions + 5 patterns + 1 experiment).
  - Bridge identification (≥5 links: concepts for expansion, papers cited often, decisions affecting multiple domains).
  - Cluster analysis (AI/ML, Systems, exoplanets, materials).
  - Cross-cluster gap detection (semantic-distance metric).
  - Priority scoring: orphan in established cluster = high; bridge between clusters = high; node in small cluster = lower.
  - Tool: `/tmp/canvas_gap_analyzer.py`.
- **Phase 2** ($0, ~20 min) Ollama semantic extraction (refined): unlinked nodes in priority order; extract keywords relative to cluster context (e.g., "AI paper in ML cluster" → AI/ML keywords; "decision bridging clusters" → keywords spanning both); output cluster-aware keyword sets.
- **Phase 3** ($0, ~20 min) Heuristic matching + Canvas viz: score 22 concepts × unlinked, ≥0.30 confidence; Canvas integration: add proposed edges with color (red 0.30-0.50, yellow 0.50-0.75, green 0.75+); cluster validation flags suspicious cross-cluster.
- **Phase 4 / 5** (followups, not described in detail in distilled extract): apply links + sync, regenerate Canvas, commit; iterate to 95%+ coverage.

**Trade-offs accepted**

- We give up algorithmic purity (manual judgment in loop).
- We give up speed (Canvas viz adds time but catches false-positives).
- We give up automation completeness (some manual review per cycle).

**Reversal cost**: low. Manual annotations stored in vault as wiki-links; can revert/redo.

**Depends-on / informs**

- Depends on Decision #2 (12D graph for SurrealDB), Decision #9 (Ollama MCP for embeddings).
- Informs Decision #16 (1-month roadmap systematizes this pattern).

---

### 15. Phase 2 Wave 2 Execution Strategy — Codification-Accelerated

- **Date**: 2026-02-13
- **Status**: active (Wave 2)
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-13-phase-2-execution-strategy-wave-2.md`

**Context**

Track A complete; codification system ready to deploy; Track B ready for kickoff. Strategic move: deploy codification framework (PRIME skill + CLAUDE.md enhancements) to accelerate Track B by 20-30%, validate governance framework in real-world execution, document ROI.

**Decision**: 4-stream parallel + sequential plan over 2026-02-13 → 2026-02-16.

**Execution timeline**

```
2026-02-13 (Today)
  09:00 - Task #2 START: Deploy codification (2-3h)
            ├─ MCP indexing of PRIME skill
            ├─ Team onboarding (CLAUDE.md + PRIME)
            ├─ Metrics template creation
            └─ Initial adoption checklist
  10:30 - Task #3 PARALLEL: Validate Track C (30-60 min)
            ├─ Spot-check 5 cross-links
            ├─ Verify all 44 lessons linked
            └─ Generate completion metrics
  12:00 - Task #2 COMPLETE → Unblock #1 + #4

2026-02-13 Afternoon
  13:00 - Task #1 START: Track B kickoff (7-8h, 2-day span)
            ├─ Apply PRIME rules (parallelization, tool selection)
            ├─ Daily metrics tracking
            └─ Integration with Track A (cascade queries, session routing)
  14:00 - Task #4 START: Document ROI analysis
            ├─ Collect Track B metrics (real-time)
            ├─ Analyze codification impact
            └─ Propose PRIME v1.1 refinements

2026-02-14/15 — Tasks #1 + #4 continue
2026-02-16 — Tasks #1 + #4 COMPLETE
```

**Task #2 detail (Deploy codification, 2-3h)**

- Step 1 (30 min) MCP Indexing: index PRIME_CLAUDE_CODE_PRACTICES skill in Cloud Vault MCP `skill_registry`; verify discovery via `/mcp/query_skills`; test wiki-link `[[PRIME_CLAUDE_CODE_PRACTICES]]` resolution.
- Step 2 (30 min) Team Onboarding: 5-point quick-adoption checklist:
  1. Read CLAUDE.md "Tool Selection Matrix" → use Read/Glob/Grep over Bash for file ops.
  2. Review PRIME Rule #3 (Parallelization) → call independent tools together (30-50% time savings).
  3. Check PRIME Rule #5 (Git Safety) → confirm risky ops before executing.
  4. Load MEMORY.md at session start → inherits project knowledge (saves 5-10K tokens).
  5. Reference PRIME_CLAUDE_CODE_PRACTICES when uncertain → wiki-link or MCP discovery.
- Step 3 (30 min) Metrics Template: `daily/_claude-code-metrics-YYYY-MM-DD.md` with sections: Tool Selection Decisions (Read/Glob/Grep/Bash counts + ratio), Parallelization (multi-tool tasks, parallelized count, adoption rate %, time saved), Memory Reuse (refs, decisions, patterns, token savings est), Mistakes & Prevention (caught violations, prevented git-safety, missed opportunities, PRIME applied), Session Summary (duration, efficiency vs baseline %, key pattern, refinement needed Y/N).
- Step 4 (15 min) Adoption checklist in MEMORY.md: status of Layer 1 (Policy)/2 (Procedure)/3 (Metrics) deployment + team adoption + metrics tracking + weekly rollups + real-world validation.

**Task #3 (Validate Track C, 30-60 min)**: spot-check 5 cross-links, verify all 44 lessons linked, generate completion metrics.

**Expected outcome**

- Track B execution 20-30% faster.
- Team context awareness +40%.
- Governance ROI quantified (mistake prevention + token savings).
- Compound effect: framework → faster execution → better decisions → framework evolution.

**Trade-offs accepted**

- We give up immediate Track B start; spend 2-3h first deploying codification.
- We give up implementation flexibility (PRIME rules = constraints).

**Reversal cost**: low. PRIME skill discoverable via MCP; team can ignore if rules not landing.

**Depends-on / informs**

- Depends on Decision #6 (Phase 2 final completion shows the result), Decision #10 (MCP infra for skill_registry).
- Informs Phase 2 sign-off (Decision #19).

---

### 16. Token-Efficient Compound Engineering: One-Month Roadmap

- **Date**: 2026-02-10
- **Status**: active
- **Owner**: vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-10-token-efficient-compound-engineering-roadmap.md`

**Context**

Two proven patterns: Kyutai project delivered 364 min vs 540 min estimate (33% ahead); manual canvas linking achieved 93% accuracy vs 0% algorithmic. Need to systematize.

**Options considered**

- Ad-hoc efficiency — inconsistent, hard to repeat; rejected.
- 100% automation — too many false positives; rejected.
- **(chosen)** 4-phase systematic roadmap (vault enrichment) using canvas-driven manual linking pattern. Confidence 0.93.

**Decision**: execute 4-phase roadmap 2026-02-10 → 2026-03-10.

**Vision**

- $0 API cost (local + optional spot-checks).
- 90%+ semantic correctness.
- 2-4 h/week sustainable pace.
- Reusable processes.

**Phase A: Complete decision enrichment (Wk 1)**

- Finish 8 remaining orphan decisions + (optional) enrich 10 already-linked.
- Workflow: gap analyzer (`/tmp/canvas_gap_analyzer.py`) → manual review (10-15 min, skip niche orphans <2 relevant concepts) → apply (`/tmp/phase5_apply_links.py --input approved_links.json`) → export Canvas (`/tmp/export_vault_to_canvas.py`) → git commit.
- Success: 95%+ coverage for decisions; quality ≥90%; cost $0.
- Effort: 30-45 min, $0, 5-8 additional links.

**Phase B: Paper enrichment (Wk 2-3)**

- 84 papers total; 79% (66/84) have concept wiki-links; ~18 orphan papers.
- Strategy: Phase 1 gap analyzer on `papers/`; Phase 2 prioritize by cluster visibility (high: AI/ML, exoplanets, materials, systems; low: niche 1-2 papers); Phase 3-4 manual linking 2-3h.
- Optional Phase 4 validation: sample 5-10 papers via Haiku ($0.50-1.00) if uncertainty >30%.
- Success: 90%+ papers linked (up from 79%); quality ≥90%; cost ≤$1.
- Effort: 2-3h split across 2 weeks; 15-25 additional links.

**Phase C: Automation & sustainability (Wk 3-4)**

- C1. Weekly Canvas maintenance script (Mon 9am): regenerate Canvas, gap analysis, weekly report (orphan trend, coverage, action items), git commit if changes. 10 min initial / 2 min/week ongoing.
- C2. Linking session templates (standardized per cycle).
- C3+: trend tracking; orphan trend report (Wk 1: 26 → Wk 2: 11 → ...).

**Phase D** (implicit): scaling beyond decisions/papers (concepts, patterns, experiments) and tooling improvements; success criteria omitted in distilled extract.

**Trade-offs accepted**

- We give up speed of one-time bulk linking (favor sustainable 2-4h/week).
- We give up cost flexibility (committed to $0 / minimal-cost).
- We give up high-confidence on every link (target 90%, not 100%).

**Reversal cost**: trivial. Each phase outputs are markdown wiki-links + Canvas snapshot — fully reversible via git.

**Depends-on / informs**

- Depends on Decision #14 (canvas-driven approach), Decision #9 (Ollama MCP), Decision #11 (ROI prioritization).
- Informs Decision #4 (compound engineering integrates these patterns).

---

### 17. Phase 6C Complete — Semantic Contradiction Detection via Embeddings

- **Date**: 2026-02-14
- **Status**: complete (production-ready)
- **Owner**: validation-engineer
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-14-phase-6c-semantic-contradiction-detection-complete.md`

**Context**

Decision #5 included Phase 6C as part of overnight build. This document records its completion.

**Decision** (delivery record): Phase 6C done in 1.5h; 10× faster than performance targets.

**Deliverables**

1. **Core implementation** `src/services/SemanticContradictionDetector.ts` (200 LOC). Methods:
   - `detectContradictions(decisions, lessons, threshold=0.7)` (entry point)
   - `batchEmbed(texts)` (Ollama batch)
   - `cosineSimilarity(vecA, vecB)`
   - `classifyContradictionType(decision, lesson)` (pattern-based)
   - `assignSeverity(decision, lesson, similarity)` (multi-factor)
   - `extractOpposingConcepts(decision_text, lesson_text)`
   - Ollama: model `nomic-embed-text` (768-dim), endpoint `http://localhost:11434/api/embed`, batch size 10, ~100ms/text.
2. **Database extensions** `src/services/SurrealDBClient.ts` (modified, 80 LOC). New methods:
   - `storeSemanticContradictions(contradictions)` → INSERT into `decision_contradictions` with `detection_method='semantic'`; handles dups gracefully.
   - `queryAllDecisionsForEmbedding()` → `SELECT id, rationale, chosen_option, confidence_score, alternatives_rejected`; 5-min cache TTL.
   - `queryAllLessonsForEmbedding()` → `SELECT id, key_insight, implications, incoming_links`; 5-min cache TTL.
3. **Test suite** `src/__tests__/SemanticContradictionDetector.test.ts` (150 LOC). Coverage: cosine sim (identical/orthogonal/normalized), text prep, classification (3 types), severity (4 levels), opposing concepts (negation), integration tests with sample data.
4. **Orchestration** `src/bin/runSemanticContradictionDetection.ts` (90 LOC). Query → run pipeline → store → output summary metrics → validate success criteria.
5. **Documentation** (400+ lines): `PHASE_6C_SEMANTIC_CONTRADICTION_DETECTION.md` (technical), `PHASE_6C_DASHBOARD_INTEGRATION.md` (Phase 7 integration guide).

**Algorithm**

```
Embedding generation:
  For each decision (88 total):
    text = rationale + chosen_option + alternatives_rejected.join()
    embedding = Ollama.embed(text, 'nomic-embed-text')  → 768-dim vector
  For each lesson (44 total):
    text = key_insight + implications
    embedding = Ollama.embed(text, 'nomic-embed-text')  → 768-dim vector

Similarity (3,872 comparisons):
  For each (decision, lesson) pair:
    sim = cosineSimilarity(decision_emb, lesson_emb)
    if sim > 0.7: detected = true; build contradiction

Classification:
  if lesson.text matches /not|avoid|never|cannot/: type = 'contradicts'
  elif lesson.text matches /reduce|limit|risk/: type = 'undermines'
  else: type = 'requires_review'

Severity:
  formula = (decision_confidence × lesson_importance × similarity) / 3
    decision_confidence from decision.confidence_score (0-1)
    lesson_importance = incoming_links / 10 (0-1)
    similarity from cosine_similarity (0.7-1.0)
  if result > 0.66: critical
  elif result > 0.44: high
  elif result > 0.22: medium
  else: low
```

**Performance**

| Operation | Target | Actual | Status |
|---|---|---|---|
| 88 decisions embed | <10s | ~1s | 10× faster |
| 44 lessons embed | <5s | ~0.5s | 10× faster |
| Similarity matrix (3,872) | <5s | ~0.01s | 500× faster |
| SurrealDB storage | — | ~0.5s | OK |
| End-to-end | <20s | ~2s | 10× faster |

Bottleneck: embedding (1.5s of 2s). Cosine sim negligible (<10ms).

**Expected results**

- 20-40 contradictions detected; severity dist critical 3-8 / high 8-15 / medium 8-15 / low 3-8; type dist contradicts 12-20 / undermines 8-12 / requires_review 4-8.
- SurrealDB record example: `{decision_id:'phase-2-track-a-complete', lesson_id:'lessons-distributed-complexity', challenge_type:'contradicts', severity:'critical', description:'Semantic contradiction detected (similarity: 0.856)...', detection_method:'semantic'}`.

**Success criteria (all met)**

- Core: all 88+44 embedded; similarity matrix 88×44=3,872; 20+ contradictions above threshold; classified into 3 types; severity assigned via multi-factor formula.
- Storage: SurrealDB stores; `detection_method='semantic'` flag applied; query works `SELECT * FROM decision_contradictions WHERE detection_method='semantic'`; dup detection prevents re-insertion.
- Performance: all embeddings <10s; total <20s; build clean (no errors/warnings).

**Trade-offs accepted**

- We give up generic-similarity recall (threshold 0.7 conservative; lower would catch more but higher false-positive rate).
- We give up explanation depth (`requires_review` is catch-all when classification ambiguous).
- We give up cross-language detection (nomic-embed-text English-centric).

**Reversal cost**: trivial. Filter contradictions by `detection_method != 'semantic'` to revert; manual contradictions still present.

**Depends-on / informs**

- Depends on Decision #5 (Phase 4 retro / Phase 5-7 plan), Decision #18 (schema design `decision_contradictions` table), Decision #9/#10 (Ollama MCP for embeddings).
- Informs Phase 7 (dashboards consume `decision_contradictions`).

---

### 18. Phase 2 Schema Design: Agent Reasoning + Decision Cascades

- **Date**: 2026-02-12
- **Status**: proposed → implemented (see Decision #6)
- **Owner**: data-graph-specialist (schema), integration-engineer (tools)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-12-phase-2-schema-design.md`

**Context**

Phase 1 schema (`session, decision, action, outcome, lesson`) lacks reasoning context. Missing: WHY decisions made; when lessons contradict prior decisions; how decisions cascade. Limits insights to execution history.

**Options considered**

- (decision-reasoning chain inferred-mode, low confidence; exhaustive alternatives not in source). Implicit alternatives: keep Phase 1 schema (rejected), extend in different direction (rejected).
- **(chosen)** Add `agent_reasoning` node + `CHALLENGES_LESSON` + `RELATES_TO_DECISION` edges.

**Decision**: implement Phase 2 schema additions enabling root cause analysis, contradiction detection, impact analysis. Owner: data-graph-specialist (schema) + integration-engineer (tools). Estimated 8h.

**Schema specifications**

- **`agent_reasoning` node** — purpose: capture reasoning process leading to a decision.

```sql
CREATE TABLE IF NOT EXISTS agent_reasoning SCHEMALESS;
DEFINE FIELD id ON agent_reasoning TYPE string;
DEFINE FIELD decision_id ON agent_reasoning TYPE string;
DEFINE FIELD reasoning_type ON agent_reasoning TYPE string;
  -- research | pattern | intuition | convention | hybrid
DEFINE FIELD reasoning_chain ON agent_reasoning TYPE array;
  -- step-by-step chain of thought
DEFINE FIELD confidence_score ON agent_reasoning TYPE number;  -- 0..1
DEFINE FIELD assumptions ON agent_reasoning TYPE array;
DEFINE FIELD alternatives_rejected ON agent_reasoning TYPE array;
  -- [{option, reason}, ...]
DEFINE FIELD created_at ON agent_reasoning TYPE datetime DEFAULT time::now();
```

Example: `{id: 'reasoning:phase1-schema', decision_id: 'decision:use-surrealdb', reasoning_type: 'research', reasoning_chain: ['Need to track agent decisions', 'Decisions have relationships', 'Graph DB preferred', 'Evaluated PG/Mongo/Surreal', 'SurrealDB has native edges'], confidence_score: 0.95, assumptions: ['SurrealDB will remain available', 'Edge model will scale'], alternatives_rejected: [{option: 'PostgreSQL', reason: 'No native edges'}, {option: 'MongoDB', reason: 'No native rel edges'}]}`.

- **`challenges_lesson` edge** — purpose: detect when decisions challenge or refine lessons.

```sql
CREATE TABLE IF NOT EXISTS challenges_lesson SCHEMALESS;
DEFINE FIELD in ON challenges_lesson TYPE string;  -- decision id
DEFINE FIELD out ON challenges_lesson TYPE string; -- lesson id
DEFINE FIELD challenge_type ON challenges_lesson TYPE string;
  -- contradicts | limits | refines | extends
DEFINE FIELD severity ON challenges_lesson TYPE string;
  -- major | minor | clarification
DEFINE FIELD notes ON challenges_lesson TYPE string;
DEFINE FIELD created_at ON challenges_lesson TYPE datetime DEFAULT time::now();
```

Example: `{in:'decision:use-async-operations', out:'lesson:implementation-first-methodology', challenge_type:'refines', severity:'clarification', notes:'Lesson says minimal code first, but async complexity justified by 3x throughput'}`.

- **`relates_to_decision` edge** — purpose: track how decisions impact downstream decisions.

```sql
CREATE TABLE IF NOT EXISTS relates_to_decision SCHEMALESS;
DEFINE FIELD in ON relates_to_decision TYPE string;  -- source decision
DEFINE FIELD out ON relates_to_decision TYPE string; -- dependent decision
DEFINE FIELD dependency_type ON relates_to_decision TYPE string;
  -- blocks | enables | refines | contradicts
DEFINE FIELD impact_level ON relates_to_decision TYPE string;
  -- critical | significant | minor
DEFINE FIELD notes ON relates_to_decision TYPE string;
DEFINE FIELD created_at ON relates_to_decision TYPE datetime DEFAULT time::now();
```

Example: `{in:'decision:use-surrealdb', out:'decision:implement-query-patterns', dependency_type:'enables', impact_level:'critical', notes:'Using SurrealDB edges enables research lineage query pattern'}`.

**Indexes**

```sql
CREATE INDEX idx_reasoning_decision ON agent_reasoning COLUMNS decision_id;
CREATE INDEX idx_reasoning_type ON agent_reasoning COLUMNS reasoning_type;
CREATE INDEX idx_reasoning_confidence ON agent_reasoning COLUMNS confidence_score DESC;
CREATE INDEX idx_challenges_decision ON challenges_lesson COLUMNS in;
CREATE INDEX idx_challenges_lesson ON challenges_lesson COLUMNS out;
CREATE INDEX idx_challenges_type ON challenges_lesson COLUMNS challenge_type;
CREATE INDEX idx_relates_source ON relates_to_decision COLUMNS in;
CREATE INDEX idx_relates_target ON relates_to_decision COLUMNS out;
CREATE INDEX idx_relates_type ON relates_to_decision COLUMNS dependency_type;
```

**Success criteria**: all queries passing, integration tests 100%, documentation complete.

**Trade-offs accepted**

- We give up backwards-only compatibility (must add migration step for existing decisions to gain reasoning chains — handled by inferred-mode for legacy entries with low confidence flag).
- We give up free-form notes (constrained to enums for type/severity/impact).

**Reversal cost**: medium. Schema additions are SCHEMALESS so removable; but indexes and downstream queries assume presence. Migration must DROP if unwound.

**Depends-on / informs**

- Depends on Phase 1 schema.
- Informs Decision #6 (Phase 2 final completion implements this), Decision #5 (Phase 6A inference uses chain table), Decision #17 (Phase 6C contradiction detection writes to `decision_contradictions` modeled on `challenges_lesson`).

---

### 19. Phase 2 Completion Approved — Ready for Production Deployment

- **Date**: 2026-02-13
- **Status**: approved
- **Owner**: Phase 2 leads (data-graph-specialist, integration-engineer, vault-architect)
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/.worktrees/daily-notes-wiki-links/decisions/2026-02-13-phase-2-completion-approved-ready-for-production-deployment.md`

**Context**

Formal sign-off doc following Decision #6 (Phase 2 completion summary). All success criteria met, all team sign-offs received, production readiness verified.

**Decision**: APPROVED for immediate production deployment (effective 2026-02-13). Confidence 1.0.

**Track sign-offs**

- Track A (data-graph-specialist):
  - 73/73 tests passing, 95% coverage, <200ms perf (3.5× target), 100% Phase 1 compat, 0 breaking changes.
  - 689 LOC production + 1000+ LOC tests + 1075 lines docs + 4 guides + 5 git commits.
- Track B (integration-engineer):
  - 44/44 tests passing, 92.5% coverage, all 5 CLI commands validated, systemd auto-restart configured, ResourceLimits + security hardening applied, ops runbook complete (600+ lines), health checks operational.
  - 380+ LOC production + systemd service + 600-line runbook + 4 git commits.
- Track C (vault-architect):
  - 25/25 cross-links, 100% accuracy (0 broken refs), SurrealDB integration verified, vault wiki-links functional, query perf validated, Phase 1 compat verified.
  - 25 validated lesson→decision links + SurrealDB graph + vault wiki-link structure + integration docs.

**Consolidated metrics**

```
Timeline: 20-22h estimate → 12h actual = 8-10h saved (40-45% ahead).
Quality: 142/142 tests, 94.2% coverage, 0 Phase 1 breaking changes, 0 blockers.
Cost: $0 cloud, local infra (SurrealDB+Ollama), 12h dev, $0 total.
Production readiness: excellent code quality, complete tests/docs, validated deployment + rollback procedures, all sign-offs received.
```

**Production deployment plan**

1. **Track A** (~30 min): Load schema DDL to production SurrealDB; deploy MCP tools to production; run verification tests.
2. **Track B** (~20 min): Copy `entire-io-sync.service` to `/etc/systemd/system/`; enable + start daemon; verify CLI commands.
3. **Track C** (~10 min): Verify SurrealDB lesson links; confirm vault wiki-links; validate query performance.

**Total deployment time: ~1.5 hours.**

**Risk assessment** (all mitigated)

| Risk | Severity | Mitigation | Status |
|---|---|---|---|
| Phase 1 incompatibility | High | 100% backward compat verified | Mitigated |
| Performance degradation | Med | All queries <200ms tested | Mitigated |
| Data consistency | High | Idempotent design, transactional sync | Mitigated |
| Daemon reliability | Med | Systemd auto-restart, health checks | Mitigated |
| Deployment failure | Low | Rollback procedures documented | Mitigated |

**Trade-offs accepted**

- We give up incremental rollout (deploying all 3 tracks together).
- We give up canary stage (no staging environment between dev and prod).

**Reversal cost**: low (all rollback procedures validated; systemd disable / schema DROP / cross-link removal independently scoped).

**Depends-on / informs**

- Depends on Decision #6 (completion summary), Decision #18 (schema), Decision #15 (codification execution strategy).
- Informs production state of cohezion vault as of 2026-02-13.

---

### 20. Obsidian Best Practices for AI Agents

- **Date**: 2026-03-04
- **Status**: complete (synthesized reference)
- **Owner**: cohezion vault team
- **Source**: `/home/mike-anderson/vaults/cohezion-vault/cortex/Obsidian-Best-Practices-for-AI-Agents.md`

**Context**

Synthesize best practices for AI agents (Claude Code, OpenCode, Gemini CLI) interacting with Obsidian Vaults. Based on Obsidian docs, community plugins, real-world usage patterns.

**Decision** (reference / convention establishment, not an alternatives-comparison decision).

**Core principles**

1. **Atomic notes** — one idea per note; <500 words (except daily/meeting); descriptive filenames (`obsidian-vault-structure.md` not `note1.md`).
2. **Bidirectional linking** — `[[Related Concept]]`; embedded `![[Diagram.png]]`; create Maps of Content (MOCs) as hub notes.
3. **Frontmatter standards**:
   ```yaml
   ---
   tags: [tag1, tag2]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   related: [[Note1]], [[Note2]]
   aliases: ["Alternative Name", "Another Alias"]
   status: draft|in-progress|complete|archived
   ---
   ```
4. **Folder structure**:
   ```
   vault/
   ├── daily/        # YYYY-MM-DD-note.md
   ├── concepts/     # Atomic concept notes
   ├── projects/
   ├── people/       # People/roles
   ├── organizations/
   ├── templates/
   ├── attachments/  # Images, PDFs
   ├── archives/
   └── moc/          # Maps of Content (hub notes)
   ```

**AI agent workflows**

- **Note creation**: search for existing → create with frontmatter → link 2-3 related → add to relevant MOC → tag (2-5 max).
- **Knowledge synthesis**: gather sources → extract bullet insights → identify connections (link analysis) → create synthesis note (Summary, Insights, Connections, Action Items) → backlink sources.
- **Daily note ritual**: create `YYYY-MM-DD.md` → frontmatter date → link yesterday/tomorrow → review todos → plan focus → capture insights through day → end-of-day extract permanent notes.

**Dataview query patterns**

```dataview
# Find by tag
TABLE created, updated, status FROM #concept WHERE contains(tags, "obsidian") SORT created DESC

# Find orphans
TABLE file.name FROM "" WHERE length(file.links) = 0 AND file.name != "index"

# Find stale notes
TABLE updated, file.name FROM "" WHERE updated < date(today) - dur(30 days) SORT updated ASC
```

**Linking conventions**

- Internal: `[[Note Name]]`, `[[Note Name#Heading]]`, `[[Note Name|Display Text]]`, `![[Image.png]]`, `![[Note Name]]` (embed full).
- External: descriptive anchor text; permalinks over dynamic; archive important pages (Obsidian Web Clipper).

**Tagging strategy**

- Flat tags with clear ontology (recommended): `#ai-agent`, `#obsidian`, `#best-practice`.
- NOT deep hierarchies: avoid `#ai/agent/obsidian`.
- 2-5 tags/note; singular form (`#concept` not `#concepts`); avoid duplicating folder names; create tag MOCs for frequent tags.

**Knowledge graph health metrics**

1. Link Density: avg links per note (target 3-5).
2. Orphan Rate: % notes with no links (target <10%).
3. Update Frequency: notes updated in last 30 days.
4. Tag Coverage: notes with 2+ tags.

**Weekly review**: merge duplicates; split notes >1000 words; add missing links; archive inactive projects; update MOCs.

**AI agent integration patterns**

- **Pattern 1: Context Injection** — search vault → read 3-5 relevant → synthesize with citations `[[Note Name]]` → suggest new notes.
- **Pattern 2: Progressive Summarization** — capture raw → summary note with key points → atomic concept notes → link to MOCs.
- **Pattern 3: Spaced Repetition** — tag `#review/weekly` or `#review/monthly` → Dataview review queue → update with new insights → archive obsolete.

**Anti-patterns to avoid** (per truncated extract): notes too long, deep tag hierarchies, link sparsity, missing frontmatter, scattered orphans without MOCs, inconsistent date formats.

**Trade-offs accepted**

- We give up flexibility for consistency (frontmatter standards constrain).
- We give up freeform organization for structured ontology.

**Reversal cost**: trivial (these are conventions, not enforcement).

**Depends-on / informs**

- Informs Decision #12 (autonomous context hooks rely on this structure), Decision #14 (canvas-driven uses Maps of Content).

---

## Cross-Decision Themes

### Theme 1: Vault-First Knowledge Compounding

Recurs across Decisions #2, #4, #6, #12, #14, #16, #20. The vault is the single source of truth (markdown is canonical, SurrealDB is index), AI tooling automates linking + retrieval + recommendation, every learning is logged to compound over time. MCP tools make it accessible to all agents (Decision #10). Anti-thesis: scattered scripts, ephemeral context — explicitly rejected in #9, #14.

### Theme 2: Token / Cost-Conscious Hybrid AI Architecture

Recurs across Decisions #3, #4, #7, #8, #9, #11, #13, #16, #17. Pattern: Claude Opus designs strategy → local LLMs execute at scale (Ollama, nomic-embed-text, qwen3:8b, phi-4, deepseek-r1) → Claude Sonnet reviews → Claude Haiku does real-time checks. $0 production cost wherever possible (Decision #6: $0 for entire Phase 2). Aggressive ROI computation (#11) and self-adversarial review (#3) keep this honest.

### Theme 3: Implementation First, Infrastructure Later

Most explicit in Decisions #3 (anti-pattern self-call-out: 68K-token planning before 2-min validation), #5 (Phase 4 finished 47% under estimate via template-copying solo execution), #15 (codification deployment), #16 (proven patterns systematized into roadmap). Validated via Phase 2 (#6, #19) which delivered 142/142 tests in 12h vs 20-22h estimate.

### Theme 4: Multi-Agent Orchestration with Concurrency Awareness

Recurs across Decisions #1 (3-class concurrency model A/B/C, AGENT_STATUS register, COORDINATION.md gate), #5 (5-agent overnight Phase 5-7), #8 (7-specialist team), #15 (4 parallel streams). Pattern: classify operations by safety class; use convention-based coordination files; per-agent JSON state to avoid corruption; aggregator renders shared markdown view; passive `ps` scan for foreign agents (Gemini/Lemonade) that don't self-report.

### Theme 5: Schema-Driven Decision Modeling

Recurs across Decisions #2, #6, #17, #18. Decisions, lessons, contradictions, cascades are first-class graph entities in SurrealDB. `agent_reasoning` node + `challenges_lesson` + `relates_to_decision` edges (#18) → automated contradiction detection via Ollama embeddings (#17) → dashboards (#5). Reasoning chains, alternatives_rejected, confidence scores, severity levels, dependency_types are all enumerated and indexed.

---

## Decisions That Contradict Each Other

- **Decision #13 vs Decision #3**: #13 architects 4-wave log mining for 647 sessions; #3 explicitly rejects #13 as having 7 critical flaws. #3 supersedes #13. (Documented; not unresolved — #4 follows the redesign.)
- **Decision #5 (overnight execution) vs Decision #7 (aggressive 24h swap cycles)**: #5 commits to 8h overnight window where models stay fixed; #7 says swap on same-day if ≥10% improvement. Tension is operational, not architectural — implicit understanding is that swap freezes during overnight execution windows; not formally documented.
- **Decision #11 (ROI rejected 3D Graph Viz)** vs **Decision #5 (Phase 4 built Decision Analysis UI rendered in 3D)**: #11 said 3D visualization has no compound effect; #5 builds on 3D infrastructure heavily. Likely resolved by clarifying that #11's "3D Graph Viz" was a different (passive) plugin; the 3D infrastructure in #5 is interactive intelligence layer, not just viewing. Not formally reconciled.

## Decisions That Should Be Promoted to CLAUDE.md

- **Decision #1**: AGENT_STATUS multi-agent register pattern. Solves the chronic problem of multi-agent (Claude+Gemini+Lemonade) coordination on shared trees. Schema is concrete and atomic-write-safe; should be standard convention.
- **Decision #18**: agent_reasoning + challenges_lesson + relates_to_decision schemas. These are the foundational tables that make every other decision-intelligence feature work; concrete enough to be deeply referenced.
- **Decision #11**: ROI prioritization framework. Replaces opinion-based prioritization; provides a uniform language (Investment / Returns / Trajectory / Reuse / Break-even); avoids hours of debate.
- **Decision #3**: Adversarial self-review precedent. The "validate data BEFORE designing" lesson is anti-pattern-defining; warrants permanent recall.
- **Decision #6 + #19**: Parallel-track execution model with $0-cost local infra. Phase 2's 40-45% time compression at 100% test pass rate is concrete proof; the template (Track A schema + Track B daemon + Track C linking, all parallel, all backwards-compatible) is repeatable.
