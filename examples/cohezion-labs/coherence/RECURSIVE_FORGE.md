# Cohezion Recursive Forge — Integration & Simplicity Plan

## 1. Thesis

Cohezion is three converged engines pretending to be one. **Recursive learning** (ouroboros self-heal + mycelium skill-synthesis + quadrature consensus calibration) captures every execution and *can* re-tune future governance. **Local-silicon availability** (lemonade NPU/iGPU/CPU + GAIA adapter) gives that loop free, on-AMD-silicon inference at $0/run via a purpose-built single-door fleet (`route()`/`extend_claude`). **Universe generation** (SWIFT EVO coupling, COLIBRE cosmological bridge, the cosmogony chain, and the FLUME/JEPA world model) grounds the agents in a physical substrate whose coherence is, *mathematically exactly*, the same `4·x·(1-x)` HIHO kernel the governance layer optimizes toward (0.5 equilibrium). The unifying invariant is HIHO: COLIBRE star-formation efficiency `4·f_hot·(1-f_hot)`, LENR reaction rate, IonicCluster plasma, cosmogony Step-8, and the consensus governor's 0.5 coherence target are the *same equation* on different substrates. Every subsystem is built and high-quality. The defect named by the prior coherence audit — "a dozen finished subsystems wired to scaffolds/tests instead of to each other" — is literally true here: the loop is open at the seams, the live silicon door has zero production callers, and the universe bridges are exported-but-never-invoked. This plan closes the one seam that makes recursion *real*, routes the recursion onto free silicon, and deletes the duplication that masks the wiring.

---

## 2. The Recursion Gap

The experience→skill→routing loop is built in **three independent half-circuits, none of which closes back into skills or routing in production.** Trace:

### Circuit A — Cross-subsystem (capture → consume): ZERO call edges
- **Capture side (LIVE):** `compound/executor.py:1234-1256` (Step 10.6) ingests execution journals into a MyceliumRegistry and runs `run_audit()` every 10 entries — non-blocking, real.
- **Consume side (ORPHANED):** `swarm/quadrature_nexus.py:196` `apply_mycelium_feedback()` — the genuine recursive core: additive per-voice (Architect/Engineer/Ethicist/Resource) score-offset calibration with oscillation damping (`_detect_oscillation`, `:181`). Fully built, fully tested-shaped, **zero callers.**
- **The break:** there are *no call edges* between `run_audit()` output and `apply_mycelium_feedback()`. Executions are captured and skills synthesized, but nothing routes the audit deltas into the governor. The loop is open.
- ⚠️ **Brief-level error to not propagate:** `apply_mycelium_feedback` lives in **`swarm/quadrature_nexus.py:196`**, NOT `governance/quadrature_nexus.py` (which is a 64-line HIHO-state stub at `governance/quadrature_nexus.py:32` with no such method). The task brief itself mis-attributed this.

### Circuit B — Within-mycelium (writer ≠ reader): two empty instances
This is the **more precise, more fixable** break:
- **Writer:** `compound/executor.py:1241` builds `self._mycelium_registry = MyceliumRegistry()` — *instance-local* (`learning/mycelium_registry.py:54`).
- **Reader:** `api/services/mycelium_api.py:36/150` builds its OWN `global _registry = MyceliumRegistry()`.
- **Result:** writer and reader are **two different empty instances of the same class.** Synthesized skills are written to one object and read from another — the `/skills` endpoint always returns an audit done elsewhere (i.e., nothing). Learning is captured but *never read back.*
- Compounding: the capture logic is **duplicated verbatim** in `compound/post_execution.py:730` inside `PostExecutionOrchestrator`, which has **zero callers** (dead extraction).

### Circuit C — Quadrature telemetry ingestion: front-half trigger missing
- `swarm/quadrature_nexus.apply_mycelium_feedback` (back half) is fully wired into `_evaluate_architect/engineer/ethicist/resource`.
- But its only entry point, `deliberate()` at `swarm/quadrature_nexus.py:305` (rich 256D ExperienceEncoder + FlumeJourneyEvent emit at `:441`/`:479`), has **zero production callers** — the sole `.deliberate(` hit in non-test src is the docstring at `:124`. So `telemetry → ingest_evo_journeys → apply_mycelium_feedback` is never triggered.

### Bonus dead-trip — Ouroboros self-heal can never fire
- `ouroboros/recorder.py:111` hardcodes `coherence=0.5` ("placeholder — would query FLUME"). `AnomalyDetector.is_anomaly()` (`ouroboros/detector.py:8`) keys on *deviation from 0.5* — so a constant 0.5 is **never anomalous.** The detector→healer path is inert by construction. The only live healer call is `healing/scripts/trajectory_guard.py:76`, and `HealerAgent.synthesize_patch` (`ouroboros/healer.py:23`) returns free-text nothing applies.

