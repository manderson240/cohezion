---
title: Skill Keyword Matching Is Broad: Invocation Triggers on Weak Matches
date: 2026-02-23
severity: MEDIUM
category: agent-workflow
tags: [skills, claude-code, keyword-matching, agent-workflow]
status: validated
---

# Lesson: Skill Keyword Matching Is Broad: Invocation Triggers on Weak Matches

## Context

Claude Code skill invocation matches on broad keyword patterns. Skills intended for specific contexts can trigger on loosely related user requests, causing inappropriate skill activation.

## Core Learning

**Skill trigger patterns must be specific and exclusive. Broad keywords cause unintended invocations that disrupt workflow.**

### Pattern
```markdown
# BAD trigger description (too broad)
Use when: user mentions "review" or "check"

# GOOD trigger description (specific and exclusive)
Use ONLY when: user explicitly says "/security-review" or asks to
"check for security vulnerabilities" in code. Do NOT trigger for
general code reviews, PR reviews, or quality reviews.
```

## Recommendations

### Do
- Include explicit exclusions in skill trigger descriptions
- Use slash command prefixes (/skill-name) for unambiguous invocation

### Don't
- Use single-word triggers ("review", "check", "fix")
- Omit explicit exclusion conditions from trigger descriptions

## Related Concepts

- [[compound-engineering]] - Precise skill triggers enable reliable compound workflows
- [[testing-agent-skills-with-evals]] - The evals framework's "process goals" category measures whether agents invoke the right tools in the right sequence; broad keyword matching is the primary failure mode for process goal eval failures

## Validation

**Discovered**: Feb 2026 in Cohezion skill development
**Status**: Validated
