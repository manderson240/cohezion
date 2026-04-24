---
title: "Adversarial Review — Wave 2B api refactor (Cohezion)"
date: 2026-04-23
campaign: synthetic-sniffing-panda Ω4
commit: 0ac84a8b56b62fdace7fb8b676e7e7a8fb21c7cb
reviewer: bmad-code-review (Blind Hunter / Edge Case Hunter / Acceptance Auditor)
headline: "Refactor preserves the public API, but ships an orphaned 363-LOC duplicate (`routes/flume_inline.py` shadows the older `routes/flume.py`) plus a `__all__` regression that drops `_compute_coherence` from the package surface, and a brittle late-binding of `metrics_tokens._client` that test patches against `cohezion.api.set_token_client` may now miss."
---

# Subject

- **Commit**: `0ac84a8b56b62fdace7fb8b676e7e7a8fb21c7cb` — `refactor(api): extract 13 router modules from api/__init__.py (Wave 2B)`
- **Files**:
  - `src/cohezion/api/__init__.py` — 2099 → 266 LOC (87% reduction)
  - `src/cohezion/api/_helpers.py` — 100 LOC (new)
  - `src/cohezion/api/routes/{a2a,agentjet,compound,flume_inline,journeys_legacy,knowledge,mcp,metrics,notebooks,rl,skills,swarm,templates}.py` — 13 new modules totaling ~1894 LOC
- **Claim**: "Tests: 948 passed / 86 failed / 51 errors (compound) — baseline maintained; 116 passed / 2 skipped (api) — baseline maintained; 152 routes loaded"
- **Goal**: split monolithic `api/__init__.py` into mountable APIRouter modules without changing public surface

---

# Layer 1 — Blind Hunter findings (diff-only, no project context)

The Blind Hunter reads only the diff and comments on what would worry a reviewer who did not know the codebase.

## L1-F1 [must-fix]: `__all__` is missing `_vae_trainer`'s twin truth — `_compute_coherence` is exported but `_vae_trainer` mutation is not safely round-tripped