**Where it closes today:** nowhere into skills or routing. Experience is captured (executor Step 10.6, live) and the back-half calibrator is wired (`apply_mycelium_feedback`), but the read-back edge (Circuit B), the cross-subsystem dispatch (Circuit A), and the telemetry trigger (Circuit C) are all missing. **Closing Circuit B is the smallest change that makes any learning visible.**

---

## 3. Bleeding-Edge to Integrate (one technique per topic; local-first + simple)

| Topic | ONE technique to adopt | Source URL | Target file |
|---|---|---|---|
| **Recursive self-improvement** | ERL + CER: emit **compact retrieval-keyed heuristics** (success *and* failure, one-paragraph) from retrospection, then a retrieve-and-replay step early in the loop. Training-free, +7.8% Gaia2. | arxiv.org/abs/2603.24639 · arxiv.org/pdf/2506.06698 | `compound/retrospection_engine.py` (emit heuristics) + `compound/executor.py` (retrieval step after JourneyTracker) + `cache/semantic_cache.py` L2 |
| **Local NPU serving** | **Lemonade Hybrid execution** (NPU-prefill / iGPU-decode) as the default backend for medium/reasoning tiers — a server config flag, *no draft/verify plumbing to build*. Plus AHASD entropy-gating (~30 lines). | amd.com/.../lemonade-for-local-ai.html · arxiv.org/html/2604.25326v2 | `inference/triune_orchestrator.py` (backend) + `inference/task_classifier.py` (add confidence/entropy term to escalation) |
| **Diffusion world models** | **LGS input-noising knob `k`**: `x̃ = (1-k)x + k·z` — ~5-line rollout stabilizer that turns autoregressive blow-up into bounded drift. Does NOT touch KL invariants (A3/A5). | arxiv.org/html/2602.11229 | `flume/training.py` (add `k`-noising) + `world_model/jepa_world_model.py` (rollout) |
| **Cosmological-sim ML** | **COLIBRE-style GP/Latin-hypercube emulator** — zero-GPU, CPU-only surrogate for parameter sweeps; the lowest-integration-cost option, validates the harness in a day. | arxiv.org/pdf/2509.04067 | `swarm/cost_aware_router.py` + `BudgetEnforcer` (sweep harness) |
| **Elegant agent architecture** | **smolagents code-as-action** as a thin lane: LLM emits one Python block calling MCP tools as functions instead of the full 11-step pipeline; ~30% fewer LLM round-trips. JSON tool-calling costs −27.3 pts GSM8K. | github.com/huggingface/smolagents · arxiv.org/html/2510.14453v1 | `compound/executor.py` (add `CodeActionExecutor` lane behind `ExecutorFactory.create()`) |

**Defer (require plumbing, not config):** Mirror SD (arxiv.org/pdf/2510.13161), full AHASD/Collaborative-SD, LCM decoder distillation, latent-diffusion cosmology heads. All are real but bigger than one session.

---

## 4. Extend Availability — route more work to NPU/iGPU/CPU/GAIA

**The live local-first door already exists and has zero production callers.** `route()` (`inference/fleet.py:445`) and `extend_claude()` (`inference/fleet.py:590` — *literally* try-local-fleet-first, escalate-to-Claude-only-on-quality-gate-failure) are reached only by 28 test imports. Meanwhile the recursion subsystems route through `BaseAgent._call_ollama` (`agents/base.py:293`, Ollama :11434), bypassing the purpose-built fleet entirely.

### Wiring edges (in dependency order)

1. **PREREQUISITE — reconcile the three-way model-ID drift.** This is a hard gate, not a footnote:
   - Registry (`inference/registry.py:183/209/226/244`) advertises Gemma-4-E2B/E4B/26B/31B at 13306/13307/13308/13309.
   - Triune (`inference/triune_orchestrator.py:50`) requests `llama3.2-1b-FLM`.
   - **Live substrate serves DeepSeek-Qwen3-8B on all four ports.**
   - Per harness N1/N2 model IDs are load-bearing (wrong ID triggers lemonade auto-load/eviction). **Fix:** have `health.py:82` (`check_fleet`, already reads live `/v1/models` at 13306-13309) populate the registry from live model IDs, and have triune read *from* the registry. One source of truth.

