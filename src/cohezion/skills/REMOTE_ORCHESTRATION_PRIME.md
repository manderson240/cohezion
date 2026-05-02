---
name: remote-orchestration-prime
description: "Distributed orchestration of Cohezion work from anywhere (mobile, tablet, remote machine) via GitHub Issues, file-based task queues, autonomous scheduled runs, vault coordination, and parallel worktree isolation."
---

# SKILL: REMOTE_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
Distributed orchestration of Cohezion work from anywhere (mobile, tablet, remote machine) via GitHub Issues, file-based task queues, autonomous scheduled runs, vault coordination, and parallel worktree isolation.

## KEY CONCEPTS
- **GitHub Issue Terminal**: Create work via issue templates with dropdown commands; `claude.yml` workflow dispatches to local executor on issue creation.
- **Teleport Task Queue**: File-based async task queue in vault (`~/vaults/cohezion-vault/teleport/`) for queueing work while away and executing in next session.
- **Autonomous Scheduled Runs**: Weekly and daily cron workflows (`autonomous-scout.yml`, `health-check.yml`) with optional direct prompt override for passive knowledge accumulation.
- **Session Coordination Layer**: Vault-based `session-registry.md` tracks active worktree branches, executor tasks, and result checkpoints for inter-session handoffs.
- **Parallel Multi-Agent Topology**: Independent sessions on isolated worktree branches; compound executor, refiner, test-runner, and monitor agents coordinate via vault observations and structured file paths.

## INSTRUCTION

### 1. GitHub Issue Terminal (Mobile-First Entry Point)
Create frictionless work requests from any device:

**Setup** (one-time):
- Create `.github/ISSUE_TEMPLATE/claude-command.yml` with dropdown commands and title prefix `@claude `
- Create `claude.yml` GitHub Action that triggers on issue creation with label `run-claude`
- Workflow extracts issue body and dispatches to `cohezion_execute_remote()` with `direct_prompt: true`

**Usage** (zero-friction mobile):
1. Open GitHub issue form on phone
2. Select command from dropdown (e.g., "Add feature", "Run tests", "Health check")
3. Title auto-populates: `@claude add feature: refactor FLUME VAE`
4. Submit → `claude.yml` fires → Local executor processes in next session
5. Results posted back to issue as comment

**Example issue template**:
```yaml
name: Claude Command
description: Queue work for Claude orchestration
body:
  - type: dropdown
    id: command
    label: Command
    options:
      - Add Feature
      - Fix Bug
      - Run Tests
      - Health Check
      - Autonomous Scout
  - type: textarea
    id: details
    label: Details
    placeholder: Additional context or requirements
```

### 2. Teleport Task Queue (Async Delegation)
Queue work while away; execute in next local session:

**Storage Structure**:
```
~/vaults/cohezion-vault/teleport/
  ├─ pending/
  │   ├─ task-<uuid>.md
  │   └─ task-<uuid>.md
  ├─ claimed/
  │   └─ task-<uuid>.md          # Executor claimed; in-progress
  └─ completed/
      └─ task-<uuid>.md          # Verified; ready for integration
```

**Create Task** (from anywhere):
```python
from cohezion.persistence import teleport_create_task

teleport_create_task(
    title="Refactor compound executor error handling",
    description="Add circuit breaker fallback + comprehensive logging",
    priority="high",  # high|medium|low
    estimated_tokens=2500,
    tags=["compound", "reliability"],
    due_date="2026-03-12"
)
# Returns: ~/vaults/cohezion-vault/teleport/pending/task-<uuid>.md
```

**Claim Task** (executor at session start):
```python
from cohezion.persistence import teleport_claim_task

task = teleport_claim_task(priority="high")  # Moves pending/ → claimed/
if task:
    print(f"Claimed: {task.title}")
    # Execute task...
```

**Complete Task** (after verification):
```python
from cohezion.persistence import teleport_complete_task

teleport_complete_task(
    task_id="<uuid>",
    status="completed",
    result_summary="Circuit breaker implemented. 15 new tests added. All tests pass.",
    metrics={
        "tokens_used": 2340,
        "files_changed": 3,
        "tests_added": 15,
        "duration_minutes": 47
    }
)
# Moves claimed/ → completed/; logged to vault
```

