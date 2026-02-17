# Session Context

## User Prompts

### Prompt 1

[SPEC] Continue workflow from previous session. IMMEDIATELY use the Skill tool: Skill(skill="spec", args="--continue docs/plans/2026-02-17-autonomous-repo-management.md") Do NOT do anything else first.

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

### Prompt 4

Stop hook feedback:
[uv run python "${CLAUDE_PLUGIN_ROOT}/hooks/spec_stop_guard.py"]: warning: `VIRTUAL_ENV=/home/mike-anderson/.cache/uv/builds-v0/.tmpyeB1ec` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
[0;31m⛔ /spec workflow active - cannot stop without user interaction[0m
[0;33mActive plan: /home/mike-anderson/dev/cohezion/docs/plans/2026-02-17-autonomous-repo-management.md (Status: PENDING)[0m
[0;33m�...

### Prompt 5

# /spec-implement - Implementation Phase

**Phase 2 of the /spec workflow.** Reads the approved plan and implements each task using TDD (Red → Green → Refactor).

**Input:** Path to an approved plan file (`Approved: Yes`)
**Output:** All plan tasks completed, status set to COMPLETE
**Next phase:** On completion → `Skill(skill='spec-verify', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                                        ...