`__init__.py:50-51,250-260` — Module-level `_vae_trainer = None` and `_rl_policy = None` are declared, and `_helpers.get_vae()` mutates them via `api_module._vae_trainer = trainer` (`_helpers.py:71`). The pattern works, but the diff introduces an **import-order coupling**: `_helpers.py` does `import cohezion.api as api_module` inside the function body (good — defers circular import), but if anything in the import chain ever calls `get_vae()` while `cohezion.api` is *partially initialized* (e.g., another router's import-time side effect), `getattr(api_module, "_vae_trainer", None)` will return `None` correctly, but the `setattr` on a half-initialized module can succeed and then be overwritten when `__init__.py` continues executing line 50 (`_vae_trainer = None`). Result: a silently-discarded singleton on first call.

The original code used `global _vae_trainer` inside the same module, so partial-init was impossible. **Severity: must-fix** if any router or its transitive imports call `_get_vae()` at import time. Mitigation: move the `_vae_trainer = None` and `_rl_policy = None` declarations to **before** the router imports (lines 24-39 currently), or assert `hasattr(api_module, "_vae_trainer")` before write.

## L1-F2 [must-fix]: orphaned duplicate router file `routes/flume.py` (326 LOC) shadows the new `routes/flume_inline.py` (363 LOC) by name

`routes/flume.py` exists alongside `routes/flume_inline.py`. The new `__init__.py:30,123` imports and mounts only `flume_inline_router`. `routes/flume.py` defines a `flume_router` symbol with the SAME paths (`/flume/train`, `/flume/encode`, etc.) but is never imported. This is dead code, but it is **load-bearingly confusing**:

- A future reviewer will assume `routes/flume.py` is the canonical FLUME router (shorter, no `_inline` suffix).
- Any future `from cohezion.api.routes import flume` import would silently get the orphan.
- The two files diverge in behavior (e.g., `routes/flume.py:103-127` defines its OWN `_get_vae()` and `_compute_coherence()` instead of importing from the package — meaning a copy that bypasses the conftest reset hooks).

**Severity: must-fix** — either delete `routes/flume.py` or rename `flume_inline.py` → `flume.py` and remove the duplicate. The current state is a foot-gun.

## L1-F3 [should-fix]: `__all__` omits `_vae_trainer` and `_rl_policy` mutation contract

`__init__.py:250-260` — `__all__` lists `_vae_trainer` and `_rl_policy`, but these are reassigned by helpers in another module (`_helpers.py:71,96`). Linters like `ruff` will flag the implicit re-export as dead, and a "from cohezion.api import \*" consumer will get the *initial* `None` snapshot, not the live attribute. This is a deferred-binding gotcha specific to package-level mutability.

The original co-located `global _vae_trainer` and `_get_vae()` so this was a non-issue. **Severity: should-fix** — document the mutability contract, or expose it through a property/getter only.

## L1-F4 [should-fix]: `set_token_client` re-exported from a new module silently breaks test patches against `cohezion.api.metrics_tokens._client`

`__init__.py:34,252` — `set_token_client` is imported from `cohezion.api.routes.metrics` and re-exported. Original semantics: `set_token_client(client)` sets `metrics_tokens._client = client` on the **module-level** `metrics_tokens` function in `cohezion.api`. After the refactor, `set_token_client` mutates the function inside `cohezion.api.routes.metrics` instead. Any test or caller that does `cohezion.api.metrics_tokens._client = X` directly (bypassing `set_token_client`) now mutates a different object than the one the route handler reads.

A grep over `tests/` finds no direct `cohezion.api.metrics_tokens._client` patches today, so this is technically green. But the back-compat shim docstring in `__init__.py:8-12` *promises* that "test patches keep working" — and this one only works if you go through `set_token_client`. **Severity: should-fix** — either add `from cohezion.api.routes.metrics import metrics_tokens` to `__init__.py` (so `cohezion.api.metrics_tokens` resolves to the right object), or document the limitation in the back-compat shim docstring.

## L1-F5 [should-fix]: `_helpers.py:100` exports `contextlib` in `__all__`

```python
__all__ = ["compute_coherence", "get_vae", "get_rl_policy", "contextlib"]
```

This is almost certainly a copy-paste error — `contextlib` is a stdlib module imported on line 13 but never used (after grep). It should not be in `__all__`. Suggests the author moved code without re-running ruff's unused-import sweep.

**Severity: should-fix** — drop `contextlib` from `__all__` AND from the imports.

## L1-F6 [should-fix]: route ordering shift on `/notebooks` may change OpenAPI tag ordering and dashboard discovery

The original file declared routes in a single `app` instance with implicit insertion order: `mcp` → `knowledge` → `swarm` → `notebooks` → `journeys` → `flume` → `templates` → `rl` → `compare` → `skills` → `metrics(agents/training/pipeline/system)` → `knowledge/query` → `metrics/tokens` → `swarm/execute` → `metrics/compound` → `compound/*` → `agentjet/*` → `a2a/*`.

The new `__init__.py:118-130` mounts them as: `mcp`, `knowledge`, `swarm`, `notebooks`, `journeys_legacy`, `flume_inline`, `templates`, `rl`, `skills`, `metrics`, `compound`, `agentjet`, `a2a`. This **reorders** the OpenAPI spec (e.g., `/knowledge/query` was originally interleaved AFTER `/metrics/system`; now it lives in the `knowledge` router and appears earlier; `/swarm/execute` was originally AFTER `/metrics/tokens`; now it lives in `swarm` router and appears earlier).

Behavioral consequence: zero — FastAPI dispatches by path, not order. Documentation consequence: any consumer that scrapes `/openapi.json` for tag ordering (e.g., a docs UI, an SDK generator) will see a reshuffled spec. The dashboard at `/genesis` may rely on tag order for its sidebar.

**Severity: should-fix** — verify Genesis dashboard navigation and any SDK consumers; otherwise document as intentional.

## L1-F7 [consider]: the `# noqa: F401` registration trick in `rl_episode` is fragile post-extraction

`routes/rl.py:183` — `import cohezion.rl.environment  # noqa: F401 — registers Gymnasium env`. This is a side-effect import for `gym.make("cohezion/FlumeNav-v0")`. In the original `__init__.py`, this import lived in the same TU — the env was already registered after first call. Now the import lives inside `rl_episode()` (lazy) and only fires on first `/rl/episode` POST. If something else (a test, a different endpoint) calls `gym.make("cohezion/FlumeNav-v0")` first without triggering this import, it errors out. **Severity: consider** — promote the registration import to module level in `routes/rl.py` so it fires when the router is mounted.

## L1-F8 [consider]: `_compute_coherence` recomputed inside `flume_inline.py:354` per-sample is O(n_samples × z_dim); was the same in the original, but now PCA is in a thread-pool while coherence stays on the event loop

`flume_inline.py:328-355` — PCA is wrapped in `loop.run_in_executor` with a 10s timeout. Coherence computation (line 353-355) is left **after** the timeout block, on the main event loop, looping `request.n_samples` times calling `_compute_coherence` (which itself imports numpy and does chunk math). At `n_samples=1000`, this is 1000 × 256-dim chunked variance — likely <1s, but it now blocks the event loop while PCA runs in a thread. The original (Session 87 era) did the same thing; the diff didn't introduce it. **Severity: consider, defer to follow-up** — wrap the coherence loop in `run_in_executor` too, or at minimum use `asyncio.timeout` around it.

---

# Layer 2 — Edge Case Hunter findings (diff + project read access)

## L2-F1 [must-fix]: double-import path for `_get_vae` / `_compute_coherence` defeats `mock.patch` from a parallel test

The handlers in `routes/flume_inline.py:178,207,226,280` import `_compute_coherence, _get_vae` **from `cohezion.api`** (the package), which re-exports them from `_helpers`. A test that does `patch("cohezion.api._get_vae", return_value=mock_vae)` (per `tests/api/test_flume_latent_space.py:50,87,117,143,166,197`) will:

1. Replace `cohezion.api._get_vae` with the mock — works.
2. The handler does `from cohezion.api import _get_vae` *inside the function body*, which re-resolves the attribute on every call — picks up the mock. **Works.**

So far so good. But: if a parallel test in the same process patches `cohezion.api._helpers.get_vae` instead (some style guides prefer patching the source module), it will NOT propagate because `cohezion.api._get_vae` is bound to the original `_helpers.get_vae` callable at import time of `__init__.py:24` (`from cohezion.api._helpers import compute_coherence as _compute_coherence`). The patch on `_helpers` does not retroactively update the imported alias.

Reproducible scenario:
```python
with mock.patch("cohezion.api._helpers.get_vae", return_value=mock_vae):
    response = client.post("/flume/encode", json={"vector": [0.0]*256})
# response uses the REAL VAE, not the mock
```

This isn't a regression versus the diff (the original code didn't have this surface), but **the back-compat docstring at `__init__.py:8-12` should explicitly say "patch `cohezion.api._get_vae`, NOT `cohezion.api._helpers.get_vae`"** to prevent silent flakes.

