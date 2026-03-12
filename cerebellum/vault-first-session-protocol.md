---
title: "Vault-First Session Protocol"
date: 2026-03-05
tags: [pattern, vault-first, session-management, knowledge-persistence]
aspect: thinker
---

# Pattern: Vault-First Session Protocol

## Problem

Claude Code sessions produce valuable intermediate artifacts (decisions, experiments, patterns, blockers) that live only in the context window. When context fills up or the session ends, these artifacts are lost forever.

## Solution

Follow a strict protocol at every session lifecycle point to persist artifacts to the vault:

1. **Session Start**: Pull prior context, register session, load relevant decisions
2. **Before Each Task**: Push session state snapshot
3. **After Each Task**: Log decisions/experiments to vault, update task status
4. **On Error/Blocker**: Log experiment with hypothesis, method, result, learnings
5. **On Pattern Discovery**: Extract reusable pattern to `cerebellum/`
6. **Before Context Handoff** (80%+): Full state dump to vault with continuation instructions

## Code Example

```
# Anti-pattern → Correct pattern
"I'll remember this"           → vault_write() NOW
Plan exists only in context    → vault_write("motor/plan.md")
Decision made but not logged   → vault_log_decision() immediately
Error found, moved on          → vault_log_experiment() first
"Noted for later"              → TaskCreate() immediately
```

## When to Use

- Every Claude Code session (this is a universal protocol)
- Especially critical for sessions likely to hit context limits
- Mandatory for sessions that produce architectural decisions or discover patterns

## Related

- [[2026-03-05-vault-first-enforcement-protocol]] — the operational enforcement protocol
- [[2026-02-11-vault-first-knowledge-architecture]] — the architectural decision behind vault-first
