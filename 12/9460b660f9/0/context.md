# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Auto-lint Hook for Python File Edits

## Context

After reviewing `~/.claude/settings.json` and `.claude/settings.json`, the setup is mature but missing automatic lint enforcement. Currently, `ruff` violations in edited Python files are only caught if explicitly run or tests are invoked. A `PostToolUse` hook on `Edit|Write|MultiEdit` that runs `ruff check --fix` on changed `.py` files will silently maintain code quality with zero friction.

Adding to **g...

