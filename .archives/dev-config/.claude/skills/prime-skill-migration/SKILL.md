---
name: prime-skill-migration
description: Use when migrating Cohezion PRIME skills to Anthropic spec, adding
  YAML frontmatter to skill files, or when user mentions "migrate skills",
  "add frontmatter", "skill upgrade", or "PRIME migration".
---

# PRIME Skill Migration

Repeatable workflow for adding Anthropic-spec YAML frontmatter to Cohezion's
flat-file PRIME skills in `src/cohezion/skills/`.

## Status

- **Migrated:** 18 skills (have `---` frontmatter block)
- **Remaining:** ~72 skills (no frontmatter)
- Check live: `grep -rL "^---" src/cohezion/skills/*PRIME*.md | wc -l`

## YAML Frontmatter Template

Prepend this block before the existing `# SKILL:` content:

```yaml
---
name: kebab-case-name
description: |
  [What it does]. Use when [trigger conditions / user mentions X].
  Key capabilities: [list].
metadata:
  version: "1.0"
  legacy-name: ORIGINAL_PRIME_NAME
---
```

## Description Formula (Anthropic Spec)

`[What it does] + [When to use it] + [Key capabilities]`

- Max 1024 characters
- Include exact trigger phrases users would say
- No reserved words: avoid "claude", "anthropic", no XML brackets in name
- Name = kebab-case of the PRIME concept (e.g., `BATCHING_PROTOCOL_PRIME` → `batching-protocol`)

## Process

1. **Read** the PRIME skill file — understand its purpose and domain
2. **Draft name** — kebab-case, no reserved words, descriptive
3. **Draft description** — use the formula, include trigger phrases, <1024 chars
4. **Prepend** the frontmatter block before the existing `# SKILL:` heading
5. **Verify** — `grep "^name:" src/cohezion/skills/*.md | head -20`

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Name uses underscores | Use hyphens: `batching-protocol` not `batching_protocol` |
| Description too long | Cut to <1024 chars; focus on triggers, not full explanation |
| Missing `legacy-name` | Always include original filename for traceability |
| Frontmatter after content | Must be the very first thing in the file |

## Quick Reference

Already migrated (don't re-do):
`compound-engineering`, `testing`, `security-guardrails`, `flume-methodology`,
`token-efficiency`, `team-orchestration`, `reliability`, `self-healing`,
`model-routing`, `semantic-caching`, `capability-registry`,
`computational-relativity`, `dissipative-structures`, `hiho-stability`,
`holographic-flume`, `noether-conservation`, `physics-lineage`,
`universe-simulation-persistence`
