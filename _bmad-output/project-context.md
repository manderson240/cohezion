---
project_name: 'cohezion'
user_name: 'Mike-anderson'
date: '2026-04-22'
status: 'draft'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - code_quality_rules
  - workflow_rules
  - dont_miss_rules
  - hardware_and_environment
optimized_for_llm: true
---

# Project Context for AI Agents — Cohezion

_Critical rules and patterns AI agents must follow when implementing code in this project. Focused on unobvious details that agents might otherwise miss. Read this BEFORE writing code — it prevents the most common drift patterns._

---

## Technology Stack & Versions

**Language & Tooling:**
- Python `==3.11.*` (EXACT, pinned in `pyproject.toml`; ruff target `py311`, mypy `python_version=3.11`).
  ⚠️ Do NOT use `match/case` exhaustiveness patterns requiring 3.12+, `type` statement (PEP 695), or 3.13-only syntax. CLAUDE.md's "3.13+" reference is stale.
- Package manager: `uv` — **MANDATORY**. Never `pip`, `pip install`, or `python -m pip` directly.
- Formatter/linter: `ruff >=0.8.0` (line-length **100**, double-quote style)
- Type checker: `mypy >=1.5.0` (`strict_equality=true`, `no_implicit_optional=true`, `check_untyped_defs=true`)

**Runtime:**
- FastAPI ≥0.104.0 (92 route handlers on port 8080)
- Pydantic ≥2.0.0 + `pydantic-settings` (use Pydantic v2 APIs — `model_validate`, `model_dump`, not v1 `parse_obj`/`dict()`)
- SurrealDB ≥0.3.0 via WebSocket on `ws://localhost:8001` (SurrealKV backend, `?versioned=true`)
- Redis ≥7.2.1, aiohttp ≥3.13.3, httpx ≥0.25.0, structlog ≥25.5.0
- fastmcp ≥3.1.0 (MCP server framework)

**ML/Compute:**
- `torch==2.5.1+rocm6.2` + `pytorch-triton-rocm==3.1.0` — **ROCm, NOT CUDA**
- Explicit UV index: `[[tool.uv.index]] name = "pytorch-rocm"` — torch/torchvision/torchaudio/triton resolved from this index only
- numpy ≥1.24.0, gymnasium ≥1.2.3, qiskit ≥1.0.0, bluequbit ≥0.18.5b1, polars ≥1.39.3, datasets ≥4.5.0

**Test Stack:**
- pytest ≥9.0.2, pytest-asyncio ≥1.3.0, pytest-cov ≥7.0.0
- Markers: `fast` (<1s, no live services), `integration` (Ollama/SurrealDB), `mcp` (vault access)
- 509 test files, 6,369 collected

**Canonical commands:**
```bash
uv run pytest tests/ -q              # Full suite
uv run pytest tests/ -m fast         # Fast only
make all                              # format + lint + type-check + test + 8 guards
make format && make lint             # ruff format + ruff --fix
make type-check                      # mypy
make validate                        # 23-check compound loop validation (~18s)
```

---

## Critical Implementation Rules

### Hardware & Environment Rules (TRUTH ANCHOR)

- **Hardware is AMD Ryzen AI MAX+ 395 "Strix Halo" — NOT NVIDIA.** iGPU is Radeon 8060S with unified memory (128 GiB LPDDR5X). Never generate code that assumes CUDA, nvcc, RTX, sm_XX, or NVIDIA driver paths. Use ROCm / HIP / gfx1151 wherever GPU code is needed. See `HARDWARE_PROFILE_PRIME.md`.
- **No `torch.cuda.is_available()` gating without AMD fallback.** Use device-agnostic code: `device = torch.device("cuda" if torch.cuda.is_available() else "cpu")` works because ROCm torch exposes the CUDA API surface, but check `torch.version.hip` for AMD-specific branches.
- **Ollama global limit: 4 concurrent models.** DynamicModelRouter enforces this. Don't spawn unbounded local-model workers.
- **Cloud cost posture:** Cloud Run is free-tier only (no idle instances). Prefer local Ollama / Lemonade over API calls. Cost tiers: 70% simple (free local) → 20% medium (Sonnet $3/M) → 10% hard (Opus $15/M).

### Language-Specific Rules (Python 3.11)

- **`from __future__ import annotations` at the top of every module.** Enables PEP 563 string annotations; non-negotiable for mypy behavior in this codebase.
- **Import order** (isort via ruff, `known-first-party = ["cohezion"]`):
  1. `__future__`
  2. stdlib
  3. third-party
  4. `cohezion.*`
  with 2 blank lines after imports (`lines-after-imports = 2`).
