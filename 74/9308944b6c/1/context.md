# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# /learn: Extract Knowledge from Anthropic Skill Architecture Research Session

## Context

The previous session researched Anthropic's official 29-page "Complete Guide to Building Skills for Claude" and applied its recommendations to Cohezion's skill infrastructure. Two reusable patterns emerged that are worth capturing as project skills:

1. **PRIME skill migration workflow** — A repeatable, non-obvious workflow for upgrading Cohezion's 143 flat-file PRIME ski...

### Prompt 2

Base directory for this skill: /home/mike-anderson/.claude/plugins/cache/claude-plugins-official/superpowers/4.3.1/skills/writing-skills

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

**Personal skills live in agent-specific directories (`~/.claude/skills` for Claude Code, `~/.agents/skills/` for Codex)** 

You write test cases (pressure scenarios with subagents), watch them fail (baseline behavior), write the skill (documentat...

### Prompt 3

Provide a code review for the given pull request.

To do this, follow these steps precisely:

1. Use a Haiku agent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from you from earlier. If so, do not proceed.
2. Use another Haiku agent to give you a list of file paths to (but not the contents of) any relevant CLAUDE.md files from the c...