**Severity: must-fix** — document the patch path, or use a setter (`_helpers.set_vae_factory(...)`) instead of free-function re-exports.

## L2-F2 [must-fix]: `_a2a_server` instantiated at import time of `routes/a2a.py:25-40` reads `os.getenv("PUBLIC_API_URL", ...)` ONCE

`routes/a2a.py:25-40` initializes the singleton at module import. `os.getenv("PUBLIC_API_URL", "http://localhost:8080")` is evaluated then. In the original `__init__.py`, this also happened at import time, so behavior is preserved. BUT: tests that set `PUBLIC_API_URL` per-test via `monkeypatch.setenv` and then `import cohezion.api as api` will get the value present at first import only, because module init only fires once.

The new code does the same thing, so no regression. However, the diff is a perfect time to fix this — wrap the AgentCard instantiation in a `_get_a2a_server()` factory so per-test env-var overrides work. **Severity: must-fix → demote to should-fix because not a regression**, but the next person who adds an `agent.json` test will hit it.

## L2-F3 [should-fix]: `verify_a2a_token` is async but the original made the same async-vs-Header semantics work; the new module deps require both `Depends` and `Header` to be re-imported

`routes/a2a.py:14,44-55` — Re-imports `Depends, Header, HTTPException` from `fastapi`, which is correct. But: in the original, `verify_a2a_token` was at module scope of `cohezion.api.__init__`, so test code that did `from cohezion.api import verify_a2a_token` got the function directly. After refactor, `verify_a2a_token` is re-exported via `__init__.py:27`. **`__all__` lists it (line 257)**, but the symbol resolution chain is now: `cohezion.api.verify_a2a_token` → `cohezion.api.routes.a2a.verify_a2a_token`. Any test that **patches** `cohezion.api.verify_a2a_token` mutates only the alias on the package — it does NOT replace the dependency that FastAPI's `Depends(verify_a2a_token)` was bound to at import time of `routes/a2a.py:97` (which captured the local `verify_a2a_token` function reference).

