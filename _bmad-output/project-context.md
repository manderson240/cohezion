---
project_name: 'cohezion'
user_name: 'Mike-anderson'
date: '2026-04-22'
status: 'complete'
generated_by: 'bmad-generate-project-context + 8-reviewer party-mode synthesis'
reviewers: [architect, senior-engineer, edge-case-hunter, security, agent-ux, test-ci, data-ml, lenr-physics, governance, agent-team, knowledge-graph]
sections_completed:
  - session_invariants
  - silent_failure_catalog
  - hardware_device
  - language_py311
  - scripts_vs_src
  - new_modules_flume_wire
  - llm_calls_costawarerouter
  - autonomy_tiers
  - graph_data_disambiguation
  - knowledge_graph_graphrag
  - surrealdb
  - physics
  - mcp_stdio
  - agent_coordination
  - security
  - testing
  - development_workflow
  - learning_ids
  - quick_reference
  - open_items
optimized_for_llm: true
rule_count: 95
scope_tags_legend: "[Feature] = agents writing features follow this. [Orch] = orchestrator-layer concern, usually invisible to feature code. [Infra] = infrastructure discipline (hooks, LFS, tooling)."
---

# Project Context for AI Agents — Cohezion

_Critical rules and patterns AI agents must follow. Focus on non-obvious details that prevent silent failures. Read this BEFORE writing code. Rules are tagged [Feature] / [Orch] / [Infra] so you know when they apply._

---

## Session Invariants (Read First)

True on 100% of tasks. If the document gets truncated, THIS section must survive:

- **Cohezion is a POLYGLOT project** — use the right language for the job. Primary Python package at `src/cohezion/` (Python `==3.11.*`); Rust physics core at `src/cohezion-physics-core/` (Cargo); web app at `src/web/` (Next.js / Three.js / Tone.js); multiple MCP servers and scripts in Python. Language rules in this doc apply to the scope they name — do NOT apply Python rules to Rust or TypeScript.
- **Hardware is AMD Ryzen AI MAX+ 395 Strix Halo (gfx1151) — NOT NVIDIA.** Use ROCm/HIP, never CUDA/nvcc/RTX/sm_XX. `torch==2.5.1+rocm6.2` EXACT pin.
- **Python package manager is `uv`** — never `pip`, `pip install`, or `python -m pip`. (Rust uses `cargo`, web uses `npm`/`pnpm` — they follow their own idioms.)
- **All I/O is async in Python** with mandatory timeouts. No `requests.get`, no `time.sleep`, no blocking file I/O in executor paths.
- **`from __future__ import annotations`** at the top of every Python module (exception: Pydantic v2 models with self-refs — see Language section).
- **Never print, echo, or include secrets in any output** — including journey logs, SemanticCache keys, LLM prompts, `_bmad-output/` files, or commits.
- **Every LLM call routes through `CostAwareRouter`** (`src/cohezion/swarm/cost_aware_router.py`). Direct Anthropic / Ollama / Gemini SDK calls are BANNED in production code.
- **`make all` is the CI gate.** Run it before pushing.

### Polyglot Structure

Pick the right language for the job:

| Scope | Language | Location | Toolchain |
|---|---|---|---|
| Orchestration, agents, compound loop, API, ML inference glue | Python 3.11 | `src/cohezion/**` | `uv`, `ruff`, `mypy`, `pytest` |
| High-perf physics, numerical kernels | Rust | `src/cohezion-physics-core/` | `cargo`, `rustfmt`, `clippy` |
| Web UI, dashboards, visualization | TypeScript / React | `src/web/anima_dashboard/` | `npm`, Next.js 16, Three.js, Tone.js |
| MCP stdio servers (tooling) | Python (FastMCP) | `cloud-vault-mcp/`, standalone MCP packages | `uv`, FastMCP ≥3.1 |
| Ops scripts, hooks, one-offs | Python (preferred), Bash | `scripts/` | follow the target language's idioms |

**Cross-language boundaries** (Python ↔ Rust, Python ↔ TS): go through explicit FFI or HTTP/stdio contracts. Do not reach into another language's internals. If calling Rust from Python, use PyO3 bindings exposed at `src/cohezion-physics-core/`'s Python module, not raw ctypes.

---

## Silent-Failure Catalog

These fail without error messages. Each is a real hazard in this codebase:

