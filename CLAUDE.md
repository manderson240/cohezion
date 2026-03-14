# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Cohezion - Compound AI Orchestration

COHEZION: 12D agentic universe with FLUME VAE, compound engineering, multi-agent swarm, and autonomous skill refinement. **Governed by Constitution (`.agent/CONSTITUTION.md`) and Charter (`.agent/COHEZION_CHARTER.md`).**

## Token-Efficient Essentials

### ⚡ Core Commands
```bash
uv run pytest tests/ -q              # Full test suite (3,200+ tests, ~90s)
uv run pytest tests/compound/ -v     # Run module tests
uv run pytest tests/test_*.py::name  # Single test
make format && make lint && make all # Check → fix → verify
```

### ⚡ Security Standards (MANDATORY)
```bash
# NEVER print, echo, or display any passwords or secrets
# NEVER store SUDO_PASSWORD in .env for scripts - use passwordless sudo
# NEVER write secrets to temp files that persist

# ALWAYS use 'uv' for package management - NEVER bare 'pip' or 'pip install'
uv pip install package              # Install package
uv venv && source .venv/bin/activate && uv pip install -e .  # New project setup

# For sudo: configure passwordless sudo for automation OR run interactively
# Do NOT attempt to parse .env for SUDO_PASSWORD - this is a security risk
```

### ⚡ Critical Principles (Sessions 40-55)
1. **Implement ONE feature, validate manually, write 5 tests** (NOT 600 pre-implementation tests)
2. **Use proven templates** (e.g., cloud-vault-mcp: 40+ tools) over greenfield exploration
3. **Mock live services at source**: `@patch("cohezion.swarm.compound_client.get_compound_client")`
4. **Report honest metrics** (98.8% beats inflated 100% for decision-making)
5. **Never write infrastructure for products that don't exist**

### ⚡ Vault-First Knowledge Management

All session learnings go to vault (`~/vaults/cohezion-vault/`), not MEMORY.md. Use `vault_log_decision()`, `vault_log_experiment()`, `vault_extract_pattern()`. Search via `vault_find_relevant_context(query)`. Regenerate MEMORY.md: `uv run python scripts/compile_memory_from_vault.py`

### ⚡ Architecture at a Glance
| Layer | Components | Entry |
|-------|-----------|-------|
| **Compound** | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `CompoundExecutor` |
| **Swarm** | TeamOrchestrator, ExecutionOrchestrator, DynamicModelRouter | `TeamExecutor` |
| **Cache** | SemanticCache (L1 hash + L2 cosine + L3 vault, 95%+ hit rate) | `SemanticCache` |
| **Cost Opt** | CostAwareRouter (27.3% savings), BudgetEnforcer, ModelQualityClassifier | `CostAwareRouter` |
| **Persistence** | SessionPersistence (vault + JSONL), MetricsCollector, DegradationDetector | `SessionManager` |
| **Knowledge** | Vault-First (decisions/patterns/experiments), auto-compiled MEMORY.md | `vault_find_relevant_context` |

