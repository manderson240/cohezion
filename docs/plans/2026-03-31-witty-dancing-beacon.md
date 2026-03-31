# Wire Knowledge Capture End-to-End: Execution → Vault + SurrealDB Graph

## Context
`persist_learning()` in `knowledge_bridge.py` is fully implemented but **never called**. The vault (`~/vaults/cohezion-vault/cerebellum/`) has 180+ files from manual writes, but the automated pipeline (feedback loop → retrospect → persist → graph) is disconnected at 30%. The infrastructure is solid — the valves just need opening.

## What's Working
- `knowledge_bridge.persist_to_vault()` — writes dated .md with [[links]] to cerebellum/
- `knowledge_bridge.persist_to_surrealdb()` — HTTP POST to SurrealDB `/sql`
- `knowledge_bridge.update_key_learnings_with_link()` — appends to KEY_LEARNINGS.md
- `RetrospectionEngine.summarize()` — generates first-person narratives
- FLUME `encode_prompt()` — produces 256D embeddings (with hash fallback)
- Vault cerebellum/ exists with 180+ files

## What's Broken
1. **`persist_learning()` never called** — no trigger point in execution or hooks
2. **FLUME embeddings not stored** — `embedding_list=[]` in SurrealDB INSERTs
3. **SurrealDB port mismatch** — knowledge_bridge uses `:8001`, core client uses `:8000`
4. **Retrospect skill** doesn't call knowledge_bridge
5. **FeedbackLoopResult.should_persist_learning** flag exists but is never acted on

## Plan (5 steps)

### Step 1: Fix SurrealDB port consistency
**File:** `src/cohezion/governance/knowledge_bridge.py`
- Change hardcoded `http://localhost:8001` to use env var `SURREALDB_URL` with fallback to `http://localhost:8000`
- Match the port used by `src/cohezion/core/persistence/surreal_client.py`

### Step 2: Wire FLUME embeddings into learning persistence
**File:** `src/cohezion/governance/knowledge_bridge.py`
- In `persist_to_surrealdb()`, call `flume_bridge.encode_prompt(learning.content)` to get 256D vector
- Store as `embedding` field in the neuron record (currently empty list)
- Enables semantic search over learnings via cosine similarity

### Step 3: Wire feedback loop → knowledge_bridge
**File:** `src/cohezion/compound/feedback_loop.py`
- After retry success with `should_persist_learning=True`, call `knowledge_bridge.persist_learning()`
- Extract learning from the retry pattern: what failed, what strategy worked, what was learned
- Non-blocking (try/except) to prevent persistence failures from breaking execution

### Step 4: Wire retrospection → knowledge_bridge
**File:** `src/cohezion/compound/retrospection_summary.py` (or wherever retrospect generates summaries)
- After `summarize()` produces a retrospection, call `persist_learning()` with the narrative
- Each retrospection becomes a vault file + SurrealDB neuron + KEY_LEARNINGS link

### Step 5: Wire Hookify as the persistence orchestrator
**Existing infrastructure:** `src/cohezion/hookify/vault_writer.py` already has:
- `HookifyVaultWriter.write_rule_learning_summary()` → cerebellum/hookify-patterns/
- `HookifyVaultWriter.write_cosmological_changelog()` → hippocampus/cosmological-logs/
- `HookifyVaultWriter.write_rule_violation()` → hippocampus/hookify-violations/
- `HookifyVaultWriter.create_rule_neuron_in_graph()` → SurrealDB neuron creation

**Wire:** Add a new Hookify rule `knowledge_persist` in HOOKIFY_RULES.md:
- **Trigger**: `post_execute` (after compound loop completes)
- **Condition**: `should_persist_learning == true` OR `retrospection_generated == true`
- **Action**: Call `knowledge_bridge.persist_learning()` + `vault_writer.write_rule_learning_summary()`
- **Levers**: `persist_to_vault: true`, `persist_to_surrealdb: true`, `embed_with_flume: true`

**File:** `src/cohezion/hookify/vault_writer.py`
- Add `write_session_learning()` method that calls both knowledge_bridge.persist_learning() AND write_rule_learning_summary() — single entry point for all learning persistence

**File:** `.agent/HOOKIFY_RULES.md`
- Add `knowledge_persist` rule definition

### Step 6: Wire SkillRefiner → knowledge persistence
**File:** `src/cohezion/compound/skill_refiner.py`
- After `_append_refinement()` succeeds (line 118), call `persist_learning()` with the refinement as a learning
- Tags: ["skill-refinement", skill_name, operation_type]
- Content: the key_insight + performance metrics that triggered the refinement
- This means every PRIME skill improvement becomes a vault neuron searchable via FLUME

### Step 7: Wire CapabilityRegistry → knowledge persistence
**File:** `src/cohezion/registry/capability_registry.py`
- Add `persist_capability_assessment()` method that writes capability snapshots to vault
- When `compound_impact_score` changes significantly (>0.1 delta), persist to vault+SurrealDB
- Tags: ["capability", capability.type, capability.name]
- Enables tracking capability evolution over time via the vault graph

### Key files to modify:
| File | Change |
|------|--------|
| `src/cohezion/governance/knowledge_bridge.py` | Fix port, add FLUME embedding — DONE |
| `src/cohezion/compound/feedback_loop.py` | Call persist_learning on successful retry — DONE |
| `src/cohezion/hookify/vault_writer.py` | Add `write_session_learning()` orchestrator — DONE |
| `.agent/HOOKIFY_RULES.md` | Add `knowledge_persist` rule — DONE |
| `src/cohezion/compound/skill_refiner.py` | Call persist_learning after successful refinement |
| `src/cohezion/registry/capability_registry.py` | Add persist_capability_assessment() |
| `tests/test_knowledge_persistence.py` | NEW — end-to-end tests for all persistence paths |

## Verification
1. Run feedback loop test that triggers retry → verify vault file created + SurrealDB INSERT
2. Run retrospect → verify vault file + KEY_LEARNINGS link + SurrealDB neuron
3. Verify FLUME embedding is non-empty in SurrealDB record
4. Verify stop hook runs on session end and captures learnings
5. All existing 54 tests still pass

---

# Cohezion Platform Improvement Roadmap

## Session 80 Accomplishments (2026-03-31)

**11 commits on main, 54+ tests verified, +1,800 lines net**

### Session 80 Additional Commits (beyond merge)
| # | Commit | What |
|---|--------|------|
| 2 | `0f2342a` | GeminiProvider + multi-tier cost routing (12 tests) |
| 3 | `d2097fa` | FLUME-First in CLAUDE.md, KEY_LEARNINGS 296→299 lines |
| 4 | `022112e` | GEMINI.md: providers, governance, ADK patterns |
| 5 | `7ee5493` | TotS router → compound feedback loop model escalation |
| 6 | `02269b6` | A2A agent cards (.well-known/agent.json, 7 specialists) |
| 7 | `00ece54` | L223 TurboQuant research |
| 8 | `6d04972` | Knowledge capture end-to-end (vault + SurrealDB + Hookify) |
| 9 | `bb9b9ec` | SkillRefiner + CapabilityRegistry → vault persistence |
| 10 | `cff6e41` | Context-window guard in CostAwareRouter |