| # | Silent failure | Symptom | Prevention |
|---|---|---|---|
| 1 | `asyncio_mode` NOT set in `pyproject.toml` | Every `async def test_*` collected as coroutine object, never awaited — all async tests vacuous-pass | Industry standard for pytest-asyncio is `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`. **Action: add it.** Until then, `@pytest.mark.asyncio` is required on every async test. |
| 2 | `conftest.py` transformers mock removed | sklearn-torch BLAS allocator SIGSEGV mid-suite, no stack | Never remove module-level mocks in `tests/conftest.py` (L290) |
| 3 | Agent writes at `AutonomyTier.VOID` | Actions silently no-op; engine withholds execution, no error | Declare tier ≥ `SO3_4` for action-capable code |
| 4 | `except (SubclassError, Exception)` (L359) | Semantically identical to bare `except Exception:` — all errors swallowed | Name 3–5 sibling types only; never include `Exception` in the tuple |
| 5 | `sys.executable` in subprocess (L367) | Works under `uv run`, fails in git hooks/systemd/cron with `ModuleNotFoundError: No module named 'cohezion'` | Use `<repo_root>/.venv/bin/python3` |
| 6 | MCP stdio server prints to stdout | Protocol channel corrupted; client sees malformed JSON, server appears missing | Silence stdout during init; `uv -q run server.py` |
| 7 | Missing YAML frontmatter on `AGENTS.md` | Entire capability set goes dark (L273–L275) | Always include `name` + `description` |
| 8 | Neuron embedding with wrong dim | HNSW returns semantically wrong neighbors; NO write-time error (schema has no dim constraint) | All embeddings: 768-dim float32 via `cohezion.flume.embedding_provider` |
| 9 | LLM call bypasses `CostAwareRouter` | Spend uncounted by BudgetEnforcer; wrong tier; no fallback chain | All LLM calls route through `CostAwareRouter` |
| 10 | `kg-guard` "passes" | `kg-guard` is a v2.0 placeholder that logs intent but doesn't enforce — passing it means nothing | Do not rely on kg-guard for embedding/coherence validation |
| 11 | SurrealDB `UPDATE` in place on bi-temporal table | History silently lost; temporal queries return wrong results | Use append-only: close old record with `valid_to=time::now()`, insert new with `valid_to=NONE` |
| 12 | Pydantic v2 model with `from __future__ import annotations` + self-reference | `model_rebuild()` fails at runtime, not lint time | Either call `model_rebuild()` after types defined, OR omit `__future__` and use string literals |
| 13 | Agent treats platform specialist as live LLM agent | Hangs waiting for a response that never comes — platform specialists are metadata + PRIME skills, not LLM clients | Read the specialist's `CARD` via `get_specialist(name)`; don't SendMessage |

---

## Critical Implementation Rules

### Hardware & Device Placement [Feature]

- ROCm exposes the CUDA API surface, so `torch.cuda.is_available()` returns `True` — this is misleading. Use `torch.version.hip is not None` for AMD-specific branching.
- **Always pass `device=` explicitly**: `torch.zeros(n, device="cuda")`. Default placement is CPU; silently mixed CPU/GPU tensors are the dominant ROCm correctness bug.
- **`@torch.compile` is BANNED on gfx1151** unless explicitly tested. `backend="inductor"` generates Triton kernels that are not reliably supported on gfx1151 in torch 2.5.1+rocm6.2 / pytorch-triton-rocm 3.1.0. If you must compile, use `backend="eager"` — no kernel generation, always safe.
- **AMP: prefer `torch.float16`** on gfx1151. bf16 on RDNA has had bugs through torch 2.5 — verify before using.
- **16 GiB max per single model allocation.** Unified memory: GPU allocations steal from the same 128 GiB pool as CPU, SurrealDB (~2 GB), API (~1 GB), Ollama (4 × up to 8 GB each). OOM takes down the whole host including the IDE. Check `torch.cuda.memory_reserved()` before large loads.
- **`torch==2.5.1+rocm6.2` is an EXACT pin**, not a minimum. Relaxing to `>=` silently pulls a CUDA wheel from PyPI on any machine without the explicit ROCm index. Upgrading requires matching ROCm runtime upgrade AND explicit user approval.

### Python Rules (applies to `src/cohezion/**` and other Python code) [Feature]

- **`from __future__ import annotations`** at the top of every module.
  - **EXCEPTION**: Pydantic v2 model files using self-referential or cross-file forward references. Either call `model_rebuild()` explicitly after all referenced types are defined, OR omit `__future__` and use string-literal annotations. PEP 563 deferred evaluation breaks `get_type_hints()` used internally by Pydantic v2.