**Task File Format** (`.md`):
```markdown
# Task: <title>

## Metadata
- ID: <uuid>
- Priority: high
- Created: 2026-03-05T14:30:00Z
- Due: 2026-03-12T00:00:00Z
- Estimated Tokens: 2500
- Tags: [compound, reliability]

## Description
<task description>

## Acceptance Criteria
- [ ] Feature implemented
- [ ] 5+ tests added
- [ ] All tests pass
- [ ] No type errors

## Result
(populated by executor after completion)
```

### 3. Autonomous Scheduled Runs (No-Touch Accumulation)
Define cron workflows for passive knowledge accumulation:

**Weekly Autonomous Scout** (`autonomous-scout.yml`):
```yaml
name: Autonomous Scout
on:
  schedule:
    - cron: '0 2 * * 0'  # Every Sunday 02:00 UTC
  workflow_dispatch:
    inputs:
      direct_prompt:
        description: 'Direct prompt override'
        required: false

jobs:
  scout:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Scout Cohezion
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DIRECT_PROMPT: ${{ inputs.direct_prompt }}
        run: |
          # Trigger compound executor with scout mode
          uv run python scripts/drivers/autonomous_scout.py \
            --direct-prompt="${DIRECT_PROMPT}" \
            --vault-path="${GITHUB_WORKSPACE}/vaults/cohezion-vault"
```

**Daily Health Check** (`health-check.yml`):
```yaml
name: Health Check
on:
  schedule:
    - cron: '0 0 * * *'  # Daily 00:00 UTC

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Health Check
        run: |
          uv run pytest tests/health_checks/ -v --tb=short
          uv run python scripts/drivers/health_check.py \
            --vault-path="${GITHUB_WORKSPACE}/vaults/cohezion-vault"
```

**Scout Driver Logic** (`scripts/drivers/autonomous_scout.py`):
```python
import asyncio
from cohezion.compound import CompoundExecutor
from cohezion.persistence import vault_pull_session_context

async def autonomous_scout(direct_prompt=None, vault_path=None):
    # 1. Load vault context (decisions, patterns, experiments)
    context = vault_pull_session_context(
        query="recent learnings and active patterns",
        vault_path=vault_path
    )

    # 2. Detect scout tasks (high-value low-cost)
    tasks = detect_scout_tasks(context)

    # 3. Execute with compound executor
    executor = CompoundExecutor(vault_path=vault_path)
    for task in tasks:
        result = await executor.execute(
            skill_name="KNOWLEDGE_HARVESTING",
            prompt=direct_prompt or task.prompt,
            context=context,
            timeout_minutes=30  # Safety cap
        )
        # Logs automatically to vault

    # 4. Publish metrics
    publish_metrics_to_dashboard()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-prompt", required=False)
    parser.add_argument("--vault-path", required=True)
    args = parser.parse_args()

    asyncio.run(autonomous_scout(
        direct_prompt=args.direct_prompt,
        vault_path=args.vault_path
    ))
```

### 4. Session Coordination Layer (Vault Registry)
Track parallel sessions and coordinate handoffs:

**Session Registry** (`~/vaults/cohezion-vault/session-registry.md`):
```markdown
# Active Sessions (Last Updated: 2026-03-05T15:00:00Z)

## Session 56 (Executor)
- **Branch**: session-56-feature
- **Status**: in_progress
- **Worktree**: /home/mike/dev/cohezion-session-56
- **Goal**: Refactor compound executor
- **Started**: 2026-03-05T08:00:00Z
- **Last Activity**: 2026-03-05T14:45:00Z
- **Checkpoint**: 3 tests added, circuit breaker 70% implemented
- **Blockers**: None
- **Next Steps**: Complete circuit breaker, add 2 more tests

## Session 57 (Test Runner)
- **Branch**: session-57-tests
- **Status**: idle (waiting for session-56)
- **Worktree**: /home/mike/dev/cohezion-session-57
- **Goal**: Add comprehensive test coverage
- **Started**: 2026-03-05T12:00:00Z
- **Dependencies**: [session-56]  # Blocked until session-56 completes
- **Next Activity**: Resume after session-56 publishes checkpoint

## Completed Sessions (Last 7 Days)
- Session 55: Knowledge extraction from vault → Patterns published
- Session 54: FLUME VAE training checkpoint → Model validated
```

