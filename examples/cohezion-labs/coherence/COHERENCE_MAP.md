# Cohezion Coherence Map & Wiring Plan

## 1. Coherence thesis

Cohezion is unified by three threads that are supposed to braid into one rope: the **HIHO 4x(1-x) kernel** (peak coherence at 0.5, mathematically identical to the logistic map at r=4 and shared by physics/LENR/ionic/attention), the **12D manifold** as the universal coordinate system every agent execution gets projected into, and the **compound loop** (execute → retrospect → refine → re-route, each pass making the next cheaper). In principle every execution flows: task → FLUME-encode to 256D latent → 12D journey point → SurrealDB + Obsidian → retrospection → skill refinement → routing improvement, all measured against the 0.5 HIHO coherence floor. **In practice the rope is unbraided at every splice.** The journey gets encoded by a SHA-256 *hash fake* (`journey_tracker.py:264`), not FLUME, so the 256D latent space the whole architecture promises never holds real semantics. The shared SurrealDB table every session already writes to (`journey_transition`) carries **no agent_id/session_id**, so N live sessions write to a common DB but none can read each other. The semantic cache is **read-only** (no write-back path exists in this worktree), so it stays perpetually empty and the "$0 local inference" story never warms. The self-healing loop **detects but never heals** (the apply-line is a code comment). The physics package **fails to import at all** (6 missing Phase-18 modules). And the unifying kernel itself is **copy-pasted** rather than imported from one source. Cohezion is not under-built — it is a dozen finished subsystems wired to tests and scaffolds instead of to each other.

## 2. The wiring graph — highest-value orphan edges

