# /learn - Extract Reusable Knowledge

Evaluates the current session for extractable knowledge and saves it as a reusable skill or note.

## When This Is Useful

| Trigger | Example |
|---------|---------|
| Non-obvious debugging | Spent 10+ min investigating; solution wasn't in docs |
| Misleading errors | Error pointed the wrong direction; found real cause |
| Workarounds | Found a creative solution to a limitation |
| Undocumented tool integration | Figured out how to use an API in an undocumented way |
| Repeatable workflow | Multi-step task that will recur |

**If the session has none of these, output nothing and exit.**

## Evaluation

Ask yourself:
1. Was there a non-obvious discovery in this session?
2. Would this session's solution be hard to rediscover next time?
3. Would a repeatable workflow save time?

If **all three** are "no" → exit silently.

## Extraction Steps

1. **Name it:** Short, descriptive title (e.g., "Reading Claude Code session JSONL for context estimation")
2. **Summarize the problem:** What was unclear or hard?
3. **Document the solution:** Steps, commands, code snippets
4. **Note the context:** When does this apply? What are the prerequisites?
5. **Save it:**

**As a vault note:**
```bash
# Create a pattern note
touch patterns/<kebab-case-name>.md
```

```yaml
---
title: <Title>
date: YYYY-MM-DD
tags: [pattern, <domain>]
---

## Problem
<What was unclear or hard>

## Solution
<Steps, code, commands>

## When to Use
<Conditions that trigger this pattern>

## Caveats
<Limitations, edge cases>
```

**As a skill** (if it's a repeatable workflow):
```
.claude/commands/<name>.md
```

## Output

Tell the user:
- What was extracted
- Where it was saved
- Why it's worth keeping