**Update Registry** (before session end):
```python
from cohezion.persistence import session_registry_update

session_registry_update(
    session_id=56,
    status="in_progress",
    checkpoint={
        "branch": "session-56-feature",
        "worktree": "/home/mike/dev/cohezion-session-56",
        "goal": "Refactor compound executor",
        "progress": "3 tests added, circuit breaker 70% implemented",
        "blockers": [],
        "next_steps": "Complete circuit breaker, add 2 more tests"
    }
)
```

**Check Registry** (at session start):
```python
from cohezion.persistence import session_registry_get_dependencies

dependencies = session_registry_get_dependencies(session_id=57)
for dep in dependencies:
    if dep.status not in ("completed", "idle"):
        logger.info(f"Waiting for {dep.session_id}: {dep.status}")
        # Poll or sleep
```

### 5. Parallel Multi-Agent Topology (Worktree Isolation)
Execute specialized agents in parallel on isolated branches:

**Topology Architecture**:
```
Main Branch (main)
├─ session-56-feature (Executor Agent)
│   ├─ src/cohezion/compound/ → Circuit breaker changes
│   ├─ tests/compound/ → New test cases
│   └─ docs/ → Updated architecture docs
│
├─ session-57-tests (Test Runner Agent)
│   └─ Waits for session-56 to publish checkpoint
│       Then adds comprehensive test coverage
│
├─ session-58-refiner (Skill Refiner Agent)
│   └─ Analyzes execution metrics from vault
│       Updates PRIME skill definitions
│
└─ session-59-monitor (Health Monitor Agent)
    └─ Passive monitoring and metrics aggregation
        No worktree (read-only observations)
```

**Create Isolated Worktree** (session start):
```bash
# Executor creates worktree for this session
git worktree add -b session-56-feature \
  /home/mike/dev/cohezion-session-56 main

cd /home/mike/dev/cohezion-session-56

# Work is ISOLATED here; main branch untouched
uv run pytest tests/ -q  # Baseline
# ... make changes ...
git commit -m "Session 56: Implement circuit breaker for compound executor"
```

**Coordinate via Vault** (inter-session handoff):
```python
# Session 56 (Executor) publishes checkpoint
vault_push_session_state(
    session_id=56,
    state={
        "branch": "session-56-feature",
        "checkpoint": "circuit_breaker_v1",
        "files_changed": ["src/cohezion/compound/executor.py"],
        "metrics": {
            "tests_passing": 3212,
            "tests_failing": 0,
            "coverage": "87.3%",
            "new_tests": 15
        }
    }
)

# Session 57 (Test Runner) polls and resumes
checkpoint = vault_pull_session_context(
    query="latest checkpoint from session-56",
    session_id=56
)
if checkpoint:
    # Pull session-56 changes
    git pull origin session-56-feature
    # Add tests on top
```

**Merge Back to Main** (after verification):
```bash
# After all tests pass in the worktree session
cd ~/dev/cohezion-session-56
git push -u origin session-56-feature

# Switch back to main
cd ~/dev/cohezion
git checkout main

# Squash-merge the feature branch
git merge --squash origin/session-56-feature
git commit -m "Session 56: Implement circuit breaker for compound executor

## Accomplishments
- Circuit breaker with exponential backoff
- 15 new tests added, all passing
- Integration tests verify fallback behavior
- No regressions

## Metrics
- Tests: 3212 passing / 3212 total (100%)
- Coverage: 87.3%
- Tokens used: 2,340
- Duration: 47 minutes

Co-Authored-By: Claude <noreply@anthropic.com>"

# Clean up worktree
git worktree remove /home/mike/dev/cohezion-session-56

# Push to remote
git push origin main
```

### 6. Vault as Perpetual Accumulator
Every session logs to vault; next session loads enriched context:

**Log Decision** (during execution):
```python
from cohezion.persistence import vault_log_decision

vault_log_decision(
    project="cohezion",
    title="Circuit breaker pattern for compound executor",
    context="Executor failures cascade; needed graceful degradation",
    decision="Implement exponential backoff + fallback to local Ollama",
    rationale="Decouples remote failures from local work; improves HIHO stability"
)
```

