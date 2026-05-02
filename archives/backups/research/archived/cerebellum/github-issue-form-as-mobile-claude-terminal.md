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

## Full Issue Form Template

```yaml
# .github/ISSUE_TEMPLATE/claude-command.yml
name: Claude Command
description: Run a Claude Code command remotely
labels: [claude-command]
body:
  - type: dropdown
    id: command
    attributes:
      label: Command
      description: Select the command to run
      options:
        - /vault-keeper
        - /vault-keeper --quick
        - /daily-research
        - /vault-keeper --triage
        - pytest
        - deploy
        - compound-cycle
    validations:
      required: true

  - type: input
    id: context
    attributes:
      label: Additional context (optional)
      description: Extra notes for the agent
      placeholder: "e.g., focus on cerebellum/ this run"

  - type: checkboxes
    id: confirm
    attributes:
      label: Confirm
      options:
        - label: I understand this will run Claude Code on the remote machine
          required: true
```

## Workflow Integration

The corresponding `@claude` GitHub Actions workflow listens for issues labeled `claude-command`:

```yaml
on:
  issues:
    types: [opened]

jobs:
  run:
    if: contains(github.event.issue.labels.*.name, 'claude-command')
    steps:
      - name: Extract command
        run: |
          COMMAND=$(echo '${{ github.event.issue.body }}' | grep -A1 'command' | tail -1)
          echo "CLAUDE_COMMAND=$COMMAND" >> $GITHUB_ENV
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: ${{ env.CLAUDE_COMMAND }}
```

## Security Considerations

| Risk | Mitigation |
|------|------------|
| Anyone with repo access can trigger agent runs | Use repository-level issue permissions (collaborators only); add `if: github.actor == 'mike-anderson'` guard |
| Prompt injection via free-text context field | Sanitize the context field; use a whitelist for the command dropdown (no free-text commands) |
| Runaway costs from repeated submissions | Add issue-rate-limit check: max 1 claude-command issue per hour |
| Agent takes destructive action | Scope agent permissions; use read-only vault access for audit commands |

## Adding New Commands

1. Add the command to the `options` list in the issue form YAML
2. Ensure the corresponding skill exists in `.claude/skills/`
3. Test with `workflow_dispatch` before enabling on mobile

## When to Use

- When away from your development machine but need to trigger a task
- For non-technical team members who need to invoke agent workflows
- Any scenario where a constrained set of commands should be available via a simple UI
- As a lightweight alternative to a full web UI for agent control

## Cohezion Relevance

This pattern extends Cohezion's agent access surface to mobile-first, zero-infrastructure environments. By treating GitHub Issues as a structured input channel, it reuses existing GitHub authentication and audit trails without building a custom interface. It pairs naturally with the [[github-actions-as-autonomous-claude-code-scheduler]] pattern: scheduled runs handle baseline maintenance autonomously, while issue-form triggers handle ad hoc mobile-initiated requests.

## Related

- [[2026-03-05-github-issues-as-remote-claude-code-terminal]] — the ADR proposing this pattern
- [[agent-architecture]] — agents accessible via multiple interfaces
- [[github-actions-as-autonomous-claude-code-scheduler]] — the complementary scheduled-run pattern
- [[agentic-ai]] — remote interface access is a core agentic capability
- [[workflow-orchestration]] — issues are one trigger layer in the broader orchestration hierarchy
- [[tool-use]] — GitHub Issues as a structured tool invocation mechanism for agents
