---
title: "GitHub Actions as Autonomous Claude Code Scheduler"
date: 2026-03-05
tags: [pattern, github-actions, autonomous-agent, scheduling]
aspect: thinker
neural:
  activation: 0.63
  stage: embryo
  synapse_in: 2
  synapse_out: 2
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

## Full Workflow Variants

### Nightly Vault Audit

```yaml
# .github/workflows/vault-audit.yml
name: Nightly Vault Audit
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch: {}

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: Run Vault Keeper
        uses: anthropics/claude-code-action@v1
        with:
          direct_prompt: true
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Run /vault-keeper --quick and commit any frontmatter fixes.
            Push changes if any were made.
```

### Weekly Research Scout

```yaml
# .github/workflows/scout.yml (Sunday 6 AM UTC)
prompt: |
  Run /daily-research. Commit any new sensory/ notes found.
  Update the research pipeline log in hippocampus/.
```

## Security Considerations

| Risk | Mitigation |
|------|------------|
| API key exposure | Store as GitHub Actions secret; never log or echo |
| Unconstrained prompt injection via repo content | Sandbox Claude to read-only vault access; pin commit SHA in `uses:` |
| Excessive API spend | Set `max_turns` limit in claude-code-action; monitor spend via Anthropic dashboard |
| Commit bot impersonation | Use a dedicated bot account with limited push scope; sign commits |
| Noisy PRs from failed runs | Add `if: success()` guard on commit steps; send failure to Slack webhook instead |

**Minimum required PAT scopes:** `contents:write` (to push vault changes), `issues:read` (for the reactive `@claude` pattern).

## Cost Estimation

| Task | Typical token cost | Monthly cost (weekly cadence) |
|------|-------------------|-------------------------------|
| `/vault-keeper --quick` | ~15K tokens | ~$0.30 (Sonnet) |
| `/daily-research` | ~40K tokens | ~$0.80 (Sonnet) |
| Full `/vault-keeper` run | ~80K tokens | ~$1.60 (Sonnet) |
| GitHub Actions compute (ubuntu-latest) | ~5 min/run | ~$0.04/run |

Nightly audits cost approximately **$10–15/month** total for a medium-sized vault. The research scout adds another ~$4/month.

## Failure Handling

1. **Workflow fails**: GitHub sends notification email; check Actions tab for error log
2. **Claude hits token limit mid-task**: Partial commits may land; next run picks up from vault state
3. **Push rejected** (branch protection): Configure a bypass rule for the bot account on the `track-c` branch
4. **Duplicate commits**: Add `git diff --quiet && echo "No changes" && exit 0` before commit step

## When to Use

- Recurring research or audit tasks that don't need human oversight
- Nightly CI-style vault health checks
- Any scheduled agentic workflow where results are committed to the repo
- Replacing fragile cron+SSH setups with managed GitHub Actions infrastructure

## Cohezion Relevance

This pattern enables the vault to self-maintain without continuous human attention — a key step toward realizing the Ouroboros Loop's vision of autonomous self-improvement. The scheduled vault-keeper run is how the `metabolism/` dashboard stays fresh between active development sessions. Combined with [[parallel-session-coordination-via-vault-registry]], it forms a two-layer automation: scheduled baseline health (GitHub Actions) + reactive parallel work (multi-terminal sessions).

## Related

- [[2026-03-05-autonomous-scout-via-scheduled-github-actions]] — the ADR that proposed this pattern
- [[agentic-ai]] — autonomous scheduled execution is a core agentic AI capability
- [[workflow-orchestration]] — scheduling is the outermost layer of agent workflow orchestration
- [[compound-engineering]] — scheduled maintenance is how compound engineering runs without manual intervention
- [[Ouroboros-Loop]] — this pattern is one operational implementation of the autonomic feedback loop
- [[parallel-session-coordination-via-vault-registry]] — complements scheduled runs with real-time session coordination
- [[non-blocking-observability]] — scheduled workflows must not block or interfere with active sessions