**Log Experiment** (during trial):
```python
from cohezion.persistence import vault_log_experiment

vault_log_experiment(
    project="cohezion",
    hypothesis="Teleport queue will reduce context switching overhead",
    method="Implemented async task queue; measured token consumption",
    result="Context switching overhead reduced 34%; queue throughput stable",
    learnings="File-based queues better than in-memory for persistent sessions"
)
```

**Extract Pattern** (discovered technique):
```python
from cohezion.persistence import vault_extract_pattern

vault_extract_pattern(
    source_path="src/cohezion/compound/executor.py",
    pattern_name="Circuit Breaker with Exponential Backoff",
    description="When to use: Remote service failures need graceful degradation",
    code_example="""
import asyncio
from cohezion.reliability import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    backoff_multiplier=2.0
)

async def call_remote():
    try:
        async with cb:
            return await remote_api.call()
    except CircuitBreakerOpen:
        logger.warning("Circuit open, using fallback")
        return fallback_behavior()
""",
    domain="reliability"
)
```

**Pull Context at Session Start** (richer context each run):
```python
from cohezion.persistence import vault_pull_session_context

context = vault_pull_session_context(
    query="circuit breaker patterns and reliability lessons",
    vault_path="~/vaults/cohezion-vault",
    limit=5  # Top 5 most relevant
)
print(f"Loaded {len(context)} prior decisions and patterns")
# Context includes: decisions made, experiments run, proven patterns
```

**Regenerate Memory Cache** (weekly):
```bash
# Run weekly or after major sessions
uv run python scripts/compile_memory_from_vault.py \
  --vault-path=~/vaults/cohezion-vault \
  --output-path=MEMORY.md \
  --days=7
```

## ANTI-PATTERNS

- **Single-Threaded Orchestration**: Don't queue all work in a single session task queue; use parallel worktrees for true concurrency.
- **Vault Polling Without Backoff**: Polling vault every second wastes I/O; use exponential backoff (1s → 2s → 4s → max 60s).
- **Ignoring Session Registry**: Without coordination layer, parallel sessions conflict on file edits; always check dependencies first.
- **Autonomous Runs Without Safeguards**: Cron workflows without `timeout_minutes` and resource limits can cascade failures; always set caps.
- **Losing Track of Worktrees**: Forgetting to clean up `git worktree remove` after merge pollutes the filesystem; track active worktrees in session registry.
- **Treating Teleport Queue as Real-Time**: Teleport is async; don't expect sub-second feedback; use GitHub Issues for time-sensitive work requiring immediate response.
- **Vault Logging Without Retrieval**: Logging decisions without periodically synthesizing them into MEMORY.md wastes the archive; regenerate cache weekly.

## SEE ALSO
- TEAM_ORCHESTRATION_PRIME
- AUTONOMOUS_RESILIENCE_PRIME
- KNOWLEDGE_HARVESTING_PRIME
- COMPOUND_ENGINEERING_PRIME
- SESSION_PERSISTENCE_PRIME (checkpoint and rollback patterns)

## VERSION
1.0.0

## QUICK REFERENCE

**Mobile Work Entry**:
```bash
# 1. GitHub issue form → dropdown command
# 2. Title: @claude <command>: <details>
# 3. Submit → claude.yml dispatches to local executor
```

**Async Task Queue**:
```bash
# Create
teleport_create_task(title="...", priority="high", estimated_tokens=2500)

# Claim
task = teleport_claim_task(priority="high")

# Complete
teleport_complete_task(task_id="<uuid>", status="completed", result_summary="...")
```

**Cron Automation**:
```yaml
# autonomous-scout.yml: Weekly passive knowledge accumulation
schedule: cron: '0 2 * * 0'

# health-check.yml: Daily health monitoring
schedule: cron: '0 0 * * *'
```

**Session Coordination**:
```bash
# Update registry before session end
session_registry_update(session_id=56, status="in_progress", checkpoint={...})

# Check dependencies at session start
dependencies = session_registry_get_dependencies(session_id=57)
```

**Isolated Worktrees**:
```bash
# Create worktree
git worktree add -b session-56-feature /path/to/worktree main

# Merge and cleanup
git merge --squash origin/session-56-feature
git worktree remove /path/to/worktree
```

**Vault Accumulation**:
```python
# Log decisions and patterns
vault_log_decision(...)
vault_log_experiment(...)
vault_extract_pattern(...)

# Load enriched context at start
context = vault_pull_session_context(query="...", limit=5)
```
