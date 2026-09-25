---
title: Dynamic Modularity Audit
date: 2026-09-24
instrument: scripts/ci/modularity_audit.py
scope: src/cohezion (1,726 modules, 113 top-level entries, 100 importable packages probed)
environment: Linux cloud sandbox, CPython 3.13.12, `uv sync --frozen` (CPU torch, no ROCm)
status: report-only; no source changes
---

# Dynamic Modularity Audit — 2026-09-24

## TL;DR

**The package boundaries in `src/cohezion` are real on paper and not real at runtime.**

- The static edge graph is reasonably modular: Newman **Q = 0.63** for the package partition.
  Most imports stay inside their own package.
- At runtime almost none of that holds. **1,238 of 1,563 leaf modules (79%)** eagerly load
  **≥ 400 cohezion modules**. The median leaf module drags in **525**.
- Measured in a fresh interpreter, one at a time: `import cohezion.core.event_bus`
  (the most-imported module in the tree, 105 cross-package import sites) takes
  **5.2 s and 593 MB**, loads **498 cohezion modules**, and loads torch, transformers,
  sklearn, pandas, scipy, datasets, gymnasium and fastapi.
  The same file **loaded by path** takes **43 ms and 11 MB** and loads **0** cohezion modules and no torch.
  That is **120× the time and 53× the memory**, and all of it comes from the package layer.
- **Root cause:** eager package `__init__.py` facades. There are **686 `contextlib.suppress(Exception)`
  import blocks across 112 `__init__.py` files**, 51 of them added by "wiring-sweep" passes that made
  orphan modules look reachable. Any import of a leaf module runs its parent `__init__`, which imports the
  whole package, which imports other packages' leaves, which run *their* `__init__`s.
- **Counterfactual:** with inert package `__init__`s, the median eager closure falls from **525 to 3**
  and no leaf module reaches 400. The code inside the modules is mostly clean. The facades are
  what blow it up.
- **A second, independent problem:** 29 packages form one strongly-connected component even with every
  `__init__` edge removed. `core` depends on 11 packages, including `compound`, `inference` and `agi`,
  so it is not a foundation layer.
- The facades also hide real breakage. **27 modules fail to import.** At least 7 of those are
  internal breakages, not missing optional dependencies. **11** are wrapped in suppressed `__init__`
  imports, so the package imports "successfully" without them.

## Method

`scripts/ci/modularity_audit.py` has two layers. It is report-only, and its self-test
kills 3 of 3 planted mutants.

| Layer | What it does | Why |
|---|---|---|
| **Static** | AST over every module. Each import is classified as `eager` (module scope), `lazy` (inside a `def`), `typing` (`if TYPE_CHECKING`), or `dynamic` (`import_module("…")` with a literal). Builds the package graph, Martin fan-in/fan-out/instability, Tarjan SCCs, and Newman Q. | This is the declared coupling. |
| **Dynamic** | `import cohezion.<pkg>` in a **fresh interpreter per package**. Records wall ms, RSS delta, the cohezion modules loaded, foreign packages, heavy third-party packages, and errors. It also diffs what actually loaded against the static eager closure. | This is the consumed coupling. `lineage_scan.py` already documented that a static BFS reported 0 reach for a module that loaded torch in practice. |

Plus one supplementary pass: import all 1,726 modules in a single process and record every failure.

```bash
uv run python scripts/ci/modularity_audit.py --self-test
uv run python scripts/ci/modularity_audit.py --json /tmp/modularity.json   # ~3.5 min, 4 workers
```

> Timing note: the full run uses parallel probes, which inflates per-package wall time to about 14 s.
> The serial numbers quoted in this report (≈5.2–5.7 s) come from one probe at a time. RSS and module
> counts are unaffected by parallelism.

## Findings

### F1 — Eager package facades amplify every import into a ~500-module closure (critical)

The dynamic probe of each top-level package, ranked by modules loaded:

