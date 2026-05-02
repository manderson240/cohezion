# Skill: multi-agent-improvement-sprint

Orchestrate a team of specialist agents for parallel codebase improvement campaigns using phased execution with task dependencies.

## When to Use

- Multiple independent improvement tasks identified (security, testing, assessment, knowledge enrichment)
- Need parallel execution with phased dependencies (e.g., test-coverage waits for security fixes)
- Running a structured improvement campaign across a codebase or MCP server
- Want reproducible multi-agent sprints with clean startup/shutdown

## Pattern Overview

```
Phase 1 (Parallel)          Phase 2 (Sequential)         Phase 3 (Cleanup)
+-----------------+         +-------------------+        +----------------+
| matrix-analyst  |--+      |                   |        |                |
+-----------------+  |      |                   |        |                |
| security-sweep  |--+----> | test-coverage     |------> | Review + Stop  |
+-----------------+  |      | (blocked on Ph.1) |        | TeamDelete     |
| knowledge-enrich|--+      |                   |        |                |
+-----------------+         +-------------------+        +----------------+
```

## Step-by-Step Workflow

### Step 1: Create the Team

```
TeamCreate(
  teamName="improvement-sprint",
  description="Multi-agent codebase improvement campaign"
)
```

### Step 2: Create Tasks with Dependencies

Create all tasks upfront. Use `addBlockedBy` to encode phase dependencies.

```
# Phase 1 tasks (independent, no blockers)
TaskCreate(subject="Run CapabilityMatrix assessment", owner="matrix-analyst")       → task #A
TaskCreate(subject="Security sweep of critical files", owner="security-sweep")      → task #B
TaskCreate(subject="Knowledge enrichment scout", owner="knowledge-enricher")        → task #C

# Phase 2 task (blocked on Phase 1)
TaskCreate(
  subject="Extend test coverage for modified code",
  owner="test-coverage",
  addBlockedBy=["A", "B", "C"]   # Waits for all Phase 1 agents
)                                                                                   → task #D
```

### Step 3: Launch Phase 1 Agents (Parallel)

Launch all three simultaneously. Each agent gets a scoped prompt with exact file paths and expected deliverables.

```
# All three launched in the SAME response (parallel execution)
Agent(
  name="matrix-analyst",
  team="improvement-sprint",
  run_in_background=true,
  prompt="You are the matrix-analyst agent. Your task:
    1. Run CapabilityMatrix assessment on <target files/modules>
    2. Write results to vault via vault_write or graph tools
    3. Exercise graph-sync pipeline (store_node, graph_neighborhood)
    4. Report findings via SendMessage to team lead
    Expected deliverables: Assessment report, vault entries, graph nodes"
)

Agent(
  name="security-sweep",
  team="improvement-sprint",
  run_in_background=true,
  prompt="You are the security-sweep agent. Your task:
    1. Review these critical files for OWASP vulnerabilities: <file list>
    2. Fix CRITICAL severity issues inline (edit files directly)
    3. Flag HIGH/MEDIUM issues in your report (do not fix)
    4. Report all findings via SendMessage to team lead
    Expected deliverables: Fixed CRITICALs, vulnerability report"
)

Agent(
  name="knowledge-enricher",
  team="improvement-sprint",
  run_in_background=true,
  prompt="You are the knowledge-enricher agent. Your task:
    1. Scout for new models, capabilities, or patterns in <domain>
    2. Enrich neuron graph via graph_annotate_neuron, graph_write_latent_synapse
    3. Record discoveries in vault via vault_write
    4. Report findings via SendMessage to team lead
    Expected deliverables: Graph enrichments, vault notes, discovery summary"
)
```

### Step 4: Monitor Phase 1

Team lead monitors progress via messages. Wait for all three agents to report completion.

### Step 5: Launch Phase 2 Agent (Sequential)

Only after Phase 1 completes (task dependencies enforce this):

```
Agent(
  name="test-coverage",
  team="improvement-sprint",
  run_in_background=true,
  prompt="You are the test-coverage agent. Your task:
    1. Identify files modified by security-sweep agent
    2. Extend test coverage for new/modified code paths
    3. Run full test suite: uv run pytest tests/ -q
    4. Report results (pass count, fail count, coverage delta)
    Expected deliverables: New test files, passing suite, coverage report"
)
```

### Step 6: Review and Shutdown

After all phases complete:

```
# 1. Review deliverables from each agent
# 2. Send shutdown request to each agent
SendMessage(to="matrix-analyst", message="shutdown_request")
SendMessage(to="security-sweep", message="shutdown_request")
SendMessage(to="knowledge-enricher", message="shutdown_request")
SendMessage(to="test-coverage", message="shutdown_request")

# 3. Wait for confirmations, then clean up
TeamDelete(teamName="improvement-sprint")
```

## Agent Role Templates

### matrix-analyst
- **Purpose**: Assess codebase capabilities, write structured reports
- **Tools**: vault_write, graph_search, graph_neighborhood, store_node
- **Output**: Assessment report with scores, vault entries, graph nodes

### security-sweep
- **Purpose**: Find and fix security vulnerabilities
- **Tools**: Read, Edit, Grep (file analysis), vault_log_decision (record fixes)
- **Output**: Fixed CRITICAL issues, vulnerability report for HIGH/MEDIUM

### knowledge-enricher
- **Purpose**: Scout external knowledge, enrich the neuron graph
- **Tools**: graph_annotate_neuron, graph_write_latent_synapse, vault_write, web search
- **Output**: New graph nodes/synapses, vault discovery notes

### test-coverage
- **Purpose**: Write tests for new/modified code, verify suite health
- **Tools**: Read, Write, Edit, Bash (pytest)
- **Output**: New test files, full suite passing, coverage delta

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Phase 1 agents are independent (parallel) | No data dependencies between assessment, security, and knowledge tasks |
| Phase 2 blocked on all of Phase 1 | Test-coverage needs to know which files were modified by security fixes |
| `run_in_background=true` on all agents | Team lead monitors asynchronously, doesn't block on any single agent |
| Scoped prompts with exact file paths | Prevents agents from wandering; each knows exactly what to deliver |
| Shutdown protocol via SendMessage | Graceful teardown; agents can finalize work before stopping |
| Task dependencies via addBlockedBy | Enforces correct execution order without manual coordination |

## Customization

The four-agent template is a starting point. Adapt by:

- **Adding agents**: Insert more Phase 1 agents for additional parallel work (e.g., documentation-sweep, dependency-audit)
- **Changing phases**: Add Phase 3 agents blocked on Phase 2 for multi-stage pipelines
- **Scoping prompts**: Replace `<file list>` and `<target files/modules>` with actual paths for your sprint
- **Adjusting roles**: Swap agent specializations to match your improvement goals

## Anti-Patterns

- Do NOT launch Phase 2 agents before Phase 1 completes (task dependencies prevent this, but don't override)
- Do NOT give agents open-ended prompts like "improve the codebase" (scope tightly)
- Do NOT skip the shutdown protocol (agents may hold resources or have pending writes)
- Do NOT run more than 4 concurrent agents unless hardware supports it (see HARDWARE_PROFILE_PRIME.md)

---

**Version:** 1.0.0
**Status:** Proven (extracted from live session)
**Origin:** Multi-agent improvement sprint on cloud-vault-mcp (2026-03-25)