### ⚡ Quick Reference
- **Language**: Python 3.13+ | **Package Manager**: `uv` (never bare python)
- **DB**: SurrealDB (ws://localhost:8000) | **API**: FastAPI :8080
- **Tests**: 3,214 passing / 4 failing (99.9%) | **Coverage**: html report in `htmlcov/`
- **CI**: `make lint-check && uv run pytest` before commit
- **Entry point**: `cohezion = "cohezion.__main__:main"`
- **Vault**: `~/vaults/cohezion-vault/` — Query via `vault_find_relevant_context(query)`

## The Compound Engineering Loop (Production-Ready)

```
PRIME Skill (markdown)
  ↓
InstructionExpander (parse → tasks)
  ↓
PlanExecutor (tactical plan)
  ↓
ExecutionOrchestrator (execute with 11-step pipeline)
  ├─ RequestAlignmentAnalyzer (coherence check)
  ├─ GlobalMetricsAggregator (record instance metrics)
  ├─ DegradationDetector (thermal, quality thresholds)
  └─ JourneyTracker (12D universe position)
  ↓
RetrospectionEngine (extract learnings, flag anomalies)
  ↓
SkillRefiner (update skill definition)
  ↓
SkillConsensusVoter (multi-agent validation)
  ↓
Updated Skill (loop again)
```
**CLI**: `uv run python scripts/drivers/compound_cycle.py` (dry-run) or via `/compound` API endpoint.

## Key Directories (Find Anything Fast)

| Path | Purpose | Key Files |
|------|---------|-----------|
| `src/cohezion/compound/` | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `executor.py` (11-step) |
| `src/cohezion/swarm/` | Team orchestration, cost routing, model quality | `team_executor.py`, `cost_aware_router.py` |
| `src/cohezion/cache/` | L1/L2/L3 semantic cache (95%+ hit rate) | `semantic_cache.py` |
| `src/cohezion/skills/` | 124 PRIME skill definitions (*.md + *.py) | `skill_registry.json` |
| `src/cohezion/persistence/` | SurrealDB, checkpoints, session recovery | `surreal_client.py` |
| `src/cohezion/api/` | FastAPI backend (72 endpoints) | `__init__.py` (FastMCP patterns) |
| `src/cohezion/flume/` | FLUME VAE (256D latent space) | `flume_vae.py` |
| `tests/conftest.py` | **CRITICAL**: Singleton reset for FLUME VAE, RL policy, loggers | **Read this first** |

## Coding Standards (Compound-Ready)

- **Type hints**: Mandatory (mypy --strict). Enables alignment analysis at compile-time
- **Docstrings**: NumPy-style. Document "why" intent, state assumptions for request alignment
- **Async**: All I/O must be `async/await` with timeouts. No blocking calls in executors
- **Error handling**: Specific exceptions + circuit breakers (`cohezion.reliability.get_circuit()`)
- **Validation**: Pydantic at boundaries (input/output). Fail fast with assertions
- **KISS**: Simple logic beats multi-agent swarms. Measure first, optimize later
- **Every `src/` dir**: MUST have `__init__.py`. Enables vault skill discovery
- **Observability**: Log state transitions (input → processing → output). Track coherence. Measure alignment

### Journey Tracking & Alignment

When implementing features: add input logging, state change recording, metrics, coherence checks, and retrospection output. Check alignment before execution (`coherence < 0.5` = HIHO threshold, escalate). See `docs/patterns/compound-loop-patterns.md` for full code examples.

## Token Budgets

| Task | Tokens | | Anti-Pattern | Tokens |
|------|--------|-|-------------|--------|
| Implement 1 feature | 500-1,500 | | Research-first (no impl) | 5,000-10,000 |
| Research + implement | 2,000-3,000 | | Infrastructure play | 8,000+ |
| Full test suite | 100 | | | |

**Rule**: Implement first, validate, THEN test. Don't build infrastructure for products that don't exist.

## Operational Patterns

### ⚡ Test Isolation (Critical)
Tests fail only as full suite? **NOT a logic bug — singleton pollution**. Fix in `tests/conftest.py`:
- FLUME VAE: `cohezion.api._vae_trainer = None` (checkpoint mismatch causes NaN)
- RL Policy: `cohezion.api._rl_policy = None` (bad reward state persists)
- Loggers: `logging.getLogger().handlers.clear()` (formatters corrupt across files)

### ⚡ Mocking External Services
```python
# CORRECT: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")

# WRONG: Mocking after import fails randomly
with patch("cohezion.api.compound_client"):  # Import already happened
```

### ⚡ Measurement Integrity
- **Report actual numbers**: 2,675/2,700 passing (98.1%) > 1,599 passing (inflated)
- **Flag discrepancies**: If independent test shows different count, request re-verification immediately
- **Verify claims**: "Complete" = files exist AND tests pass, not projected

### ⚡ Verification Protocol
Before declaring task complete:
1. **Code**: Reads logically? Type hints present?
2. **Tests**: `uv run pytest tests/module/ -v` passes? No warnings?
3. **Metrics**: Honest count? Zero regressions?
4. **Alignment**: Does code match what was requested?
5. **Rollback**: Can prior version recover? (State transitions logged?)

## Hardware & Constraints (Strix Halo)

- **CPU**: AMD Ryzen AI MAX+ 395 (16C/32T, AVX-512, AMX) | **GPU**: Radeon 8060S (iGPU, unified memory)
- **RAM**: 128 GiB LPDDR5X | **Storage**: 2TB NVMe + 32GB swap (ZFS)
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini). **Global limit = 4 concurrent**
- **Cost**: Cloud Run = Free Tier only (no instances when idle). Prefer local Ollama over API calls
- **Truth Anchor**: See `HARDWARE_PROFILE_PRIME.md` (never assume RTX/CUDA)

## Multi-Session Worktree Pattern (MANDATORY)

Every Claude session uses an isolated worktree. Scripts: `./scripts/session/start_session.sh`, `list_sessions.sh`, `end_session.sh`. See `scripts/session/README.md` for details.

**Git Rules**: Conventional commits (`feat:`, `fix:`, `test:`, `refactor:`), `Co-Authored-By: Claude <noreply@anthropic.com>`, never force-push main, no files >1MB.

## Design Principles (Compound-Aligned)

