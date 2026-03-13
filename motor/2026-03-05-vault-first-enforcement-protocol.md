---
title: "Vault-First Enforcement Protocol"
date: "2026-03-05"
status: active
priority: critical
tags: [protocol, enforcement, vault, memory-infrastructure, compound-engineering]
aspect: doer
neural:
  activation: 0.73
  stage: growing
  synapse_in: 4
  synapse_out: 5
---

## Purpose

Ensure ALL intermediate artifacts from development sessions are stored in the Obsidian vault and/or SurrealDB — never lost to context window limits, session boundaries, or forgotten in ephemeral state.

## Core Rule

> **Nothing valuable lives only in the context window.**
> If it matters, it goes to the vault. If it might matter later, it goes to the vault.

## Mandatory Checkpoints

### Session Start
```
1. vault_pull_session_context() → Read prior state
2. track_session(agent_id, goals) → Register in SurrealDB
3. vault_find_relevant_context(query) → Load prior decisions
4. TaskList → Check for continuation tasks
```

### Before Each Phase/Task
```
1. vault_push_session_state(branch, test_status, phase, active_tasks)
2. TaskUpdate(taskId, status="in_progress")
```

### After Each Phase/Task Completion
```
1. vault_log_decision(project, title, context, decision, rationale)
   OR vault_log_experiment(project, hypothesis, method, result, learnings)
2. TaskUpdate(taskId, status="completed")
3. vault_push_session_state() → Update phase/status
```

### On Error/Blocker Discovery
```
1. vault_log_experiment(
     project="cohezion",
     hypothesis="Expected X to work",
     method="Attempted Y",
     result="Failed because Z",
     learnings="Root cause and workaround"
   )
2. TaskCreate(subject="Fix blocker: Z")
```

### On Reusable Pattern Discovery
```
1. vault_extract_pattern(
     source_path="projects/current-project",
     pattern_name="Pattern Name",
     description="When and how to use",
     code_example="...",
     domain="devops|testing|git|etc"
   )
```

### Before Context Handoff (80%+ context)
```
1. vault_push_session_state(branch, test_status, phase, active_tasks, last_commit)
2. vault_write("sessions/YYYY-MM-DD-handoff-<slug>.md", full_state_dump)
3. Include: what's done, what's in progress, what's next, blockers, file paths
```

## What Goes Where

| Artifact Type | Storage | Tool |
|---------------|---------|------|
| Technical decisions | Vault `decisions/` | `vault_log_decision` |
| Experiments & findings | Vault `experiments/` | `vault_log_experiment` |
| Reusable patterns | Vault `patterns/` | `vault_extract_pattern` |
| Session state snapshots | Vault `sessions/` | `vault_push_session_state` |
| Master plans | Vault `projects/` | `vault_write` |
| Research lineage | SurrealDB | `record_decision` + `track_session` |
| Task progress | Claude Code tasks | `TaskCreate` / `TaskUpdate` |
| Git operation results | Vault decisions/ | `vault_log_decision` |

## Anti-Patterns (NEVER DO)

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| "I'll remember this" | Write it to vault NOW |
| Summarizing in chat only | vault_write + chat summary |
| Plan exists only in context | vault_write to projects/ |
| Decision made but not logged | vault_log_decision immediately |
| Error found, moved on | vault_log_experiment first |
| "Noted for later" without TaskCreate | TaskCreate immediately |
| Session ending without state push | vault_push_session_state ALWAYS |

## Verification

At session end, verify:
- [ ] Session tracked in SurrealDB (`track_session` called at start)
- [ ] All completed phases have a vault decision/experiment entry
- [ ] Session state pushed to vault
- [ ] Any blockers logged as experiments
- [ ] Any patterns extracted
- [ ] Tasks reflect actual progress

## Why This Matters

1. **Context windows are finite** — vault is permanent
2. **Parallel sessions need shared state** — vault is the bridge
3. **Compound engineering requires history** — patterns and decisions compound
4. **Recovery from disasters** — if repo breaks, vault has the plan
5. **Claude Code cloud instances** — can pull vault context without local state

## Related

- [[2026-03-05-repo-sync-master-plan]] — the plan this protocol enforces
- [[2026-02-11-vault-first-knowledge-architecture]] — the architectural decision behind vault-first
- [[repo-and-process-debt]] — the debt this protocol prevents
- [[vault-first-session-protocol]] — reusable pattern extracted from this protocol
- [[parallel-session-coordination-via-vault-registry]] — pattern for coordinating parallel sessions through the vault
