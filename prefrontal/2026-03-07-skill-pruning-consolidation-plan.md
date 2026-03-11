---
title: "Skill Pruning & Consolidation Plan"
date: 2026-03-07
status: proposed
tags: [decision, skill-routing, token-optimization, maintenance]
impact: medium
reversibility: high
aspect: thinker
neural:
  activation: 0.392
  stage: embryo
  cluster: decisions
---

# Decision: Skill Pruning & Consolidation Plan

## Context

After taxonomizing all 258 installed capabilities across 7 source layers, analysis reveals ~60 redundant or dormant entries inflating the skill listing by ~40%. This noise increases routing ambiguity and wastes tokens on skill enumeration.

## Decision

### Phase 1: Remove Triple-Duplicate Plugin Skills (DONE - 2026-03-09)

Removed 2 of 3 identical plugin namespaces:
- **Kept:** `document-skills@anthropic-agent-skills` (canonical namespace)
- **Removed:** `claude-api@anthropic-agent-skills` (~17 skills, identical)
- **Removed:** `example-skills@anthropic-agent-skills` (~17 skills, identical)

**Impact:** -34 redundant entries, zero capability loss. Backup at `~/.claude/plugins/installed_plugins.json.bak.20260309`.

### Phase 2: Consolidate Review Skills (Short-term)

| Current | Action |
|---------|--------|
| `code-review:code-review` | Remove (subset of `pr-review-toolkit:review-pr`) |
| `bmad-gds-code-review` | Disable unless game project active |

### Phase 3: Disable Dormant GDS Skills (When No Game Project)

The GDS module adds ~20 commands + 7 agent personas that are irrelevant unless actively building a game. Recommend a "game mode" toggle:
- Default: GDS commands hidden from routing
- When game project detected (e.g., `_bmad/gds/` populated): auto-enable

### Phase 4: Evaluate Low-Signal Plugins

| Plugin | Recommendation |
|--------|----------------|
| `ralph-loop:*` | Remove if unused after 30 days |
| `sentry:*` | Keep dormant; auto-enable when Sentry DSN configured |
| `hookify:writing-rules` | Remove (covered by `hookify:hookify`) |

## Expected Impact

- **Token savings:** ~60 fewer entries in skill listing = reduced enumeration noise
- **Routing clarity:** Fewer ambiguous overlaps = faster, more accurate skill selection
- **Reversibility:** All removals are plugin uninstalls or command renames — fully reversible

## Alternatives Considered

1. **Do nothing** — Accept the noise. Rejected: token costs compound across every session.
2. **Merge all content skills into one namespace** — Would require plugin refactoring. Deferred.
3. **Dynamic loading based on project type** — Best long-term solution but requires infrastructure. Deferred to Phase 3.

## Related

- [[skill-taxonomy-7-layer-architecture]]
- [[skill-routing-decision-tree]]
- Full analysis: `_bmad-output/planning-artifacts/research/technical-skills-taxonomy-research-2026-03-07.md`
