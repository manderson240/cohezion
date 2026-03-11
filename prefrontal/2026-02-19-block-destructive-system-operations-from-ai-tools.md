---
title: 'Block destructive system operations from AI tools'
date: '2026-02-19'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: 'Destructive operations (vacuum, rm -rf on logs, database drops) are irreversible. AI tools operate fast and don't naturally pause to consider irreversibility. The guard hook forces a manual step for destructive operations, which gives the human operator a moment to consider whether backup is needed. The journald config prevents the root cause (unbounded journal growth) so vacuum should rarely be needed. The cascade: crash loop → journal bloat → panic vacuum → lost diagnostics. Breaking ANY link in this chain prevents the problem.'
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Block destructive system operations from AI tools'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
aspect: thinker
neural:
  activation: 0.567
  stage: growing
  cluster: decisions
---

## Context

A crash-loop recovery incident revealed a dangerous cascade: when SurrealDB entered a crash loop, systemd journal grew unbounded, consuming disk space. An AI tool (Claude Code agent) attempted to resolve the disk pressure by running `journalctl --vacuum-size=100M`, which permanently deleted diagnostic logs needed to understand the root cause of the crash loop. The cascade was:

```
crash loop -> journal bloat -> disk pressure -> AI runs vacuum -> diagnostics lost
```

This exposed a fundamental safety gap: AI tools execute fast and do not naturally pause to consider whether an operation is irreversible. Operations like `journalctl --vacuum-*`, `rm -rf` on log directories, `DROP TABLE`, and `git reset --hard` are destructive and cannot be undone. An AI agent optimizing for "fix the immediate problem" will reach for these tools without considering the long-term cost of losing diagnostic data.

The incident is documented in [[log-lifecycle-management]] and the broader principle in [[2026-02-09-operational-principle-no-destructive-operations-without-learning]].

## Decision

Implement a guard hook system that blocks AI tools from executing destructive system operations without explicit human approval. The guard operates as a pre-execution filter on Bash commands within Claude Code:

1. **Pattern matching**: A pre-tool-use hook intercepts Bash commands and checks against a blocklist of destructive patterns
2. **Human approval gate**: Matched commands are blocked with an explanation of the risk, requiring the human operator to explicitly approve
3. **Preventive configuration**: For the specific journal bloat case, configure systemd journal size limits (`SystemMaxUse=2G`) so vacuum is rarely needed

### Blocked Patterns

| Pattern | Risk | Category |
|---------|------|----------|
| `journalctl --vacuum-*` | Permanent log deletion | Log destruction |
| `rm -rf /var/log/*` | System log deletion | Log destruction |
| `DROP TABLE` / `DROP DATABASE` | Data destruction | Database destruction |
| `git reset --hard` | Uncommitted work loss | Version control destruction |
| `git clean -fd` | Untracked file deletion | Version control destruction |
| `systemctl disable` | Service disablement | Service destruction |
| `dd if=/dev/zero` | Disk overwrite | Storage destruction |

## Chosen Option

**Pre-tool-use guard hook with human approval gate + preventive journald configuration**

## Alternatives Considered

### Alt 1: Trust AI Tool Judgment (No Guard)
- **Rejected**: The incident proved AI tools optimize for the immediate problem without considering irreversibility. "Fix disk pressure" led directly to "delete diagnostics." This will recur without a structural guard.

### Alt 2: Allowlist-Only Bash Commands
- **Rejected**: An allowlist would be impractically large (thousands of safe commands). A blocklist of known-destructive patterns is more maintainable and catches the highest-risk operations.

### Alt 3: Read-Only Mode for AI Tools
- **Rejected**: Too restrictive. AI tools need write access for normal operations (file editing, git commits, service restarts). The goal is to block specifically destructive operations, not all writes.

### Alt 4: Post-Hoc Logging Only (No Prevention)
- **Rejected**: Logging after the fact does not prevent data loss. The journal vacuum already happened before anyone could review the decision. Prevention must be pre-execution.

## Decision Reasoning

### Why This Option?

1. **Breaks the cascade at the cheapest point**: A guard hook is a single configuration change. Preventing the vacuum is cheaper than recovering lost logs.
2. **Preserves AI tool capability**: The guard only blocks destructive operations. All other Bash commands execute normally. No loss of productivity.
3. **Human-in-the-loop for irreversible actions**: The approval gate ensures a human considers backup needs before destructive operations.
4. **Preventive configuration addresses root cause**: `SystemMaxUse=2G` in journald prevents unbounded journal growth, eliminating the disk pressure that triggers vacuum requests.
5. **Aligns with [[ai-safety]] principles**: Autonomous agents must have guardrails on irreversible actions.

### Alternatives Rejected

Trusting AI judgment failed empirically. Allowlist is impractical. Read-only is too restrictive. Post-hoc logging does not prevent data loss.

### Confidence Level

**0.95** -- Very high confidence. The incident is well-documented, the root cause is clear, and the guard mechanism is simple to implement and test.

## Expected Outcomes

1. Zero unintentional destructive operations by AI tools
2. Human operator reviews all destructive actions before execution
3. Journal growth stays within 2 GB limit (preventive configuration)
4. Diagnostic logs preserved for all future crash-loop investigations
5. Pattern reusable for any environment where AI tools have system access

## Metrics & Impact

### Estimated

| Metric | Before | After |
|--------|--------|-------|
| Destructive ops blocked | 0 | 100% of known patterns |
| Diagnostic data lost to AI actions | 1 incident | 0 |
| Journal disk usage | Unbounded | Max 2 GB |
| False positive rate (safe commands blocked) | N/A | <1% |

### Actual (Post-Implementation)

Guard hook implemented and active. See [[2026-02-22-security-fixes-session-id-path-traversal-and-github-date]] for companion security hardening applied in the same session.

## Related Decisions & Lessons

- [[log-lifecycle-management|Log Lifecycle Management Pattern]] — the concrete pattern that emerged from the SurrealDB crash-loop incident; shows what happens when destructive operations (vacuum) are run without pre-flight checks
- [[compound-engineering-investigation-retrospection-before-destructive-operations|Compound Engineering: Investigation Before Destructive Operations]] — the principle this decision operationalizes
- [[2026-02-09-operational-principle-no-destructive-operations-without-learning|Operational Principle: No Destructive Operations Without Learning]] — the predecessor principle; this decision adds a system-level enforcement hook
- [[ai-safety|AI Safety]] — the broader field motivating guards on irreversible AI tool actions
- [[alignment]] — blocking destructive operations is an alignment enforcement mechanism ensuring AI tool actions match human intent
- [[ai-safety-alignment]] — guard hooks on destructive operations are a concrete implementation of safety-alignment principles for autonomous agents
- [[2026-02-22-security-fixes-session-id-path-traversal-and-github-date]] — companion security fix addressing path traversal; both decisions harden AI tool safety
