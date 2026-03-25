---
title: "Patterns — Directory Index"
purpose: "Reusable solutions, runbooks, and proven approaches for recurring problems"
type: directory-index
aspect: thinker
neural:
  activation: 0.37
  stage: growing
  synapse_in: 0
  synapse_out: 5
---

# Patterns

**Purpose:** Document repeatable solutions to common problems. Each pattern includes problem context, solution, code examples, and when to apply.

**Put here when:** You discover a reusable approach, workflow, or code pattern that solves a recurring problem. Must be validated (not speculative).

**Naming:** Kebab-case descriptive name (e.g., `safe-file-split-checklist.md`). No date prefix.

**Required frontmatter:**
- `title` — Pattern name
- `date` — Creation date (YYYY-MM-DD)
- `tags` — Array of tags (`[pattern, topic-area]`)

**Template:** Yes — `_template.md` (includes Problem/Solution/Code Example/When to Use sections)

**Current count:** 89 notes

**Key notes:**
- [[surrealdb-agent-context-schema]] — Schema design for agent context in SurrealDB
- [[implementation-first-infrastructure-later]] — Build working code before abstracting infrastructure
- [[phase1-production-validation-runbook]] — Step-by-step production validation procedure

**Related MOC:** [[MOC-compound-engineering]], [[MOC-platform-infrastructure]]