### compound-spine
- `ExecutorFactory.create` **--should-wire-->** `SemanticCache.get_instance()` as a `semantic_cache=` kwarg : the documented CB4 injection point; the factory signature has no cache param, so the executor can never write-back. *(NOTE: the `_populate_semantic_cache` write method named by CB4 is **absent from this worktree's src/** — verified. The edge requires re-introducing the method, not just calling it.)*
- `CompoundExecutor.execute_fn` (`executor.py:561-610`) **--should-wire-->** `TapeLogger.record` (`tape_logger.py:32`) : a complete crash-safe record/replay logger with **zero production importers** — wiring it to the LLM call site enables deterministic compound re-runs the Charter calls for.
- `ExecutorFactory` **--should-wire-->** one canonical `SkillRefiner`/`RetrospectionEngine` package : today the factory mixes `compound.skill_refiner` with `core.compound.retrospection` (two of three coexisting copies); collapse to one.

### journey-capture (FLUME → SurrealDB → Obsidian)
- `JourneyTracker._flume_encoder` (`journey_tracker.py:146`, currently `None`) **--should-wire-->** `FlumeVAEEncoder.encode` / `JourneyToFlumeEncoder.encode_trajectory` : replaces the SHA-256 `_text_to_latent` (`journey_tracker.py:264,428`) with real 256D latents — the single most semantically-impactful wire in the repo.
- `JourneyToTrainingBridge.journey_to_agent_trajectory` (`journey_to_training.py:144`, **zero importers**) **--should-wire-->** `train_flume_on_journeys` (`flume/train.py:75`) : the API trains FLUME on `np.random` synthetic data (`flume.py:291`); this is the built-and-forgotten adapter that would feed real captured journeys.
- `post_execution.py:647` (already writes SurrealDB `genesis`) **--should-wire-->** `ObsidianWiki.create_wiki_page` with `surreal_id` frontmatter : makes the "dual-store for journeys" real for the first time on the live path; retires 3 unreachable scaffold binders (TriuneEngine, EvoAgent, FlumeWikiBridge).
- Three dead imports **--should-wire-->** `cohezion.core.persistence.surreal_client:get_surreal_client` : `compound/persistence.py` (`get_client`), `jepa_world_model_persistent.py` (`SurrealDBConnection`), `flume/trajectory_capture.py` (`store_journey_transition`) all reference symbols that **do not exist** — dead-on-arrival, silently swallowed.

### self-healing (ouroboros + mycelium)
- `DegradationDetector` anomaly (`degradation_detector.py:308-321`, already built) **--should-wire-->** `HealerAgent.synthesize_patch` → `TriuneSimulationEngine.inject_patch` : detection currently dead-ends in a passive alert; the heal half is orphaned with the apply-line commented out (`trajectory_guard.py:91`). The inject contract is already specified by `test_engine_feedback.py:28`.
- `__main__.py:572` **--should-wire-->** `cohezion.ouroboros.recorder` (real) instead of `cohezion.system.ouroboros_recorder` (**phantom module, does not exist**) : one repoint resurrects the dead `cz ouroboros start` command.
- `executor.py:1254` synthesized skill output **--should-wire-->** `QuadratureNexus.apply_mycelium_feedback` (`quadrature_nexus.py:196`, 13 passing tests) : the loop-closing consumer is invoked only from `scripts/overnight_evo_loop.py`, never from src/ — production synthesizes skills then drops them.
- `__main__.py:649` **--should-wire-->** `cohezion.mycelium.scripter` instead of `cohezion.mycelium.shadow_scripter` (**non-existent path**) : the entire `cohezion mycelium grow/garden` CLI raises ImportError today.

### physics + worldviews
- `physics/__init__.py:10-44` **--should-wire-->** try/except guards (or the 6 missing modules: bec_bridge, colibre_bridge, mhd_plasma, sarfatti_bridge, tensor_metric_engineering, toroidal_moment) : **nothing can `import cohezion.physics`** — every downstream consumer (swarm_env, genesis API) dies at import.
- `lenr.py:88` + `ionic_cluster.py:92` (inline `4.0*t*(1.0-t)`) **--should-wire-->** `model/hiho_attention.py:50 hiho_kernel` : the "unifying invariant" is copy-pasted, not shared — give it one source of truth.
- `worldviews/tradition_data.py` TOE_STEPS **--should-wire-->** `physics/cosmogony.py` PhaseTransitionEvent stream (`cosmogony.py:609-650`) : both hardcode the identical 10-step chain; a stage→tradition resolver makes "17 traditions validate the same physics" executable instead of prose.

### local-inference
- `executor.py:561-569` **--should-wire-->** `self._inference_provider.run(prompt)` : the TieredOrchestrator is built and injected but used only as a **truthiness flag**; the runtime path imports `compound.local_inference.make_local_execute_fn` — a module that is **MISSING from this worktree** (verified). This is the broken seam.
- `swarm/cost_aware_router.py` **--should-wire-->** `inference.check_fleet()` / `FleetRegistry` : the swarm runs a *separate* Lemonade router against hardcoded port tables (`cost_aware_router.py:373-377`), blind to live lane health.
- `SemanticCache` encoder (`cache/text_encoder.py:38`, 384D MiniLM) **--should-wire-->** `flume/embedding_provider.py:35 OllamaEmbeddingProvider` (768D nomic-embed @ :11434) : the cache ignores the exact encoder the **live Ollama node already serves**.

### cross-session
- `JourneyTracker` CREATE statement (`journey_tracker.py:543-546`) **--should-wire-->** `agent_id` + `session_id` + `created` fields : rows are anonymous, so no trajectory is attributable to a peer session.
- `ConciergeAgent.gather_briefing` (`concierge.py:137-143`) **--should-wire-->** SurrealDB `journey_transition` query instead of globbing empty `continuation.md` : the one component whose entire job is cross-session orientation already health-checks SurrealDB (`concierge.py:70 surrealdb_healthy`) but reads the sparse file substrate.

## 3. External grounding — one technique per pillar

| Pillar | Adopt (cited) | Maps to file |
|---|---|---|
| **cross-agent-comms** | Blackboard post-and-volunteer routing (13–57% E2E gain), validated against AgentsNet + AgentCollabBench — [arXiv:2510.01285](https://arxiv.org/abs/2510.01285), [arXiv:2507.08616](https://arxiv.org/html/2507.08616v1), [AgentCollabBench](https://huggingface.co/datasets/AgentCollabBench/AgentCollabBench) | `swarm/team_executor.py` (pull-routing over the 7 A2A specialist cards; SemanticCache L3/SurrealDB = the blackboard) |
| **world-models-jepa** | Value head over JEPA/FLUME latents → value-guided latent rollout (replaces greedy per-step routing) — [arXiv:2601.00844](https://arxiv.org/pdf/2601.00844) | `world_model/jepa_world_model.py` + `compound/executor.py` (compose with `feynman_path_weight`, harness CC2) |
| **semantic-memory-vault** | Graphiti-style conflict-detection-on-write: search-for-contradiction then `valid_to=now()` — [arXiv:2501.13956](https://arxiv.org/abs/2501.13956) / [getzep/graphiti](https://github.com/getzep/graphiti) | `core/persistence/surreal_client.py` + the `vault_log_decision` write path (extends CB2 soft-delete) |
| **local-slm-orchestration** | NPU-coordinated speculative decoding (1.06–3.81× throughput, $0 cost, lossless) — [arXiv:2510.15312](https://arxiv.org/abs/2510.15312) | `inference/triune_orchestrator.py` (NPU tier 13306, `llama3.2-1b-FLM`) — gated on FLM exposing a draft/assisted-gen hook |
| **agentic-environments-evals** | Reward-hacking / trajectory-exploit detector via RHB taxonomy + TRACE contrastive (paired) detection (+18pts) — [arXiv:2605.02964](https://arxiv.org/abs/2605.02964), [arXiv:2601.20103](https://arxiv.org/html/2601.20103v1) | `persistence/` DegradationDetector + `RetrospectionEngine` anomaly-flag step + `SkillConsensusVoter` (feed paired good/candidate) |

*(Section 4's demonstrator deliberately uses the **nomic-embed 768D** encoder the memory-vault pillar points at, and reads back cross-session in the blackboard spirit — no contradiction with the techniques above.)*

## 4. The one demonstrator to build NOW

### Name: **`journey_roundtrip` — the real-FLUME cross-session journey demonstrator**

A single runnable script that drives one agentic task through local inference, encodes the journey with the **real** FLUME/nomic encoder (not the SHA-256 fake), persists it to **both** SurrealDB and Obsidian with a bidirectional id, then proves a **second** session can read that trajectory back. This is the only thread that satisfies all five hard constraints (FLUME-encode + SurrealDB + Obsidian + local inference + cross-session read-back) and it threads compound-spine, journey-capture, persistence-vault, local-inference, and cross-session pillars simultaneously.

### Concrete steps
1. **Inject a real encoder into JourneyTracker.** Set `JourneyTracker._flume_encoder` (`journey_tracker.py:146`) to an instance of `OllamaEmbeddingProvider` (`flume/embedding_provider.py:35`, 768D nomic-embed @ :11434 — the live node). The real-encoder branch at `journey_tracker.py:605-606` already exists; this just populates the slot so `_text_to_latent` (`:264`) stops returning hash noise. Project 768D→12D for the manifold point as the existing pipeline does.
2. **Drive one execution through local inference.** Run a trivial task ("classify sentiment: 'this works'") through the triune path to Ollama:11424→11434 / NPU 13306. Capture the `track_execution` call (`executor.py:1110`).
3. **Add attribution to the SurrealDB write.** Extend the CREATE in `journey_tracker.py:543-546` to include `agent_id`, `session_id` (from `COHEZION_SESSION_ID`), and `created = time::now()`. Persist via the existing `_persist_to_surreal` buffer (`:529`, ns=cohezion db=cohezion :8001).
4. **Dual-store to Obsidian.** After the SurrealDB write in `post_execution.py:647`, call `ObsidianWiki.create_wiki_page` (`integrations/obsidian_wiki.py:30`) into `~/vaults/cohezion-vault/` with YAML frontmatter carrying `surreal_id: journey_transition:<id>` and the 12D point. Store the obsidian path back on the SurrealDB row (bidirectional link).
5. **Repoint the dead client imports** *only if hit* — use `cohezion.core.persistence.surreal_client:get_surreal_client` (`:1134`), not the phantom `cohezion.persistence.surreal_client.get_client`.
6. **Cross-session read-back.** Re-point `ConciergeAgent.gather_briefing` (`concierge.py:142`) to query `SELECT * FROM journey_transition WHERE session_id != $self ORDER BY created DESC LIMIT 5` instead of globbing `continuation.md`. It already holds `surrealdb_healthy` (`:70`).
7. **Simulate the second session.** Run the script a second time with a different `COHEZION_SESSION_ID`; have it instantiate ConciergeAgent and print the prior session's trajectory + task.

### Entry points / files wired
`compound/journey_tracker.py:146,264,428,543,605` · `flume/embedding_provider.py:35` · `compound/post_execution.py:647` · `integrations/obsidian_wiki.py:30` · `governance/concierge.py:70,142` · `core/persistence/surreal_client.py:1134`

### How to VERIFY (real evidence, runnable)
- **(a) Real latent, not hash:** `curl -s http://localhost:8001/sql -H "surreal-ns: cohezion" -H "surreal-db: cohezion" -H "Content-Type: text/plain" -u root:root --data "SELECT latent, agent_id, session_id FROM journey_transition ORDER BY created DESC LIMIT 1;"` — the vector must be a dense 768/256D float array with non-degenerate variance, and `agent_id`/`session_id` must be populated (not null). Sanity-check it's *not* a hash: two near-identical tasks should give cosine ≥ 0.58 (harness CA1 threshold for 768D nomic); two unrelated tasks ≈ 0.15–0.20.
- **(b) Obsidian dual-store:** `ls ~/vaults/cohezion-vault/` and read the new `.md` — frontmatter must contain `surreal_id: journey_transition:<id>` matching the row from (a).
- **(c) Cross-session aware:** run #2 with a new session id; assert stdout prints session #1's task string and 12D point, retrieved *via SurrealDB through ConciergeAgent* (not from a local file). This is the constraint-critical step — a journey that persists but is never read by a second session fails "cross-session aware."

## 5. Honest risk list

**Unverified / contradictions (do not paper over):**
- **CB4 / `local_inference.py` contradiction (CONFIRMED this session):** The compound and inference maps state `_populate_semantic_cache` and `compound/local_inference.py` are **absent from this worktree** — I verified both: `grep` for `_populate_semantic_cache` returns nothing, and `compound/local_inference.py` does not exist. Yet harness invariants CB4 and the `make_executor` pattern (CLAUDE.md) assert they exist. **These cannot both be true.** The harness likely validates a different checkout (main, or an archive copy). **Do NOT** make the demonstrator depend on "restore local_inference.py" as step 1 — the demonstrator above routes through the triune path directly and sidesteps the missing module. The semantic-cache write-back is listed as a *wiring opportunity* (§2), not a demonstrator step, precisely because its prerequisite method is missing.
- **`is_available()` / checkpoint reality:** `OllamaEmbeddingProvider` and `FlumeVAEEncoder` both fall back to hash when no checkpoint loads (`vae_encoder.py:61` default path `./data/flume/checkpoints/flume_vae_ep2.pt` does not exist). The demonstrator uses the **Ollama nomic path** (a live HTTP service, no checkpoint needed) specifically to avoid this — but verify `is_available()` returns True before claiming "real latent."

**Services that may be down:**
- **CLaSp 13308 is DOWN** (research footer). Do not route any demonstrator inference through it. NPU 13306 / iGPU 13307 / CPU 13309 / router 13305 / Ollama 11434 are UP.
- SurrealDB 8001 must be UP (ns=cohezion, SurrealKV bi-temporal) — the demonstrator's verify steps assume it. Confirm with a `SELECT 1` before running.

**Infrastructure-drift traps to avoid (scope OUT — not buildable in one session, will burn the budget):**
- Fixing the 6 physics Phase-18 modules / making `cohezion.physics` import — large, unrelated to the demonstrator's five constraints.
- Training FLUME VAE from scratch or wiring `JourneyToTrainingBridge → train_flume_on_journeys` — the demonstrator uses the *already-serving* nomic encoder; training is a follow-on, not a prerequisite.
- The ACP blockchain/DHT/DID federation stack ([arXiv:2602.15055]) — explicitly rejected by the research as lowest-leverage for a single-node Strix Halo box; borrow only the JSON-LD message schema if anything.
- Building a new orchestration framework (CORAL dynamic info-flow) before the journey round-trip works — that's the "build a tool to build the thing" anti-pattern (CLAUDE.md Execution Priority). Wire the existing executor first.

**Git/state caution:** This is the `warm-squishing-wigderson` worktree, not the Kaggle worktrees. Any edits to `journey_tracker.py`/`concierge.py`/`post_execution.py` are real source changes — present a numbered plan and get approval before editing (workflow-enforcement: >2 file changes), and do not commit without explicit user instruction (git-operations rule).