| Band | Packages | cohezion modules loaded | RSS | Heavy deps |
|---|---|---|---|---|
| **Fat (48 packages)** | wiring, api, benchmarks, agent, agentjet, compound, research, security, mycelium, simulations, … core, config, physics, inference, governance, storage, persistence, rewards, reliability, … | **421 – 631** | **567 – 607 MB** | torch, transformers, sklearn, pandas, scipy, datasets, fastapi (+ gymnasium) |
| Mid (5) | rl, audio, models, datamesh, model | 6 – 13 | 220 – 524 MB | torch (own dependency, legitimate) |
| **Lean (47)** | vibe, mass_sim, registry, graph, knowledge_graph, agi, actioner, worldviews, sessions, memory, … | 2 – 15 | 0 – 25 MB | none |

The fat band is flat. `config`, `core`, `physics`, `governance`, `inference`, `learning`, `storage`
and `environments` all load **exactly 498** modules, which means they all resolve to the same closure.
Once you touch any of them you get all of them.

The shortest static eager paths to torch show the pattern. Every one goes through a package `__init__`:

```
cohezion.config      → config.config_monitoring → core.event_bus → cohezion.core(__init__) → core.silicon_guard → torch
cohezion.physics     → physics.dimension_extractor → core.persistence.surreal_client → cohezion.core(__init__) → core.silicon_guard → torch
cohezion.security    → security.guardrail_adapters → core.resource_monitor → cohezion.core(__init__) → core.silicon_guard → torch
cohezion.reliability → reliability.semantic_cache → compound.exp_persistence.vault → cohezion.compound(__init__) → compound.distillation_engine → torch
cohezion.skills      → skills.cohezion_mcp → reliability.context_harness → cohezion.reliability(__init__) → … → torch
```

Most-imported cross-package targets (eager): `core.event_bus` (105), `core.persistence.surreal_client` (40),
`data_mesh.kanban_bridge` (26), `agi.autoharness_policy` (26), `contracts` (23), `reliability` (19),
`reliability.oom_guard` (19). Every one of these except `contracts` sits under a fat `__init__`.
`contracts` is a top-level module, and its closure is **2**. That is what the others would look like
without the facade.

**Counterfactual (static, all 1,563 leaf modules):**

| | median eager closure | p90 | leaves reaching ≥ 400 |
|---|---|---|---|
| Today | **525** | 555 | **1,238 (79%)** |
| Package `__init__`s made inert | **3** | 10 | **0** |

| Module | closure today | closure with inert `__init__` |
|---|---|---|
| `core.event_bus` | 524 | 3 |
| `core.persistence.surreal_client` | 524 | 5 |
| `reliability.oom_guard` | 525 | 3 |
| `physics.poincare_manifold` | 526 | 4 |

The dynamic measurement confirms the static counterfactual for `event_bus`:
**498 modules / 5.2 s / 593 MB via the package, 0 modules / 43 ms / 11 MB by path.**

**Why it matters here specifically**
- **Reflexes are not reflexes.** `reliability.oom_guard` is imported from 19 cross-package sites. Its
  job is to act under memory pressure, and loading it costs about 590 MB. `lineage_scan.py` only protects
  4 curated roots, and only because it loads them *by path*, which works around the defect instead of fixing it.
- **Startup tax everywhere:** every CLI, MCP stdio server, hook and test worker that touches `config`
  or `event_bus` pays about 5 s and 590 MB before doing anything. CLAUDE.md's MCP rule ("config lookups
  must be LAZY… slow checks exceed CLI handshake timeout") is violated structurally, not only by
  individual modules.
- **Test isolation:** any test that imports anything under a fat package loads torch.

### F2 — The "wiring-sweep" pattern is a declaration, not a consumption (root cause of F1)

- **686** `with contextlib.suppress(Exception):` import blocks across **112** `__init__.py` files.
  The heaviest are `core` (52), `security` (49), `compound` (42), `flume` (40), `research` (20),
  `inference` (20), `universe` (18) and `api.routes` (18).
- **51** `__init__.py` files carry "Wiring-sweep" provenance comments. These were added so orphan modules
  would register as reachable.
- Under `.claude/rules/verification-depth.md` §2, an import in a package `__init__` is not a consumer.
  Nothing reads or acts on the re-exported symbol. The sweep made dormancy invisible to the scanner and
  paid for it with F1 and F3.

### F3 — Suppressed imports mask real breakage (high)

