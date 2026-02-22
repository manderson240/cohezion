# /sync - Sync Rules and Skills with Codebase

Explores the current codebase and updates `.claude/rules/` and `.claude/commands/` to reflect the actual project structure, conventions, and tooling.

## When to Use

- After adding or changing significant infrastructure
- When rules reference outdated commands, paths, or tools
- When onboarding this project to a new machine
- After a major refactor that changes conventions

## Steps

### 1. Explore Current State

Read these files to understand what exists:
- `.claude/rules/*.md` — current rules
- `.claude/commands/*.md` — current skills/commands
- `CLAUDE.md` — project-level instructions
- `tools/cohezion-engine/` — CLI tool structure
- `.claude/hooks/` — hook scripts

### 2. Explore Codebase

Using `vexor search` and Grep:
- What are the main modules and their purposes?
- What CLI commands exist (`cz --help`)?
- What test patterns are used?
- What conventions are established (naming, formatting)?

### 3. Identify Gaps

For each rule file, check:
- Are tool references accurate? (correct binary paths, correct commands)
- Are directory paths correct?
- Are any commands documented that no longer exist?
- Are new commands or workflows missing documentation?

### 4. Update Rules

For each gap found:
- Update the relevant `.claude/rules/*.md` file
- Add new rule files if a major new system was added
- Remove or mark deprecated any outdated content

### 5. Update Skills

For each command file:
- Verify the steps are still accurate
- Update command references to match current CLI

### 6. Update CLAUDE.md (if needed)

Update the project's CLAUDE.md if major infrastructure changed:
- New services or ports
- New tooling or conventions
- New directories

### 7. Report

Summarize:
- Files updated
- New files created
- Items flagged as potentially outdated (but not auto-changed)

## Rules

- Do NOT auto-delete rule files — flag them for review instead
- Verify changes are accurate before writing (read existing content first)
- Keep rules concise — tables and examples over prose
