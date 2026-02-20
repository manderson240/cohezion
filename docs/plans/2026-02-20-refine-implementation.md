# Refine Implementation with Lasting Solutions

Created: 2026-02-20
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Fix settings bloat, eliminate recurring warnings, and add preventive automation so these issues don't return.

**Architecture:** Three-pronged approach: (1) curate wildcard permission patterns from the 292 accumulated rules, (2) reset settings.local.json to clean state, (3) add a Claude Code hook + maintenance script to prevent re-accumulation and provide periodic cleanup.

**Tech Stack:** Bash scripting, Claude Code hooks (JSON), Python for the cleanup script.

## Scope

### In Scope

- Curate wildcard permission patterns from 292 accumulated rules in `settings.local.json`
- Add curated patterns to user-level `~/.claude/settings.json` (so they apply globally)
- Reset project-level `settings.local.json` to empty permissions
- Fix YAML frontmatter parse warning in `~/.claude/commands/spec.md`
- Resolve `SONATYPE_GUIDE_TOKEN` warning (disable unused plugin or set token)
- Create a maintenance script to clean `settings.local.json` on demand
- Add a Claude Code hook that warns when `settings.local.json` exceeds a size threshold

### Out of Scope

- Changes to the 3D graph plugin or MCP server code
- Vault content (papers, decisions, patterns)
- Changes to the `entire` hooks infrastructure
- Modifications to Pilot CLI or its hooks

## Prerequisites

- Access to `~/.claude/settings.json` (user-level)
- Access to `.claude/settings.local.json` (project-level)
- Claude Code must be restarted after settings changes take effect

## Context for Implementer

- **Patterns to follow:** The user settings at `~/.claude/settings.json` already has well-structured wildcard patterns (lines 27-75) like `Bash(cp:*)`, `Bash(git:*)`, etc. New patterns should follow this same format.
- **Key finding:** Claude Code saves the FULL command string as a permission when a user approves it interactively. Pre-defined wildcard patterns prevent this because matching commands don't trigger new saves.
- **The bloat source:** 292 rules accumulated in `.claude/settings.local.json`, including entire Python scripts (up to 16KB each) and multi-page markdown documents stored as heredoc permission strings.
- **Key limitation:** Hooks cannot intercept permission saves — they happen in Claude Code's internal logic after user approval. Prevention must be pattern-based, not hook-based.
- **Important:** The user settings file already has `"Bash"` (bare, line 28) which should match ALL Bash commands. The project `settings.local.json` accumulated rules because project-level permissions are checked separately.

**Gotchas:**
- Settings changes require Claude Code restart to take effect
- The `settings.local.json` is gitignored (personal, not shared)
- The `argument-hint` field in spec.md YAML uses `<>` characters that some YAML parsers choke on

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Curate wildcard patterns and update user settings
- [x] Task 2: Reset project settings.local.json
- [x] Task 3: Fix spec.md YAML frontmatter warning
- [x] Task 4: Resolve SONATYPE_GUIDE_TOKEN warning
- [x] Task 5: Create settings maintenance script
- [ ] Task 6: Add settings size monitoring hook
- [ ] Task 7: Add PreToolUse hook for permission management
- [ ] Task 8: Add PostToolUse hook for settings cleanup

**Total Tasks:** 8 | **Completed:** 5 | **Remaining:** 3

## Implementation Tasks

### Task 1: Curate Wildcard Patterns and Update User Settings

**Objective:** Extract useful general command patterns from the 292 accumulated rules and add them to `~/.claude/settings.json` so they pre-authorize common commands without accumulating one-off entries.

**Dependencies:** None

**Files:**

- Modify: `~/.claude/settings.json`

**Key Decisions / Notes:**