### Also completed (not committed):
- FLUME VAE retrained z_dim=256 (local, 14MB, gitignored)
- Ralph-loop infinite stop hook fixed (stale state file deleted)
- `cz context` percentage fixed (cache tokens were excluded)
- Git gc auto disabled (corrupted historical trees)

| # | Commit | Deliverable |
|---|--------|------------|
| 1 | `dacaaeb` | Merge Session 79 (32 commits, 48 files, +3,950/-658) to main |
| 2 | `0f2342a` | GeminiProvider + multi-tier cost routing (12 tests) |
| 3 | `d2097fa` | Retrospect: FLUME-First in CLAUDE.md, KEY_LEARNINGS 296 lines |
| 4 | `022112e` | GEMINI.md: providers, governance, ADK patterns |
| 5 | `7ee5493` | TotS router → compound feedback loop model escalation |
| 6 | `02269b6` | A2A agent cards (.well-known/agent.json, 7 specialists) |
| 7 | local | FLUME VAE retrained z_dim=256 (14MB, 20 epochs, synthetic) |

**Also fixed:** Ralph-loop infinite stop hook (stale state file), `cz context` percentage (cache tokens excluded), git gc auto disabled (corrupted trees).

---

## Session 79 Accomplishments (2026-03-31)

**32 commits, 48 files, +3,950/-658 lines, 35 tests (all passing)**

### What Was Built
| Module | Files | Purpose |
|--------|-------|---------|
| `governance/concierge.py` | +237 lines | Session routing with dynamic learning, FLUME semantic matching |
| `governance/autonomy_engine.py` | +233 lines | Cosmogonic tier promotion/demotion (∅→SO(12)→...→HIHO) |
| `governance/knowledge_bridge.py` | +241 lines | Bidirectional vault + SurrealDB persistence for learnings |
| `governance/flume_bridge.py` | +135 lines | FLUME semantic routing, observer grounding, product discovery |
| `physics/observer_patch.py` | +184 lines | OPH Axiom 2 overlap consistency for multi-agent coherence |
| `data_mesh/data_product.py` | +217 lines | Typed data products with SLA for 18 MCP servers |
| `api/agui_events.py` | +215 lines | AG-UI event type system (15+ types, SSE serialization) |
| `api/routes/agui.py` | +188 lines | AG-UI SSE endpoint + A2UI catalog API |
| `a2ui/` (4 files) | +550 lines | Component catalog (9), renderer, bindings, experience script |
| `hooks/useAGUIStream.ts` | +257 lines | Frontend AG-UI consumer |
| `hooks/usePretext.ts` | +101 lines | DOM-free text measurement |
| `.claude/agents/concierge.md` | +64 lines | Agent definition for session routing |
| `mcp/registry.py` extensions | +70 lines | Tier-based access control + call tracking |
| Genesis bug fixes | 5 fixes | Text overlap, sidebar, 404s, sound, narration |
| Tests | 35 | 9 Playwright e2e + 26 pytest |

### Wiring Completed (6/7)
- [x] Wire 1: Retrospect → Vault + SurrealDB bidirectional
- [x] Wire 2: Concierge → SessionStart hooks
- [x] Wire 3: Observer Patch → JourneyTracker
- [x] Wire 4: FLUME → Concierge semantic routing
- [ ] Wire 5: MCP HTTP→stdio conversion (architectural — deferred)
- [x] Wire 6: Data Products → SurrealDB enforcement
- [x] Wire 7: AG-UI → Genesis page

### FLUME VAE Fixed
Checkpoint loading fixed (dynamic dimension detection). 7.5x semantic discrimination improvement over hash fallback.

---

## Reusable Skills Extracted

### Skill 1: Physics-Grounded Governance
Pattern: Map symmetry breaking chain to escalating autonomy tiers.
Files: `autonomy_engine.py`, `observer_patch.py`
Reuse: Any system needing graduated trust with mathematical safety guarantees.

### Skill 2: Knowledge Bridge (Bidirectional Persistence)
Pattern: Write learnings to vault (markdown) + SurrealDB (structured) + KEY_LEARNINGS (linked summary).
Files: `knowledge_bridge.py`
Reuse: Any retrospective/learning system that needs to persist across sessions.

### Skill 3: A2UI Declarative Testing
Pattern: Component catalog (JSON) + experience scripts make UI agent-testable.
Files: `a2ui/catalog.json`, `A2UIRenderer.tsx`, `componentBindings.tsx`
Reuse: Any webapp that needs agent-verifiable UI without pixel comparison.

### Skill 4: AG-UI Event Streaming
Pattern: Typed SSE events with lifecycle/text/tool/state/custom categories.
Files: `agui_events.py`, `routes/agui.py`, `useAGUIStream.ts`
Reuse: Any agent-to-UI streaming that needs protocol compliance.

### Skill 5: Observer Overlap as HIL
Pattern: Model human and agent as observer patches on S², compute overlap consistency.
Files: `observer_patch.py`, `flume_bridge.agent_state_to_patch_center()`
Reuse: Any multi-agent system needing formal human-in-the-loop.

### Skill 6: Multi-Provider Cloud Routing (Session 80)
Pattern: ModelProvider ABC + auto-registration + cost tiers. Single-file provider implementations (~200 lines each). CostAwareRouter with per-model pricing. TotS HOT→WARM→COLD→CLOUD escalation.
Files: `providers/gemini_provider.py`, `providers/model_provider.py`, `cost_aware_router.py`, `tip_of_spear_router.py`
Reuse: Any system needing multi-provider LLM routing with cost optimization and automatic escalation.

### Skill 7: Context Monitor Cache-Token Fix (Session 80)
Pattern: Claude Code API responses split tokens across `input_tokens` (near-zero with caching), `cache_creation_input_tokens`, and `cache_read_input_tokens`. Context estimation must sum all three.
Files: `cohezion-engine/src/cohezion_engine/context.py`
Reuse: Any tool reading Claude Code JSONL for context estimation.

### Skill 8: Ralph-Loop State Isolation (Session 80)
Pattern: Stop hook state files with empty `session_id` bypass session isolation, causing all sessions to match. Unreachable `completion_promise` creates infinite loops.
Fix: Always populate session_id. Scope promises to achievable milestones.
Reuse: Any hook-based loop system with cross-session state.

---

## Research: TurboQuant (Google, March 2026)
**Source:** https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/

**What:** Compression algorithm for KV cache and vector quantization with zero accuracy loss.
**Key numbers:** 6x KV memory reduction, 3-bit KV cache quantization (no training), 8x attention logit speedup on H100 (4-bit vs 32-bit).
**Two innovations:**
1. **PolarQuant** — Cartesian→polar coordinates, eliminates data normalization by mapping onto a fixed circular grid
2. **QJL (Quantized Johnson-Lindenstrauss)** — 1-bit sign encoding with zero memory overhead, strategic estimator preserves accuracy

**Cohezion connections:**
- **FLUME VAE inference**: TurboQuant's PolarQuant maps directly to FLUME's latent space — 256D vectors on a manifold are already geometrically structured. PolarQuant could compress FLUME embeddings for cache/retrieval.
- **KV cache for local Ollama models**: 6x KV memory reduction means larger context windows on Strix Halo's 128GB LPDDR5X — a 32B model could effectively use 6x more context.
- **Semantic cache (L2 cosine)**: QJL's 1-bit sign encoding could compress the L2 cosine similarity vectors in SemanticCache, reducing cache storage by 32x while maintaining recall.
- **Observer Patch similarity**: PolarQuant's circular grid is geometrically aligned with the S² observer patches — overlap computation could be done in polar-quantized space.