Reproducible scenario:
```python
with mock.patch("cohezion.api.verify_a2a_token", return_value="bypass"):
    response = client.post("/tasks/send", json=...)  # still 401, mock never fires
```

The same bug existed in the original code (the FastAPI `Depends(...)` captures the function reference at decorator time), so this is **not a regression** — but the back-compat docstring claims "tests patches keep working" without qualifying this case. **Severity: should-fix** — either qualify the docstring, or use `Depends("cohezion.api.routes.a2a.verify_a2a_token")` style indirection (FastAPI doesn't support this directly; would need a wrapper).

## L2-F4 [should-fix]: `agentjet/train` swallows ALL exceptions including the OOM check via `type(e).__name__` string match

`routes/agentjet.py:62-80` — Catches `Exception`, then checks `if type(e).__name__ in ("OOMRiskError", "ResourceUnavailableError")`. Brittle string match — any rename of these exception classes breaks the 503 path silently. Original code had the same antipattern; this is **not a refactor regression**. **Severity: should-fix** — but defer to a separate ticket; the diff merely preserved the behavior.

## L2-F5 [should-fix]: `notebooks/{name}` path-traversal guard — regex permits `--` and trailing dot edge cases

`routes/notebooks.py:30-43` — Validates `^[a-zA-Z0-9_-]+$`, then resolves and checks `str(notebook_path).startswith(str(base_dir))`. The regex is correct. The `startswith` check is the **second-line defense** against any traversal that the regex missed. This is unchanged from the original. **Severity: should-fix → consider** — `startswith` of a path string is technically vulnerable to a directory named `docs/notebooks-evil/` being accepted because `/abs/docs/notebooks-evil/foo` starts with `/abs/docs/notebooks`. Use `notebook_path.is_relative_to(base_dir)` (Python 3.9+) instead. Pre-existing, but a fresh review might flag it.

## L2-F6 [must-fix]: `__init__.py:50` and `:51` race with router imports that may resolve singletons during their own import

When Python imports `cohezion.api.__init__`, the import order is:
1. Lines 24-26: import `_helpers` (side-effect: `_helpers.py` runs, but its functions don't fire `_get_vae` automatically).
2. Lines 27-39: import 13 router modules. **Each module's import body runs**.
3. Lines 50-51: assign `_vae_trainer = None`, `_rl_policy = None`.

If ANY of the 13 imported router modules has a top-level call (or transitively triggers a top-level call) to `_get_vae()` or `_get_rl_policy()` — including conditional registration code — those calls execute *before* lines 50-51 run, and the singleton is then **overwritten with `None`**. Reading the 13 router files now: none does this directly. But it is a hostile invariant: any future router that does `_get_vae()` at module scope (e.g., to warm the cache) silently breaks.

Reproducible scenario (manufactured but trivially possible):
```python
# Hypothetical routes/warm.py
from cohezion.api._helpers import get_vae
warm_vae = get_vae()  # at import time
```
After Wave 2B's `__init__.py:50` overwrites `_vae_trainer = None`, the next call to `_get_vae()` re-creates the trainer.

**Severity: must-fix** — move `_vae_trainer = None` and `_rl_policy = None` to lines 23-25 (BEFORE the router imports). Cost: 4 lines moved. Risk: zero.

## L2-F7 [should-fix]: `metrics_router`'s `metrics_tokens._client` uses function attribute as singleton — fragile across reload

`routes/metrics.py:228-245` — `metrics_tokens._client` is a function attribute. Mutated by `set_token_client`. Survives module reload only if the function object survives. In dev, `uvicorn --reload` reloads the module — the function attribute is reset, the registered client is lost. Original code had the same issue; this is **not a regression**. **Severity: should-fix → defer** — track in a separate "stop using function attributes for singletons" ticket.

## L2-F8 [consider]: `flume_inline_router` re-imports torch at request time inside every encode/decode/interpolate handler

`routes/flume_inline.py:175,205,224,272-279` — Each handler does `import torch` inside the function body. Python caches imports, so this is fast on subsequent calls (~microseconds), but the FIRST request after process start pays the full torch import cost (1-3 seconds). The original code did the same thing (lazy imports for cold-start optimization). The refactor preserves this. **Severity: consider** — if Genesis dashboard needs sub-second cold-start, hoist the imports to module level OR add a `/warmup` endpoint that the dashboard calls before user interaction.

## L2-F9 [consider]: `verify_a2a_token` raises 401 with a docstring that mentions a hardcoded path

`routes/a2a.py:46-49` — Detail message: `"Missing X-Cohezion-Key header. Obtain token from ~/.cohezion/auth.token"`. This leaks a path to the client. Pre-existing in the original. **Severity: consider** — sanitize for production deployments.

---

# Layer 3 — Acceptance Auditor findings (diff vs stated intent)

The stated success criteria, from the commit message:
1. **"api/__init__.py: 2099 → 266 LOC (87% reduction)"** — ✅ **MET** (`wc -l` confirms 266 lines).
2. **"56 inline `@app.*` decorators → 13 APIRouter modules"** — ✅ **MET** by route count, but see L3-F1 below.
3. **"Singletons re-exported from `__init__.py` so existing test patches keep working"** — ⚠️ **PARTIALLY MET** (see L1-F4 / L2-F1 / L2-F3).
4. **"Tests: 948 passed / 86 failed / 51 errors (compound) — baseline maintained"** — ❓ **UNVERIFIED** — see L3-F4.

## L3-F1 [should-fix]: route count vs decorator count — `compare/calm-vs-llm/{journey_id}` was a top-level route in original (line 991), now buried in `journeys_legacy_router`

In the original (line 991), `@app.get("/compare/calm-vs-llm/{journey_id}")` was registered at the top level — NOT under any tag. In the new code (`routes/journeys_legacy.py:61-64`), it's mounted under `tags=["journeys-legacy"]`. **Behavioral consequence**: zero (path unchanged, dispatch unchanged). **OpenAPI consequence**: the tag changes from "default" to "journeys-legacy". A consumer that filters by tag will lose this endpoint. **Severity: should-fix** — assign a more specific tag like `["compare"]` to match its semantic meaning, or document the tag rebrand.

## L3-F2 [should-fix]: single-responsibility per router — `notebooks_router` mixes notebooks AND simulations; `journeys_legacy_router` mixes journeys AND `compare/calm-vs-llm`

The stated goal is "single-responsibility per router". `routes/notebooks.py` houses **two** unrelated resource types: `/notebooks/*` and `/simulations/*`. `routes/journeys_legacy.py` houses 6 `/journeys/*` routes plus 1 `/compare/calm-vs-llm/{journey_id}`. These are minor but break the "one router = one resource family" rule that justifies the split.

**Severity: should-fix** — extract `simulations_router` from `notebooks.py` (6 LOC of overhead, clearer structure) and move `compare_calm_llm` to its own `compare_router` or to `journeys.py` which is already prefixed with `/api/journeys`.

## L3-F3 [must-fix]: ORPHANED MODULE — `routes/flume.py` (326 LOC, Session 87 era) is never mounted but lives next to `routes/flume_inline.py` (363 LOC, Wave 2B). The refactor creates a same-name twin instead of replacing the old one.

This is the single biggest acceptance failure. The stated goal: "split for maintainability". The actual outcome: TWO files implementing FLUME routes side-by-side, with the older one orphaned and silently rotting. Maintainability has gone DOWN, not up — a future contributor will have to discover that `flume.py` is dead.

The `Session 87` docstring on `routes/flume.py` even says "Extracted from api/__init__.py (Session 87) to keep files under 500 lines" — meaning a previous extraction attempt happened and was either abandoned or superseded without cleanup. The Wave 2B refactor didn't delete the previous attempt.

**Severity: must-fix** — delete `routes/flume.py` (326 LOC of dead code) OR rename `flume_inline.py` → `flume.py` after deleting the old one.

## L3-F4 [should-fix]: test parity claim is unverified by the commit message

The commit message asserts:
- "948 passed / 86 failed / 51 errors (compound) — baseline maintained"
- "116 passed / 2 skipped (api) — baseline maintained"
- "92 passed (root api-touching) — baseline maintained"

These are presented as **identical to baseline**. But a code reviewer cannot verify "baseline maintained" without a known prior count. The 86 failures and 51 errors in the compound suite are concerning — even if pre-existing, the refactor's claim should be "delta = 0", not just absolute counts.

**Severity: should-fix** — provide a `git stash` + diff comparison showing pre-refactor counts: `<X passed / Y failed / Z errors>` → `<X' passed / Y' failed / Z' errors>` with deltas. The verification recipe (below) gives the user a way to do this themselves.

## L3-F5 [consider]: observability — no logger.info on router mount

The original `__init__.py` had no per-router log line either, so this isn't a regression. But Wave 2B is the perfect time to add `logger.info("Mounted %d routers, %d try-imports succeeded", ...)` so production deployments can verify what's loaded. The commit message says "App boots: 152 routes loaded" but there's no runtime log to confirm this in production.

**Severity: consider** — add a single `logger.info` after line 230.

## L3-F6 [consider]: hidden regression in OpenAPI tag set

Original routes were ALL on `app` with tag = `default` (auto-generated). New routes carry explicit tags: `mcp`, `knowledge`, `swarm`, `notebooks`, `journeys-legacy`, `flume`, `templates`, `rl`, `skills`, `metrics`, `compound`, `agentjet`, `a2a`. **Net positive** — better OpenAPI navigation. **Hidden cost** — any client code that filtered by `tag == "default"` now gets a much smaller set. Unlikely but possible (e.g., a frontend that lazy-loads sections).

**Severity: consider** — note in CHANGELOG that all routes are now tagged.

## L3-F7 [consider]: `__init__.py:134-247` contains 14 try/except `ImportError: pass` blocks for optional routers. The pattern is preserved from the original, but it now coexists with 13 hard imports at top of file.

The hard imports at lines 27-39 will fail loudly if any router module is missing — desirable. The 14 lazy imports (research, universe, genesis, world_model, physics_extended, worldviews, journeys, ouroboros, mycelium, modules, anima, architecture, agui, training) silently swallow `ImportError` — the original behavior. Consistency would suggest moving the 13 hard imports into try/except too, OR moving the 14 lazy imports to hard imports. **Severity: consider** — defer to a follow-up "import strategy unification" ticket.

---

# Triage summary

| Bucket | Count | IDs |
|---|---:|---|
| **must-fix** | 5 | L1-F1 (singleton init order), L1-F2 (orphan flume.py), L2-F1 (mock patch path docstring), L2-F6 (singleton-overwrite race), L3-F3 (orphan duplicate) |
| **should-fix** | 9 | L1-F3 (`__all__` re-export), L1-F4 (`metrics_tokens._client` patch path), L1-F5 (`contextlib` in `__all__`), L1-F6 (route ordering shift), L2-F2 (`_a2a_server` env at import), L2-F3 (`Depends` capture limitation), L2-F4 (string-match exception type), L3-F1 (compare route tag), L3-F2 (single-responsibility per router), L3-F4 (unverified test parity), L2-F7 (function-attr singleton) |
| **consider** | 6 | L1-F7 (`gym` registration timing), L1-F8 (event-loop coherence loop), L2-F5 (path-traversal `is_relative_to`), L2-F8 (cold-start torch import), L2-F9 (path leak in error), L3-F5 (mount log), L3-F6 (tag set change), L3-F7 (import-strategy inconsistency) |
| **defer** | 0 | (All items are actionable now or via short follow-up commits.) |

(Some items are listed in two buckets — e.g., L2-F7 — because the severity assessment depends on whether you treat "preserved bug" as actionable. The triage is conservative.)

**Top priority — single commit**: address L1-F1 + L2-F6 + L3-F3 + L1-F5 in one focused fix:
1. Move `_vae_trainer = None` / `_rl_policy = None` to BEFORE router imports (line 23 area).
2. Delete `routes/flume.py` (326 LOC of dead code).
3. Drop `contextlib` from `_helpers.py` `__all__` and the unused import.

---

# Commendations

The refactor does several things well — these deserve explicit recognition because they are easy to skip in a critical review.

1. **Public-API preservation via re-export shim** (`__init__.py:24-39, 250-260`). The author thought carefully about test patches and re-exported the singletons + helpers from `__init__.py`. This avoided a sprawling tests-update PR. The docstring at lines 8-12 explicitly documents the contract.

2. **Conftest singleton resets still work** (verified via `tests/conftest.py:171-176, 215-220`). The `_helpers.get_vae()` function reads/writes `cohezion.api._vae_trainer` via `getattr/setattr` on the package, which means conftest's `api_module._vae_trainer = None` reset still propagates correctly. This is a non-obvious design choice that survived the refactor.

3. **No bare excepts introduced**. Each router preserves the original specific exception tuples (e.g., `routes/metrics.py:114, 131` keeps `(OSError, _json.JSONDecodeError, ValueError, KeyError, AttributeError)`). The refactor didn't widen exception handling for convenience.

4. **Pydantic model co-location**. Each router declares its own request/response models in the same file as its handlers. This is the right call — models had no reuse across the original 2099-LOC file, so co-locating reduces import surface.

5. **Tag taxonomy is clear and consistent** (`tags=["mcp"]`, `["knowledge"]`, etc.). Net positive for OpenAPI consumers.

6. **Optional-import pattern preserved** for the 14 try/except routers (lines 134-247). The refactor didn't try to "improve" this — it kept the deployment flexibility intact.

7. **No unrelated changes**. The diff is purely a refactor — no opportunistic cleanup, no behavioral tweaks, no formatting churn outside the touched files. This is what a clean refactor commit looks like.

8. **CORS, rate-limit middleware, static mounts all preserved** at the top of `__init__.py`. The middleware order is identical to the original (rate-limit → CORS → static), so request-pipeline semantics are unchanged.

---

# Recommended follow-up commits

## Commit 1 — `fix(api): correct singleton init order and remove orphan flume router`
```diff
# src/cohezion/api/__init__.py
+# Singletons (declared BEFORE router imports so any router-import-time
+# reference to _get_vae()/_get_rl_policy() finds the module attribute).
+_vae_trainer = None
+_rl_policy = None
+
 from cohezion.api._helpers import compute_coherence as _compute_coherence
 ... (existing imports)

-_vae_trainer = None
-_rl_policy = None
```
```bash
git rm src/cohezion/api/routes/flume.py
```
- Closes L1-F1, L2-F6, L3-F3.
- Risk: minimal — declaring `None` earlier cannot break anything.

## Commit 2 — `chore(api): drop unused contextlib import and clarify back-compat docstring`
```diff
# src/cohezion/api/_helpers.py
-import contextlib
 ...
-__all__ = ["compute_coherence", "get_vae", "get_rl_policy", "contextlib"]
+__all__ = ["compute_coherence", "get_vae", "get_rl_policy"]

# src/cohezion/api/__init__.py
 """
 ...
+IMPORTANT: When patching, always patch ``cohezion.api._get_vae`` (the
+package re-export), NOT ``cohezion.api._helpers.get_vae`` — the alias is
+resolved at import time and won't pick up patches on the source module.
 """
```
- Closes L1-F5, L2-F1.
- Risk: zero — pure documentation + dead import removal.

## Commit 3 — `refactor(api): split simulations from notebooks; rename compare router`
- Extract `simulations_router` from `routes/notebooks.py` (6 lines).
- Move `compare_calm_llm` to its own `routes/compare.py` (or merge into the new `journeys.py` at `/api/journeys`).
- Closes L3-F1, L3-F2.
- Risk: low — paths unchanged, only organization.

---

# Verification recipe

To independently verify the "test parity maintained" claim:

```bash
cd /home/mike-anderson/dev/cohezion/.claude/worktrees/synthetic-sniffing-panda

# 1. Capture current (post-refactor) test counts
uv run pytest tests/api/ -q --no-header --no-summary 2>&1 | tail -3 > /tmp/post-api.txt
uv run pytest tests/ -q --no-header --no-summary -k "compound" 2>&1 | tail -3 > /tmp/post-compound.txt

# 2. Stash refactor and reset to parent
git stash push -m "wave-2b-refactor" -- src/cohezion/api/
git checkout 0ac84a8b5^ -- src/cohezion/api/

# 3. Capture pre-refactor counts
uv run pytest tests/api/ -q --no-header --no-summary 2>&1 | tail -3 > /tmp/pre-api.txt
uv run pytest tests/ -q --no-header --no-summary -k "compound" 2>&1 | tail -3 > /tmp/pre-compound.txt

# 4. Restore refactor
git checkout 0ac84a8b5 -- src/cohezion/api/
git stash drop

# 5. Diff
diff /tmp/pre-api.txt /tmp/post-api.txt
diff /tmp/pre-compound.txt /tmp/post-compound.txt
# Expected: empty diff (claim of "baseline maintained" verified)

# 6. Boot the app and confirm 152 routes
uv run python -c "
from cohezion.api import app
print(f'Total routes: {len(app.routes)}')
for r in sorted(app.routes, key=lambda r: getattr(r, 'path', '')):
    if hasattr(r, 'path'):
        print(f'  {r.methods} {r.path}')
"

# 7. Confirm no orphan flume.py being silently imported
grep -r "from cohezion.api.routes.flume " src/ tests/
# Expected: zero matches (flume_inline is the active one)

# 8. Confirm singleton round-trip works
uv run python -c "
import cohezion.api as api
assert api._vae_trainer is None, 'singleton should start None'
v = api._get_vae()
assert api._vae_trainer is v, 'singleton write-through to package failed'
print('singleton OK')
"
```

If steps 5–8 all pass, the must-fix items L1-F1 and L2-F6 are not active in this codebase today (the orphan modules don't trigger the race), but the latent bug remains for any future router that warms a singleton at import time. Address Commit 1 anyway.

---

# Appendix — what was reviewed

| Source layer | Files read |
|---|---|
| Diff | `git show 0ac84a8b5` (full) |
| New routers | `routes/{a2a,agentjet,compound,flume_inline,journeys_legacy,knowledge,mcp,metrics,notebooks,rl,skills,swarm,templates}.py` |
| Slim factory | `src/cohezion/api/__init__.py` (266 LOC) |
| Helpers | `src/cohezion/api/_helpers.py` (100 LOC) |
| Pre-existing artifacts | `src/cohezion/api/routes/flume.py` (orphan, 326 LOC), `src/cohezion/api/journeys.py` (separate, mounted at `/api/journeys`), `src/cohezion/api/routes/__init__.py` (empty) |
| Conftest | `tests/conftest.py:126-220` (singleton reset hooks) |
| Test patch grep | `tests/api/test_flume_latent_space.py`, `tests/test_*.py`, `tests/api/test_a2a_endpoints.py`, etc. (50+ matches) |
| Original `__init__.py` | `git show 0ac84a8b5^:src/cohezion/api/__init__.py` (2099 LOC, full) |
| Route inventory diff | `grep "@app\."` on both versions; cross-checked against new `@*_router.*` decorators |