- The user settings already has `"Bash"` (bare) at line 28, which matches all Bash commands. However, this alone doesn't prevent project-level accumulation because `settings.local.json` is a separate scope.
- Add commonly-used command patterns that are NOT already covered: `docker`, `curl`, `node`, `npm`, `npx`, `git`, `systemctl`, `journalctl`, `gh`, `entire`, `pip`, `chmod`, `tee`, `head`, `wc`, `sort`, `du`, `lsof`, `netstat`, `pgrep`, `ss`, `kill`, `lscpu`, `gcloud`
- Also add `mcp-cli` and `vexor` patterns used by the rules system
- Keep the list organized alphabetically within sections

**Definition of Done:**

- [ ] All tests pass (unit, integration if applicable)
- [ ] No diagnostics errors (linting, type checking)
- [ ] `~/.claude/settings.json` contains curated wildcard patterns for all common command categories
- [ ] JSON is valid (parseable by `python3 -c "import json; json.load(open(...))"`)

**Verify:**

- `python3 -c "import json; json.load(open('/home/mike-anderson/.claude/settings.json'))"` — valid JSON
- `grep -c 'Bash(' ~/.claude/settings.json` — shows increased pattern count

### Task 2: Reset Project settings.local.json

**Objective:** Replace the bloated 608KB settings.local.json with a clean file containing only essential project-specific permissions (the `Read` deny rule).

**Dependencies:** Task 1 (patterns must be in place before removing old rules)

**Files:**

- Modify: `/home/mike-anderson/vaults/cohezion-vault/.claude/settings.local.json`

**Key Decisions / Notes:**

- Back up the old file to `/tmp/settings.local.json.bak` before replacing
- Preserve the existing hooks configuration and the `Read(./.entire/metadata/**)` deny rule
- The `permissions.allow` array becomes empty — all needed patterns come from user-level settings

**Definition of Done:**

- [ ] Backup created at `/tmp/settings.local.json.bak`
- [ ] New `settings.local.json` has empty allow array and preserves hooks + deny rules
- [ ] File size under 1KB
- [ ] JSON is valid

**Verify:**

- `wc -c .claude/settings.local.json` — under 1000 bytes
- `python3 -c "import json; d=json.load(open('.claude/settings.local.json')); print(len(d['permissions']['allow']))"` — prints 0

### Task 3: Fix spec.md YAML Frontmatter Warning

**Objective:** Fix the YAML parse error in `~/.claude/commands/spec.md` that produces `[WARN] Failed to parse YAML frontmatter` on startup.

**Dependencies:** None

**Files:**

- Modify: `~/.claude/commands/spec.md`

**Key Decisions / Notes:**

- The `argument-hint` field contains `<task description>` and `<path/to/plan.md>` — angle brackets may be interpreted as YAML tags
- Fix by quoting the value with single or double quotes
- Must not change the semantic meaning

**Definition of Done:**

- [ ] `argument-hint` value is properly quoted in YAML frontmatter
- [ ] No YAML parse errors when validated with a YAML parser
- [ ] Command still functions correctly

**Verify:**

- `python3 -c "import yaml; yaml.safe_load(open('/home/mike-anderson/.claude/commands/spec.md').read().split('---')[1])"` — no errors

### Task 4: Resolve SONATYPE_GUIDE_TOKEN Warning

**Objective:** Eliminate the `[WARN] Missing environment variables in plugin MCP config: SONATYPE_GUIDE_TOKEN` warning that appears multiple times on startup.

**Dependencies:** None

**Files:**

- Modify: `~/.claude/settings.json`

**Key Decisions / Notes:**

- The Sonatype Guide plugin is enabled (`"sonatype-guide@claude-plugins-official": true`) but its required env var is not set
- Since the user hasn't set up this token, the plugin is likely unused — disable it
- Set `"sonatype-guide@claude-plugins-official": false` in `enabledPlugins`

**Definition of Done:**

- [ ] Sonatype Guide plugin disabled in settings
- [ ] No `SONATYPE_GUIDE_TOKEN` warnings in debug log after restart

**Verify:**

