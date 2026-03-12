---
title: "GitHub Actions as Autonomous Claude Code Scheduler"
date: 2026-03-05
tags: [pattern, github-actions, autonomous-agent, scheduling]
aspect: thinker
---

# Pattern: GitHub Actions as Autonomous Claude Code Scheduler

## Problem

You want Claude Code to run autonomously on a schedule (e.g., weekly research scouting, nightly vault audits) without manual intervention. SSH/cron approaches require persistent infrastructure and are fragile.

## Solution

Use GitHub Actions scheduled workflows with `direct_prompt: true` to bypass the issue-comment trigger pattern. A dedicated workflow file runs Claude Code on a cron schedule, passing a prompt directly.

Key design choices:
- **Separate workflow file** from the reactive `@claude` issue-comment handler — keeps concerns clean
- **`direct_prompt: true`** bypasses issue-based triggering entirely
- **Weekly cadence** (e.g., Sunday) balances freshness vs. API cost
- **Sunday timing** means findings are ready for Monday planning sessions

## Code Example

```yaml
# .github/workflows/scout.yml
name: Autonomous Scout
on:
  schedule:
    - cron: '0 6 * * 0'  # Sunday 6 AM UTC
  workflow_dispatch: {}    # Manual trigger

jobs:
  scout:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Claude Code
        uses: anthropics/claude-code-action@v1
        with:
          direct_prompt: true
          prompt: |
            Run /daily-research and commit findings to the vault.
```

## When to Use

- Recurring research or audit tasks that don't need human oversight
- Nightly CI-style vault health checks
- Any scheduled agentic workflow where results are committed to the repo

## Related

- [[2026-03-05-autonomous-scout-via-scheduled-github-actions]] — the ADR that proposed this pattern
- [[agentic-ai]] — autonomous scheduled execution is a core agentic AI capability
