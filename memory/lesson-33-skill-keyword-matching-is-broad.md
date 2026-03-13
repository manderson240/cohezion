---
title: Skill Keyword Matching Is Broad: Invocation Triggers on Weak Matches
date: 2026-02-23
severity: MEDIUM
category: agent-workflow
cost_of_forgetting: "Wrong skill invoked for user requests; workflow disrupted by inappropriate skill activation"
tags: [skills, claude-code, keyword-matching, agent-workflow]
status: validated
aspect: knower
neural:
  activation: 0.7
  stage: growing
  synapse_in: 6
  synapse_out: 4
---

# Lesson: Skill Keyword Matching Is Broad: Invocation Triggers on Weak Matches

## Context

During Cohezion skill development in February 2026, several custom skills were created for specific workflows (security review, spec planning, code auditing). These skills had trigger descriptions using broad keywords like "review" or "check." The result was that asking Claude Code to "review this PR" would trigger the security review skill instead of a general code review. Asking to "check the tests" would trigger the code audit skill instead of running `pytest`.

## Problem

Claude Code's skill invocation system matches user requests against skill trigger descriptions using keyword similarity. This creates false positives:

1. **Broad keywords match too many requests**: A skill with trigger "review" matches "review this PR," "review these changes," "review the architecture," and "let me review what happened" -- all very different intents.
2. **Missing exclusions**: Without explicit exclusion conditions, the skill system cannot distinguish between intended and unintended matches.
3. **Workflow disruption**: An incorrectly triggered skill changes the agent's behavior (loading skill instructions, following skill-specific procedures), derailing the user's actual request.
4. **User confusion**: The user asks for one thing and gets something different. They may not immediately recognize that a skill was invoked.

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

## Solution

Skill trigger descriptions were rewritten with three components:

1. **Specific trigger**: Name the exact command or phrase that should activate the skill (e.g., `/security-review` or "check for security vulnerabilities")
2. **Explicit exclusions**: List common similar requests that should NOT trigger the skill (e.g., "Do NOT trigger for general code reviews")
3. **Slash command prefix**: Use `/skill-name` as the primary invocation mechanism for unambiguous activation

## Prevention

- **Use slash commands as primary triggers**: `/security-review` is unambiguous; "review" is not
- **Include explicit exclusion list**: For every trigger condition, list 2-3 similar requests that should not trigger
- **Test with adversarial prompts**: Try common requests that share keywords with the skill and verify they do not trigger it
- **Keep trigger descriptions narrow**: It is better to miss a legitimate trigger than to false-positive on an unrelated request

## Cost of Forgetting

- **Wrong skill activated**: User gets security review when they wanted a code review
- **Workflow disruption**: Skill instructions override normal agent behavior
- **User trust erosion**: Unpredictable skill activation makes the tool feel unreliable

## Recommendations

### Do
- Include explicit exclusions in skill trigger descriptions
- Use slash command prefixes (/skill-name) for unambiguous invocation

### Don't
- Use single-word triggers ("review", "check", "fix")
- Omit explicit exclusion conditions from trigger descriptions

## Related Concepts

- [[compound-engineering]] - Precise skill triggers enable reliable compound workflows
- [[testing-agent-skills-with-evals]] - process goals measure correct tool invocation; broad matching is the primary failure mode
- [[prompt-engineering]] - skill trigger descriptions are a form of prompt engineering for tool selection
- [[tool-use]] - skill invocation is a tool-use decision; precision in triggers prevents tool misuse

## Validation

**Discovered**: Feb 2026 in Cohezion skill development
**Impact**: Multiple skill invocation false positives eliminated by adding exclusions and slash command prefixes
**Status**: Validated
