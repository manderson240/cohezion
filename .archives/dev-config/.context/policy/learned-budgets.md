---
version: 1.0.0
updated_at: '2026-04-11T17:17:53.166700+00:00'
profiles:
  focused:
    flux_top_k: 5
    flux_min_relevance: 0.7
    token_budget: 800
    skill_overlay: true
  exploratory:
    flux_top_k: 10
    flux_min_relevance: 0.3
    token_budget: 1500
    skill_overlay: true
  routine:
    flux_top_k: 2
    flux_min_relevance: 0.8
    token_budget: 300
    skill_overlay: false
task_overrides: []
outcome_summary:
  total_executions: 289
  by_profile:
    focused:
      successes: 201
      failures: 85
      avg_coherence: 0.4549230769230783
      count: 286
    routine:
      successes: 0
      failures: 3
      avg_coherence: 0.55
      count: 3
---


































































































































































































































































































# Learned Context Budgets

Cross-platform context policy for Cohezion compound engineering.
Updated automatically by `ContextPolicy.record_outcome()`.

## Profiles

| Profile | Use Case | Breadth (top_k) | Depth (min_rel) | Tokens |
|---------|----------|-----------------|------------------|--------|
| **focused** | Single-domain tasks (debug, fix) | 5 | 0.7 | 800 |
| **exploratory** | Cross-domain design, high drift | 10 | 0.3 | 1500 |
| **routine** | Template hits, simple persist/search | 2 | 0.8 | 300 |

## How Profiles Are Tuned

Outcomes accumulate in the YAML frontmatter above. The `outcome_summary`
tracks successes, failures, and average coherence per profile. Task overrides
record soft signals (drift-prone patterns, over-classifications) that inform
future task classification.

## Access

| Tool | Read | Write |
|------|------|-------|
| Claude Code | `ContextPolicy.__init__()` | `record_outcome()` |
| Gemini CLI | `get_context_policy` MCP tool | `update_context_policy` MCP tool |
| Zed / Antigravity | MCP tool or file read | MCP tool |
| Pi / others | Read this file directly | Edit YAML frontmatter |
| SurrealDB | `SELECT * FROM context_policy` | Automatic write-through |
