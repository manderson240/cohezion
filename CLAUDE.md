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

### ⚡ Vault-First Knowledge Management (NEW: Session 56)

**CRITICAL**: All session learnings MUST be logged to vault, not MEMORY.md directly.

**MEMORY.md = Compiled Cache** (auto-generated weekly):
- 95 lines (vs 1177 lines old version)
- Recent decisions (last 7 days)
- Most-used patterns (top 10)
- Quick reference only

**Vault = Single Source of Truth**:
- `~/vaults/cohezion-vault/` (150+ decisions, patterns, experiments)
- Searchable via `vault_find_relevant_context(query)`
- Survives across sessions, compounds knowledge

**How to Log Learnings**:
```python
# Log architectural decisions
vault_log_decision(
    project="cohezion",
    title="Short decision title",
    context="What led to this decision",
    decision="What was decided",
    rationale="Why this option was chosen"
)

# Log experiments (what was tried & learned)
vault_log_experiment(
    project="cohezion",
    hypothesis="What you expected",
    method="What you did",
    result="What happened",
    learnings="Key takeaways"
)

# Extract reusable patterns
vault_extract_pattern(
    source_path="path/to/source",
    pattern_name="Pattern Name",
    description="When to use this pattern",
    code_example="```python\n# example\n```",
    domain="testing|mcp|compound-engineering|etc"
)
```

**Regenerate MEMORY.md**:
```bash
# Run weekly or after major learnings
uv run python scripts/compile_memory_from_vault.py
```

**Token Savings**: 10K+ tokens/session (load only relevant context via search vs loading all 1177 lines)

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

### Journey Tracking Checklist (Compound Loop)
When implementing features, add:
1. **Input logging**: `journey_tracker.record_request(alignment_score)` at entry
2. **State changes**: Record before/after for rollback capability
3. **Metrics**: Call `metrics_collector.record_execution()` at completion
4. **Coherence**: Check `degradation_detector.check_coherence()` before proceeding
5. **Reflection**: Populate RetrospectionEngine output for skill refinement

### Alignment Assessment (Before Execution)
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(request_state, available_skills, agent_context)
if alignment.coherence < 0.5:  # HIHO threshold
    logger.warning(f"Low coherence: {alignment.issues}")
    # Escalate or fallback
```

## Token Budgets (Conservative Estimates)

| Task | Tokens | Pattern |
|------|--------|---------|
| Implement 1 feature | 500-1,500 | Copy template → code → manual test → 5 tests |
| Research + implement | 2,000-3,000 | Quick survey → proof of concept → tests |
| Full test suite run | 100 | `uv run pytest tests/ -q` (no code changes) |
| Single test debug | 200-500 | Add print → run → check output → fix → verify |
| Skill refinement loop | 1,500-2,500 | Analyze failures → update PRIME skill → retest |
| **ANTI-PATTERN**: Research-first | 5,000-10,000 | 1,200 lines research + 600 tests + 0 implementation = wasted |
| **ANTI-PATTERN**: Infrastructure play | 8,000+ | Dependency research, 4,400 placeholder tests, product doesn't exist |

**Rule**: If feature doesn't exist yet, DON'T build infrastructure. Implement, validate, THEN test.

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

See skill: `cohezion-worktree-workflow` — covers session scripts (start/end/list_sessions.sh), manual git worktree commands, commit format with Co-Authored-By, and recommended git config.

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

## Agent Journey Tracking & Request Alignment

See skill: `cohezion-journey-tracking` — covers JourneyTracker API (record_state, record_transition, save_checkpoint, rollback), RequestAlignmentAnalyzer (coherence/completeness/drift-risk), and alignment anti-patterns.

## Metrics & Observability (Production Monitoring)

See skill: `cohezion-metrics-observability` — covers GlobalMetricsAggregator (record_execution, get_metrics_snapshot, get_skill_metrics), BudgetEnforcer (monthly budget checks, token control), and cost tracking.

## Data Storage Architecture for Simulations

See skill: `cohezion-data-governance` — covers three-tier storage (Git/SurrealDB/External), pre-commit hook for >50MB files, JourneyTracker artifact registration, deterministic recovery, and success metrics.

---

## Common Debugging Scenarios