- **Import order** (ruff's isort, `known-first-party = ["cohezion"]`): `__future__` → stdlib → third-party → `cohezion.*`. 2 blank lines after imports (`lines-after-imports = 2`).
- **No stealth bare-except** (L359). `except (FooError, Exception)` is semantically identical to `except Exception:` because `Exception` is a supertype. Either name 3–5 sibling types (`except (ImportError, AttributeError, KeyError, TypeError, ValueError)`) or let it propagate.
- **Sentinel values are bugs.** Never return `0.0`, `None`, or `{}` as "something went wrong" — raise a specific exception. No bare `except Exception: pass`. Every handler must log or re-raise.
- **`sys.executable` in subprocess calls is wrong** (L367). Use `<repo_root>/.venv/bin/python3`. Pattern: `scripts/hooks/experiential_learning_hook.py::_python_exec`.

### `scripts/` vs `src/` Scope [Feature]

- **`src/cohezion/**` is package code**: `__init__.py` required in every directory; async I/O only; no blocking calls.
- **`scripts/` is NOT a package**: no `__init__.py` (do not add one — creates accidental packages); `from __future__ import annotations` still required; blocking I/O (`input()`, `sys.stdin`) permitted ONLY in script entrypoints, never in `src/`.

### New Module Creation [Feature] — FLUME, Wire, Size

- **New semantic-state modules MUST encode/decode through FLUME** (L215). Don't retrofit — wire at creation. Contract:
  ```
  encode(x: Tensor[B, D_in]) -> Tensor[B, 256]     # dtype float32, always batched (B≥1)
  decode(z: Tensor[B, 256])  -> Tensor[B, D_in]
  ```
  FLUME is a singleton — device-aware; match your module's device. Never pass unbatched vectors like `(256,)` — broadcasting will silently produce wrong latents.
- **Wire-at-Creation** (L227). Every new module declares a wiring target at creation: `DegradationDetector`, `CapabilityMatrix`, a `CompoundExecutor` step, or a Hookify rule. Build-then-forget = orphan module (41 and counting per KEY_LEARNINGS).
- **File size: <300 lines preferred, 500 hard limit.** For files ALREADY over 500: fix the immediate task, then split in a follow-up commit before marking the task complete. Never add net-new lines to a file at or above 500.

### LLM Call Discipline [Feature] — CostAwareRouter Is Mandatory

- **Every new LLM call path MUST route through `CostAwareRouter`** at `src/cohezion/swarm/cost_aware_router.py`. No direct Anthropic / Ollama / Gemini SDK calls in production code.
- Bypass has three silent consequences: (1) spend uncounted by `BudgetEnforcer`, (2) wrong tier selected (potentially Opus for a trivial task), (3) no automatic fallback when the primary provider fails.
- **Automatic fallback chain** (only when routing through `CostAwareRouter`): Ollama → Flash-Lite → Sonnet → Opus.

### Autonomy Tiers [Orch] — Governance Contract

- **Default tier is `VOID`** (observe-only). Code that mutates state or executes actions must operate at `SO3_4` or above. `AutonomyEngine` silently withholds execution on VOID — it does NOT raise an error. See `src/cohezion/governance/autonomy_engine.py`.
- **HIHO threshold is `0.50` INCLUSIVE.** Use `>= TIER_THRESHOLDS[AutonomyTier.HIHO]`, never `> 0.5`. The 0.50 value is the HIHO stability point, not an arbitrary half.
- **Import `AutonomyTier` freely** in modules participating in access control (data products, MCP tools). Do NOT import `AutonomyEngine` (the singleton) outside `governance/` and `compound/executor.py`.
- **`DataProduct.required_autonomy` defaults to `AutonomyTier.SO12`** (observe-only, safe) — verified at `data_product.py:88`. Override only for action-capable consumers.

### Graph & Data Subsystems [Infra] — Disambiguation

Four subsystems coexist. Wrong import = no lint-time warning:

| Need | Import from | Not to be confused with |
|---|---|---|
| Multi-agent DAG workflows | `cohezion.graph` (`WorkflowEngine`, `AgentNode`) | `cohezion.knowledge_graph` |
| Vector+graph+temporal retrieval | `cohezion.knowledge_graph` (`GraphRAGEngine`) | `cohezion.datamesh.knowledge_graph_layer` |
| Typed data products with SLA | `cohezion.data_mesh` (underscore) — `DataProduct`, `get_cohezion_data_products()` | `cohezion.datamesh` (no underscore) |
| CQRS layer — federation, ingestion, query | `cohezion.datamesh` (no underscore) | `cohezion.data_mesh` (typed products) |

- **`data_mesh/` (typed products) ≠ `datamesh/` (CQRS layer).** The underscore matters. `grep -l "data_mesh\." vs "datamesh\."` before assuming which one a caller uses.
- **Guards in `make all`:** `data-mesh-guard` (SLA/quality violations in `data_mesh_registry.json`), `kg-guard` (currently a placeholder — see below).

### Knowledge Graph & GraphRAG [Orch] — Mostly Leave It Alone

**Coding agents should NOT call `GraphRAGEngine` directly.** GraphRAG is an orchestrator-internal read interface. For session-level knowledge access use `vault_find_relevant_context(query)`, `KEY_LEARNINGS.md`, and `entire explain`.

When you DO need GraphRAG:

- **Write path: JourneyTracker only.** Never write to `neurons` or `synapses` tables directly. Direct writes bypass coherence checks and can corrupt the HNSW index.
- **Embeddings: 768-dim float32** via `cohezion.flume.embedding_provider`. SurrealDB does NOT enforce dimension at the schema level (`genesis_schema.surql` uses `TYPE array` with no constraint) — mismatched embeddings silently corrupt HNSW retrieval (Silent-Failure #8).
- **Query mode selection** (narrowest first):
  - `vector_search` — semantic similarity, top-K nearest neighbors
  - `graph_search` — entity-link traversal from a known `neuron_id` anchor
  - `temporal_search` — point-in-time reconstruction (provenance/rollback)
  - `hybrid_search` — expensive; justify reaching for it
- **`graph_search` is 1-hop only.** `depth` parameter defaults to 1; the implementation only supports 1-hop (`graphrag_engine.py:99` docstring: "currently 1-hop; future versions will support deeper"). Chain calls explicitly for multi-hop.
- **`temporal_search(as_of=T)` returns an empty list** when T precedes all records' `valid_from`. Empty is a VALID "no state at this time" response, NOT an error. Callers must not pattern-match "empty = bug."
- **`hybrid_search` score is vector-only.** Graph is expansion, temporal is a filter, neither contributes to the score. Do not rank results on the returned score without domain-specific re-ranking.
- **`kg-guard` is currently a placeholder** (v2.0 at `src/cohezion/knowledge_graph/scripts/kg_guard.py`). Logs intent but does not enforce coherence thresholds. Do NOT rely on it catching bugs. Verify behavior before depending on its output.

### SurrealDB [Feature]

- **Single client**: `cohezion.core.persistence.surreal_client` (or `cohezion.persistence.surreal_client` depending on import path). Never open a raw WebSocket — the client manages reconnection, auth, versioned-query mode.
- **Bi-temporal write pattern — APPEND-ONLY** for `neurons`, `agent_journey`, `universe_node`:
  ```sql
  -- Insert with open-ended validity
  CREATE agent_journey SET
    state = $state,
    valid_from = time::now(),
    valid_to = NONE;

  -- On supersede: close old, then insert new
  UPDATE agent_journey SET valid_to = time::now() WHERE id = $old_id;
  CREATE agent_journey SET
    state = $new_state,
    valid_from = time::now(),
    valid_to = NONE;
  ```
  **Never `UPDATE state` in place.** `?versioned=true` on the KV layer is separate from application-level bi-temporal columns — you must maintain both.
- **Point-in-time read:**
  ```sql
  SELECT * FROM agent_journey
    WHERE valid_from <= $t AND (valid_to > $t OR valid_to IS NONE);
  ```
- **Local:** `ws://localhost:8001` (SurrealKV backend, `?versioned=true`).
- **Credentials — secure pattern:** SurrealDB credentials come from the Bitwarden vault, NOT from `.env`, `pyproject.toml`, shell history, or hardcoded strings. The client at `cohezion.core.persistence.surreal_client` reads from vault key `surreal/local` (or `surreal/<environment>`). Default `root/root` is INSECURE — never accept it even for local dev. If the vault lookup fails, refuse to connect rather than falling back to defaults.

### Physics Code [Infra]

- **Before editing any file in `src/cohezion/physics/`:** run `uv run pytest tests/physics/ -v`. Verify the 37 conservation + invariant tests pass BEFORE and AFTER your change. These are NOT unit tests — they are physics contracts.
  - Anchors: `invariant_checker.py` (22 conservation + 15 invariants), `observer_patch.py` (OPH axioms, SPIN coherence).
- **Theoretical-bridge anti-pattern.** HIHO / EVO / LENR are THEORETICAL framings, not implementation contracts. The 0.50 coherence threshold in cost-routing is a design metaphor. Do NOT import physics/ modules into `compound/`, `swarm/`, `api/`, or `governance/` to "implement" HIHO semantics. `from cohezion.physics.evo_model import EVOState` in a compound executor is a cross-layer contamination bug.
- **Extending `evo_model.py`:** `EVOState` requires minimum fields `spin`, `charge_density`, `coherence`, `lifetime`. Missing fields = silent `KeyError` in `world_model/` consumers, not at construction.
- **Geometry & units:** SI units throughout. Right-handed toroidal orientation in `mhd_mereon.py` / `mereon_projector.py` — do NOT substitute cylindrical as an approximation. See `src/cohezion/skills/advanced_physics_simulation.md` for conventions.
- **`cosmogony.py`** has a 10-step structure mapped to `src/cohezion/worldviews/` (16 traditions). Not self-documenting — read `advanced_physics_simulation.md` before assuming structure is dead symbolic code.

### MCP stdio Servers [Infra]

- **YAML frontmatter on `AGENTS.md` MANDATORY** (`name` + `description`). Missing = silent failure, entire capability set goes dark (L273–L275).
- **Config lookups MUST be lazy** — not at module import. Eager vault/Bitwarden checks exceed the CLI handshake timeout. WRONG: `SECRET = get_vault_secret()` at module scope. RIGHT: `def get_secret(): return get_vault_secret()`.
- **stdout MUST be silent during init.** stdout is the protocol channel; any `print`/`logger.info` at module scope corrupts the stream. Use `.venv/bin/python server.py` or `uv -q run server.py`.
- **Trust boundary.** MCP stdio servers trust the launching process — whoever execs the server binary can invoke every tool. Servers exposing tools that read secrets or PII require either caller-identity verification at connection time OR an explicit note in `AGENTS.md` that the server is orchestrator-only.
- **Proven template:** `cloud-vault-mcp/` (40+ tools, FastMCP). Copy when building new MCP servers rather than greenfield.

### Agent Teams & Coordination [Orch] — Mostly Not Your Problem

- **Solo first.** Spawn another agent only when parallelism OR isolation is the explicit requirement. Workflow-enforcement global rule already forbids ad-hoc sub-agents — use `Read`/`Grep`/`Glob` directly.
- **Platform specialists are PRIME skill markdown, NOT running services.** `vault-keeper`, `claude-specialist`, `ollama-specialist`, `mcp-specialist`, `platform-coordinator`, `surreal-dba`, `gemini-specialist` — treating them as live agents with inboxes will hang your session. Read the PRIME markdown or invoke the BMAD skill.
- **Agent cards (A2A discovery) are now available for 7 platform specialists.** `src/cohezion/agents/specialists/` exports `VaultKeeper`, `SurrealDBA`, `ClaudeSpecialist`, `GeminiSpecialist`, `OllamaSpecialist`, `MCPSpecialist`, `PlatformCoordinator` — each with a frozen `AgentCard` dataclass declaring name, description, role, capabilities, principles, prime_skill_ref, and canonical_modules. Discover via `cohezion.agents.specialists.list_specialists()` / `describe_all()` / `get_specialist(name)`. These are STILL NOT live LLM-calling agents — they are metadata entities. Do not SendMessage to them.
- **Domain agents (e.g. `EcoResilienceAgent`) are a different class** — they subclass `cohezion.agents.base.BaseAgent` and DO call LLMs via an injected provider. Do not confuse the two: platform specialists are lightweight metadata; domain agents are heavy LLM clients. A single directory (`agents/specialists/`) hosts both patterns for historical reasons — check which base class a file inherits from.
- **A2A not yet stable.** Until A2A is marked stable, inter-agent calls go through the existing Python call graph (`TeamExecutor`, `ExecutionOrchestrator`). Do NOT implement ad-hoc `SendMessage` / inbox semantics — that is the A2A team's work; premature abstraction will conflict.
- **Claude Code Agent Teams** (experimental, v2.1.32+) is disabled by default. Do not assume availability.
- **Canonical locations:** new specialists → `src/cohezion/agents/specialists/`; new orchestration infrastructure → `src/cohezion/swarm/`. Do NOT create new top-level agent directories. `agent/` (singular) is the harness, `agentjet/` is a separate abstraction — neither is a specialist home.

### Security [Feature] — Hard Stops

- **Never print, echo, or include passwords/secrets in any output.**
- **All values returned by vault/Bitwarden client calls are SECRETS.** Never log, print, cache in `SemanticCache`, include in LLM prompts, or write to journey records. Vault keys follow `<service>/<name>`.
- **No `SUDO_PASSWORD` in `.env`.** Configure passwordless sudo or run interactively. Never parse `.env` for sudo creds.
- **External content must be wrapped in untrusted-content delimiters** before LLM interpolation. GitHub issues (`github-scout` daemon), PR bodies, commit messages, web fetches. Never f-string external content directly into prompts — it's a prompt-injection vector straight into `JourneyTracker`.
- **Sanitize before persisting.** Agent inputs/outputs passed to `JourneyTracker` or `SemanticCache` must never contain secrets or verbatim external content. Prompt-injected journey entries pollute every future session that reads journey history.
- **New SurrealDB tables carrying user-visible data** must carry a data classification (internal/PII/secret). Secrets must NOT be stored in SurrealDB.
- **Supply chain:** `uv.lock` is committed (verified). New dependencies MUST be added to `pyproject.toml`, then `uv lock` run. **`uv pip install X` without updating `pyproject.toml` is BANNED** — dep won't be in the diff, won't trigger hooks, won't be reviewable.
- **`detect-secrets` baseline.** `.secrets.baseline` updates require explicit human review and a commit-message justification for every new entry. Agents must NOT run `detect-secrets scan --update .secrets.baseline` autonomously — it silently whitelists real secrets pattern-matching known false-negatives.
- **`_bmad-output/` is committed by design** (BMAD convention — agents need planning artifacts cross-session/cross-machine). This file ends up in git. **Never put real credentials in it, even as examples.** Ensure `.secrets.baseline` covers `_bmad-output/**` so `detect-secrets` scans it; any mask placeholder (`<VAULT_KEY>`, `***`, `REDACTED`) is fine, but no real values.
- **External-content prompt injection.** No `prompt-injection-guard` skill exists in this project (verified: absent from `~/.claude/skills/` and `.claude/skills/`). Until it does, manual vigilance is the control: any agent reading GitHub issue text, PR bodies, commit messages, or web fetches must wrap that content in untrusted-content delimiters before LLM interpolation. **This gap is a tracked follow-up.**

### Testing [Feature]

- **`tests/conftest.py` mocks `transformers` and `sentence_transformers` at module import** (before pytest collection) to prevent a sklearn-torch BLAS allocator SIGSEGV (L290). Never remove these module-level mocks. Never import real `transformers` in a test file.
- **Mock at the source, not the call site**: `@patch("cohezion.swarm.compound_client.get_compound_client")`, NOT `@patch("anthropic.Anthropic")`.
- **Fixture scopes:** default to `function`. `session`-scoped fixtures must be read-only or stateless. A session-scoped `AsyncMock` corrupts state across the entire suite.
- **Filesystem writes in tests use `tmp_path`.** No `Path.cwd()`, no relative paths like `Path("output/")` (the `no-hardcoded-home-paths` hook catches `/home/` but not `Path("output/")`).
- **Markers:** `fast` (<1s, no services), `integration` (Ollama/SurrealDB), `mcp` (vault). A test cannot be both `fast` AND `integration` — that's contradictory.
- **`asyncio_mode = "auto"` is currently NOT set** in `pyproject.toml [tool.pytest.ini_options]` — verified. Industry standard for pytest-asyncio is `asyncio_mode = "auto"`. **Action: add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`.** Until that change lands, every `async def test_*` requires an explicit `@pytest.mark.asyncio` decorator — without either, async tests collect as coroutine objects and vacuous-pass.
- Under `asyncio_mode="auto"`: never call `asyncio.run()` or `loop.run_until_complete()` inside a test or fixture. Use `async def` tests and `await` directly.
- **Determinism.** Tests asserting numerical values must call a `seed_everything(42)` fixture covering: `PYTHONHASHSEED`, `random.seed`, `np.random.seed`, `torch.manual_seed`, `torch.cuda.manual_seed_all`. Gymnasium envs use `env.reset(seed=seed)` — `env.seed()` was removed in gymnasium ≥0.26.
- **Correctness Gate before performance.** Assert shapes/dtypes → hand-calculable input → `torch.allclose` vs reference → edge cases → THEN measure perf.
- **Execution verifies correctness, tests verify code.** Run the actual program after tests pass — check exit code, stdout/stderr, file changes. Already a global rule; reinforced for ML/physics code where mocked tests hide real failures.

### Development Workflow [Feature]

- **Git is read-only by default.** Write ops (`add`, `commit`, `push`, `pull`, `rebase`, `reset`, `stash`, `checkout`) need EXPLICIT user permission. `git add -f` is BANNED — no exceptions. See `~/.claude/rules/git-operations.md`.
- **Commit style:** `feat(scope):` / `fix(scope):` conventional prefix when touching `src/cohezion/`. Free-form acceptable on research/scratch branches (recent history has both).
- **Branch patterns:**
  - `kaggle/*` — competition work (enforced by `kaggle-branch-guard` pre-commit hook)
  - `spec/<slug>` — worktrees from `/spec`
  - `isolated/<name>` — isolated feature branches
  - `agent-autonomous-session-*` — autonomous sessions
  - `archive/stash/*` — preserved WIP (do NOT `git stash pop` `stash@{0}` — it holds pre-Kaggle session-oom work; see `~/.claude/rules/kaggle-portfolio.md`)
- **Worktree isolation:** Kaggle work lives in `.worktrees/nemotron-june/` (branch `kaggle/nemotron-june`) and `.worktrees/agi-golf/` (branch `kaggle/agi-golf`). Do NOT make Kaggle changes on `isolated/session-oom-modularity`. Use `git -C <worktree-path> ...` for per-worktree operations since `cwd` persists across Bash calls.
- **Git LFS active** for: `*.so`, `*.whl`, `*.pt`, `*.pth`, `*.pkl`, `*.tar.gz`, `*.bundle`, `*.jsonl`. Bundle 182 MB (was 14 GB pre-migration). **`.jsonl` exemption:** small test fixtures under `tests/` should not be LFS-tracked — if `lfs-pointer-check` complains on a small fixture, add `tests/**/*.jsonl -filter=lfs -diff=lfs -merge=lfs -text` to `.gitattributes`.
- **Pre-commit hooks** (ordering principle: formatters → linters → file guards → branch guards → security):
  - Formatters: `ruff-format`
  - Linters: `ruff`, `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-merge-conflict`
  - File guards: `check-added-large-files`, `detect-private-key`, `no-hardcoded-home-paths`, `large-artifact-gate`, `lfs-pointer-check`
  - Branch guards: `kaggle-branch-guard`, `version-consistency`, `playwright-tests`
  - Security: `detect-secrets`, `bandit`
  - **New hooks** go in the matching group. Never `--no-verify`.
- **Surgical commits against high-churn trees (L363+L368):** before committing, verify `git diff --cached --name-only` contains EXACTLY your intended files. If pre-commit's internal stash/restore cycle expanded the set, soft-reset and re-stage explicitly: `git reset --soft HEAD~1 && git reset HEAD && git add <exact paths>`.
- **`make all` = format + lint + type-check + test + 8 guards.** Guards: `agent-guard`, `mcp-guard`, `kg-guard` (placeholder), `data-mesh-guard`, `health-guard`, `async-guard`, `routing-guard`, `a2a-guard`. Each guard invokes a script — source of truth is the `Makefile` target definitions. To debug a failing guard, run its script directly (e.g. `uv run python src/cohezion/knowledge_graph/scripts/kg_guard.py --verbose`); do NOT suppress with `|| true`.

### Learning IDs — Resolution Order

`L###` references resolve in this order:

1. **`src/cohezion/knowledge_graph/KEY_LEARNINGS.md`** — primary ledger (L1–L296 as of 2026-04, 264 lines).
2. **`CLAUDE.md`** — newer IDs (L333+, L359, L363, L366, L367, L368) not yet back-filled to KEY_LEARNINGS.md. Search `§"Coding Standards"` and `§"Operational Patterns"`.
3. **`~/vaults/cohezion-vault/`** — extended context via `vault_find_relevant_context("L###")`.

**Append-only.** Correct prior errors with explicit annotation, not inline rewrites. Schema: `L### (Session NNN): [imperative title] — [detail paragraph]`. Commit L entries with the code change they document — never batch distinct learnings in one commit (breaks `entire explain` checkpoint correlation).

---

## Quick Reference

| Need | File / Command |
|---|---|
| Hardware truth anchor | `HARDWARE_PROFILE_PRIME.md` |
| Constitution (hard constraints) | `.agent/CONSTITUTION.md` |
| Charter (design theory) | `.agent/COHEZION_CHARTER.md` |
| Test isolation (BLAS SIGSEGV prevention) | `tests/conftest.py` |
| Compound executor (11-step pipeline) | `src/cohezion/compound/executor.py` |
| Cost routing (mandatory for LLM calls) | `src/cohezion/swarm/cost_aware_router.py` |
| FLUME VAE (256D latent) | `src/cohezion/flume/flume_vae.py` |
| Embedding provider (768-dim) | `src/cohezion/flume/embedding_provider.py` |
| Journey tracking (only write path to graph) | `src/cohezion/compound/journey_tracker.py` |
| GraphRAG (orchestrator-only reads) | `src/cohezion/knowledge_graph/graphrag_engine.py` |
| Key learnings ledger | `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` |
| Physics invariants (37 contracts) | `src/cohezion/physics/invariant_checker.py` |
| OPH bridge / SPIN coherence | `src/cohezion/physics/observer_patch.py` |
| Advanced physics simulation | `src/cohezion/skills/advanced_physics_simulation.md` |
| Autonomy tiers / governance | `src/cohezion/governance/autonomy_engine.py` |
| Data products (typed SLA) | `src/cohezion/data_mesh/data_product.py` |
| MCP template (proven, copy from) | `cloud-vault-mcp/` |
| CI gate | `make all` |
| Pre-commit config | `.pre-commit-config.yaml` |
| Subprocess venv python | `<repo_root>/.venv/bin/python3` |

---

## Resolved Decisions & Follow-Ups

Decisions locked in from synthesis review:

| # | Item | Decision | Follow-up action |
|---|---|---|---|
| 1 | CLAUDE.md says "Python 3.13+"; pyproject.toml pins `==3.11.*` | **Python package is 3.11. Project is polyglot — Rust and TS live alongside Python.** See "Polyglot Structure" section. | Fix CLAUDE.md to say `Python 3.11+ for src/cohezion/` and add a polyglot note. |
| 2 | `asyncio_mode = "auto"` not set in pyproject.toml | **Adopt industry standard.** Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`. | PR: add one line to pyproject.toml; remove redundant `@pytest.mark.asyncio` decorators in a follow-up pass. |
| 3 | `_bmad-output/` gitignore status | **Committed by design** (BMAD convention — planning artifacts are shared). | Ensure `.secrets.baseline` covers `_bmad-output/**`; never store real credentials in any file there. |
| 4 | SurrealDB credentials source | **Vault-backed, never default.** Client reads from Bitwarden key `surreal/local` (or `surreal/<env>`). Refuse to connect if vault lookup fails — no fallback to `root/root`. | Verify `cohezion.core.persistence.surreal_client` actually implements this pattern; if not, update it. |
| 5 | `prompt-injection-guard` skill | **Does not exist.** Gap confirmed. | Tracked follow-up: design and implement `prompt-injection-guard` skill. Until then, manual delimiter-wrapping is the control. |
| 6 | 7-specialist A2A roster | **DONE (2026-04-22).** `src/cohezion/agents/specialists/` now exports 7 `PlatformSpecialist` subclasses with `AgentCard` metadata, registry, and discovery functions. | Write per-specialist PRIME skill markdown at `src/cohezion/skills/<name>.md` (paths referenced by each `CARD.prime_skill_ref`). |

**Verified during synthesis** (no action needed):

- Python package `requires-python = "==3.11.*"` ✓
- `uv.lock` committed ✓
- `src/cohezion-physics-core/Cargo.toml` present (Rust) ✓
- `src/web/` present (TypeScript / Next.js) ✓
- `KEY_LEARNINGS.md` exists at 264 lines, L1–L296 ✓
- `DataProduct.required_autonomy` defaults to `SO12` (safe) ✓
- `graph_search` is 1-hop only ✓
- Neuron embeddings are 768-dim (schema has no enforcement) ✓
- `kg-guard` is a v2.0 placeholder (logs intent, does not enforce) ✓
- `hybrid_search` score is vector-only ✓

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code. The Session Invariants block at the top is non-negotiable.
- When a rule tagged `[Feature]` conflicts with one tagged `[Orch]`, apply the Feature rule — Orch rules describe orchestrator internals you should not touch.
- When in doubt between two interpretations, pick the more restrictive option.
- If you find yourself reaching for a rule that isn't here, propose an addition in your output rather than guessing.
- For deeper context on any Learning ID (`L###`), follow the resolution order in the Learning IDs section — do NOT guess or ignore.

**For Humans:**
- Keep this file lean. Every addition costs context tokens on every session. Cut ruthlessly when rules become obvious via tooling (ruff, mypy) or CLAUDE.md.
- Update when: a new silent-failure mode is discovered, the tech stack changes (polyglot language added, major version bump), a new cross-layer boundary is established, or a reviewer catches a contradiction with CLAUDE.md.
- The six Resolved Decisions table items are follow-ups — each one is a concrete actionable change, not indefinite TODO text. Close them.
- Review quarterly. Deprecate rules that (a) haven't fired in practice, (b) are enforced by tooling, or (c) duplicate CLAUDE.md after drift.
- `_bmad-output/project-context.md` is committed — any change to this file is a visible PR. Treat it like you'd treat a CLAUDE.md edit.

Last Updated: 2026-04-22
