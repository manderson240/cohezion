# Session Context

## User Prompts

### Prompt 1

# /spec - Unified Spec-Driven Development

**For new features, major changes, and complex work.** Creates a spec, gets your approval, implements with TDD, and verifies completion - all in one continuous flow.

This command is a **dispatcher** that determines which phase to run and invokes it via `Skill()`.

## ⛔ MANDATORY: /spec = Workflow. No Exceptions.

**When `/spec` is invoked, you MUST follow the spec workflow exactly. The user's phrasing after `/spec` is the TASK DESCRIPTION — it is NO...

### Prompt 2

# /spec-plan - Planning Phase

**Phase 1 of the /spec workflow.** Explores the codebase, designs an implementation plan, verifies it, and gets user approval.

**Input:** Task description (new plan) or plan path (continue unapproved plan)
**Output:** Approved plan file at `docs/plans/YYYY-MM-DD-<slug>.md`
**Next phase:** On approval → `Skill(skill='spec-implement', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                     ...

### Prompt 3

# /spec-implement - Implementation Phase

**Phase 2 of the /spec workflow.** Reads the approved plan and implements each task using TDD (Red → Green → Refactor).

**Input:** Path to an approved plan file (`Approved: Yes`)
**Output:** All plan tasks completed, status set to COMPLETE
**Next phase:** On completion → `Skill(skill='spec-verify', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                                             ...

### Prompt 4

# /spec-verify - Verification Phase

**Phase 3 of the /spec workflow.** Runs comprehensive verification: tests, process compliance, code review, program execution, E2E tests, and edge case testing.

**Input:** Path to a plan file with `Status: COMPLETE`
**Output:** Plan status set to VERIFIED (success) or looped back to implementation (failure)
**On success:** Workflow complete
**On failure:** → `Skill(skill='spec-implement', args='<plan-path>')` to fix issues

---

## ⛔ KEY CONSTRAINTS (Rule...

### Prompt 5

<task-notification>
<task-id>br5me5psk</task-id>
<tool-use-id>toolu_01U2KeuxQ9Adcs8xCvWpcpAd</tool-use-id>
<output-file>/tmp/claude-1000/-home-mike-anderson-dev-cohezion/tasks/br5me5psk.output</output-file>
<status>completed</status>
<summary>Background command "Run both research test files and check results" completed (exit code 0)</summary>
</task-notification>
Read the output file to retrieve the result: /tmp/claude-1000/-home-mike-anderson-dev-cohezion/tasks/br5me5psk.output

### Prompt 6

<task-notification>
<task-id>btlk8icwn</task-id>
<tool-use-id>toolu_011Yq5YYYXnLtaMQooNFT25k</tool-use-id>
<output-file>/tmp/claude-1000/-home-mike-anderson-dev-cohezion/tasks/btlk8icwn.output</output-file>
<status>completed</status>
<summary>Background command "Final run of both research test files" completed (exit code 0)</summary>
</task-notification>
Read the output file to retrieve the result: /tmp/claude-1000/-home-mike-anderson-dev-cohezion/tasks/btlk8icwn.output

### Prompt 7

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

