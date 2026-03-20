---
title: "Remote Claude Code Leverage Architecture"
date: "2026-03-05"
status: complete
tags: [experiment, agentic-ai, github-actions]
aspect: thinker
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 1
  synapse_out: 2
---

# Remote Claude Code Leverage Architecture

## Hypothesis

GitHub Actions workflows can serve as autonomous Claude Code execution environments, enabling scheduled vault maintenance and remote task dispatch without a persistent local session.

## Method

Explored two approaches: (1) GitHub Issues as a remote command interface, and (2) Scheduled Actions running Claude Code on a cron. Tested feasibility of vault-first session protocols in CI environments.

## Results

Both approaches proved viable. The key insight was that **Claude Code sessions can be bootstrapped from vault context alone**, without requiring a live user session. The vault's VAULT_MANIFEST, relevant MOCs, and session continuation files provided enough context for a cold-start agent to resume work meaningfully.

### Approach Comparison

| Approach | Trigger | Latency | Suitable For |
|----------|---------|---------|-------------|
| GitHub Issue Form | Human opens issue on mobile | ~2 min (GH queue) | Ad hoc commands, non-critical tasks |
| Scheduled Actions | Cron | Predictable (e.g., 2 AM UTC) | Recurring maintenance, vault audits |
| Webhook from external system | Event | Near-real-time | CI/CD integration, monitoring alerts |

### Session Bootstrap Architecture

The critical architecture insight: a remote Claude Code session needs three things from the vault at startup:
1. `VAULT_MANIFEST.md` — routing and conventions (~1K tokens)
2. `metabolism/graph-briefing.md` — current vault health (~1K tokens)
3. The target continuation file or task description (~300 tokens)

Total cold-start cost: ~2.3K tokens to orient a remote session. This is < 2% of a 200K context window — making remote bootstrapping highly token-efficient.

## Learnings

- Remote execution requires careful session identity management to avoid collisions
- Vault-first protocol is essential: the vault IS the session state, not ephemeral context
- Cold-start orientation costs ~2.3K tokens — negligible compared to the value of autonomous execution
- Session identity must use UUIDs (not PID-based IDs) in CI environments where PIDs are not stable
- GitHub Actions runners have a 6-hour job limit — tasks must be designed to complete or checkpoint within that window
- See [[2026-03-05-autonomous-scout-via-scheduled-github-actions]] for the ADR
- See [[github-actions-as-autonomous-claude-code-scheduler]] for the implementation pattern

## Related

- [[github-actions-as-autonomous-claude-code-scheduler]] — the pattern extracted from this experiment
- [[github-issue-form-as-mobile-claude-terminal]] — the mobile interface pattern extracted from this experiment
- [[vault-first-session-protocol]] — the protocol that makes remote bootstrapping possible
- [[parallel-session-coordination-via-vault-registry]] — session collision avoidance for multi-agent remote runs
- [[agentic-ai]] — autonomous remote execution as a core agentic capability
