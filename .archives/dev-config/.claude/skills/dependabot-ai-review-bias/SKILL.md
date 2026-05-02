---
name: dependabot-ai-review-bias
description: |
  Knowledge cutoff bias pattern in AI code reviews of Dependabot PRs.
  Use when: (1) reviewing a Dependabot dependency bump PR with AI agents,
  (2) an AI review agent flags "version X does not exist" on a Dependabot PR,
  (3) review agents produce contradictory findings about whether versions exist.
  Key insight: Dependabot only proposes versions verified via live GitHub API —
  it is authoritative. Review agents with stale training data are not.
  Secondary finding: slackapi/slack-github-action v1→v2 is a breaking API change.
author: Claude Code
version: 1.0.0
---

# Dependabot AI Review Bias

## Problem

When multi-agent AI code review pipelines review Dependabot PRs, agents with stale
training data (knowledge cutoffs) will **confidently but incorrectly** flag proposed
version bumps as "non-existent." This creates false blocking findings that look credible
because the agents cite specific evidence ("current latest is v4, v6 does not exist").

## Context / Trigger Conditions

- Reviewing a Dependabot PR that bumps GitHub Actions to major versions
- AI review agents flag something like "actions/checkout@v6 does not exist" or
  "this version has not been released"
- Multiple agents disagree on whether a version exists
- Dependabot PR is from a date well past the reviewing agents' knowledge cutoffs

## Root Cause

Dependabot uses live GitHub API calls to discover available versions — it will NEVER
propose a version that doesn't exist as a real tag/release. AI review agents, by
contrast, have static training data with knowledge cutoffs. An agent trained in 2025
has no knowledge of 2026 GitHub Actions releases, but will confidently state they
don't exist rather than expressing uncertainty.

**The asymmetry:**
| Source | Data freshness | Reliability for version existence |
|--------|---------------|----------------------------------|
| Dependabot | Live GitHub API | **Authoritative** — version must exist |
| AI review agent | Training cutoff (static) | Unreliable — may predate the release |

## Solution

When an AI agent flags a Dependabot-proposed version as non-existent:

1. **Treat it as a false positive** — Dependabot cannot propose non-existent versions
2. **Discard the finding** — it does not need to be investigated further
3. **Focus on behavioral changes** — the real risk in major version bumps is breaking
   API changes, not the existence of the version

### What to Actually Review in Dependabot Action Bumps

Instead of checking if versions exist, check:
- **Breaking input changes**: Do any `with:` parameters change between versions?
- **Removed/renamed inputs**: Does the action's API surface change?
- **Node runtime requirements**: Some v7+ actions require Node 24 (default since March 2026)
- **Deprecated parameter warnings**: Will existing `with:` params silently do nothing?

## Known Breaking Changes (GitHub Actions)

### slackapi/slack-github-action v1 → v2

**Breaking change**: v1 accepted `payload:` as a standalone input with a raw JSON block.
v2 requires a *technique* to be specified — either:
- `webhook:` + `payload:` (for incoming webhooks), OR
- `method: chat.postMessage` + `token:` (for bot token API)

**Symptom**: Slack notifications stop working when tests fail. The step errors out
because no technique is configured.

**Pattern that breaks:**
```yaml
# BROKEN in v2 — missing webhook: or method: + token:
- uses: slackapi/slack-github-action@v2
  with:
    payload: |
      { "text": "Build failed" }
```

**Fix:**
```yaml
# CORRECT — specify webhook technique
- uses: slackapi/slack-github-action@v2
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
    webhook-type: incoming-webhook
    payload: |
      { "text": "Build failed" }
```

Note: This issue only triggers on the `if: failure()` path, so it won't break normal
CI — it only breaks Slack failure notifications.

## Verification

To verify a proposed version actually exists:
```bash
# Check GitHub releases for an action
gh api repos/actions/checkout/releases --jq '.[].tag_name' | head -5
gh api repos/slackapi/slack-github-action/releases --jq '.[].tag_name' | head -5
```

Dependabot's proposal is itself the verification — but if in doubt, use `gh api`.

## Example

During review of a 2026 Dependabot PR (PR #34 in cohezion):
- Agent #2 flagged: "actions/checkout@v6 does not exist — current latest is v4"
- Agent #4 flagged: "actions/setup-node@v6 does not exist"
- Agent #3 verified live: both v6 tags exist (v6.0.2 and v6.3.0 respectively)

All "version does not exist" findings were false positives. The only real issue was
`slackapi/slack-github-action` v1→v2 (a genuine breaking API change scored 75/100
— real but only triggers on failure path).

## References

- Dependabot version resolution: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates
- slackapi/slack-github-action v2 migration: https://github.com/slackapi/slack-github-action/releases/tag/v2.0.0
