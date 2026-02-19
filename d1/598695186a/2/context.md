# Session Context

## User Prompts

### Prompt 1

# /spec - Unified Spec-Driven Development

**For new features, major changes, and complex work.** Creates a spec, gets your approval, implements with TDD, and verifies completion - all in one continuous flow.

This command is a **dispatcher** that determines which phase to run and invokes it via `Skill()`.

## ⛔ MANDATORY: /spec = Workflow. No Exceptions.

**When `/spec` is invoked, you MUST follow the spec workflow exactly. The user's phrasing after `/spec` is the TASK DESCRIPTION — it is N...

### Prompt 2

# /spec-plan - Planning Phase

**Phase 1 of the /spec workflow.** Explores the codebase, designs an implementation plan, verifies it, and gets user approval.

**Input:** Task description (new plan) or plan path (continue unapproved plan)
**Output:** Approved plan file at `docs/plans/YYYY-MM-DD-<slug>.md`
**Next phase:** On approval → `Skill(skill='spec-implement', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                    ...

### Prompt 3

# /spec-implement - Implementation Phase

**Phase 2 of the /spec workflow.** Reads the approved plan and implements each task using TDD (Red → Green → Refactor).

**Input:** Path to an approved plan file (`Approved: Yes`)
**Output:** All plan tasks completed, status set to COMPLETE
**Next phase:** On completion → `Skill(skill='spec-verify', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                                        ...

### Prompt 4

<task-notification>
<task-id>ad4bf33</task-id>
<status>completed</status>
<summary>Agent "Plan verifier review" completed</summary>
<result>## Plan Verification Complete

**Status: PASS**

The plan at `/home/mike-anderson/dev/cohezion/docs/plans/2026-02-18-system-crash-prevention.md` has been verified against the user's requirements. Here is the assessment:

### Requirement Coverage (All 4 requirements met)

1. **Fix SurrealDB corruption** -- Covered by Tasks 1 and 3. Task 1 stops the crash loop...

### Prompt 5

<task-notification>
<task-id>ab85951</task-id>
<status>completed</status>
<summary>Agent "Plan challenger review" completed</summary>
<result>Findings written successfully to `/home/mike-anderson/.pilot/sessions/default/findings-plan-challenger.json`.

## Plan Challenger Summary

I performed an adversarial review of the system crash prevention plan, examining the actual system state (MANIFEST file contents, .env file, service files, systemd version, code dependencies) to validate or challenge th...

### Prompt 6

I ran them

### Prompt 7

Done

### Prompt 8

# /spec-verify - Verification Phase

**Phase 3 of the /spec workflow.** Runs comprehensive verification: tests, process compliance, code review, program execution, E2E tests, and edge case testing.

**Input:** Path to a plan file with `Status: COMPLETE`
**Output:** Plan status set to VERIFIED (success) or looped back to implementation (failure)
**On success:** Workflow complete
**On failure:** → `Skill(skill='spec-implement', args='<plan-path>')` to fix issues

---

## ⛔ KEY CONSTRAINTS (Rul...

### Prompt 9

We don't want to just vacuum.  The journals are our agents' experiences.  It's what we're using to build our universes.

### Prompt 10

Did we really lose all of todays?  There's no rollbacks?

### Prompt 11

commit this

