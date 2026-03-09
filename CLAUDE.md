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

**Every Claude session MUST start with an isolated worktree.** This is the primary development pattern.

### ⚡ Quick Start (Session Scripts)

```bash
# Start session (interactive or explicit)
./scripts/session/start_session.sh           # Auto-increments session ID
./scripts/session/start_session.sh 56 feature  # Explicit

# List active sessions
./scripts/session/list_sessions.sh

# End session (commit, push, cleanup)
./scripts/session/end_session.sh 56
```

See [`scripts/session/README.md`](scripts/session/README.md) for complete documentation.

### Manual Worktree Commands (Fallback)

```bash
# Create worktree with new branch
git worktree add -b session-56-feature ~/dev/cohezion-session-56 main
cd ~/dev/cohezion-session-56

# Session work: One goal, atomic commits
uv run pytest tests/ -q  # Verify baseline
# ... make changes, test incrementally ...

# Commit with session summary
git commit -m "Session 56: feature

## Accomplishments
- [Deliverables + test count/%, regressions: zero]

## For Session 57
- [Key assumptions, remaining work, gotchas]

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and cleanup
git push -u origin session-56-feature
cd ~/dev/cohezion && git worktree remove ~/dev/cohezion-session-56
```

**Why**: Isolation → no conflicts | Reversibility → safe branching | Audit trail → clear history | Safety → main never edited directly

**Git Rules** (see `.claude/rules/git-workflow.md`):
- Never force-push to main/develop
- Conventional commits: `feat:`, `fix:`, `test:`, `refactor:`, `chore:`
- AI commits include: `Co-Authored-By: Claude <noreply@anthropic.com>`
- No files >1MB (use git-lfs)
- Check `git status` before any commit

**Recommended Git Config**:
```bash
git config worktree.useRelativePaths true   # Portable worktrees
git config worktree.guessRemote true        # Auto-track remotes
git config gc.worktreePruneExpire 2.weeks.ago
```

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

## Agent Journey Tracking (Compound Loop Observability)

**Every agent action must be trackable through 12D universe. Required for skill refinement and drift detection.**

### Journey Entry Point
```python
from cohezion.compound.journey_tracker import JourneyTracker

tracker = JourneyTracker()
state_before = tracker.record_state(
    agent_id="researcher-1",
    phase="research",  # {research, planning, execution, reflection}
    position={"x": 0.5, "y": 0.3, ...},  # 12D coordinates
    coherence=0.85,  # Agent's skill coherence
    context=request_state  # Input to this phase
)
```

### Checkpoints (Non-Blocking)
```python
# Record at state transitions (try/except to prevent crashes)
try:
    tracker.record_transition(
        state_before,
        action_taken,
        result,
        coherence_after=0.83,
        alignment_score=0.92  # How well action matched request
    )
except Exception as e:
    logger.warning(f"Journey tracking failed (non-blocking): {e}")
```

### Recovery Checkpoint (Rollback Path)
```python
# Before executing irreversible action, save checkpoint
checkpoint = tracker.save_checkpoint(
    agent_id="researcher-1",
    phase="execution",
    state=current_state
)
# ... execute ...
if failure:
    tracker.rollback_to_checkpoint(checkpoint)
```

### Query Journey (Debugging + Skill Refinement)
```python
# Retrospection engine uses this to refine skills
journey = tracker.get_journey(agent_id="researcher-1")
anomalies = tracker.detect_anomalies(journey)  # Drift, coherence collapse
for anomaly in anomalies:
    logger.info(f"Anomaly: {anomaly.phase} → coherence {anomaly.before} → {anomaly.after}")
```

## Request Alignment Assessment (Before Execution)

**Every request must be assessed for alignment with available skills and agent context. Prevents wasted tokens on misaligned tasks.**

### Alignment Analysis Pipeline
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
from cohezion.compound.skill_selector import SkillSelector

analyzer = RequestAlignmentAnalyzer()
selector = SkillSelector()

# 1. Parse request and check available skills
request = parse_request(user_input)  # {goal, constraints, context}
available_skills = selector.find_relevant_skills(request.keywords)

# 2. Assess alignment
alignment = analyzer.analyze(
    request=request,
    available_skills=available_skills,
    agent_coherence=agent.coherence_history,  # Historical performance
    computational_budget=5000  # Tokens available
)

