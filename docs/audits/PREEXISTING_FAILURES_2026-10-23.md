---
type: audit
date: 2026-10-23
branch: fix/preexisting-failures-rca
base: github/main b3342cf18
status: complete
---

# Pre-existing test / CI failures: root-cause audit (2026-10-23)

Base: `github/main` @ `b3342cf18`. (The working clone's `origin/main` pointed at the local
checkout's `main`, `3fec1909e`, which was behind GitHub. The branch was re-based onto the GitHub
tip before any work.) Environment: CI dependency shape (`uv sync --frozen --extra dev`, Python
3.13.11). `pytest-timeout` is **not** installed in that shape, so the suite has no per-test
timeout. Every run here was wrapped in an outer `timeout`.

## Test-run isolation (harness, not committed)

The local fleet was live (`:13305` answering), and inference ports are hard-coded in `src/`
(`lemonade_available(npu_port=13305)`), so env vars cannot redirect them. To make the run match
CI (no lemonade, ollama, or SurrealDB) and keep the suite from mutating the live fleet, each run
put a `sitecustomize.py` on `PYTHONPATH`. It refuses `socket.connect` to localhost ports
13305-13309, 11434 and 8001.
Control: unguarded `curl :13305/v1/models` returned the catalog, while the guarded
`httpx.get(...)` got `ConnectError` and `lemonade_available()` returned `False`.
Limits: the guard covers only in-process Python and Python subprocesses that inherit
`PYTHONPATH`. A `curl` or `lemonade` CLI subprocess, or one launched with a cleared env, would
bypass it. A before/after residency comparison was attempted, but `/api/v1/health` returned
HTTP 200 with an **empty body**, so whether the fleet was mutated is **UNKNOWN**, not "unchanged".
(A network namespace via `unshare -rn` would be the stronger isolation. It is unavailable
inside the agent sandbox: nested user namespace limit.)

## Baseline (run 1, pristine github/main)

`timeout 3600 uv run pytest tests/ -q -p no:cacheprovider --tb=line -rfE`

```
collected 14069 items / 1 error / 5 skipped
ERROR tests/scripts/test_producer_consumer_audit.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=================== 5 skipped, 1 warning, 1 error in 25.48s ====================
```

**0 of 14,069 collected tests ran.** One collection error interrupts the whole session.

### Automerge-guard gates (run individually; the guard itself needs a PR number + `gh` and merges)

| Gate | main @ b3342cf18 |
|---|---|
| ruff format --check, ruff debt ratchet, mypy ratchet (+self-test) | PASS |
| local-llm choke-point | **FAIL**: 1 new raw call site `scripts/ci/local_adversarial_review.py` |
| dormancy, doc-code, phantom-attr, lineage, false-contract, surreal-http, declared-field, unrestricted-exec, self-test-coverage, producer-consumer (each + self-test) | PASS |
| mutation ratchet (+self-test) | PASS |
| systemd unit audit | **FAIL**: host state, see G3 |
| graph cardinality, version governance | PASS |
| unit / import-smoke / inference pytest steps | covered by the full-suite runs below |

## Root-cause groups

### G1: collection error aborts the entire suite (sys.path basename collision). FIXED

- **Symptom:** `ImportError: cannot import name 'AUDIT_PAIRS' from 'producer_consumer_audit'
  (.../scripts/producer_consumer_audit.py)`. It passes when run alone and fails under
  `tests/scripts/` or `tests/`.
- **Mechanism:** two files share the basename `producer_consumer_audit.py` (`scripts/` and
  `scripts/ci/`). `test_dormancy_scan.py` inserts `scripts/ci` into `sys.path`. Then
  `test_overnight_compound_session.py` (and others) insert `scripts/` at index 0. The test's
  `if dir not in sys.path: insert` guard then **skips**, so the bare import resolves to the wrong
  file. This is order-dependent collection pollution, not a src regression.
- **Blast radius:** total. Every test is unrun locally. In CI the unit step (`tests/unit/`) does
  not collect `tests/scripts/`, but the integration step (`pytest tests/ --ignore=tests/unit/
  --ignore=tests/inference/`) does, and it has `continue-on-error: true`. So this error
  **voided that whole step without turning CI red**: the same class as the earlier
  "collection error hid 217 integration failures" incident.