- **All I/O is async.** No `requests.get`, no `time.sleep`, no blocking file I/O in executor paths. Use `httpx.AsyncClient`, `asyncio.sleep`, `aiofiles`. Timeouts are mandatory on every external call.
- **Error handling — no stealth bare-except (Learning 359).** `except (SomeSubclass, Exception)` is semantically identical to `except Exception:` because `Exception` is a supertype. Either name 3–5 sibling types (`except (ImportError, AttributeError, KeyError, TypeError, ValueError)`) or let the exception propagate. Never suppress errors silently.
- **Sentinel values are bugs.** Do not return `0.0`, `None`, or `{}` as "something went wrong." Raise a specific exception. No bare `except Exception: pass`. Every handler must log or re-raise.
- **`sys.executable` in subprocesses is wrong (Learning 367).** Use `<repo_root>/.venv/bin/python3` for subprocesses — `sys.executable` resolves to system Python when the parent is launched by git hooks / systemd / cron, causing `ModuleNotFoundError: No module named 'cohezion'`. Pattern in `scripts/hooks/experiential_learning_hook.py::_python_exec`.
- **Type hints are expected** (`check_untyped_defs=true`). Use PEP 604 unions (`str | None`) not `Optional[str]`. Built-in generics (`list[str]`, `dict[str, int]`) not `List`/`Dict`.
- **Dataclasses, Pydantic v2, or TypedDict** at module boundaries. No loose `dict[str, Any]` for public APIs.

### Framework-Specific Rules

**FastAPI / API:**
- Routes live under `src/cohezion/api/` (`__init__.py` assembles 92 handlers). Services under `src/cohezion/api/services/`.
- Pydantic at every boundary — request and response models. Use `response_model=` on route decorators.
- Start with `uv run uvicorn cohezion.api:app --reload`.

**Pydantic v2:**
- `model_config = ConfigDict(...)` not nested `class Config:`.
- `.model_validate(data)` / `.model_dump()` — NOT `parse_obj` / `.dict()`.
- `@field_validator` / `@model_validator` — NOT `@validator`.

**SurrealDB:**
- Single client at `src/cohezion/persistence/surreal_client.py`. Always reuse — don't open new WebSocket connections per call.
- Bi-temporal schemas (`valid_from`/`valid_to`) on `neurons`, `agent_journey`, `universe_node`. Query with VERSION clause for temporal snapshots.
- SurrealQL record-ID interpolation (`plan:{slug}`) is allowed and has a per-file ruff ignore for `S608` in `src/cohezion/traceability/plan_graph.py` — do not expand that ignore without review.

**FLUME-First Architecture:**
- New modules that produce or consume semantic state MUST encode/decode through FLUME (`src/cohezion/flume/flume_vae.py`, 256D latent). Start with `encode()` → latent reasoning → `decode()`. Do NOT retrofit — wire from the start (Learning 215).
- **Wire-at-Creation (Learning 227):** Every new module MUST declare a wiring target at creation: DegradationDetector, CapabilityMatrix, CompoundExecutor step, or Hookify rule. Build-then-forget = 41 orphaned modules.

**Compound Executor (11-step pipeline):**
- `src/cohezion/compound/executor.py` orchestrates: RequestAlignmentAnalyzer → GlobalMetricsAggregator → DegradationDetector → JourneyTracker (+JEPA+bioelectric) → OuroborosBridge (+Mycelium) → MyceliumRegistry → RetrospectionEngine → SkillRefiner → SkillConsensusVoter.
- Do not bypass steps. Do not add a 12th step without updating the CLAUDE.md table and the corresponding test in `tests/compound/`.

**MCP stdio Servers (L273–L275, hard rules):**
- Markdown `AGENTS.md` MUST have valid YAML frontmatter with `name` + `description`. Missing frontmatter = silent failure; the entire server disappears.
- Config lookups MUST be lazy — not at module import. Slow checks (e.g. Bitwarden vault) at startup exceed the CLI handshake timeout. WRONG: `SECRET = get_vault_secret()`. RIGHT: `def get_secret(): return get_vault_secret()`.
- **stdout must be silent during init.** stdout is the message channel; any print/log corrupts the protocol. Use `.venv/bin/python server.py` or `uv -q run server.py`. No `logger.info("Starting…")` at module scope.

### Testing Rules