# 3. Make routing decision
if alignment.coherence < 0.5:  # HIHO threshold
    logger.warning(f"Low alignment: {alignment.issues}")
    action = "escalate" or "decompose"  # Break into smaller requests
elif alignment.estimated_tokens > budget:
    action = "batch_or_defer"
else:
    action = "proceed"  # Execute with confidence
    selected_skill = alignment.best_matching_skill
```

### Alignment Score Components
- **Coherence** (0.0-1.0): How well request matches agent's expertise
- **Completeness** (0.0-1.0): Are all required params present?
- **Constraint Satisfaction** (0.0-1.0): Can execution honor time/token/resource constraints?
- **Drift Risk** (0.0-1.0): How much could this destabilize coherence?
- **Estimated Tokens**: Projection for cost budgeting

### Anti-Patterns
- ❌ Accept ANY request without alignment check (wastes tokens)
- ❌ Proceed with coherence <0.5 (HIHO collapse)
- ❌ Ignore computational_budget (tokens explode)
- ❌ Skip drift detection (coherence decays)

## Metrics & Observability (Production Monitoring)

**Global metrics track efficiency, cost, and quality across all agents and executions.**

### Recording Metrics
```python
from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator

agg = GlobalMetricsAggregator()

# Record after each execution
agg.record_execution(
    instance_metrics={
        "executions": 1,
        "tokens_used": 1250,
        "coherence": 0.87,
        "cache_hit_rate": 0.95,
        "cost_usd": 0.002,
        "latency_ms": 450,
    },
    skill_name="research",
    agent_id="researcher-1"
)
```

### Querying Metrics (Dashboards + Analysis)
```python
# Real-time dashboard (5-min rolling window)
snapshot = agg.get_metrics_snapshot()
print(f"Throughput: {snapshot.avg_tokens_per_sec} tokens/sec")
print(f"Cache hit: {snapshot.cache_hit_rate:.1%}")
print(f"Cost trending: ${snapshot.daily_cost_estimate:.2f}")

# Historical trends (skill refinement)
skill_metrics = agg.get_skill_metrics("research", days=7)
if skill_metrics.coherence_trend < -0.05:  # Degrading
    logger.warning("research skill coherence degrading, trigger refinement")
```

### Cost Tracking (Budget Enforcement)
```python
from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer

enforcer = BudgetEnforcer(monthly_budget_usd=100)

# Check before execution
can_proceed, remaining = enforcer.check_budget(estimated_tokens=5000)
if not can_proceed:
    logger.info(f"Budget exhausted, {remaining} tokens remain for month")
    action = "defer_or_escalate"
```

## Data Storage Architecture for Simulations (Session 55 Patterns)

**Problem**: Universe simulation systems generate large artifacts (model checkpoints, training logs, metrics). Without governance, data accumulates exponentially: 13 GB/session → 13 TB after 10 sessions without controls.

**Solution**: Three-tier storage strategy with pre-commit enforcement and JourneyTracker registry.

### Three-Tier Storage Tiers

**Tier 1: Git (Reproducible Configs)**
- Store: checksums, model configs, training hyperparameters, seed values
- Size: <1 MB per checkpoint (metadata only, not weights)
- Purpose: version control, audit trail, reproducibility
- Retention: permanent (part of codebase history)
- Example: `data/flume/session55_config.json` (metadata, no weights)

**Tier 2: SurrealDB (Queryable Index)**
- Store: artifact metadata (path, size, checksum, lifetime, retention_policy)
- Purpose: fast queries ("find all checkpoints from Session 55"), lifecycle management
- Retention: rolling window (100K records = ~10 sessions at typical scale)
- Query latency: <5 ms
- Example: `JourneyTracker.query(session_id="session-55", tier="external")`

**Tier 3: External (Large Artifacts)**
- Store: checkpoint weights, large run artifacts (>50 MB)
- Backends: s3, gdrive, local NVMe archive
- Purpose: scalable storage, cost-managed archival
- Retention: policy-driven (30-90 days for research, longer for production)
- Example: `s3://cohezion-data/session-55/checkpoint-ep50.pt`

### Enforcement: Pre-Commit Hook

