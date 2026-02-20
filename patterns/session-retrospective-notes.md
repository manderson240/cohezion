---
title: "Session Retrospective Notes"
date: "2026-02-07"
tags: [pattern, workflow, knowledge-capture, vault-automation]
---

## Problem

At the end of an AI-assisted engineering session, valuable context — architectural decisions made, experiments run, concepts clarified — exists only in the conversation transcript. Once the session ends and the context window is gone, that knowledge is lost unless explicitly captured. Manually writing up session notes is tedious and often skipped.

## Solution

Before ending a session, run a **structured retrospective pass** that creates permanent vault notes for each significant accomplishment. For each item:

1. **Classify** — Is it a decision, experiment, pattern, or concept?
2. **Match the template** — Use the target directory's `_template.md` frontmatter schema
3. **Cross-link** — Add `[[wiki-links]]` between related notes from the same session and to existing vault content
4. **Write from what happened** — Use the actual session transcript as source material, not aspirational descriptions

A single session typically produces 2-5 notes across directories. Creating them in one batch at session end is more efficient than writing incrementally.

## Code Example

Prompt pattern for the retrospective pass:

```markdown
Create session retrospective notes for the following accomplishments:

1. [Decision] We chose X architecture because Y → `decisions/YYYY-MM-DD-slug.md`
2. [Experiment] We tested hypothesis X, result was Y → `experiments/YYYY-MM-DD-slug.md`
3. [Pattern] We discovered reusable approach X → `patterns/slug.md`
4. [Concept] We defined/clarified X → `concepts/slug.md`

Requirements:
- Match each directory's _template.md frontmatter schema
- Cross-link notes with [[wiki-links]]
- Content reflects what actually happened (reference transcript if needed)
```

## When to Use

- **End of every non-trivial session** — If the session produced decisions, discoveries, or reusable approaches, capture them
- **After multi-step work** — Sessions involving exploration → decision → implementation are prime candidates
- **When the [[compound-engineering]] vault would benefit** — Ask: "Would future-me or future-agents benefit from knowing what happened here?"
- **Skip for trivial sessions** — Quick bug fixes or single-file edits don't need retrospectives

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[surrealdb-query-driven-analysis]]
- [[agent-logs-vault-schema]]
