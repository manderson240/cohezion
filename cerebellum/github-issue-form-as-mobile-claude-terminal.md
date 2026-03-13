---
title: "GitHub Issue Form as Mobile Claude Terminal"
date: 2026-03-05
tags: [pattern, github-issues, mobile, remote-control]
aspect: thinker
neural:
  activation: 0.63
  stage: embryo
  synapse_in: 1
  synapse_out: 2
---

# Pattern: GitHub Issue Form as Mobile Claude Terminal

## Problem

You need to trigger Claude Code tasks from a mobile phone (no SSH, no terminal, no typing long commands). Standard GitHub issue comments are error-prone on mobile.

## Solution

Use GitHub Issue Form templates with dropdown selectors for predefined commands. Opening a GitHub issue on your phone, selecting a command from a dropdown, and submitting triggers the `@claude` workflow on your local machine.

Key design choices:
- **Dropdown menus** prevent typos that would cause the workflow to silently skip
- **Predefined command set** covers common operations: heal, audit, scout, deploy, compound-cycle, pytest
- **Zero-latency interface**: open GitHub app → pick template → submit → Claude runs locally
- **No infrastructure needed** — just GitHub Actions and the existing `@claude` workflow

## Code Example

```yaml
# .github/ISSUE_TEMPLATE/claude-command.yml
name: Claude Command
description: Run a Claude Code command remotely
body:
  - type: dropdown
    id: command
    attributes:
      label: Command
      options:
        - /vault-keeper
        - /daily-research
        - pytest
        - deploy
        - compound-cycle
    validations:
      required: true
```

## When to Use

- When away from your development machine but need to trigger a task
- For non-technical team members who need to invoke agent workflows
- Any scenario where a constrained set of commands should be available via a simple UI

## Related

- [[2026-03-05-github-issues-as-remote-claude-code-terminal]] — the ADR proposing this pattern
- [[agent-architecture]] — agents accessible via multiple interfaces