- `python3 -c "import json; d=json.load(open('/home/mike-anderson/.claude/settings.json')); print(d['enabledPlugins'])"` — shows sonatype-guide as false

### Task 5: Create Settings Maintenance Script

**Objective:** Create a script that analyzes and cleans `settings.local.json` files by removing rules that are already covered by wildcard patterns in higher-priority settings files.

**Dependencies:** Task 1

**Files:**

- Create: `/home/mike-anderson/.claude/scripts/clean-settings.py`

**Key Decisions / Notes:**

- Script reads user settings patterns, then checks each project `settings.local.json` rule against them
- Rules covered by wildcards are removed
- Rules over a configurable length threshold (default: 200 chars) are removed (these are embedded scripts/docs)
- Script shows what it would remove before doing it (dry-run by default, `--apply` to execute)
- Outputs statistics: total rules, covered rules, oversized rules, remaining rules
- Uses Python (available everywhere, no dependencies)

**Definition of Done:**

- [ ] Script runs without errors: `python3 ~/.claude/scripts/clean-settings.py --help`
- [ ] Dry-run mode shows accurate analysis of current settings
- [ ] `--apply` mode correctly removes covered/oversized rules
- [ ] Script preserves non-permission settings (hooks, deny rules)
- [ ] Script creates backup before modifying

**Verify:**

- `python3 ~/.claude/scripts/clean-settings.py /home/mike-anderson/vaults/cohezion-vault/.claude/settings.local.json` — runs without error, shows analysis

### Task 6: Add Settings Size Monitoring Hook

**Objective:** Add a Claude Code hook that monitors `settings.local.json` size and warns when it exceeds a threshold, reminding the user to run the cleanup script.

**Dependencies:** Task 5

**Files:**

- Create: `/home/mike-anderson/.claude/hooks/check-settings-size.sh`
- Modify: `~/.claude/settings.json` (add hook configuration)

**Key Decisions / Notes:**

- Use a `SessionStart` hook that checks `settings.local.json` size
- Threshold: 10KB (the clean file is ~1KB, so 10KB means significant accumulation)
- Hook outputs a warning message visible to the user at session start
- The hook should be lightweight (< 100ms execution)
- Hook checks all project settings.local.json files in common project directories, or just the current project

**Definition of Done:**

- [ ] Hook script exists and is executable
- [ ] Hook is registered in `~/.claude/settings.json` under `hooks.SessionStart`
- [ ] Hook warns when `settings.local.json` exceeds 10KB
- [ ] Hook runs in < 100ms
- [ ] Warning message includes the cleanup command to run

**Verify:**

- `bash ~/.claude/hooks/check-settings-size.sh` — runs without error
- `ls -la ~/.claude/hooks/check-settings-size.sh` — executable permission set

### Task 7: Add PreToolUse Hook for Permission Management

**Objective:** Add a PreToolUse hook that runs before Bash tool calls and can auto-approve commands matching known safe patterns, reducing the number of interactive permission prompts that create settings.local.json entries.

**Dependencies:** Task 1 (patterns must exist first)

**Files:**

- Create: `/home/mike-anderson/.claude/hooks/pre-bash-check.sh`
- Modify: `~/.claude/settings.json` (add PreToolUse hook)

**Key Decisions / Notes:**

- The hook receives tool input via stdin JSON (includes `tool_name`, `tool_input.command`)
- For Bash tools, the hook can check the command against a local allowlist of safe patterns
- If the command matches a known-safe pattern, the hook exits 0 (allow) — no permission prompt shown, no entry saved to settings.local.json
- If the command doesn't match, the hook exits 0 with no output (pass through to normal permission flow)
- The allowlist is maintained in a simple text file (`~/.claude/hooks/safe-patterns.txt`) for easy editing
- Patterns use shell glob matching (e.g., `docker *`, `npm *`, `git *`)
- The hook must be fast (< 50ms) since it runs on EVERY tool call