- **Test isolation via `tests/conftest.py`** is load-bearing. It mocks `sentence_transformers` and `transformers` at module import before anything else runs, to prevent a sklearn-torch BLAS allocator SIGSEGV (L290, Session 94). Never remove those module-level mocks. Never import real `transformers` in a test file — `tests/test_aimo_predict_tdd.py` overrides with `MagicMock` anyway.
- **Mock at the source**, not at the call site: `@patch("cohezion.swarm.compound_client.get_compound_client")`, not `@patch("anthropic.Anthropic")`.
- **Singleton resets** for FLUME VAE, RL policy, and loggers are in `conftest.py`. New singletons MUST add a reset fixture or tests will flake across ordering.
- **Marker discipline:** Pure unit = `fast` (<1s, no network, no disk beyond tmp_path). Anything requiring Ollama/SurrealDB = `integration`. Anything requiring vault = `mcp`. CI runs `fast` by default.
- **`asyncio_mode = "auto"`** (pytest-asyncio). `async def test_*` is picked up automatically — no `@pytest.mark.asyncio` decorator needed.
- **One feature → manual validate → 5 tests.** NOT 600 pre-implementation tests. Implement → run → verify → then tests. (Sessions 40–55 principle.)
- **Verify execution, not just test pass (`verification-before-completion.md`).** Tests passing ≠ program working. After tests pass, RUN the actual program and check exit codes / output / file changes.
- **Correctness Gate before performance.** Assert shapes/dtypes → hand-calculable input → compare against reference (`torch.allclose`) → edge cases → THEN measure perf.

### Code Quality & Style Rules

- **File size limit:** production files <300 lines preferred, 500 hard limit. Above 500 = refactor immediately.
- **Every `src/cohezion/**` dir MUST have `__init__.py`.** Enables vault skill discovery.
- **Naming:**
  - Modules: `snake_case.py`
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `SCREAMING_SNAKE_CASE`
  - Private: `_leading_underscore`
  - Descriptive, intent-revealing names: `calculate_discount`, not `process`/`handle`/`data`/`temp`.
- **Dead code:** delete unused functions and commented blocks. Use git to recover.
- **Dependency check before modifying:** `Grep` or LSP `findReferences` to find all callers. Plan updates for affected call sites.
- **Structured config files** humans may read use YAML frontmatter `.md` (vault, skills, `.context/` convention). JSON only for wire formats / machine-to-machine.
- **Ruff rules active:** `E, F, W, I, N, UP, S, B, A, C4, SIM, TCH, RUF`. `S` (bandit) is on — no `assert` in production code (tests have a per-file override).
- **YAML frontmatter is mandatory** on all agent markdown files and skill definitions. Missing `name`/`description` silently disables the file.

### Development Workflow Rules

- **Git operations are READ-ONLY by default.** Read freely (`status`, `diff`, `log`, `show`, `branch`). Write operations (`add`, `commit`, `push`, `pull`, `rebase`, `reset`, `stash`, `checkout`, etc.) require EXPLICIT user permission. See `~/.claude/rules/git-operations.md`.
- **`git add -f` is BANNED.** No exceptions. If something is gitignored, update `.gitignore` instead.
- **Commit message style is mixed but biased toward descriptive + conventional prefixes.** Examples from recent history: `feat(skills): …`, `feat(hooks): …`, `NeuroGolf: …`, `CompetitionOrchestrator: …`. Use conventional prefix (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) when touching `src/cohezion/`; free-form is acceptable for research/scratch commits on non-main branches.
- **Branch patterns:**
  - `kaggle/*` — competition work (enforced by `kaggle-branch-guard` pre-commit hook)
  - `spec/<slug>` — worktrees from `/spec` workflow
  - `isolated/<name>` — isolated feature branches
  - `agent-autonomous-session-*` — autonomous agent sessions
  - `archive/stash/*` — preserved WIP (do NOT `git stash pop` stash@{0} without checking `~/.claude/rules/kaggle-portfolio.md`)
