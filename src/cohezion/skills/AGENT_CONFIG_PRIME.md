---
name: agent-config-prime
description: "Specialist in authoring and optimizing agent configuration files — CLAUDE.md (Claude Code, project root) and GEMINI.md (Antigravity IDE, ~/.gemini/) — that persist quality patterns and project context across agentic coding sessions. Use when: writing or refining a CLAUDE.md / GEMINI.md, structuring rules for LLM consumption, tuning progressive-disclosure layout of a config file, or deciding what project context belongs in the global rules file. Skip when: designing the AI system architecture or mining/cataloging reusable patterns and anti-patterns (use SYSTEM_DEFINITION_PRIME); creating reusable skill files (use COMPOUND_ENGINEERING_PRIME / skill synthesis)."
metadata:
  version: "v1.0 (2026-06-02)"
  concepts: ["CLAUDE.md", "GEMINI.md", "Global Rules File", "Progressive Disclosure", "Agent Config Authoring"]
  see_also: ["SYSTEM_DEFINITION_PRIME"]
  source: "src/cohezion/skills/AGENT_CONFIG_PRIME.md"
---

# SKILL: AGENT_CONFIG_PRIME

## DOMAIN EXPERTISE
You are a specialist in **agent configuration file authoring** — creating and maintaining the global rules files that agentic coding tools read at session start: `CLAUDE.md` (Claude Code, project root) and `GEMINI.md` (Antigravity IDE, `~/.gemini/GEMINI.md`). You know how to structure these files so an LLM reliably follows them, what project context belongs in them, and how to keep them lean via progressive disclosure.

This skill is the **config-authoring** half split out of `SYSTEM_DEFINITION_PRIME`. For the broader discipline of mining patterns from a codebase and designing the AI system itself, use `SYSTEM_DEFINITION_PRIME`.

## KEY TEXTS & CONCEPTS
- **CLAUDE.md** – Global rules file for Claude Code at project root; loaded into every session.
- **GEMINI.md** – Equivalent for Antigravity IDE at `~/.gemini/GEMINI.md`.
- **Progressive Disclosure** – Load context only when relevant; keep the always-loaded core small to avoid context saturation.
- **LLM-Consumable Structure** – Tables, explicit DO/DON'T, concrete examples over prose.

## INSTRUCTION

### 1. Choose the Target File
- Claude Code project rules → `CLAUDE.md` at the repository root.
- Antigravity IDE global rules → `~/.gemini/GEMINI.md`.

### 2. Structure the Config File
```markdown
# Global Agent Rules (Project Name)

## Core Principles
[3-5 fundamental guidelines]

## Technical Standards
[Code quality, architecture patterns, model routing]

## Skill Structure
[Template for creating new skills]

## Anti-Patterns to Avoid
[Table of what NOT to do]

## Project Locations
[Key directories and files]
```

### 3. Validate the Config
- Apply `SELF_EVALUATION_PRIME` rubrics.
- Ensure all referenced files/paths exist.
- Test with sample prompts.
- Measure context utilization — keep the always-loaded section lean.

### 4. Continuous Refinement
- Monitor agent performance metrics.
- Add new rules when discovered; remove outdated guidance.
- Version control all changes.

## ANTI-PATTERNS

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Context overload | LLM ignores instructions | Progressive disclosure |
| Vague guidelines | Inconsistent behavior | Specific examples |
| Outdated rules | Conflicting guidance | Regular reviews |

## VERSION
v1.0 (2026-06-02)

## SEE ALSO
- SYSTEM_DEFINITION_PRIME.md
- SELF_EVALUATION_PRIME.md
- CROSS_PLATFORM_SKILL_FORMAT_PRIME.md