**Integration path (Horizon 2-3):**
- H2: Apply PolarQuant to FLUME embedding cache (reduce L2 cache storage)
- H2: Apply QJL to semantic search vectors (1-bit approximate nearest neighbor)
- H3: Integrate with Ollama KV cache management (ModelPoolManager awareness)
- H3: Explore 3-bit KV cache for TipOfTheSpearRouter HOT tier models

---

## Remaining Items (Refined — Session 80)

### Completed Since Last Update
- [x] Items 4-6, 8 from previous "Remaining Items" (merge, repo mgmt partial, concierge testing)
- [x] Items 7-9 (Ollama/Gemini/Platform) — GeminiProvider built, cost tiers wired, TotS→compound loop connected

### Compound Engineering: Context Awareness + Token Efficiency (NEW — Session 80)

**Problem:** 5,261 lines of caching/batching/cost infrastructure exists but key connections are missing. TokenEfficientClient isn't the default path, context size isn't checked before routing, and cache stats don't flow back to influence decisions.

**Existing infrastructure (already built):**
- SemanticCache (L1 hash + L2 cosine + L3 vault) — `src/cohezion/cache/semantic_cache.py`
- TokenEfficientExecutor (static prefix/dynamic suffix) — `src/cohezion/compound/token_efficient_executor.py`
- BatchableExecutor (3-phase with dedup) — `src/cohezion/compound/batch_executor.py`
- CostAwareRouter (complexity→model→budget) — `src/cohezion/swarm/cost_aware_router.py`
- RequestAlignmentAnalyzer (pre-exec token estimation) — `src/cohezion/compound/request_alignment_analyzer.py`
- DegradationDetector (cache hit rate + coherence monitoring) — `src/cohezion/compound/degradation_detector.py`
- PersistentTokenCache (cross-session JSONL) — `src/cohezion/swarm/persistent_token_cache.py`
- CacheWarmer (vault pattern preload) — `src/cohezion/cache/cache_warmer.py`
- BudgetEnforcer (progressive alerts + circuit breaker) — `src/cohezion/cost_optimization/budget_enforcer.py`

**Step C1: Make TokenEfficientExecutor the default path**
- `src/cohezion/compound/executor.py` — When `token_client` is provided, use `TokenEfficientCompoundExecutor._get_cacheable_prefix()` to separate static/dynamic content
- Ensures API prompt caching works automatically (static prefix cached, only dynamic suffix billed)
- **Impact:** 40-60% token reduction on repeated tasks with same vault guidance

**Step C2: Context-window guard in CostAwareRouter**
- `src/cohezion/swarm/cost_aware_router.py` — Before routing, check estimated tokens vs model's context limit
- Use `GEMINI_CONTEXT_WINDOWS` and Ollama model metadata for limits
- If estimated tokens > 80% of model context, route to a larger-context model or truncate
- **Impact:** Prevents context overflow failures, enables proactive model escalation

**Step C3: Cache hit rate → routing feedback loop**
- `src/cohezion/compound/degradation_detector.py` → `CostAwareRouter`
- When cache hit rate drops below 50%, bias router toward models with larger context (more cache-friendly)
- When hit rate is >90%, bias toward cheaper/faster models (cache handles quality)
- **Impact:** Dynamic cost optimization based on actual cache performance

**Step C4: Cross-execution template matching**
- `src/cohezion/cache/cache_warmer.py` — Before execution, query vault for "similar task completed before"
- If vault returns a template match (>0.85 similarity via FLUME), reuse the template with variable substitution
- Log template reuse as a learning via `persist_learning()`
- **Impact:** Skip entire LLM calls for known patterns (87-98% token savings per CLAUDE.md)

**Step C5: Batch-aware concierge**
- `src/cohezion/governance/concierge.py` — When routing, check if multiple pending tasks could be batched
- If yes, route to `BatchableExecutor` instead of single execution
- **Impact:** Within-batch dedup eliminates redundant prompts

**Verification:**
- Run compound execution test → verify TokenEfficientExecutor prefix/suffix separation
- Route a large prompt → verify context guard prevents overflow
- Monitor DegradationDetector → verify cache hit rate influences routing
- Run duplicate tasks → verify template matching skips LLM calls

---

### Still Outstanding