A single-process import of all 1,726 modules gave **27 failures**. After removing optional or
environment-only dependencies (`triton`, `treequest`, `cotengra`, `mem0`, Kaggle data files), these remain
as **internal defects**:

| Module | Failure | Masked by an `__init__`? |
|---|---|---|
| `agents.adk_swarm.aimo_specialists.agent`, `.orchestrator` | `cohezion.sandbox.aimo` does not exist | yes |
| `flume.git_encoder` | `cohezion.swarm.git_health` does not exist | yes (`flume/__init__`) |
| `scripts.dogfooding_monitor` | `cohezion.mcp.servers.surreal_server` does not exist | — |
| `mcp.servers.traceability.server` | `from mcp import Server`: not exported by the pinned `mcp` 1.30 | yes |
| `agents.adk_swarm.*.metacognition_agent`, `aimo_specialists.number_theorist` | pydantic `instructions` extra field rejected by the current google-adk | yes |
| `agents.arc_specialists.manifold_agent` | `google.adk.tool` attribute does not exist | yes |
| `swarm.model_capability_registry_resource_safe` | bare `import model_capability_registry` (not package-relative) | yes (`swarm/__init__`) |
| `reliability.memory_manager` | imports `ollama`, which is **not declared** in `pyproject.toml` | yes (`reliability/__init__`) |
| `competition.eval_identity_check` | reads `/home/mike-anderson/dev/cohezion/...` **at import time**, a forbidden hardcoded home path | — |
| `competition.nemotron_solver.debug_model`, `kaggle_notebook` | read data files at import time (script bodies living as modules) | — |

In total, **11** failing modules are imported from a suppressed `__init__` block. Their packages report
a clean import, and the missing symbols only show up later as an `ImportError` or `AttributeError` at
the call site.

### F4 — A 29-package dependency cycle, independent of the facades (high, structural)

- The eager package graph has one SCC of **29 packages**: actioner, agents, agi, competition, compound,
  config, core, data_mesh, environments, flume, governance, inference, integrations, knowledge_graph,
  learning, mcp, ouroboros, persistence, physics, platform, reliability, research, researcher, rewards,
  security, storage, swarm, universe, worldviews.
- Removing every edge that originates in an `__init__.py` **does not break it**. It is made of leaf-to-leaf
  imports (only 18 of 1,019 cross-package eager edges start in an `__init__`). Adding lazy imports widens
  it to **53** packages.
- **33 mutual (bidirectional) package pairs**, e.g. core↔compound, core↔inference, core↔physics,
  compound↔inference, inference↔reliability, agi↔core.
- **`core` is not a foundation.** It has fan-in 30 and fan-out 11 (instability 0.27), and it depends on
  `agi` (4 edges), `compound` (6), `data_mesh` (5), `physics` (4), `flume`, `governance`, `inference`,
  `platform`, `reliability`, `storage` and `universe`.
- `governance` is the one well-shaped foundation: fan-in 13, fan-out 1 (→ `core`), instability 0.07.
- **61 of 168** package edges inside the SCC carry a weight of 1, meaning a single import. Those are the
  cheapest places to break the cycle.
- There is only one module-level eager cycle (`research` ↔ `research.orborous`). The cycles live at the
  package level, not between individual files.

### F5 — Size and shape (informational)

| Package | Modules | LOC | Fan-in | Fan-out | Instability |
|---|---|---|---|---|---|
| compound | 205 | 58,994 | 17 | 29 | 0.63 |
| inference | 121 | 33,463 | 16 | 10 | 0.39 |
| swarm | 105 | 31,768 | 15 | 15 | 0.50 |
| mcp | 101 | 20,376 | 6 | 11 | 0.65 |
| flume | 84 | 15,578 | 21 | 14 | 0.40 |
| physics | 76 | 13,823 | 17 | 7 | 0.29 |
| core | 66 | 12,173 | **30** | 11 | 0.27 |
| reliability | 24 | 3,271 | 20 | 5 | 0.20 |

- `compound` is 59k LOC with fan-out 29. It is the integration hub, and it is also part of the cycle with
  `core`, `inference` and `reliability`.
- 683 cross-package imports are already lazy (function-scoped). That is the right tool for breaking
  runtime reach, but it does not help while the target's package `__init__` is fat.
