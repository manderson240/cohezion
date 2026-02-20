# Session Context

## User Prompts

### Prompt 1

# /sync - Sync Project Rules & Skills

**Sync custom rules and skills with the current state of the codebase.** Reads existing rules/skills, explores code patterns, identifies gaps, updates documentation, and creates new skills when workflows are discovered.

---

## 📋 TABLE OF CONTENTS

| Phase                                                    | What Happens                                 |
| -------------------------------------------------------- | ---------------------------------------...

### Prompt 2

# /vault - Team Vault Management

**Share and install AI assets (rules, commands, skills, agents, hooks, MCP configs) across your team using sx.**

sx is a team asset manager that uses a private Git repository as a shared vault. Assets are versioned automatically and can be scoped globally or per-repository.

---

## Step 0: Check Prerequisites

1. **Check sx is installed:**

   ```bash
   which sx 2>/dev/null && sx --version
   ```

   If not installed: inform user sx is required for Team Vault...

### Prompt 3

What are we trying to accomplish here?

### Prompt 4

I thought we were referring to this Obsidian vault?

### Prompt 5

# /spec - Unified Spec-Driven Development

**For new features, major changes, and complex work.** Creates a spec, gets your approval, implements with TDD, and verifies completion - all in one continuous flow.

This command is a **dispatcher** that determines which phase to run and invokes it via `Skill()`.

## ⛔ MANDATORY: /spec = Workflow. No Exceptions.

**When `/spec` is invoked, you MUST follow the spec workflow exactly. The user's phrasing after `/spec` is the TASK DESCRIPTION — it is N...

### Prompt 6

# /spec-plan - Planning Phase

**Phase 1 of the /spec workflow.** Explores the codebase, designs an implementation plan, verifies it, and gets user approval.

**Input:** Task description (new plan) or plan path (continue unapproved plan)
**Output:** Approved plan file at `docs/plans/YYYY-MM-DD-<slug>.md`
**Next phase:** On approval → `Skill(skill='spec-implement', args='<plan-path>')`

---

## ⛔ KEY CONSTRAINTS (Rules Summary)

| #   | Rule                                                    ...

