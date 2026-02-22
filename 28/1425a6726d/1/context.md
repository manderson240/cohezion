# Session Context

## User Prompts

### Prompt 1

Multiperspective Adversarially Review Workflow complete! Plan status: VERIFIED                                                                                                                                                                    
                                                                                                                                                                                                              
  Summary                                         ...

### Prompt 2

I need you to adversarially review those claims

### Prompt 3

Base directory for this skill: /home/mike-anderson/dev/cohezion/.claude/skills/adversarial-claim-validation

# Adversarial Claim Validation

## Problem

When reporting work completion with metrics ("148 tests pass", "0 type errors",
"linting clean"), claims can be inaccurate due to:
- Testing wrong scope (all files vs new files only)
- Using stale cached results instead of fresh verification
- Mixing pre-existing issues with new code quality
- Over-generalizing partial verification

This erodes ...

### Prompt 4

Run a development retrospective that flows insights back into core files.

This is the compound engineering feedback loop. It ensures that session learnings don't just accumulate in knowledge_graph/ — they propagate back into the files that govern future behavior.

## Steps

### 1. Audit Current State
- Read `REDACTED.md` and `REDACTED.md`
- Read `CLAUDE.md`, `README.md`, and `memory/MEMORY.md`
- Identify: new learnings since last retrospect, stale/d...

### Prompt 5

1. Find in the repo history and restore it.  2. Fix them in a background session.  3. Fix them in a background session.

### Prompt 6

<task-notification>
<task-id>ad98827</task-id>
<status>completed</status>
<summary>Agent "Fix universe test collection errors" completed</summary>
<result>That's just a test name containing "error", not an actual error. The fix is working -- 63 tests collected, 0 collection errors.

**Summary of the fix:**

The single change was in `/home/mike-anderson/dev/cohezion/src/cohezion/universe/sandbox.py`:

1. **Lines 16-17** -- Changed the top-level `docker` import from a hard import to a try/except t...

### Prompt 7

<task-notification>
<task-id>a221a6b</task-id>
<status>completed</status>
<summary>Agent "Fix ruff auto-fixable errors" completed</summary>
<result>All test failures are due to a pre-existing `ModuleNotFoundError: No module named 'matplotlib'` -- this is a missing dependency issue, completely unrelated to the ruff fixes.

Here is a summary of what was done:

**Ruff auto-fix results:**
- **215 safe fixes applied** across `src/cohezion/`
- **991 remaining errors** -- all require manual fixes or `-...

### Prompt 8

Run a development retrospective that flows insights back into core files.

This is the compound engineering feedback loop. It ensures that session learnings don't just accumulate in knowledge_graph/ — they propagate back into the files that govern future behavior.

## Steps

### 1. Audit Current State
- Read `REDACTED.md` and `REDACTED.md`
- Read `CLAUDE.md`, `README.md`, and `memory/MEMORY.md`
- Identify: new learnings since last retrospect, stale/d...

### Prompt 9

fix them

### Prompt 10

Run a development retrospective that flows insights back into core files.

This is the compound engineering feedback loop. It ensures that session learnings don't just accumulate in knowledge_graph/ — they propagate back into the files that govern future behavior.

## Steps

### 1. Audit Current State
- Read `REDACTED.md` and `REDACTED.md`
- Read `CLAUDE.md`, `README.md`, and `memory/MEMORY.md`
- Identify: new learnings since last retrospect, stale/d...

### Prompt 11

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Phas...