See skill: `cohezion-debugging-scenarios` — covers test isolation/singleton pollution, flaky tests with random seeds, Ollama timeouts, journey tracking silent failures, and token count mismatches.

## Skill Routing Quick Reference

### Decision Tree (Priority Order)

When a natural language request arrives, route using this priority:

1. **Exact match** — Does it match a `/slash-command`? Execute directly
2. **Lifecycle phase** — What phase of work?
   - Research/Analysis: `bmad-bmm-technical-research`, `bmad-bmm-domain-research`, `bmad-bmm-market-research`
   - Planning/Design: `bmad-bmm-create-prd`, `bmad-bmm-create-architecture`, `bmad-bmm-create-ux-design`
   - Implementation: `bmad-bmm-dev-story`, `bmad-bmm-quick-dev`, or `/spec` (structured TDD)
   - Testing: `bmad-tea-testarch-test-design`, `test-fix`
   - Review: `bmad-bmm-code-review`, `pr-review-toolkit:review-pr`
   - Maintenance: `retrospect`, `bmad-bmm-correct-course`, `deploy`, `heal`
3. **Domain** — Game dev? Use `bmad-gds-*` variant. General product? Use `bmad-bmm-*`
4. **Meta** — About BMAD itself? Use `bmad-bmb-*` (agent/workflow/module builder)
5. **Creative** — Ideation/innovation? `bmad-brainstorming`, `bmad-cis-design-thinking`
6. **Tool need** — External data? Library docs: `context7` | Papers: `cohezion-research` | GitHub: `github` MCP | Knowledge graph: `cohezion-surreal` | Multi-perspective: `cohezion-swarm`

### Top Keyword-to-Skill Routing

| Keywords | Primary Skill | Fallback |
|----------|---------------|----------|
| "research", "investigate" | `bmad-bmm-technical-research` | `bmad-bmm-domain-research` |
| "PRD", "requirements" | `bmad-bmm-create-prd` | `bmad-bmm-edit-prd` |
| "architecture", "system design" | `bmad-bmm-create-architecture` | — |
| "story", "epic" | `bmad-bmm-create-story` | `bmad-bmm-create-epics-and-stories` |
| "sprint", "planning" | `bmad-bmm-sprint-planning` | `bmad-bmm-sprint-status` |
| "implement", "build", "code this" | `bmad-bmm-dev-story` | `bmad-bmm-quick-dev` |
| "test", "QA" | `bmad-tea-testarch-test-design` | `test-fix` |
| "review", "code review" | `bmad-bmm-code-review` | `pr-review-toolkit:review-pr` |
| "brainstorm", "ideate" | `bmad-brainstorming` | `bmad-cis-design-thinking` |
| "game", "gameplay" | Route to `bmad-gds-*` variant | — |
| "deploy", "ship" | `deploy` | — |
| "fix tests", "failing tests" | `test-fix` | — |
| "commit", "push", "PR" | `commit-commands:commit` | `commit-commands:commit-push-pr` |
| "spec", "structured dev" | `/spec` | — |
| "what now", "help" | `bmad-help` | — |

### Overlap Resolution (Key Ambiguities)

| Ambiguity | Resolution |
|-----------|------------|
| BMM vs GDS variants (code-review, sprint, story) | Domain context: game project = GDS, otherwise = BMM |
| `bmad-brainstorming` vs `superpowers:brainstorming` | `superpowers` is a meta-prompt enhancer; `bmad-brainstorming` is the interactive workflow |
| `/spec` vs `bmad-bmm-quick-spec` | `/spec` = full TDD workflow; `quick-spec` = lightweight for small changes |
| `bmad-bmm-code-review` vs `pr-review-toolkit:review-pr` | BMM = general code review; PR toolkit = PR-specific with GitHub integration |
| `retrospect` vs `bmad-bmm-retrospective` | `retrospect` = dev-focused (flows into core files); BMM = product lifecycle |

**When in doubt**: `bmad-help` — analyzes context and suggests the best next action.

**Skill sources (7 layers)**: BMAD commands (~90), project commands (3), project skills (1), global commands (7), global rules (~15), plugin skills (~40), MCP tools (~80). Full taxonomy: `_bmad-output/planning-artifacts/research/technical-skills-taxonomy-research-2026-03-07.md`

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
