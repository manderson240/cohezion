# Session Context

## User Prompts

### Prompt 1

# Debug Skill

Help the user debug an issue they're encountering in this current Claude Code session.

## Session Debug Log

The debug log for the current session is at: `/home/mike-anderson/.claude/debug/a96c8197-b434-4886-8c97-747f06d4e705.txt`

Total lines: 275

### Last 20 lines

```
2026-02-20T03:00:25.957Z [DEBUG] High write ratio: blit=468, write=558 (54.4% writes), screen=18x78
2026-02-20T03:00:25.982Z [DEBUG] High write ratio: blit=468, write=558 (54.4% writes), screen=18x78
2026-02-20T...

### Prompt 2

# /spec - Unified Spec-Driven Development

**For new features, major changes, and complex work.** Creates a spec, gets your approval, implements with TDD, and verifies completion - all in one continuous flow.

This command is a **dispatcher** that determines which phase to run and invokes it via `Skill()`.

## ⛔ MANDATORY: /spec = Workflow. No Exceptions.

**When `/spec` is invoked, you MUST follow the spec workflow exactly. The user's phrasing after `/spec` is the TASK DESCRIPTION — it is N...

### Prompt 3

# /spec-plan - Planning Phase

**Phase 1 of the /spec workflow.** Explores the codebase, designs an implementation plan, verifies it, and gets user approval.

**Input:** Task description (new plan) or plan path (continue unapproved plan)
**Output:** Approved plan file at `docs/plans/YYYY-MM-DD-<slug>.md`
**Next phase:** On approval → `Skill(skill='spec-implement', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                    ...

