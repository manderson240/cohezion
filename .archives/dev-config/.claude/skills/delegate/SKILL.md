---
name: delegate
description: Spawn parallel specialist agents with strict scope, deliverables, and
  iteration budgets. Use when a task decomposes into 2-3 independent workstreams
  that can execute concurrently. Synthesizes results and validates the combined
  outcome.
arguments:
  - name: task_description
    description: The task to decompose and delegate (e.g., "Add JWT auth with tests and docs")
    required: true
---

# Parallel Specialist Delegation

You are decomposing `$ARGUMENTS` into independent workstreams and delegating to focused agents.

## Step 1: Decompose the Task

Analyze `$ARGUMENTS` and identify 2-3 **independent** workstreams. Each workstream must:
- Have a clear, testable deliverable
- Not depend on another workstream's output
- Be completable in a single agent session

Common decomposition patterns:

| Pattern | Agent 1 | Agent 2 | Agent 3 |
|---------|---------|---------|---------|
| Feature build | Implement core logic | Write tests | Update docs/types |
| Investigation | Research approach A | Research approach B | Audit current state |
| Refactor | Migrate module X | Migrate module Y | Update integration tests |
| Bug fix | Root cause analysis | Write regression test | Search for similar bugs |

If the task cannot be meaningfully decomposed (single file, single concern), say so and execute directly instead of delegating.

## Step 2: Define Agent Contracts

For each workstream, define a strict contract:

```
Agent: <descriptive-name>
Deliverable: <what to produce — be specific: file paths, test counts, report format>
Scope: <what files/modules to touch>
Forbidden: <what NOT to do — prevents scope creep>
Budget: <max tool calls or iterations — default 30>
```

Example:
```
Agent: auth-implementer
Deliverable: JWT middleware in src/cohezion/api/auth.py with login/refresh endpoints
Scope: src/cohezion/api/auth.py, src/cohezion/api/__init__.py (route registration only)
Forbidden: Do not modify existing endpoints. Do not add new dependencies without noting them.
Budget: 30 tool calls
```

## Step 3: Launch Agents in Parallel

Spawn all agents simultaneously using `run_in_background=true`:

```
Agent(
  name="<agent-name>",
  run_in_background=true,
  prompt="You are the <agent-name> specialist.

YOUR DELIVERABLE: <deliverable>
SCOPE: <scope>
DO NOT: <forbidden>

Instructions:
1. Read all files in scope before modifying
2. Implement the deliverable
3. Verify your work (run tests, check types, read output)
4. Report your results via SendMessage(to='user'):
   - What you produced (file paths, line counts)
   - What tests pass
   - Any blockers or decisions needed

You have a budget of <budget> tool calls. Stay focused."
)
```

Launch ALL agents in the same response block — do not wait between launches.

## Step 4: Monitor and Collect Results

Wait for all agents to complete. As each reports back:
- Record their deliverable status (complete/partial/blocked)
- Note any conflicts (two agents edited the same file)
- Note any blockers that need resolution

## Step 5: Synthesize and Validate

Once all agents report:

1. **Check for conflicts**: If agents touched overlapping files, review and merge manually
2. **Run integration check**: `uv run pytest tests/ -q` to verify nothing broke
3. **Validate deliverables**: Confirm each agent produced what was contracted
4. **Fill gaps**: If an agent was blocked or partial, complete the remaining work directly

If tests fail after synthesis:
- Identify which agent's changes caused the failure
- Fix the issue (do not re-delegate for small fixes)
- Re-run tests to confirm

## Step 6: Report

Provide a summary:

```
## Delegation Results

| Agent | Deliverable | Status | Files Changed |
|-------|-------------|--------|---------------|
| <name> | <what> | Complete/Partial | <files> |

Tests: X passing, Y failing (baseline was: A passing, B failing)
Integration: [Pass/Fail]
```

## Hard Rules

| Rule | Rationale |
|------|-----------|
| Max 3 agents per delegation | More agents = more coordination overhead than time saved |
| Every agent gets explicit scope AND forbidden list | Prevents scope creep and file conflicts |
| All agents launch in parallel | Sequential defeats the purpose of delegation |
| Never delegate a task smaller than 15 minutes of work | Overhead exceeds benefit |
| Validate combined output with tests | Parallel work can create integration issues |
| Do not re-delegate failures | Fix small issues directly after synthesis |

## When NOT to Delegate

- Single-file changes (just do it)
- Tasks with strict ordering requirements (use `/execute` instead)
- When you need to understand the codebase first (explore, then decide)
- Debugging (root cause analysis needs sequential reasoning)

## Anti-Patterns

- Delegating to agents without reading the codebase first — you need context to write good contracts
- Giving agents vague deliverables like "improve the auth system"
- Launching 5+ agents that all touch the same files
- Waiting for Agent 1 to finish before launching Agent 2 (they are independent by definition)
- Re-delegating when a simple 5-line fix would resolve the gap