2. **Point self-heal at the fleet.** Change `HealerAgent.synthesize_patch` (`ouroboros/healer.py:47`) from `await self._call_ollama(prompt)` → `await extend_claude(prompt)` (or `route()` with `task=CODE_GEN`). Self-heal now runs on free silicon with a quality-gated cloud fallback; `_call_ollama` becomes deletable.

3. **Enable Lemonade Hybrid** (NPU-prefill/iGPU-decode) as the default medium/reasoning backend in `triune_orchestrator.py` — server flag, the SOTA form of what N1/N2 half-implement.

4. **Use GAIA's AMD ranking as the single ordering authority.** `amd_optimized_hierarchy` / `rank_models_by_amd_optimization` (`inference/gaia_adapter.py:127/108`) currently duplicate triune's hardcoded tier order. Build triune's tier list *from* the ranking, or delete the unused helpers — one authority, not two.

5. **Add the confidence/entropy escalation term** to `task_classifier.py` so low-confidence NPU outputs escalate and high-confidence ones don't (AHASD finding 1), validated against the existing 8-case accuracy test (CL1).

---

## 5. Refactor for Elegant Simplicity (top 6 wins)

| # | Anti-pattern | file:line | Simpler form |
|---|---|---|---|
| 1 | **Two empty MyceliumRegistry instances** (writer ≠ reader) | writer `compound/executor.py:1241`; reader `api/services/mycelium_api.py:36/150` | One shared `get_instance()` singleton (harness CA2 pattern) — both point at the same object; `/skills` goes live. |
| 2 | **Dead verbatim capture duplicate** | `compound/post_execution.py:730` (`PostExecutionOrchestrator._run_mycelium`) — **zero callers**, exact copy of executor Step 10.6 | Delete the file/method. One capture path. |
| 3 | **Two classes named `QuadratureNexus`** | `governance/quadrature_nexus.py:32` (64-line HIHO stub, only caller `compound/aimo_reasoning.py`) vs `swarm/quadrature_nexus.py:147` (real governor) | Rename governance stub → `QuadratureState` (or fold its 12-param dataclass into the swarm governor) — kills the name collision the brief itself fell for. |
| 4 | **Four copy-pasted UCB1 selectors + 5 UCB_C constants** | `autoresearch_driver.py:130`, `lhao_orchestrator.py:110`, `arpao_orchestrator.py:103`, `tcrao_orchestrator.py:135`, `autoresearch_funding.py` | Promote `autoresearch_driver._ucb1_select` + `UCB_C` to public API; the four orchestrators import it. Net deletion of ~3 orchestrators' worth of bandit logic. |
| 5 | **Three/four-copies orchestrators** | live `inference/orchestrator.py:101`; dead `inference/tri_compute_orchestrator.py:349` (NPU port 8004 wrong, numpy/print placeholders); test-only `inference/orchestrator_autoharness.py:170/486` | Delete the two dead/orphaned files (~1,160 lines) and the NPU-port drift with them. |
| 6 | **Hardcoded `sys.path.insert` machine path** | `universe/agentic_evo_swift.py:28` (`"/home/mike-anderson/dev/cohezion/src"`) — only such hack in `universe/`; makes `agentic_evo_mhd.py:24`'s bare import work by accident | Convert to `from cohezion.universe.agentic_evo_swift import AgenticEVO`. |

**Bonus trivial:** `autoresearch_driver.py:163` no-op double-loop `[np.dot(current_vec, wv) for win_vec in win_vectors for wv in [win_vec]]` → `[np.dot(current_vec, wv) for wv in win_vectors]`. And the SHA-256 fake-latent paths (`vae_encoder.py:172` `_hash_encode`, `journey_tracker.py:615` sha512-rng, `engine.py:565`) should consolidate to one fallback encoder — ideally the live nomic 768D `OllamaEmbeddingProvider` — so the fix lands once, not three times.

---

## 6. The One Artifact to Build NOW

### `close_mycelium_loop` — shared-singleton wire + live verification driver

**What it is:** The convergent answer across 4+ sweeps. Make `learning.MyceliumRegistry` a shared singleton (harness CA2 `get_instance()` pattern), point writer + reader at it, delete the dead `PostExecutionOrchestrator`, then *prove* the loop closes by running a real task through live lemonade silicon and showing the synthesized skill read back. **Refactor-plus-one-wire — no new subsystem.** The verification driver is a demo/test script, not infrastructure (stays clear of the CLAUDE.md drift trap).