- The static layer found no literal `importlib.import_module("cohezion…")` calls. The 17 to 125 modules
  per probe that load outside the static eager closure (e.g. 17 `swarm.*` modules under `config`) come
  from conditional or `try:` module-scope imports and loops.
- 8 unresolved imports point at native crates that aren't in the tree (`cohezion_core`,
  `cohezion_physics_core`). All but one are guarded.

## Recommendations (ranked by leverage)

1. **Make package `__init__`s lazy (PEP 562), starting with `core`, `compound`, `reliability`.**
   Replace the `suppress(Exception)` blocks with a `__getattr__` that maps each public name to its
   submodule. This keeps every `from cohezion.core import X` call working, loads nothing until the name
   is used, and lets real import errors surface where they happen. `core/__init__` alone moves the
   105-site `event_bus` import from 524 modules to 3. Measure success with this audit: `core.event_bus`,
   `config` and `reliability.oom_guard` should each load under 20 cohezion modules with no torch.
2. **Retire the wiring-sweep re-exports** that have no production consumer, and let `dormancy_scan`
   report those modules honestly as dormant.
3. **Fix the F3 defects.** There are 7 internal import breakages, 1 undeclared dependency (`ollama`),
   and 3 modules that do I/O at import time, one of them through a forbidden hardcoded home path.
4. **Break the cycle at `core`.** Move the 11 upward dependencies out of `core` (into `compound`/`platform`,
   or behind lazy or injected callables), starting with the weight-1 edges. The goal is `core` with fan-out ≈ 0,
   shaped like `governance`.
5. **Turn this into a ratchet.** Once (1) lands, gate on "no leaf module's closure grows past N" and
   "torch is loaded only by an allow-list of packages", using the same pattern as `lineage_scan.py` and
   `mypy_ratchet.py`. Until then the script stays report-only so it can land without failing CI on
   known state.

## Caveats

- Run in a cloud sandbox with CPU torch rather than the Strix Halo/ROCm box. Absolute times and RSS will
  differ on the target. Module counts and ratios won't.
- The static layer can't tell `from pkg import missing_submodule` apart from `from pkg import Symbol`.
  The dynamic layer and the import-all pass are what catch those.
- Some F3 failures depend on the environment (google-adk and mcp versions resolved by `uv.lock`). They are
  real for anyone running `uv sync --frozen`.

## Remediation log

### R1 — `cohezion.core` made lazy (commit `1e58e12`, 2026-09-25)

`core/__init__.py`: 52 `suppress(Exception)` blocks replaced by a PEP 562 `__getattr__` over a
59-name map. Measured in a fresh interpreter (same sandbox as above):

| Import | Before | After |
|---|---|---|
| `cohezion.core.event_bus` | 498 modules / 5.2 s / 593 MB / torch | **4 modules / 68 ms / 10 MB / no torch** |
| `cohezion.core` | 498 modules | **3 modules / 43 ms** |
| `cohezion.config` | 498 modules | **25 modules / 269 ms / 27 MB** |
| `cohezion.physics`, `reliability`, `security` | 499 / 421 / 581 | 409 / 335 / 535 (still fat via the `compound` and `reliability` facades — next targets) |

Verification:
- **Differential oracle (prior revision):** all 59 names resolve to identical objects; the
  `import *` set is identical. `hasattr` on a broken submodule is still `False`, but the real
  `ImportError` is now chained rather than suppressed.
- **Differential tests:** 46 files (tests/core, data_mesh, sessions, and every test importing
  `cohezion.core`) gave 550 passed / 2 failed / 1 skipped on both revisions. Both failures
  (`test_context_engineering_mcp.py`, a MagicMock-vs-list assertion) were re-confirmed on the old revision.
- **Independent adversarial pass** (separate agent, told to assume the change is broken):
  0 confirmed defects. Checked module-scope side effects, nested submodule access, patch targets,
  self-import cycles, concurrent first access (16 threads), and the CI scanners.
- **Finding:** no production module imports anything from the `cohezion.core` package itself
  (`grep "^from cohezion.core import "` over `src/` is empty). The 59 eager re-exports had no
  production users, which confirms F2: the facade was purely declarative.