- **Fix:** the test loads `scripts/ci/producer_consumer_audit.py` by file path via
  `importlib.util.spec_from_file_location` under a unique module name. That makes it
  independent of `sys.path` order. Nothing was deleted or renamed.
- **Evidence (neutralized = original bare import):**
  `pytest tests/scripts/test_dormancy_scan.py tests/scripts/test_overnight_compound_session.py
  tests/scripts/test_producer_consumer_audit.py`. Before: `23 collected, 1 error`. Dropping the
  dormancy file: `17 collected` (proves the ordering). After the fix: `28 passed`.
- **Commit:** `96775254b`.
- **Latent:** 6 other duplicate script basenames (`apply_lemonade_recipes`,
  `audit_lemonade_recipes`, `main`, `multiperspective_code_review`, `scan_todos`,
  `sync_skill_registry`) carry the same hazard. No test imports them by bare name today.

### G2: origin/main fails its own choke-point gate (raw chat call without the contract). FIXED

- **Symptom:** `check_local_llm_chokepoint.sh`: `NEW raw chat/completions call site outside
  blessed path: scripts/ci/local_adversarial_review.py`.
- **Mechanism:** a real latent defect, not baseline drift. `_ask()` returned
  `message["content"]` only. A reasoning model that answers in `reasoning_content`
  (content == "") left the lane UNKNOWN. JSON drafted inside `<think>` could be parsed
  **instead of** the final answer (e.g. a draft `hold` read in place of the final `ship`, or the
  reverse).
- **Fix:** `_ask` delegates to `cohezion.inference.gaia_adapter._answer_only` (the shared
  contract: content to reasoning_content fallback, think/channel strip, never-empty). The
  reviewed call site was then added to `chat_chokepoint_baseline.txt` (+1 line, no other baseline
  change), per the gate's documented `--update-baseline after review` path.
- **Evidence:** `tests/scripts/test_local_adversarial_review_ask.py` (urlopen mocked, no router
  traffic). On the unfixed `_ask`: **2 failed, 1 passed** (fallback and think-strip cases).
  After: 3 passed. Gate: `new (unbaselined): 0`, rc=0.