- **HIHO Stability** (50% coherence): Optimal balance between exploitation + exploration
- **Compound Engineering**: Every feature makes future features easier (loop → skill updates → better routing)
- **Observable AI**: Log states before action. Track coherence. Expose confidence. Enable rollback
- **Deterministic Responsibility**: Idempotency keys for all external calls. Replay from checkpoints
- **Expert Domain Lattice**: Route complex requests through specialist agents (Architect, Engineer, Biologist, QHW, QAlgo)
- **SPIN Coherence**: Information unit = Rotation + Precession. Alignment when phases match

## Critical References (Read First)

| Document | Purpose | Key Insight |
|----------|---------|------------|
| `tests/conftest.py` | **TEST ISOLATION** | FLUME VAE + RL policy + logger resets prevent flaky tests |
| `.agent/CONSTITUTION.md` | **HARD CONSTRAINTS** | No WMD/infrastructure attacks. Honesty mandatory. Idempotency required |
| `.agent/COHEZION_CHARTER.md` | **DESIGN THEORY** | SPIN, FLUME, HIHO, Expert Domain Lattice |
| `HARDWARE_PROFILE_PRIME.md` | **TRUTH ANCHOR** | Never assume RTX/CUDA. AMD Ryzen AI MAX+ 395 only |
| `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | **LESSONS EXTRACTED** | Historical patterns, anti-patterns, cost lessons |
| `.claude/rules/git-workflow.md` | **GIT PATTERNS** | Conventional commits, branch naming, PR targets |
| `.claude/rules/testing.md` | **TEST RULES** | Avoid `walk_packages`, mock at source, HIHO invariant |
| `cloud-vault-mcp/` | **MCP TEMPLATE** | 40+ tools, FastMCP proven. Copy when building MCP servers |

## Compound Loop Patterns (Reference)

Full code examples for journey tracking, alignment assessment, metrics, and data storage architecture are in `docs/patterns/compound-loop-patterns.md`. Key APIs:

- **JourneyTracker**: `record_state()`, `record_transition()`, `save_checkpoint()`, `get_journey()`, `detect_anomalies()`
- **RequestAlignmentAnalyzer**: `analyze()` → coherence, completeness, drift risk scores
- **GlobalMetricsAggregator**: `record_execution()`, `get_metrics_snapshot()`, `get_skill_metrics()`
- **BudgetEnforcer**: `check_budget(estimated_tokens)` → (can_proceed, remaining)
- **Data Storage**: 3-tier (Git configs / SurrealDB index / External artifacts). Pre-commit hook blocks >50MB.

## Common Debugging Quick Reference

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Tests pass individually, fail in suite | Singleton pollution | Check `conftest.py` for VAE/RL/logger resets |
| Flaky test with random seeds | FLUME VAE state not reset | `np.random.seed(42)` + `reset_flume_vae()` in fixture |
| Ollama timeout in tests | Hitting live Ollama | Mock at source: `@patch("cohezion.swarm.compound_client.get_compound_client")` |
| Journey tracking missing | try/except swallowed error | Temporarily add `raise` in except block |
| Token count mismatch | Wrong model rate | Check `cost_aware_router.py` model rates |

## Tool References (invoke with Skill tool when needed)
- GitHub operations: `gh-cli-reference` | MCP CLI: `mcp-cli-reference`
- Web search/fetch: `web-search-reference` | GitHub code search: `grep-mcp-reference`
- Persistent memory: `memory-reference` | Team vault: `team-vault-reference`
- Browser testing: `playwright-cli-reference` | Semantic search: `vexor-search-reference`
- Large commits (50+ files): `large-commit-protocol-reference`

### Disabled Plugins (re-enable in ~/.claude/settings.json if needed)
Sentry, Linear, Circleback, Greptile, Playground, Agent-SDK-Dev, Gopls-LSP, Rust-Analyzer-LSP, TypeScript-LSP, Document-Skills, Example-Skills

## Quick Lookup

| Need | Command | File |
|------|---------|------|
| Run tests (all) | `uv run pytest tests/ -q` | `pytest.ini` |
| Run tests (module) | `uv run pytest tests/compound/ -v` | `tests/conftest.py` |
| Format + lint | `make format && make lint` | `Makefile` |
| Check types | `make type-check` | `pyproject.toml` |
| Start API | `uv run uvicorn cohezion.api:app --reload` | `src/cohezion/api/__init__.py` |
| Find skill | `grep -r "skill_name" src/cohezion/skills/` | `skill_registry.json` |
| Debug journeys | `JourneyTracker.get_journey(agent_id)` | `src/cohezion/compound/journey_tracker.py` |
| Check alignment | `RequestAlignmentAnalyzer.analyze(...)` | `src/cohezion/compound/request_alignment_analyzer.py` |