**Definition of Done:**

- [ ] Hook script exists and is executable
- [ ] Hook is registered in `~/.claude/settings.json` under `hooks.PreToolUse`
- [ ] Hook correctly reads stdin JSON and extracts command
- [ ] Hook matches commands against safe-patterns.txt
- [ ] Hook runs in < 50ms
- [ ] Safe patterns file is populated with curated patterns from Task 1

**Verify:**

- `echo '{"tool_name":"Bash","tool_input":{"command":"docker ps"}}' | bash ~/.claude/hooks/pre-bash-check.sh` — exits 0
- `time echo '{"tool_name":"Bash","tool_input":{"command":"docker ps"}}' | bash ~/.claude/hooks/pre-bash-check.sh` — under 50ms

### Task 8: Add PostToolUse Hook for Settings Cleanup

**Objective:** Add a PostToolUse hook that runs after Bash tool calls and removes any newly-added oversized or redundant permission entries from settings.local.json, preventing bloat in real-time.

**Dependencies:** Task 5 (reuses cleanup logic), Task 7

**Files:**

- Create: `/home/mike-anderson/.claude/hooks/post-bash-cleanup.sh`
- Modify: `~/.claude/settings.json` (add PostToolUse hook)

**Key Decisions / Notes:**

- The hook checks settings.local.json after each Bash execution
- If the file has grown (by comparing to a cached size), it runs a quick cleanup pass
- Removes any permission entry longer than 200 characters (these are embedded scripts/heredocs)
- Removes any entry that matches a wildcard pattern already in user settings
- Caches the file size in `/tmp/.claude-settings-size` to detect growth without parsing JSON every time
- Only triggers cleanup when size has actually increased (skip if unchanged)
- Must be fast (< 100ms) — uses simple size check as gate before any JSON parsing
- Writes cleaned JSON atomically (write to temp file, then mv) to prevent corruption

**Definition of Done:**

- [ ] Hook script exists and is executable
- [ ] Hook is registered in `~/.claude/settings.json` under `hooks.PostToolUse`
- [ ] Hook detects settings.local.json growth after Bash commands
- [ ] Hook removes oversized entries (> 200 chars) automatically
- [ ] Hook preserves non-permission settings (hooks, deny rules)
- [ ] Hook uses atomic writes to prevent corruption
- [ ] Hook runs in < 100ms when no cleanup needed, < 500ms when cleaning

**Verify:**

- `bash ~/.claude/hooks/post-bash-cleanup.sh` — runs without error
- `ls -la ~/.claude/hooks/post-bash-cleanup.sh` — executable permission set

## Testing Strategy

- Unit tests: Validate JSON parsing for all modified settings files
- Integration tests: Run the cleanup script against the backed-up bloated settings file
- Manual verification: Restart Claude Code and check debug log for absence of warnings

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Over-permissive wildcard patterns | Low | Med | Only add patterns for commands already approved historically; review each pattern |
| Settings file corruption during edit | Low | High | Back up all files before modification; validate JSON after each change |
| Hook adds latency to session start | Low | Low | Keep hook under 100ms; only check file size, no parsing |
| Cleanup script removes needed permission | Low | Med | Dry-run mode by default; backup before apply; only remove covered/oversized rules |
| PreToolUse hook slows every tool call | Med | Med | Fast path: exit immediately if not Bash tool; pattern matching uses grep, not Python |
| PostToolUse hook corrupts settings.local.json | Low | High | Atomic writes (temp file + mv); size-check gate avoids unnecessary JSON parsing |
| Settings.local.json edited while Claude Code reads it | Low | Med | PostToolUse writes atomically; Claude Code re-reads on next permission check |

## Open Questions

- None — scope is clear from the debug analysis.

### Deferred Ideas

- Automated settings.local.json cleanup via cron job
- Dashboard showing permission accumulation rate over time
- Integration with `sx` vault system to share curated patterns across team