- **Commit:** `7ac97fbc9`.
- **Not touched (other branch's scope):** `run_lane`'s one-shot retry and the
  parsed-empty-findings handling belong to `fix/failure-class-audit`.

### G3: systemd unit audit fails on this host. HOST STATE, reported, not fixed

`scripts/ci/systemd_unit_audit.py` reads `~/.config/systemd/user`, not the repo. It returns 0
when that directory is absent (line 141), so it cannot fail on a CI runner. On this host it
correctly reports 5 broken user units:

- `smart-loader.service` targets `~/dev/cohezion/smart_loader.sh`. That file was deleted in-repo at
  `32eb67544` ("delete stale non-markdown root artifacts"), but the unit still references it.
- `memory-shepherd-memory.service`, `memory-shepherd-workspace.service` target
  `~/ods/memory-shepherd/memory-shepherd.sh` (missing).
- `openclaw-session-cleanup.service` targets `~/ods/scripts/session-cleanup.sh` (missing).
- `ods-mdns.service` has an unsubstituted `__PYTHON3__` template placeholder in ExecStart.
- Warning only: 19 units have `Restart=` without `StartLimitBurst`.

This is user remediation (disable the units, or restore their targets). Changing persistent user
config is outside this branch. Making the audit "hermetic" would neutralize its purpose.

## Flagged for fix/failure-class-audit (gates that cannot fail)

- `.github/workflows/ci.yml` integration step has `continue-on-error: true`. A collection error
  there aborts the step and CI stays green. G1 is the live instance.
- `pytest-timeout` is not a dependency at all (absent from `pyproject.toml` and `uv.lock`), yet
  `[tool.pytest.ini_options]` registers a `timeout` marker. The 2 `@pytest.mark.timeout(...)` uses in `tests/` are
  therefore silently inert, and nothing enforces a per-test timeout in CI.

## Full suite after G1 (run 2): the real baseline

With only G1 fixed (tests and src otherwise identical to `b3342cf18`):

```
211 failed, 13636 passed, 119 skipped, 70 xfailed, 46 xpassed in 781.54s
```

0 errors. 46 XPASS (non-strict; 37 in `tests/inference/test_model_card_harness.py`): xfails that
no longer fail, reported here, not changed. **Isolation triage:** every one of the 47 failing
files was rerun **alone on pristine `github/main`** (detached worktree, its own `src` first on
`PYTHONPATH`). 46 of 47 also fail in isolation, so the failures are real and pre-existing, not
pollution. The exception is `tests/universe/test_telemetry_mesh.py` (passes alone), which is G11.

**Recurring root cause.** Most groups below are one mechanism repeated: a *producer that stayed
while its consumer was dropped* by a refactor or reconcile merge (router defined, never mounted;
method kept, call site deleted; constructor param re-added, behaviour gone), or a *fix whose
test landed while its implementation stayed on a side branch*. In every case the code still
imports cleanly. Nothing errors; it just returns 404, or None, or the old answer. Only a
consumption check catches it.

### G4: 11 service routers dropped from the app by the #267 refactor (src). FIXED

- **Mechanism:** `8f712a8bd` (#267, "extract route handlers from `__init__.py`") deleted every
  `app.include_router` for research, universe, journey_nexus, genesis, world_model,
  physics_extended, worldviews, journeys, ouroboros, mycelium, modules. All 11 still import
  (110 routes), and every request returned 404.
- **Fix:** re-mounted with the original prefixes and order. An ImportError is now **logged**
  rather than `suppress`ed, since a quiet ImportError is how this stayed invisible.
- **No-shadow oracle:** every route served at `b3342cf18` was resolved to its endpoint function
  before and after (`starlette` route matching on concrete URLs): **50/50 unchanged**, 96 added.
- **Commit:** `c13154017`.

### G5: 33 inline routes deleted by the same refactor; their extracted routers never mounted (src). FIXED

- **Mechanism:** #267 also deleted 33 inline routes (`/flume/*`, `/rl/*`, `/templates/parse`,
  `/journeys/*`, `/compare/*`, `/skills/*`, `/query/*`, `/metrics/*`, `/knowledge/query`,
  `/swarm/execute`, `/compound/*`). Extracted replacements existed in `api/routes/` but were only
  re-exported from `routes/__init__.py`. That re-export is a declaration, and nothing consumed it.
- **Choices:** handler signatures were compared with the pre-#267 inline handlers, and there was
  no auth dependency drift in either direction. `routes/flume_inline.py` is mounted (it resolves
  `cohezion.api._get_vae` at call time, so conftest resets and patches apply). `routes/flume.py`
  keeps a private `_get_vae` copy and stays unmounted as a rival. Mounted after `main_router`, so
  the 6 paths both define keep resolving to `main_router`.
- **Not mounted (maintainer decision; never mounted pre-#267 either):**
  `api/routes/fleet.router` (fleet control), `api/services/brand.brand_router`,
  `api/services/forge.forge_router`.
- **Guard:** `tests/api/test_router_mounts.py`. Every `APIRouter` under `api/routes` and
  `api/services` must be mounted or listed in `UNMOUNTED` with a reason, and the allowlist must
  not go stale. 22 passed. With `_mount_service_routers()` neutralized: **21 failed**.
- **Oracle:** 50/50 routes unchanged; all 55 pre-#267 inline routes are served again.
- **Commit:** `1c91e69ee`.

### G6: physics endpoint contract implemented on a side branch, never landed. FIXED (cherry-pick)

- **Mechanism:** `tests/api/services/test_physics_extended.py` tests lenr, ionic-cluster,
  dielectric, sarfatti and qgp routes that `physics_extended.py` on main never defined. The
  implementation is `0c0314b6d` on `verify-physics-endpoint-contract-complete` (a rebuild of
  `23a8ab049`). It also collapses the BEC/Mercury/COLIBRE/MHD/Bismuth/Toroidal/TensorMetric
  handlers that main defines **three times** (the duplicate-operation-ID warnings).
- **Fix:** `git cherry-pick -x 0c0314b6d`, then re-verified. Main has not touched either file
  since that commit's base.
- **Commit:** `54c6ce34b`.

### G7: per-agent physics state leaked across tests (pollution). FIXED

- **Mechanism:** module-level `_ionic_cluster_agents` / `_lenr_agents` dicts persist by design.
  Two test files both use `agent_id="test-ionic-agent"`, so the second reads the first's plasma
  density. Passes alone, fails together.
- **Fix:** cleared in the existing `reset_singletons` autouse fixture.
- **Evidence:** 1 failed before, 734 passed after (tests/physics + test_physics_extended + mounts).
- **Commit:** `8f4e8178d`.

### G8: package re-export edges pinned by wiring-sweep tests never landed. FIXED (additive)

- **Mechanism:** `tests/wiring/*_wired.py` and `tests/vanguard` (landed `853084c05`) pin
  package-level identity re-exports and `__all__` membership from a 2026-06-06 sweep whose
  `__init__` edits never landed. A separate 06-22 sweep exported a different subset. Every source
  object exists.
- **Fix:** names imported inside the existing guarded blocks and appended to `__all__` *inside*
  the block, so a failed import never lists a missing name. `eval`/`flux` came from the existing
  side-branch fix `5e42905b5` (cherry-picked, `06b114ce2`).
- **Caveat:** these tests verify declaration (reachable plus identity), not consumption.
- **Evidence:** 17 failed, now 861 passed across the affected packages.
- **Commits:** `06b114ce2`, `364735b11`.

### G9: health oracle's quality-statistics alert path dropped by a reconcile merge (src). FIXED

- **Mechanism:** `768f6d811` ("method-merge ... compound_health_oracle.py", 2026-08-26) kept
  `_quality_stats()` / `_is_degrading()` but deleted the code in the assessment builder that
  calls them. The oracle silently reverted to FD-only: healthy lanes (0.85 +/- 0.005) raised
  **critical** and escalated to the expensive tier; a 0.9 to 0.2 collapse raised only **warn**.
  This is the "always-firing gate" the sibling branch reported.
- **Fix:** file restored to `768f6d811^`; every other difference was constant relocation.
  `TestCH2HihoOk` asserted HIHO => ok unconditionally, which contradicts the documented contract.
  Its own seed's last window falls 0.55 to 0.29, so it now accepts a quality-DEGRADING critical
  while still failing a regime-only impl that returns warn.
- **Evidence:** `test_health_oracle_quality_stats` 6 failed, now 11 passed. tests/compound +
  tests/unit: 4304 passed.
- **Commit:** `f3e981b16`.

### G10: conversational-memory wiring (#198) lost; #251 re-added only the params (src). FIXED

- **Mechanism:** `1ebb719d9` (#198) wired CohezionMemory: an opt-in lazy `memory_service`, a
  `remember()` of each successful turn, and factory params. It was lost before #251, whose "H1"
  re-added only the constructor params. On main: the property ignored `enable_memory`, nothing
  called `remember()`, and **`ExecutorFactory.create(..., enable_memory=True)` raised
  `TypeError`**, which a production entry point does (`scripts/codebase_refinement.py:215`).
- **Fix:** restored from #198 onto the current executor and factory.
- **Evidence:** 3 failed, now 7 passed. With `remember()` neutralized, the behavioural test fails.
  The real factory call now constructs.
- **Commit:** `318ec8b85`.

### G11: TelemetryBus could never revive a dead or stale-loop worker (src, order-dependent). FIXED

- **Mechanism:** `start()` returned early on `_running=True`. The module singleton outlives event
  loops, so after `tests/unit/test_autorun_integration.py` it arrived with `_running=True` and a
  worker from a closed loop. Nothing drained the queue. The same state arises in production
  when the worker task dies.
- **Fix:** `start()` returns early only for a live worker on the current loop. On a loop change
  it recreates the queue (its waiters are loop-bound) and carries pending events over.
- **Evidence:** `tests/core/test_telemetry_bus_restart.py` 2 failed before, 3 passed after.
  autorun followed by telemetry_mesh: 1 failed, now passing.
- **Commit:** `da55a581b`.

### G12: F821 undefined names, 4 of them runtime NameErrors. FIXED

- `twistor_worldview_functor.py` (`json`, in its `__main__` path), `dogfood_phase1_multimodal.py`
  (`urllib`, every SurrealDB upsert raised), `research_arxiv_2606_12683_agi_asi.py` (LaTeX
  `\text{ms}` inside an f-string read as interpolation of `ms`).
- Plus 2 annotation-only `Any`. `ruff --select F821`: 7 down to 0.
- **Commit:** `ccaa96991`.
- `repo_health`'s I001/F401 checks still fail on about 140 cosmetic findings. Those are left to the
  CI ruff ratchet, which governs lint debt; mass-fixing would not be surgical.

### G13: stale assertions after deliberate src fixes. FIXED (tests only)

- `test_twistor_worldview_functor`: pinned 17 traditions; the registry is 18 since stealthskater
  was restored. Now compares with `len(get_traditions())`. (`d5efb2d40`)
- `research/test_cost_optimization`: asserted the 1000x-overstated per-1K Anthropic prices that
  `eda411480` corrected. The src is right. (`a9645519a`)

## Result (run 3, branch HEAD `da55a581b`, same harness)

```
39 failed, 13850 passed, 119 skipped, 58 xfailed, 46 xpassed in 947.10s
```

That is **211 down to 39 failures** and 13636 up to 13850 passing (+214). xfailed fell 70 to 58
because the cherry-picked G6 commit retires `test_wiring_stealthskater.py`'s module-level strict
xfail; its 12 tests now pass for real. Fixes after run 3 (`b8318dc3e`, `e5530de32`) touch only
the memory import, its new test, and formatting.

The one failure new versus run 2, `tests/agentjet/test_trainer.py::test_dry_run_succeeds_without_training`,
is **host-RAM flakiness, not a regression**. It failed once in run 3 ("Platform daemon denied
training lock for qwen3.5:9b (need 30.0 GiB)" while the suite and the gate battery ran
concurrently), then passed 8/8 twice on this branch and 8/8 on pristine main once RAM recovered.
It is a hermeticity defect: a *dry run* asks the live platform daemon for a 30 GiB lock.

Automerge-guard gates re-run on HEAD: all pass except the systemd unit audit (G3, host state).
On the way there, mypy's ratchet caught that the restored G10 lazy import pointed at a
re-export that no longer exists (`from cohezion.memory import CohezionMemory`), which would
have kept memory self-disabled in production. The existing tests inject a fake and could not
see it. Fixed in `b8318dc3e`, with a discriminating test that fails on the broken import.
Version governance passes; no semver bump is required for `fix:`/`test:` commits.

## What remains (not fixed, and why)

| Group | Tests | Why not fixed here |
|---|---|---|
| **ResourceGuard floor contract conflict** | `test_resource_guard_can_load_model` (3), `vmodel/test_phase0_safety_invariants::test_sr1_3` (1) | **Policy decision needed.** The #251 TDD-red tests and SR1-3 require refusing any load below the 16 GB floor (and on CPU overload). The original gate test `test_resource_guard_oom.py` (passing) requires *allowing* a 2 GB load at 9.2 GB available. Implementing one breaks the other (verified: 2 new failures), so it was reverted. The only production caller passes `estimated_mb=0`, so either choice is low blast radius, but it is a safety-policy change. |
| **TLS verification** | `security/test_mcp_https_client` (2) | Tests expect `CERT_NONE` / no verification for self-signed certs; src enforces `CERT_REQUIRED`. **Not weakened.** The tests should probably be updated to the hardened contract; needs a security-owner decision. |
| **Telegram bot tests stale vs #302/#306** | `integrations/test_telegram_*` (10) | `_chat_omnirouter` now returns `(reply, telemetry)`; tests mock the old single value (the `ValueError` at `telegram_bot.py:788`). The model id is now the router alias `user.cohezion-router`; fallback and agent-intent call counts changed. Deliberate refactors, so the tests need per-case intent review. |
| **MD2 transition_controller never implemented** | `vmodel/test_phase4_wiring` (4 of 7) | `_default_compound_loop_state_machine`, `transition_controller` and `recursive_trace_loop` exist in **no** revision (`git log --all -S` returns 0). These are tests for unbuilt design: never-worked, not a regression. |
| **SurrealDB-required tests fail instead of skipping** | `vmodel/test_phase4_wiring::TestSurrealDBTables` (3) | They hit :8001 directly and fail when it is absent (they would also fail on the CI runner). Hermeticity fix: a skip-if-unreachable marker. |
| **Stub shadows a lost implementation** | `flume/test_real_skill_state_dataset` (3), `flume/test_diversity` (1) | `RealSkillStateDataset` is a stub added in `e51687fa9` to clear collection errors. The real implementation (`_encode_records`, `n_samples`) existed in `e5bef2f1e`. Restoring a training dataset is a larger, separate task. |
| **Semantic cache env-coupling / drift** | `cache/test_comprehensive`, `test_semantic_cache_coverage_wave3c` (2), `test_semantic_embeddings`, `validation/test_calibration_harness` | The threshold auto-tunes to whichever encoder is installed (256d FLUME gives 0.45, tests expect 0.75), and `get_project_root` was refactored to `get_config().root_dir` in `8e6c2db5b`. Needs hermetic encoder pinning. |
| **Mock-shape drift** | `core/test_context_engineering_mcp` (2) | `vault_search()` returns an un-configured MagicMock where the test expects a list. Test-side. |
| Singles | `e2e/test_marimo_rustwright_validation` (marimo export path), `unit/test_universes_environment_and_harness` (the sibling's 1 unit failure), `repo_health` I001/F401 (2; see G12), `agentjet/test_trainer` dry-run (flaky, host RAM) | Not investigated in this pass / environment. |
| Host state | systemd unit audit (G3) | User remediation. |

## Hermeticity defects found while running the suite

- **The test suite rewrites tracked repo files** on every run:
  `src/cohezion/agents/generated/skill_{0,1}_agent.py`, `src/cohezion/knowledge_graph/health_log.json`,
  `src/cohezion/skills/skill_registry.json`, `tests/mycelium/generated_test_dummy.py`,
  `data/flume/checkpoints/flume_vae_ep2.pt`, `data/rl/checkpoints/policy_final.pt`,
  `data/config-sync-logs/config_sync.jsonl`. These were restored by hand after each run on this
  branch, never committed. A suite that dirties checked-in checkpoints and registries can
  silently commit test artefacts via any broad `git add`.
- Ports are hard-coded (`lemonade_available(npu_port=13305)`), so tests cannot be redirected
  away from the live fleet by environment. The fleet guard in this audit is a test-run harness,
  not a repo fix.

## The one remaining `tests/unit` failure (CI-gating step)

`tests/unit/test_universes_environment_and_harness.py::test_ultra_realistic_agent_env_lifecycle_and_actions`
(the sibling branch's "1 unit failure"). `UltraRealisticAgentEnv._exec_in_sandbox` runs commands
under bwrap whenever bwrap is on PATH. Inside the agent sandbox, nested bwrap fails with
`Creating new namespace failed ... (ENOSPC)`, so `cat greeting.txt` returns `''`. With bwrap
hidden from `shutil.which`, all 7 tests pass. So the local failure is a sandbox artifact. **On CI it
is UNKNOWN:** `ubuntu-latest` (24.04) restricts unprivileged user namespaces via AppArmor, so bwrap
may fail there the same way. Latent src defect: a bwrap *setup* failure surfaces as empty stdout
rather than an error. Falling back to unsandboxed execution would weaken isolation of
agent-issued commands, so that is a security decision and is left unchanged.

`tests/inference` (the other gating step): 0 failures in run 3.
Gate battery on final HEAD `7a74a3949`: 29/30 pass; the 1 failure is the systemd host audit (G3).
