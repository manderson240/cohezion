---
name: compound-loop-gate-agent
description: |
  Write a Claude Code subagent (.claude/agents/*.md) that acts as a gate in the
  Cohezion compound engineering loop. Use when: (1) adding a new quality/security/
  performance gate to the compound loop, (2) user asks for a new specialist role
  (CSO, canary, performance-engineer, etc.), (3) wiring a gate before SkillRefiner,
  SkillConsensusVoter, or any compound loop phase. Produces a .md file with YAML
  frontmatter (name/description/model/tools), structured PASS/BLOCK verdict output,
  and a Compound Loop Integration section.
author: Claude Code
version: 1.0.0
tags: [compound-engineering, agents, gating, cohezion]
---

# Compound Loop Gate Agent Pattern

## Problem

The Cohezion compound loop (SkillRefiner → SkillConsensusVoter → deploy) needs quality gates at specific phases. Each gate must be a first-class Claude Code subagent: invokable via `Agent(subagent_type="<name>")`, with the right tool restrictions, model tier, and a binary PASS/BLOCK verdict.

## Key Non-Obvious Facts

- **Location**: `.claude/agents/<name>.md` — NOT `.claude/skills/`. Files here register as `subagent_type` values that appear in the agent types list.
- **`tools` key**: A list under YAML frontmatter. Restrict aggressively — security reviewers don't need Write.
- **`model` key**: Pick by gate role: `claude-haiku-4-5` for monitoring (speed), `sonnet` for analysis/security/benchmarks (reasoning).
- **Description field**: Must include "Use when:" conditions — this drives the agent type system's trigger matching.
- **Verdict format**: Always end with `**Compound Loop Gate**: PASS | BLOCK`. The orchestrator checks this line.

## YAML Frontmatter Template

```yaml
---
name: <gate-name>
description: |
  <One sentence what it does.>
  Use when: <exact conditions — method names, file paths, trigger events>.
  <Output/verdict format sentence.>
model: <haiku for monitoring | sonnet for analysis>
tools:
  - Read
  - <Bash if runtime checks needed>
  - <Glob if file scanning needed>
---
```

**Tool selection guide:**
| Gate type | Tools |
|-----------|-------|
| Security audit (CSO) | Read, Glob — never Bash, never Write |
| Health monitor (canary) | Read, Bash |
| Benchmark regression | Read, Bash |
| Code review | Read, Glob |
| Schema validator | Read, Bash |

## Output Format (mandatory)

Every gate agent must produce this structure at the end of its response:

```
## <Gate Name> Report

**Scope**: [what was checked]
**Verdict**: PASS | WARN | BLOCK

| Check | Status | Detail |
|-------|--------|--------|
| ... | ✅ PASS | ... |
| ... | ⚠️ WARN | ... |
| ... | 🚫 BLOCK | ... |

**[Component] Gate**: PASS | BLOCK
```

- `BLOCK` = loop must not advance. The calling orchestrator stops.
- `WARN` = advance with alert surfaced to user.
- `PASS` = clear.

## Compound Loop Integration Section

Every gate agent body must include a "## Compound Loop Integration" section specifying:

```markdown
## Compound Loop Integration

- **Pre-SkillRefiner**: [if this gate runs before skill updates are committed]
- **Post-SkillConsensusVoter**: [if this gate runs after multi-agent validation]
- **Post-submit**: [if this gate checks a deployment outcome]
- **Direct invocation**: `Agent(subagent_type="<name>", prompt="<context>")`
- **Hook trigger**: [which PostToolUse or PreToolUse hook fires this agent]
```

## Three Reference Implementations (Built 2026-06-22)

| File | Model | Tools | Gate position | Trigger |
|------|-------|-------|---------------|---------|
| `.claude/agents/cso.md` | sonnet | Read, Glob | Pre-SkillRefiner | Skills touching api/, compound/, MCP servers |
| `.claude/agents/canary.md` | haiku | Read, Bash | Post-submit | After `kaggle competitions submit`, SkillConsensusVoter commit |
| `.claude/agents/performance-engineer.md` | sonnet | Read, Bash | Pre-deploy | Changes to triune_orchestrator, cost_aware_router, semantic_cache |

## Workflow

1. Determine gate position in the loop (pre-skill, post-deploy, etc.)
2. Choose model: monitoring → haiku; analysis → sonnet
3. Choose tools: read-only (security) or read+bash (health/benchmarks)
4. Write YAML frontmatter with specific "Use when:" trigger conditions
5. Write body: threat model / health checks / benchmarks as bash snippets
6. End with structured verdict table + `**Compound Loop Gate**: PASS | BLOCK`
7. Add "## Compound Loop Integration" section with invocation patterns

## Verification

After writing:
```bash
# Confirm the agent type appears in the system
grep "^name:" .claude/agents/<name>.md
# Test invocation pattern
# Agent(subagent_type="<name>", prompt="test run")
```
