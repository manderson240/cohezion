---
title: 'Security fixes: session ID path traversal and hardcoded GitHub search date'
date: '2026-02-22'
status: accepted
tags: [decision, security, cohezion-engine, research-pipeline]
decision_reasoning:
  chosen_option: Sanitize session ID with regex; replace hardcoded date with dynamic timedelta
  rationale: Minimal, targeted fixes that close the vulnerabilities without changing public API or behaviour
  confidence_score: 0.95
  alternatives_rejected:
  - Reject any non-alphanumeric session ID with a ValueError (too strict — breaks PID-based fallbacks)
  - Use os.path.basename to strip traversal (doesn't strip embedded separators)
  reasoning_chain:
  - sequence: 1
    content: 'Context: Security review identified two medium-severity issues in cohezion-engine and research pipeline'
    type: research
    confidence: 0.95
    assumption: Issues were reproducible and not already mitigated elsewhere
  - sequence: 2
    content: Path traversal via COHEZION_SESSION_ID — env var used directly as path component with no sanitization
    type: pattern
    confidence: 0.95
    assumption: Attacker can control env var value
  - sequence: 3
    content: Hardcoded date 2026-02-13 in GitHub search query silently disables discovery over time
    type: research
    confidence: 0.9
    assumption: Date was left from development and not intentional
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.5
  actual_cost: 0.0
  actual_time_hours: 0.5
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
---

## Context

A security review of recently changed files (cohezion-engine and research pipeline) was run in session 2026-02-22. Two medium-severity issues were identified and fixed within the same session.

## Decision

Apply two targeted security fixes:
1. Sanitize `COHEZION_SESSION_ID` before using it as a filesystem path component
2. Replace the hardcoded GitHub search date with a dynamic 7-day rolling window

## Chosen Option

**Regex sanitization + `timedelta`**

- `session.py`: strip any character outside `[a-zA-Z0-9_\-]` to `_` before constructing the session directory path
- `harvester.py`: use `date.today() - timedelta(days=7)` in the GitHub API query parameter

## Alternatives Considered

- **Raise `ValueError` on invalid session IDs**: rejected — too strict, would break legitimate PID-based fallback IDs containing `-`
- **`os.path.basename`**: rejected — strips leading path separators but not embedded ones like `../../etc`
- **Configurable lookback window**: rejected as over-engineering; 7 days is a sensible default for trending discovery

## Decision Reasoning

### Why This Option?

Sanitization is silent and robust — it degrades gracefully for any env var value while keeping the path safe. The `timedelta` fix is a one-liner that requires no new configuration.

### Alternatives Rejected

See above.

### Confidence Level

0.95 — fixes are minimal, well-tested (9 session tests pass), and do not change observable behaviour for valid inputs.

## Expected Outcomes

- No path traversal possible via `COHEZION_SESSION_ID`
- GitHub trending adapter continues to return results indefinitely without code changes

## Metrics & Impact

- 2 files changed, 9 lines net
- PR #24 merged to `main` 2026-02-22
- All 9 cohezion-engine session tests pass

## Related Decisions & Lessons

- [[patterns/sanitize-env-var-path-components]]
- See also: remaining security review findings (XML entity expansion via `ET.fromstring`, broad exception swallowing)