- **Pre-commit hooks enforce** (in order): `ruff-format`, `ruff`, `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`, `check-merge-conflict`, `detect-private-key`, `no-hardcoded-home-paths`, `playwright-tests`, `large-artifact-gate`, **`lfs-pointer-check`** (Git LFS enforcement), **`kaggle-branch-guard`** (competition-branch isolation), `version-consistency`, `detect-secrets`, `bandit`.
- **Never `--no-verify`** to skip hooks. Investigate the failure.
- **Surgical commits against high-churn trees (L363 + L368):** Before committing, verify the staged set explicitly: `git diff --cached --name-only | grep -iE "<churn-pattern>"` must return empty. If pre-commit's internal stash/restore cycle expanded the file set, soft-reset and re-stage explicitly. Never `git add .`.
- **Git LFS is active.** `.gitattributes` tracks `*.so *.whl *.pt *.pth *.pkl *.tar.gz *.bundle *.jsonl`. Bundle size is 182MB (was 14GB pre-migration). If you commit a large binary without LFS, `lfs-pointer-check` will fail — good.
- **`make all` is the CI gate:** `format + lint + type-check + test + agent-guard + mcp-guard + kg-guard + data-mesh-guard + health-guard + async-guard + routing-guard + a2a-guard`. Run it before pushing.
- **Worktrees:** `.worktrees/<slug>/` is the pattern. `/spec` auto-creates one. Do NOT make Kaggle changes on `isolated/session-oom-modularity` — use the dedicated kaggle worktrees (see `~/.claude/rules/kaggle-portfolio.md`).

### Critical Don't-Miss Rules (Gotchas)

**Security:**
- **Never print, echo, or display passwords or secrets.** Anywhere. Ever.
- **Never parse `.env` for `SUDO_PASSWORD`.** Configure passwordless sudo or run interactively.
- **Never write secrets to temp files that persist.**
- `detect-secrets` + `bandit` pre-commit hooks enforce, but don't rely on them — think first.

**Anti-patterns that waste hours:**
- **Research-first development.** If the feature doesn't exist yet, DON'T build infrastructure. Implement → validate → then test. (Anti-pattern 2,000–10,000 tokens wasted per instance.)
- **Building a helper/framework/meta-tool when the task was to deliver a feature.** STOP. Re-read the task. "Would deleting this new helper still let me deliver?" If yes, you don't need it. After 3 drift instances in a session, ASK the user if the approach is wrong.
- **`sys.executable` in subprocesses** (see Language Rules). Silently breaks in hooks/cron.
- **Stealth bare-except** `except (FooError, Exception)` (see Language Rules). Suppresses everything.
- **Opening a new SurrealDB connection per call.** Reuse `surreal_client.py`.
- **Loading transformers/sentence_transformers in tests.** Causes BLAS SIGSEGV. conftest.py mocks them.
- **Running Kaggle work on `isolated/session-oom-modularity`.** Use the kaggle worktrees.
- **`git stash pop` on `stash@{0}`.** Holds pre-kaggle session-oom work. Leave it alone unless returning to session-oom-modularity.

**Strategy Pivot Triggers (`systematic-debugging.md`):** 3 attempts same approach with <5% improvement → STOP. API ceiling reached → STOP. Leaderboard gap >2x → STOP. Do NOT try "one more parameter." The next action must be a fundamentally different algorithm/library/architecture.

**Context Thresholds:**
- <80%: continue normally
- 80–89%: wrap up current task, avoid new complex work
- **≥90%: MANDATORY handoff.** Document remaining work, write continuation file, run `cz session send-clear`. Don't start new fix cycles.

**MCP / Agent files silent failures:**
- Missing YAML frontmatter on `AGENTS.md` → entire capability set goes dark.
- stdout noise from stdio MCP servers → protocol corruption, client sees malformed JSON.
- Eager config lookups in MCP init → handshake timeout, server appears missing.

**Verification Gates:**
- "Tests pass" ≠ "program works." Run the actual program after tests pass. Check exit code, stdout/stderr, file changes.
- "Complete" means files exist AND tests pass AND program runs, not projected.
- Report actual numbers (`2,675/2,700 passing (98.1%)`), not inflated (`1,599 passing`).

---

## Quick-Reference Pointers

| Need | File / Command |
|---|---|
| Hardware truth anchor | `HARDWARE_PROFILE_PRIME.md` |
| Constitution (hard constraints) | `.agent/CONSTITUTION.md` |
| Charter (design theory) | `.agent/COHEZION_CHARTER.md` |
| Test isolation | `tests/conftest.py` |
| Compound executor | `src/cohezion/compound/executor.py` |
| Cost routing | `src/cohezion/swarm/cost_aware_router.py` |
| Semantic cache | `src/cohezion/cache/semantic_cache.py` |
| FLUME VAE | `src/cohezion/flume/flume_vae.py` |
| Journey tracking | `src/cohezion/compound/journey_tracker.py` |
| Key learnings | `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` |
| CI gate | `make all` |
| Pre-commit config | `.pre-commit-config.yaml` |