**Steps (one session):**
1. Add `MyceliumRegistry.get_instance()` classmethod to `learning/mycelium_registry.py:54` (mirror `SemanticCache.get_instance()` exactly — harness CA2).
2. Change `compound/executor.py:1241` `self._mycelium_registry = MyceliumRegistry()` → `MyceliumRegistry.get_instance()`.
3. Change `api/services/mycelium_api.py:36` global `_registry = MyceliumRegistry()` → `MyceliumRegistry.get_instance()`.
4. Delete `compound/post_execution.py:730` `_run_mycelium` + the orphaned `PostExecutionOrchestrator` (zero callers).
5. Wire one real caller for the back half: in executor Step 10.6, after `run_audit()`, dispatch audit deltas → `swarm/quadrature_nexus.py:196 apply_mycelium_feedback()` on the universe's nexus (`universe/factory.py:146`). ~10 lines.
6. Write `scripts/drivers/close_mycelium_loop.py`: run one real task through `make_executor()` (which composes `build_triune_orchestrator` → live NPU 13306 / iGPU 13307), capture the execution, trigger the audit, then read `/skills` (or call the reader directly).

**Entry points:** `compound/__init__.py::make_executor` → `build_triune_orchestrator` (`inference/triune_orchestrator.py:21`) for live local inference; `learning/mycelium_registry.py::get_instance`; `swarm/quadrature_nexus.py:196`.

**How to VERIFY with real evidence** (the evidence IS the discriminator):
- **(a) Same object:** assert `id()` of the registry at the executor write site == `id()` at the mycelium_api read site (proves Circuit B closed).
- **(b) Read-back > 0:** after running one task, the reader returns ≥1 synthesized skill (today it returns 0 — different empty instance).
- **(c) Voice offset shifted:** capture a voice score-offset in `apply_mycelium_feedback` *before* and *after* the dispatch; assert it changed (proves Circuit A→C closed and the calibrator actually consumed feedback).
- **(d) Local inference confirmed:** log the tier each call landed on (`check_fleet` / FleetHealth at `health.py:75`) — must show NPU/iGPU, $0, no cloud.

This single change is **more capable** (real recursion: executions now tune future governance, synthesized skills become visible) AND **simpler** (deletes a dead duplicate, collapses two registries to one, justifies renaming the governance stub).

---

## 7. Honest Risks

**Services that may be down:**
- **CLaSp draft port 13308 is DOWN.** `clasp_tier.py:86` ImportError/fallback-degrades to plain E4B on every call. Do not depend on speculative decoding; the transparent-wrapper fallback is sound but the speedup is currently zero.
- Live substrate serves **DeepSeek-Qwen3-8B on all four ports** (13306-13309), NOT the registry's Gemma-4 nor triune's `llama3.2-1b-FLM`. Verify with `lemonade --port 13306 status` before routing.

**Hard prerequisite, not a footnote:** Pointing self-heal at `route()`/`extend_claude` (Section 4) **regresses from a working Ollama path to a non-functional one** unless the model-ID drift is reconciled FIRST (health.py populates registry from live `/v1/models`). Do not ship Section 4 step 2 before step 1.

**Unverified claims (do NOT quote in any submission):**
- "20–80 tok/s <2W" and "120B @ 50 tok/s on the APU" (local NPU research, secondary coverage). N1 records the verified baseline: **42 TPS for llama3.2-1b-FLM.**
- Subterranean-Agents "~2 orders of magnitude less cost" (arxiv.org/abs/2605.22502) — title-claim only, model sizes not in abstract.
- HF dataset `erisdataworks/camles-cosmoGrid-z0` existence confirmed via search snippet only — verify split/license before download.
- AHASD/Mirror/Collaborative-SD throughput multipliers — confirm against live baselines.

**What NOT to build:**
- **Do NOT build the 6 Phase-18 physics bridges** (`bec_bridge`, `colibre_bridge`, `mhd_plasma`, `sarfatti_bridge`, `tensor_metric_engineering`, `toroidal_moment`). They are *absent from this worktree's disk but committed in main@a418b1850* — a git-propagation artifact (harness C1), not deletion. Do not re-implement; do not rebase this worktree as part of this work. (If `import cohezion.physics` must succeed locally, the minimal fix is removing the dead imports at `physics/__init__.py:10,26`, NOT rebuilding the modules.)
- **Do NOT build new orchestrators.** Three already exist; two are dead (Section 5 win #5).
- **Do NOT swap the autoresearch SHA-256 latent in the same session** as the singleton wire — it's a real, complementary fix (nomic 768D) but a *separate* thread. Bundling risks drift.
- **Do NOT build draft/verify speculative-decoding plumbing** — Lemonade Hybrid gives it at the server layer for free (Section 3).
- **Do NOT re-vendor A2UI** — already at `src/web/anima_dashboard/src/a2ui`.