```bash
# .git/hooks/pre-commit
# Block commits if >50 MB files detected without external artifact registration

git diff --cached --name-only | while read file; do
  size=$(git cat-file -s ":0:$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
  if [ "$size" -gt 52428800 ]; then  # 50 MB
    echo "ERROR: Large artifact requires external storage registration"
    echo "Fix: uv run cohezion artifact register --path '$file' --tier external"
    exit 1
  fi
done
```

Cost: ~100 ms per commit | Benefit: prevents exponential accumulation

### JourneyTracker Artifact Registration

```python
from cohezion.compound.journey_tracker import JourneyTracker

JourneyTracker.record_artifact(
  session_id="session-55",
  artifact_type="checkpoint",
  path="data/flume/session55_run3.pt",
  size_bytes=234_567_890,
  tier="external",  # git|surreal|external
  checksum="sha256:abcd1234",
  lifetime_days=30,
  retention_policy="research",
  tags=["flume", "vae", "training"]
)

# Query for lifecycle management
artifacts = JourneyTracker.query(tier="external", older_than_days=7)
for artifact in artifacts:
  if artifact.is_expired():
    notify_ops(f"Archive cleanup due: {artifact.path}")
```

### Recovery Procedure (Deterministic Replay)

```python
# Recover any historical state in <5 minutes
checkpoint = CheckpointRepo.get_by_seed(seed=42, session="session-55")
state = torch.load(checkpoint.git_ref)
vae = FlumVAETrainer.from_checkpoint(state, continue_training=True)
# Deterministically reproducible from this point
```

### Success Metrics

| Metric | Target | Mechanism |
|--------|--------|-----------|
| Committed files/session | <50 MB | Pre-commit hook enforces tier assignment |
| Artifact discoverability | <5 ms | SurrealDB queries on session_id, timestamp |
| Recovery time | <5 min | Deterministic seed + checkpoint lineage |
| Audit trail completeness | 100% | JourneyTracker registers every artifact |
| Storage cost | <$5/10 sessions | Free Git + SurrealDB, s3 for >90-day archive |

### Implementation Notes

- **Backward compatible**: JourneyTracker logging is optional (try/except wrapper)
- **Graceful degradation**: If SurrealDB unavailable, falls back to JSONL queries
- **Non-blocking**: All tracking operations non-blocking (won't crash system if unavailable)
- **Reusable patterns**: See `/vaults/cohezion-vault/patterns/` for extracted patterns

### Related PRIME Skills

- `UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md`: Complete specification with ROI analysis
- See: `src/cohezion/skills/UNIVERSE_SIMULATION_PERSISTENCE_PRIME.md`

---

## Common Debugging Scenarios

### Scenario: Tests Pass Individually but Fail in Suite
**Root cause**: Singleton pollution in conftest.py fixtures
```bash
# Fix: Verify singleton reset is running
grep -n "_vae_trainer\|_rl_policy\|handlers.clear" tests/conftest.py

# Debug: Run single test module to verify
uv run pytest tests/compound/test_executor.py -v
# If passes → singleton issue
# If fails → logic bug
```

### Scenario: Flaky Test with Random Seed Issues
**Root cause**: FLUME VAE or numpy random state not reset
```python
# In your test:
import numpy as np
from cohezion.api import reset_flume_vae

@pytest.fixture(autouse=True)
def reset_random():
    np.random.seed(42)
    reset_flume_vae()
    yield
```

### Scenario: Ollama Timeout in Tests
**Root cause**: Test is hitting live Ollama instead of mock
```python
# Fix: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")
def test_my_thing(mock_client):
    mock_client.return_value = AsyncMock()  # Never talks to real Ollama
```

### Scenario: Journey Tracking Missing from Logs
**Root cause**: Non-blocking try/except swallowed the error
```python
# Debug: Temporarily make it blocking
try:
    tracker.record_transition(...)
except Exception as e:
    logger.error(f"Journey tracking: {e}")  # See the actual error
    raise  # Temporarily, to find issue
```

### Scenario: Token Count Doesn't Match Estimate
**Root cause**: Cost tracker using wrong model rate
```python
# Verify cost is being computed
agg = GlobalMetricsAggregator()
metrics = agg.get_metrics_snapshot()

# Check: Are costs accumulating?
if metrics.total_cost_usd == 0.0:
    logger.warning("Cost tracking not working, check model rates in cost_aware_router.py")
```

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
