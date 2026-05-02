---
title: "Vault-First Session Protocol"
date: 2026-03-05
tags: [pattern, vault-first, session-management, knowledge-persistence]
aspect: thinker
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 1
  synapse_out: 2
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

## Why Context Loss Is Catastrophic

A Claude Code session is a **volatile compute process**. Its context window is RAM — not disk. When the session ends, closes, or overflows:
- All intermediate reasoning is gone
- Decisions made but not written are irrecoverable
- Partially designed patterns can't be reconstructed faithfully
- Lessons from failures exist only in the conversation log (which agents can't re-read efficiently)

The vault is persistent disk. The protocol's core discipline: **if it matters, it must hit disk before the session ends**.

## Token-Efficient Vault Write Patterns

| Pattern | Cost | When |
|---------|------|------|
| `vault_write(path, content)` | ~200 tokens overhead | Full note creation or update |
| `vault_append(path, entry)` | ~50 tokens overhead | Incremental logging (hipppocampus/ daily notes) |
| Inline `[[wiki-link]]` add | ~10 tokens overhead | Cross-referencing during normal edits |
| Continuation file write | ~300 tokens | Context handoff (saves 5–50K tokens next session) |

The continuation file write is the highest-ROI vault operation: paying 300 tokens now saves reloading 5,000–50,000 tokens of context in the next session.

## Continuation File Pattern

At 80%+ context, write to `~/.cohezion-engine/hippocampus/<session-id>/continuation.md`:

```markdown
# Session Continuation — <date>
**Task:** [what you were doing]
**Active Plan:** [path or None]

## Completed:
- [x] Task A
- [ ] Task B (stopped mid-way at file X, line Y)

## Next Steps:
1. Finish Task B: edit `cerebellum/foo.md` to add Failure Modes section
2. Run verification: `grep -rl "[[foo]]" cortex/ | wc -l`

## Vault State:
- Wrote: `cerebellum/foo.md` (expanded)
- Pending: `cortex/MOC-bar.md` needs new entry for foo
```

The next session reads this file before any other action and resumes from "Next Steps".

## Enforcement Mechanisms

1. **Context monitor hook** (`context_monitor.py`) — fires at 80% and 90%, printing a structured warning that includes the continuation file path
2. **Vault-keeper PostToolUse hook** — detects when Edit/Write creates a note with no inbound links and auto-links it
3. **Session start cleanup** — first action every session is `rm -f <continuation-path>` after reading, preventing stale state

## When to Use

- Every Claude Code session (this is a universal protocol)
- Especially critical for sessions likely to hit context limits
- Mandatory for sessions that produce architectural decisions or discover patterns
- Any session in which a new cerebellum pattern or prefrontal ADR is discovered

## Cohezion Relevance

This protocol is the micro-level implementation of [[compound-engineering]]. Every session that follows it adds a permanent layer of knowledge to the vault; every session that skips it is a net loss. The pattern is what transforms ephemeral agent compute into durable vault intelligence — making the compound interest of knowledge accumulation actually compound.

## Related

- [[2026-03-05-vault-first-enforcement-protocol]] — the operational enforcement protocol
- [[2026-02-11-vault-first-knowledge-architecture]] — the architectural decision behind vault-first
- [[compound-engineering]] — the macro-level methodology this protocol operationalizes at session granularity
- [[experience-feedback-loop]] — the broader feedback cycle that this protocol feeds into
- [[context-management]] — strategies for optimizing how much context is loaded vs. deferred to vault
- [[session-retrospective]] — structured end-of-session reflection that complements this protocol
- [[token-efficiency]] — vault writes are a token investment with high ROI over multiple sessions