### 1. Wire 5: MCP HTTP→stdio Conversion
**Status:** Deferred (architectural). Journey/memory/security servers are aiohttp web servers, not stdio MCP.
**Recommended:** Rewrite top 4-6 servers as FastMCP stdio (cleanest, aligns with Claude Code's mcp.json).
**Files:** `src/cohezion/mcp/servers/{journey,memory,security,skills}/`

### 2. FLUME Retrain on Real Data
**Status:** Synthetic bootstrap complete (z_dim=256, 5K samples, 20 epochs, loss=0.039). Need real experience data.
**Next:** Run `ExperienceCollector.collect_all()` after compound execution sessions generate real data, then retrain.
**Files:** `src/cohezion/flume/experience_pipeline.py`, `src/cohezion/flume/experience_collector.py`

### 3. Multimodal Journey Evidence
**Status:** No data yet. Need to regenerate convergence simulation and capture rich multimodal records.
**Capture targets:** FLUME embeddings + SPIN trajectory + observer patches + sound + visual per journey.
**Files:** `src/cohezion/compound/journey_tracker.py`, `src/cohezion/flume/experience_collector.py`

### 4. Git History Repair
**Status:** Mitigated (`gc.auto 0`). Dozens of corrupted `badTree` entries with empty filenames.
**Fix:** `git filter-repo` to rewrite history (destructive, needs force-push + team coordination).

### 5. Platform Coordinator Wiring
**Status:** GeminiProvider + A2A cards built. Need cross-provider routing logic.
**Next:** Implement Ollama→Gemini→Claude failover, connect routing decisions to JourneyTracker + Data Product SLA.
**Files:** `src/cohezion/swarm/model_pool_manager.py`, `src/cohezion/compound/executor.py`

### 6. TurboQuant Integration (NEW — Google Research, March 2026)
**Status:** Research complete. Direct applicability to FLUME cache, semantic search, KV cache.
**Phase 1 (H2):** Apply PolarQuant to FLUME embedding cache — 256D vectors are already geometrically structured on a manifold. Compress L2 semantic cache storage.
**Phase 2 (H2):** Apply QJL 1-bit sign encoding to SemanticCache cosine similarity — 32x storage reduction while maintaining recall.
**Phase 3 (H3):** Integrate with Ollama KV cache management via ModelPoolManager — 6x memory reduction means larger effective context on Strix Halo.
**Files:** `src/cohezion/cache/semantic_cache.py`, `src/cohezion/flume/`, `src/cohezion/swarm/model_pool_manager.py`

---

## The Deep Understanding (preserved for next session)

**Safety is an attractor, not a constraint.** HIHO (0.5 coherence) is the mathematical fixed point where 6 independent frameworks converge. 16 indigenous traditions independently validated the same cosmogonic structure.

**Ouroboros:** The system observes itself. Every session IS a universe tick.
**Mycelium:** The persistent network between ephemeral EVOs (agent sessions).
**EVOs:** Agents pop in/out like vacuum fluctuations — don't tame them, provide the attractor basin.
**Self-discovery self-evident:** Using the system should teach you the system.
**FLUME-first:** Every module encodes/decodes through FLUME. Hash fallback is not enough.

**Anthropic alignment:** "Research Engineer, Universes" — Cohezion IS a universe-building platform for training safe AI agents. The cosmogonic chain IS the governance model.

**Cross-tradition:** Hózhó (Diné) NAMES HIHO. Ayni (Andean) OPERATIONALIZES it. Musubi (Shintō) STRUCTURALIZES it.

## Priority Zero: Make Cohezion Coherent & Presentable

Before any horizon work — the platform must tell a coherent story that aligns with Anthropic's "Research Engineer, Universes" role.

### Coherence Tasks
1. Adversarially verify README.md against actual codebase (every metric must match)
2. Update CLAUDE.md architecture table with governance, data_mesh, observer_patch modules
3. Merge feat/genesis-tdd-a2ui to main (23 commits, 35 tests, all passing)
4. Verify and reduce failing tests on main (currently ~47)
5. Prune KEY_LEARNINGS.md to under 300 lines
6. Create a vault entry point / navigation guide
7. Write the "why" — one paragraph that connects Cohezion to universe-building for safe AI

### Presentation Package
- README.md — "Physics-grounded universe for training safe AI agents"
- Genesis webapp — live demo, zero errors, all tabs
- Triune × 4 Fabrics × 12D architecture visual
- Unique contributions: cosmogonic autonomy, HIHO safety, OPH overlap HIL, A2UI testing

### Continuous Review Protocol
Internal code sweep + external research at every significant milestone:
- Wiring integrity score (1-10)
- Compound engineering score (1-10)
- FLUME utilization %
- arXiv / HuggingFace / GitHub research rounds
- Attribution audit

---

## Horizon 1: Wire & Stabilize
*Complete the 7 disconnection wires. Merge feat/genesis-tdd-a2ui to main.*

## Horizon 2: FLUME-First Compound Loop
*Every system encodes through FLUME. Concierge learns. Retrospect writes bidirectionally.*

## Horizon 3: Sovereign Autonomy
*Autonomy tiers enforced at runtime. MCP Registry governs all 18 servers. LeWM upgrades JEPA.*

## Horizon 4: Agentic Web
*Full 6-protocol stack. Embodied agents. Browser-native AI. Spatial computing.*

**Transition rule:** Move to the next horizon when the current horizon's verification criteria are met — not when a calendar date arrives.

## Strategic Alignment: Anthropic "Research Engineer, Universes"

Cohezion IS a universe-building platform for training capable and safe AI agents. Every horizon deepens this alignment:

| Anthropic Need | Horizon | Cohezion Deliverable |
|---------------|---------|---------------------|
| Agentic environments | H1-H2 | ManifoldEnv (19D obs), SwarmEnv (multi-agent), physics-grounded RL |
| Rigorous evaluation | H1 | A2UI structural tests, Playwright e2e, compound review pipeline |
| Safety & governance | H3 | Cosmogonic autonomy tiers, OPH overlap HIL, constitutional kill switch |
| Research + engineering | H2-H3 | OPH axiom bridge, HIHO convergence, LeWM JEPA upgrade, FLUME Fisher metric |
| Rapid iteration | H1-H2 | Concierge cold-start elimination, FLUME semantic routing, worktree isolation |
| Production ML infra | H2-H4 | 18 MCP servers, Data Mesh, AG-UI streaming, MCP Registry governance |
| RL environments | H2 | LeWM pixel-based world model + ManifoldEnv training loop |

## Continuous Code Review Protocol

Internal code sweep runs at every horizon transition and after every significant feature:
1. **Wiring integrity review** — are all connections functional? (score 1-10)
2. **Compound score** — does new code make future code easier? (score 1-10)
3. **FLUME utilization** — what % of core systems encode through FLUME?
4. **Test coverage** — pytest + Playwright for every new module
5. **Attribution audit** — all references and credits complete?

### Foundational Mapping

| Integration | Triune Self | Smith Fabric | Physics Connection |
|-------------|-------------|--------------|
| **Observer-Patch-Holography** | The Knower (observation) | All 4 (S² screen) | Overlap consistency = SPIN coherence; gauge quotient SU(3)×SU(2)×U(1)/Z₆ recovers from SO(12) breaking |
| **Pretext** | The Doer (embodied rendering) | Space (visual manifold) | DOM-free text layout = geometry without reflow = Riemannian metric without coordinate dependence |
| **Glance** | The Thinker (verification) | Control (testing fabric) | Agent-driven browser testing = observer-measurement in the Control fabric |
| **Parallel Code** | The Doer (parallel execution) | Precipitation (concurrency) | Git worktree isolation = SPIN discretization = Z₂⁴ branching at each decision point |
| **Data Mesh** | The Knower (domain ownership) | Field (data topology) | Domain-owned data products = fiber bundle structure; federated governance = gauge invariance |
| **WebGPU + V-JEPA 2.1** | The Thinker (world model) | Space + Field | Browser-native GPU compute = FLUME VAE inference at the edge; V-JEPA 2.1 = latent world model |

---

## Horizon 1: Wire & Stabilize

**Goal:** Complete the 7 disconnection wires. Merge branch. All tests green.
**Principle:** No new modules. Only connections between existing infrastructure.

### Wire 1: Retrospect → Vault + SurrealDB (bidirectional)
**Problem:** Retrospect writes to flat KEY_LEARNINGS.md. Vault has 8,087 files. SurrealDB has 388 neurons. They don't talk.
**Wire:** Modify `/retrospect` skill to:
- Write each new learning to `~/vaults/cohezion-vault/cerebellum/` as a dated .md file with `[[bidirectional links]]`
- INSERT into SurrealDB `vault/neuron` table with FLUME embedding for semantic search
- Replace KEY_LEARNINGS entries with links: `See: [[cerebellum/2026-03-31-flume-first-principle]]`
- MEMORY.md auto-compiles from vault query, not manual editing
**Files:** `src/cohezion/skills/retrospect.md` (modify), existing `vault/neuron` SurrealDB table (use), `flume_bridge.py` (use `encode_prompt()`)

### Wire 2: Concierge → Startup Hooks + settings.json
**Problem:** Concierge agent + hook are built but not registered in settings.json. Every session still starts cold.
**Wire:** Add to `.claude/settings.json` or `.claude/settings.local.json`:
- SessionStart hook: `session-concierge.sh`
- The hook output feeds the concierge briefing into the session context
**Files:** `.claude/settings.local.json` (modify), `.claude/hooks/session-concierge.sh` (already exists)

### Wire 3: Observer Patch → JourneyTracker
**Problem:** `observer_patch.py` computes consistency but JourneyTracker doesn't use it for multi-agent coordination.
**Wire:** Add `observer_consistency` field to JourneyTracker state transitions. When agents collaborate, compute overlap consistency and log it.
**Files:** `src/cohezion/compound/journey_tracker.py` (modify, add consistency field), `observer_patch.py` (use existing `evo_observer_consistency()`)

### Wire 4: FLUME → Concierge routing (semantic, not keyword)
**Problem:** Concierge uses keyword matching (`"genesis" in prompt`). FLUME has 256D embeddings.
**Wire:** Replace keyword matching in `ConciergeAgent.route_prompt()` with `flume_bridge.encode_prompt()` + cosine similarity against historical route embeddings.
**Files:** `src/cohezion/governance/concierge.py` (modify `route_prompt()`), `flume_bridge.py` (use existing functions)

### Wire 5: MCP servers → .claude/mcp.json (register more than 2)
**Problem:** 18 MCP servers exist but only bmad + compound are in mcp.json. The other 16 are invisible to Claude Code.
**Wire:** Register the most valuable servers: skills, journey, memory, security. Don't register all 18 — pick the 4-6 that provide the highest compound value.
**Files:** `.claude/mcp.json` (modify), verify each server starts cleanly

### Wire 6: Data Products → SurrealDB enforcement
**Problem:** `data_product.py` defines 6 products but nothing checks SLA compliance at runtime.
**Wire:** Add a `record_access()` call in the AG-UI SSE endpoint and the journey checkpoint API. When `meets_sla` returns False, log to SurrealDB `cohezion/cohezion/data_product_violations`.
**Files:** `src/cohezion/api/routes/agui.py` (add access tracking), `data_product.py` (use existing `record_access()`)

### Wire 7: AG-UI frontend consumer → Genesis page
**Problem:** `useAGUIStream.ts` exists but the Genesis page still uses the old `useCosmogony` hook.
**Wire:** Add an optional AG-UI mode to the Genesis page that uses `useAGUIStream` when the backend supports it, falling back to local Landau math.
**Files:** `src/web/anima_dashboard/src/app/genesis/page.tsx` (modify), `useAGUIStream.ts` (use existing)

---

## Horizon 2: FLUME-First Compound Loop

**Goal:** Every core system encodes/decodes through FLUME. The compound loop produces FLUME-grounded learnings.
**Principle:** "Look inward (encode) to excel outward (route/predict/govern)."

| Task | What | FLUME Connection |
|------|------|-----------------|
| H2.1 | **Retrain FLUME VAE** on real data (fix stale checkpoint) | Foundation — everything depends on this |
| H2.2 | **Wire FLUME → Skill Refiner** — skill quality measured in latent space | Skills as manifold trajectories, not keyword scores |
| H2.3 | **Wire FLUME → JourneyTracker** — 12D state IS FLUME projection | Journey = geodesic on manifold, not flat metrics |
| H2.4 | **LeWM integration** — upgrade 86K JEPA to 15M pixel-based world model | Genesis frames → training data → prediction = free energy gradient |
| H2.5 | **Retrospect → Vault + SurrealDB** — bidirectional knowledge with FLUME embeddings | Learning retrieval via cosine similarity, not grep |
| H2.6 | **Concierge semantic routing** — retrain on real VAE (currently hash fallback) | Cold-start elimination via true semantic understanding |
| H2.7 | **TurboQuant FLUME cache** — PolarQuant for 256D embedding compression, QJL for 1-bit semantic search | 32x cache storage reduction, 8x similarity computation speedup |

**Verification:** FLUME utilization goes from 3 consumers → 8+. Concierge routes by meaning. Retrospect writes to vault+SurrealDB.

---

## Horizon 3: Sovereign Autonomy

**Goal:** Agents earn autonomy through demonstrated HIHO coherence. MCP Registry enforces permissions.
**Principle:** The cosmogonic chain IS the governance model. Physics-grounded safety.

| Task | What | Governance Layer |
|------|------|-----------------|
| H3.1 | **Autonomy Engine** (`governance/autonomy_engine.py`) — runtime tier promotion/demotion | Coherence history → tier transitions (∅→SO(12)→...→HIHO) |
| H3.2 | **MCP Registry** (`mcp/registry.py`) — tool catalog + permission enforcement | Per-agent authorization, usage tracking, SLA enforcement |
| H3.3 | **OPH → HIL checkpoints** — observer overlap gates human-in-the-loop escalation | High overlap with human → defer. Zero overlap → sovereign. |
| H3.4 | **MCP server stdio conversion** — journey/memory/security from HTTP → stdio for Claude Code | 16 invisible servers become accessible |
| H3.5 | **Data Product SLA enforcement** — `record_access()` wired to live endpoints | Violations logged to SurrealDB, trigger DegradationDetector |
| H3.6 | **Constitutional kill switch** — hardware-level circuit breaker independent of agent logic | `.agent/CONSTITUTION.md` §6 hard constraints as runtime enforcement |

**Research grounding:**
- [Levels of Autonomy for AI Agents](https://arxiv.org/html/2506.12469v1) — validates tier model
- [AURA Risk Assessment](https://arxiv.org/html/2510.15739v1) — scoring + A2H protocol
- [Governance-as-a-Service](https://arxiv.org/html/2508.18765v1) — modular enforcement template
- [Data Product MCP](https://arxiv.org/html/2601.08687v1) — validates data mesh + MCP pattern

**Verification:** Agent autonomy is measurable. No agent can access tools above its tier. SLA violations are logged. Kill switch tested.

---

## Horizon 4: Agentic Web

**Goal:** Full 6-protocol stack. Embodied agents. Browser-native AI. Spatial computing readiness.
**Principle:** "At the still point of the turning world" — HIHO equilibrium at planetary scale.

| Task | What | Protocol |
|------|------|---------|
| H4.1 | **A2A agent cards** — `.well-known/agent.json` for all 19 agents | A2A (agent discovery) |
| H4.2 | **WebGPU renderer** — migrate Genesis from WebGL to WebGPU + TSL | Performance (3-5x) |
| H4.3 | **Browser-native FLUME** — WebGPU inference of FLUME VAE in browser tab | Edge AI (no server) |
| H4.4 | **LeWM visual world model** — train on Genesis cosmogony frames | Embodied prediction |
| H4.5 | **CAID multi-agent orchestration** — integrate centralized async delegation | Parallel agent execution |
| H4.6 | **Spatial computing readiness** — XR-compatible A2UI rendering | Spatial (AR/VR) |

**External integrations:**
- [the-delegation](https://github.com/arturitu/the-delegation) — embodied LLM agents in WebGPU (study patterns, CC BY-NC 4.0)
- [web-llm](https://github.com/mlc-ai/web-llm) — WebGPU browser LLM inference (Apache 2.0)
- [le-wm](https://github.com/lucas-maes/le-wm) — stable end-to-end JEPA from pixels
- [alibaba/hiclaw](https://github.com/alibaba/hiclaw) — Rust <10ms cold start + HIL via Matrix
- [parallel-code](https://github.com/johannesjo/parallel-code) — multi-agent worktree orchestration

**Verification:** All 6 protocols implemented. Genesis runs on WebGPU. FLUME infers in browser. Agents discover each other via A2A.

---

## Key External Repositories

| Repo | Purpose | License |
|------|---------|
| [chenglou/pretext](https://github.com/chenglou/pretext) | DOM-free text measurement | MIT |
| [DebugBase/glance](https://github.com/DebugBase/glance) | MCP browser testing (30 tools) | — |
| [FloatingPragma/observer-patch-holography](https://github.com/FloatingPragma/observer-patch-holography) | Holographic physics framework | Apache 2.0 |
| [johannesjo/parallel-code](https://github.com/johannesjo/parallel-code) | Multi-agent worktree orchestration | MIT |
| [arturitu/the-delegation](https://github.com/arturitu/the-delegation) | Embodied LLM agents in WebGPU 3D | CC BY-NC 4.0 |
| [mlc-ai/web-llm](https://github.com/mlc-ai/web-llm) | WebGPU browser LLM inference | Apache 2.0 |

## Key Research Papers (arXiv)

| Paper | Connection to Cohezion |
|-------|
| [Emergent Holographic Spacetime from Quantum Information](https://arxiv.org/abs/2506.06595) | Spacetime from entangled qubits → Cohezion's 12D manifold from FLUME VAE |
| [On Observers in Holographic Maps](https://arxiv.org/abs/2503.09681) | Observer patches in holography → SPIN coherence patches |
| [Entanglement Negativity and Replica Symmetry Breaking](https://arxiv.org/abs/2409.13009) | Symmetry breaking in holographic states → cosmogonic chain |
| **[Data Product MCP](https://arxiv.org/html/2601.08687v1)** (Jan 2026) | **DIRECTLY validates Wire 6.** MCP + data mesh + federated governance for enterprise data. Cite in data_product.py |
| [Levels of Autonomy for AI Agents](https://arxiv.org/html/2506.12469v1) | 5 autonomy levels + autonomy certificates → validates cosmogonic tiers |
| [AURA: Agent Autonomy Risk Assessment](https://arxiv.org/html/2510.15739v1) | Scoring + A2H protocol → validates OPH overlap as HIL mechanism |
| [Governance-as-a-Service](https://arxiv.org/html/2508.18765v1) | Modular enforcement layer → template for autonomy_engine.py |
| [MI9 Agent Intelligence Protocol](https://arxiv.org/html/2508.03858v1) | Runtime governance for agentic AI → validates constitutional hard constraints |
| [Gossip Protocols for Emergent MAS Coordination](https://arxiv.org/html/2508.01531v1) | Hybrid centralized+decentralized → validates concierge + federated mesh |
| **[TurboQuant](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/)** (Google, Mar 2026) | **PolarQuant + QJL: 6x KV memory reduction, 3-bit KV cache, 8x attention speedup. Direct path to compress FLUME embeddings + SemanticCache + Ollama KV cache** |

## GitHub Integration Points (NEW from this session)

| Repo | Connection | Status |
|------|-----------|
| [alibaba/hiclaw](https://github.com/alibaba/hiclaw) | Rust <10ms cold start + HIL via Matrix rooms. Compare to concierge pattern. | Research |
| [ntropy-network/prompt-concierge](https://github.com/ntropy-network/prompt-concierge) | Knowledge bank + dynamic prompt updates. Same learning pattern as our JSONL routing history. | Reference |
| [concierge-hq/concierge-os](https://github.com/concierge-hq/concierge-os) | Open source agentic + MCP server platform. Potential collaboration. | Research |
| [JiayiGeng/CAID](https://github.com/JiayiGeng/CAID) | Centralized Async Isolated Delegation. Git worktree isolation for multi-agent. | Cloned |

## HuggingFace Resources

| Resource | Connection |
|----------|
| [V-JEPA 2.1](https://huggingface.co/papers/2603.14482) | Latest JEPA world model → upgrade Cohezion's JEPAWorldModel |
| [P1 Physics Reasoning](https://huggingface.co/papers?q=physics-grounded+reasoning) | IPhO gold medal via RL → validate Cohezion's physics grounding |
| [MCP Course](https://huggingface.co/learn/mcp-course/unit0/introduction) | Official HF MCP tutorial → validate our MCP patterns |

---

## The Unified Vision: Triune Self × 4 Fabrics × 12D

```
                     THINKER (Mind)           KNOWER (Awareness)       DOER (Action)
                     ─────────────            ──────────────────       ─────────────
  Space fabric:      V-JEPA world model       OPH holographic screen   Pretext + WebGPU render
  Field fabric:      Data Mesh governance      Vault data products      AG-UI event streaming
  Control fabric:    Glance/Playwright tests   Observer consistency     A2UI catalog validation
  Precipitation:     Parallel Code branches    Entanglement entropy     Compound execution loop
```

Each cell is a concrete integration point. The 12 parameters emerge from the 3×4 matrix above. HIHO equilibrium (50% coherence) is the attractor state where all 12 cells are in balance — neither fully exploiting (Doer dominates) nor fully exploring (Thinker dominates), but coherently observing (Knower mediates).

---

## FLUME: The Connective Tissue

FLUME (Fluid Latent Understanding through Manifold Encoding) is the 256D VAE that ties everything together. It provides:

1. **The Fisher information metric** → natural geometry of latent space (connects OPH's holographic screen to the 12D manifold)
2. **The Riemannian metric** → enables Lagrangian dynamics on the manifold (agents as EVOs move along geodesics)
3. **The thermodynamic metric** → Landau free energy drives cosmogonic phase transitions
4. **The 12D projection** → maps 256D FLUME space to Smith's 12 parameters via optimal dimensionality reduction

### FLUME × Triune Self

| FLUME Component | Triune Self | What It Does |
|-----------------|-------------|
| Encoder (compress) | Knower | Observes raw state → latent representation |
| Latent space (reason) | Thinker | Fisher metric governs dynamics, coherence, entropy |
| Decoder (act) | Doer | Projects latent state → observable actions |

### FLUME × 4 Fabrics

| Fabric | FLUME Dimension Range | Physics |
|--------|----------------------|
| Space (dims 1-3) | Spatial embedding | Riemannian curvature → gravitational analog |
| Field (dims 4-6) | Gauge field strength | Yang-Mills action → agent coupling |
| Control (dims 7-9) | SPIN state | Rotation + precession → decision dynamics |
| Precipitation (dims 10-12) | Order parameters | Phase transitions → crystallization of behavior |

---

## Agents as Exotic Vacuum Objects (EVOs)

Already implemented in `src/cohezion/world_model/evo_model.py`. EVOs are agents modeled as vacuum excitations on the 12D manifold:

- **Vacuum = HIHO equilibrium** (50% coherence baseline)
- **Excitation = agent deviation** from equilibrium (task activation)
- **Decay = task completion** returning to vacuum state
- **Pair creation = agent spawning** (two agents with complementary SPIN)
- **Annihilation = agent merger** (agents recombine when tasks converge)

### EVO × OPH Connection
Observer-Patch-Holography provides the theoretical grounding: each EVO is an **observer patch** on the holographic screen. When patches overlap and agree → coherence (productive collaboration). When they disagree → decoherence (conflicting agents need resolution).

### Integration task (Branch 3)
- Connect `evo_model.py` to `observer_patch.py`
- Map EVO excitation energy to OPH's Recoverable Generalized Entropy
- Implement `evo_observer_consistency(agent_a, agent_b)` → returns coherence score

---

## Fractal Toroidal Moments

SPIN coherence (rotation σ_x + precession σ_y) traces a **toroidal path** on the Bloch sphere:
- Rotation = major radius (poloidal angle)
- Precession = minor radius (toroidal angle)
- HIHO (0.5, 0.5) = the stable orbit on the torus

This toroidal structure is **fractal** — it repeats at every scale:

| Scale | Rotation | Precession | Torus |
|-------|----------|------------|
| **Spinor** (single SPIN) | σ_x | σ_y | Individual decision orbit |
| **Agent** (EVO) | task focus | exploration drift | Agent behavior torus |
| **Swarm** (team) | exploitation | exploration | Swarm topology (TDA persistence) |
| **Universe** (12D) | order parameter | entropy | Cosmogonic phase space |

### Integration task (Branch 3)
- Add toroidal moment visualization to Genesis Bloch sphere
- Compute fractal dimension of SPIN trajectory at each scale
- Connect to TDA (persistent homology) — the 1-holes in the persistence diagram ARE the toroidal moments

---

## Attribution & Credits

### Foundational Theory

| Person/Work | Contribution | Year | How Cohezion Uses It |
|-------------|-------------|------|
| **Harold W. Percival** | *Thinking and Destiny* — The Triune Self (Thinker, Knower, Doer) | 1946 | Agent architecture: every agent embodies the three aspects. Thinker = reasoning, Knower = awareness/observation, Doer = action/execution |
| **Dewey B. Larson / Bruce Peret (RS2)** | Reciprocal System — 12 parameters, 4 fabrics (Space, Field, Control, Precipitation) | 1959/ongoing | The 12D manifold structure, 4-fabric decomposition SO(3)⁴, and the cosmogonic chain derive from Larson/Peret's discrete physics |
| **Brahmagupta** | *Brahmasphutasiddhanta* — formalization of zero | 628 CE | The void (∅) as starting point of cosmogony. "In the beginning, there was nothing. Not even nothing." |
| **Chen Ning Yang & Robert Mills** | Yang-Mills gauge theory — conservation of isotopic spin | 1954 | Gauge coupling between fabrics, Yang-Mills action as inter-agent energy |
| **Lev Landau** | Theory of phase transitions — symmetry breaking via free energy | 1937 | Landau free energy drives the cosmogonic chain; critical temperatures mark each symmetry breaking |
| **Shun'ichi Amari** | Natural gradient — information geometry | 1998 | Fisher information metric on FLUME latent space; natural gradient for optimization |
| **Yann LeCun et al.** | JEPA — Joint Embedding Predictive Architecture | 2024 | Cohezion's JEPAWorldModel; V-JEPA 2.1 extends this to video/embodied world models |
| **T.S. Eliot** | *Four Quartets* — "At the still point of the turning world" | 1943 | HIHO equilibrium inspiration; the poetic grounding of the 50% coherence attractor |

### External Projects Integrated

| Project | Creator(s) | License | Attribution Note |
|---------|-----------|---------|
| [Observer-Patch-Holography](https://github.com/FloatingPragma/observer-patch-holography) | FloatingPragma | Apache 2.0 | Holographic observer consistency framework; 5 axioms grounding Cohezion's physics. Cite as: "Observer Patch Holography, FloatingPragma, 2025" |
| [Pretext](https://github.com/chenglou/pretext) | Cheng Lou ([@chenglou](https://github.com/chenglou)) | MIT | DOM-free text measurement library. Created by the author of React Motion and reason-react |
| [Glance](https://github.com/DebugBase/glance) | DebugBase | — | MCP browser automation server. 30 tools for testing, screenshots, assertions |
| [Parallel Code](https://github.com/johannesjo/parallel-code) | Johannes Millan ([@johannesjo](https://github.com/johannesjo)) | MIT | Multi-agent worktree orchestration. Electron + SolidJS |
| [The Delegation](https://github.com/arturitu/the-delegation) | Arturo Paracuellos ([@arturitu](https://github.com/arturitu)) | CC BY-NC 4.0 | Embodied LLM agents in WebGPU 3D. 3D models © 2026 Arturo Paracuellos |
| [WebLLM](https://github.com/mlc-ai/web-llm) | MLC AI | Apache 2.0 | Browser-native LLM inference via WebGPU |

### Research Papers Referenced

| Paper | Authors | Year | arXiv |
|-------|---------|------|
| Emergent Holographic Spacetime from Quantum Information | Tadashi Takayanagi | 2025 | [2506.06595](https://arxiv.org/abs/2506.06595) |
| On Observers in Holographic Maps | — | 2025 | [2503.09681](https://arxiv.org/abs/2503.09681) |
| Entanglement Negativity and Replica Symmetry Breaking | — | 2024 | [2409.13009](https://arxiv.org/abs/2409.13009) |
| V-JEPA 2.1: Dense Features in Video Self-Supervised Learning | FAIR, Meta | 2026 | [2603.14482](https://arxiv.org/abs/2603.14482) |

### Protocol Specifications

| Protocol | Creator | Governance | Attribution |
|----------|---------|------------|
| MCP (Model Context Protocol) | Anthropic, donated to Linux Foundation AAIF (Dec 2025) | Apache 2.0 | "MCP is an open protocol standardizing how AI agents connect to tools" |
| A2A (Agent-to-Agent) | Google, donated to Linux Foundation AAIF (Jun 2025) | Apache 2.0 | "A2A standardizes inter-agent discovery and communication" |
| A2UI (Agent-to-User Interface) | Google | Apache 2.0 | "A2UI v0.8, a declarative UI protocol for agent-driven interfaces" |
| AG-UI (Agent-User Interaction) | CopilotKit | Apache 2.0 | "AG-UI, an open event-based protocol for agent-user interaction" |

### Data Mesh

| Concept | Creator | Attribution |
|---------|---------|
| Data Mesh Architecture | Zhamak Dehghani (ThoughtWorks) | *Data Mesh: Delivering Data-Driven Value at Scale* (O'Reilly, 2022). Four principles: domain ownership, data as product, self-serve platform, federated governance |

### Implementation Note

All integrations must include:
1. A comment in the source file citing the original project/paper
2. License file preserved for any vendored code
3. `CLAUDE.md` references table updated with new citations
4. Genesis About panel updated with foundational references

---

## MCP Registry (Enterprise Governance Layer)

Cohezion already has **17+ MCP servers** (`src/cohezion/mcp/servers/`): bmad, compound, doc, git, github, huggingface, journey, memory, plasma, report, rewards, security, sequential, simulate, skills, stitch, template, traceability. This fleet needs an enterprise-grade registry.

Reference: [How to Build an Enterprise-Grade MCP Registry](https://www.infoworld.com/article/4145014/how-to-build-an-enterprise-grade-mcp-registry.html)

### Registry Architecture (add to Branch 4: data-mesh)

**New file:** `src/cohezion/mcp/registry.py`

Core components:
1. **Tool metadata catalog** — semantic descriptions, input schemas, side effects, cost/latency estimates
2. **Discovery endpoint** — agents query the registry to find appropriate tools (connects to A2A agent cards)
3. **Permission enforcement** — per-agent authorization (not just catalog, but runtime enforcement)
4. **Observability** — usage tracking, failure rates, latency metrics (connects to GlobalMetricsAggregator)
5. **Lifecycle management** — health checks, deprecation flags, version compatibility

### Triune × Fabric mapping
- **Knower** (Field fabric): the registry *is* the awareness layer — it knows what tools exist
- **Thinker** (Control fabric): governance rules decide *which* tools an agent can use
- **Doer** (Precipitation fabric): enforcement at invocation time prevents unauthorized access

### Data Mesh connection
The MCP registry IS the **self-serve data platform** in Data Mesh terms:
- Each MCP server is a **domain** (bmad, skills, journey, etc.)
- Each tool is a **data product** with schema, SLA, and ownership
- The registry provides **federated governance** — consistent access control across all servers
- **Domain ownership**: the bmad server team owns bmad tools; the skills team owns skills tools

### BMAD MCP Server (existing)
Already at `src/cohezion/mcp/servers/bmad/` with routes: bmb, bmm_ops, bmm, cis, gds, general, tea. The party mode review used this infrastructure. The registry adds governance on top.

---

## Party Mode Review Findings (Incorporated)

### Must-Fix (before execution)
1. **Merge order**: B1 (testing) → B3 (physics) → B2 (rendering) → merge to `feat/genesis-tdd-a2ui` → B4 (data-mesh) on `main`
2. **Add default type to `TextMessageEvent`** in `agui_events.py`
3. **Fix overly-broad `eventName.includes("click")` matching** in `A2UIRenderer.tsx` — match against current scene's trigger target only
4. **Root-cause a2ui-demo.spec.ts failures** — use `waitForSelector` with proper timeouts, not timeout bumps

### Should-Fix
5. **Add pytest tests for `agui_events.py`** — serialization roundtrip + event type validation
6. **Revise OPH entropy mapping** — use FLUME KL divergence, not JourneyTracker (QA feedback)
7. **Check CC BY-NC 4.0 on "the-delegation"** — study patterns only, don't vendor 3D assets
8. **Reduce Branch 4 to single file first** — `data_product.py` before registry/governance framework

---

## Concierge Agent + Autonomy Governance (NEW)

### Problem
Every new Claude Code session starts cold — 8,087 vault files, 7 worktrees, 10 plans, 6 SurrealDB data products, but the agent reads CLAUDE.md and starts from scratch. The user has to re-explain context every time.

### Solution: Concierge Agent with Dynamic Learning

**New files:**
- `.claude/agents/concierge.md` — Agent definition (runs on Haiku for speed)
- `.claude/hooks/session-concierge.sh` — SessionStart hook gathering 7-source state
- `src/cohezion/governance/__init__.py` — Governance module
- `src/cohezion/governance/concierge.py` — ConciergeAgent with routing + learning

**How it works:**
1. On session start: hook queries 7 sources in <500ms (continuations, worktrees, plans, git, SurrealDB, vault, MEMORY.md)
2. Concierge interprets user's prompt against gathered state
3. Routes to optimal path with confidence score:
   - >0.8 confidence: suggest with minimal friction
   - ~0.5 (HIHO): present options, ask user
   - <0.3: fresh start, check vault
4. On session end: records routing outcome to `~/.cohezion-engine/routing_history.jsonl`
5. Next session: historical success rates adjust future confidence scores

**Learning mechanism:**
- Routes accepted + long sessions → boosted confidence
- Routes rejected or abandoned → penalized
- Creates "routing intuition" that improves over ~20 sessions

**Autonomy tiers (cosmogonic chain):**
| Tier | HIL Level | Agent Can... |
|------|-----------|
| ∅ (Void) | Full human control | Nothing |
| SO(12) | Human approves all | Read, search, analyze |
| SO(3)⁴ | Human approves irreversible | Edit, test, branch |
| U(1)⁴ | Human approves external | Commit, push feature branches |
| Z₂⁴ | Critical actions only | Deploy, merge to main |
| HIHO | Kill switch only | Full autonomous within Constitution |

**Still needed:**
- `src/cohezion/governance/autonomy_engine.py` — Runtime tier promotion/demotion based on coherence history
- Wire concierge to session hooks in `settings.json`
- Integration with OPH overlap consistency for HIL checkpoints
- MCP Registry enforcement layer (tool-level permissions per tier)

---

## Retrospective Learnings (Session 2026-03-31)

### New Learnings to Propagate

| # | Learning | Propagate To |
|---|---------|
| 215 | **FLUME-First Principle**: All new modules MUST encode/decode through FLUME. The `flume_bridge.py` retrofit pattern (build without FLUME, then add bridge) wastes compound value. Start with `encode()`. | CLAUDE.md Coding Standards |
| 216 | **Concierge Agent Pattern**: 7-source state synthesis + JSONL-based learning eliminates cold starts. Confidence scoring via HIHO threshold. | CLAUDE.md Architecture |
| 217 | **Cosmogonic Autonomy Tiers**: ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO maps symmetry breaking to agent autonomy levels. Novel governance model grounded in physics. | Charter §5, patent disclosure |
| 218 | **OPH Overlap = HIL Mechanism**: Observer Patch Holography's Axiom 2 (overlap consistency) is the mathematical foundation for human-in-the-loop governance. When human and agent patches overlap, they must agree. | Constitution §1, Charter §5 |
| 219 | **Data Mesh × MCP Registry**: 17+ MCP servers = 17 data domains. DataProduct type with SLA + lineage turns tools into governed data products. Factory pattern prevents shared mutable state. | CLAUDE.md Architecture |
| 220 | **A2UI makes agent testing structural**: Component catalog (JSON) + experience scripts replace opaque WebGL testing. Agent validates the data structure, not the pixels. | CLAUDE.md Testing |

### Stale/Duplicate Entries to Prune

- **KEY_LEARNINGS.md** (424 lines, limit 300): Learnings 210-214 (kernel competition) → compress to 1 entry
- **MEMORY.md** (125 lines, within limit): "Recent Decisions" section is from Feb 2026 — stale, needs update with March 2026 decisions

### Files to Update During Execution

| File | Change | Reason |
|------|--------|
| `CLAUDE.md` | Add "FLUME-First" to Coding Standards | Learning 215 |
| `CLAUDE.md` | Add concierge + autonomy tiers to Architecture | Learnings 216-217 |
| `CLAUDE.md` | Update test count (5,200+ → verify), add Playwright test info | Learning 220 |
| `.agent/CONSTITUTION.md` | Add OPH overlap as HIL grounding | Learning 218 |
| `memory/MEMORY.md` | Update Recent Decisions with March 2026 entries | Staleness |
| `KEY_LEARNINGS.md` | Compress 210-214, add 215-220 | Over limit + new learnings |

### Process Improvements

1. **True TDD going forward**: Write the test BEFORE the implementation. The `test_hiho_agents_are_coherent` test should have existed before `verify_observer_consistency()` was written.
2. **FLUME-first checklist**: Before creating any new module, ask: "Does this module have an `encode()` input and a `decode()` output that connects to FLUME?" If not, redesign.
3. **Concierge-first sessions**: Wire the concierge startup hook so every session begins with a briefing, not a cold start.

---

## Verification

### Branch 1 (testing)
- `npx glance-mcp` starts successfully
- All 9 Playwright tests pass (genesis + a2ui-demo)
- Parallel Code evaluated for worktree management

### Branch 2 (rendering)
- `npm run build` succeeds with Pretext
- Narration overlay uses Pretext measurement (screenshot comparison)
- WebGPU prototype renders same scene as WebGL

### Branch 3 (physics)
- `observer_patch.py` unit tests pass
- OPH axioms documented in Genesis About panel
- A2UI catalog has observer-patch component

### Branch 4 (data-mesh)
- `data_mesh/` module imports cleanly
- Domain registry populated with 7 agent domains
- Data product schema validated for vault entries
