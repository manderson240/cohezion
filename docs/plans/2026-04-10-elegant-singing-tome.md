# Plan: Autonomous Config Optimization System

## Context

**Problem:** Claude Code ships ~8 releases per 9 days (April 2026 cadence). New features, settings, env vars, hooks, and security hardening arrive faster than any human can track. Currently, your only signal is the built-in `/release-notes` picker — reactive, manual, and easy to skip.

**Current State:** Version 2.1.100 (latest). 23 plugins, 9 global hooks, 22 project hooks, comprehensive permissions. Well-tuned but with several recent features unadopted.

**Goal:** Build a self-maintaining system that (1) applies immediate optimizations from the current gap analysis, (2) automatically surfaces and recommends new features on every version bump, and (3) provides a one-command audit to diff your config against known best practices.

**Outcome:** You always know what's new, config stays optimized, and no feature falls through the cracks.

---

## Phase 1: Immediate Config Optimizations (settings.json edits)

These are features from recent releases (v2.1.94–2.1.100) that your config doesn't yet leverage.

### Task 1.1: Add new env vars for rendering and sandboxing

**File:** `~/.claude/settings.json` → `env` block

Add:
```json
"CLAUDE_CODE_NO_FLICKER": "1",
"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1"
```

- `NO_FLICKER` enables alt-screen rendering with virtualized scrollback — eliminates terminal flicker during tool calls. Unlocks the Focus View toggle (`Ctrl+O`).
- `SUBPROCESS_ENV_SCRUB` enables PID namespace isolation for subprocesses — security hardening that sandboxes Bash children.

### Task 1.2: Add `PermissionDenied` hook

**File:** `~/.claude/settings.json` → `hooks` block

Add a new hook type:
```json
"PermissionDenied": [
  {
    "matcher": "all",
    "hooks": [
      {
        "type": "command",
        "command": "/home/mike-anderson/.claude/hooks/on-permission-denied.sh"
      }
    ]
  }
]
```

**New file:** `~/.claude/hooks/on-permission-denied.sh`

This hook fires after the auto-mode classifier denies a tool call. The script will:
- Log the denied tool + reason to `~/.claude/logs/denied-tools.log`
- Track denial patterns (frequent false-positive denials → candidate for permission allow-list)
- Return `{"retry": true}` for known-safe read-only patterns (configurable allowlist in `~/.claude/hooks/safe-retry-patterns.txt`)
- **Decision: Log + auto-retry safe patterns** (user confirmed)

### Task 1.3: Add `refreshInterval` to status line

**File:** `~/.claude/settings.json`

Add top-level:
```json
"statusLine": {
  "refreshInterval": 30
}
```

If you have a custom status line command, this re-runs it every 30 seconds — useful for showing live context percentage, git branch, or session duration.

### Task 1.4: Expand Bash auto-approval with new safe commands

**File:** `~/.claude/settings.json` → `permissions.allow`

Add recently-supported safe commands:
```
"Bash(tput:*)",
"Bash(stat:*)",
"Bash(ant:*)",
"Bash(cat:*)",
"Bash(diff:*)",
"Bash(which:*)",
"Bash(file:*)",
"Bash(readlink:*)",
"Bash(realpath:*)"
```

These are read-only info commands that were recently added to Claude Code's default safe list but aren't in your explicit allowlist.

---

## Phase 2: Version Watch Hook (autonomous feature detection)

### Task 2.1: Create version-watch SessionStart hook

**New file:** `~/.claude/hooks/version-watch.sh`

Logic:
1. Read `~/.claude/.last-known-version` (create if missing, seed with current `2.1.100`)
2. Run `claude --version` and compare
3. If version changed:
   - Write new version to `.last-known-version`
   - Emit a system message: `"[version-watch] Claude Code updated: {old} → {new}. Run /release-notes to review changes, or /config-audit to check for new settings."`
4. If version unchanged: silent (zero noise)

**Wire into:** `~/.claude/settings.json` → `hooks.SessionStart` (append after existing `check-settings-size.sh`)

### Task 2.2: Create config-audit skill

**New file:** `~/.claude/commands/config-audit.md`

A slash command (`/config-audit`) that:
1. Reads `~/.claude/settings.json` (current config)
2. Fetches the latest changelog via `WebFetch` from `https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md`
3. Cross-references known feature flags, env vars, hook types, and settings against your current config
4. Reports:
   - **Adopted:** features you're already using
   - **Available:** features you haven't enabled yet, with one-line description + risk level
   - **Deprecated:** settings that were removed or superseded
5. Optionally applies recommended changes (with user confirmation)

This is the "pull" lever — you run it when you want, it tells you what's new.

### Task 2.3: Create known-features manifest

**New file:** `~/.claude/config-audit/features-manifest.json`

A structured registry of all known Claude Code features, their version of introduction, category, and whether they're enabled in your config. Example structure:

```json
{
  "features": [
    {
      "id": "no_flicker",
      "name": "Flicker-free rendering",
      "version_added": "2.1.97",
      "type": "env_var",
      "key": "CLAUDE_CODE_NO_FLICKER",
      "value": "1",
      "risk": "low",
      "category": "rendering"
    }
  ]
}
```

The `/config-audit` skill reads this manifest. When Claude Code updates, you (or the version-watch hook) can prompt to update the manifest from the changelog.

---

## Phase 3: Plugin & MCP Review

### Task 3.1: Evaluate disabled plugins for re-enablement

Currently disabled plugins to evaluate:

| Plugin | Recommendation | Rationale |
|--------|---------------|-----------|
| `hookify` | **Enable** | Auto-generates hooks from natural language — simplifies hook creation |
| `agent-sdk-dev` | **Enable** | Managed Agents hit public beta — relevant for compound loop |
| `claude-code-setup` | Skip | One-time setup, already configured |
| `document-skills` | Skip | Low relevance |
| `frontend-design` | Skip | Not relevant to Python backend |

**Decision: Enable hookify + agent-sdk-dev** (user confirmed)

### Task 3.2: Add `ant` CLI to Bash allowlist

The new `ant` CLI (Anthropic's API client) may be installed or installable. Add:
```
"Bash(ant:*)"
```
to the global permissions allowlist so it's auto-approved when used.

---

## Phase 4: Harden & Polish

### Task 4.1: Security audit of current hooks

Review all 9 global hook scripts for:
- Proper exit codes (non-zero should not block tool execution unless intended)
- No secret leakage in stdout (hooks output goes to Claude's context)
- Timeout handling (hooks that hang block the tool pipeline)
- Compatibility with new `PermissionDenied` hook type

### Task 4.2: Update autocompact prompt for new features

**File:** `~/.claude/settings.json` → `autoCompactPrompt`

Current prompt is good but doesn't mention preserving config-audit state or version-watch context. Update to include:
```
"Preserve: active plan file paths, task IDs, file paths being edited, test results, error messages, architectural decisions, config-audit findings, and version-watch alerts. Summarize exploration and research. Drop verbose tool outputs and intermediate search results."
```

### Task 4.3: Add `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE` env var

For offline resilience, add to env block:
```json
"CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE": "true"
```
This keeps the existing plugin marketplace cache when git pull fails — prevents plugin loss during network outages.

---

## Verification

1. **Immediate settings:** After Phase 1 edits, start a new Claude Code session and verify:
   - `NO_FLICKER` mode is active (check for alt-screen rendering)
   - `Ctrl+O` focus view toggle works
   - New Bash commands auto-approve without prompts
   - `PermissionDenied` hook fires on a test denial

2. **Version watch:** Simulate by temporarily editing `.last-known-version` to an older version, then starting a new session — should see the version-change message.

3. **Config audit:** Run `/config-audit` and verify it produces a meaningful diff of adopted vs available features.

4. **End-to-end:** After all phases, `claude --version` + review `/release-notes` + run `/config-audit` should form a complete "stay current" workflow with zero manual tracking.

---

## Files Modified/Created

| File | Action |
|------|--------|
| `~/.claude/settings.json` | Edit: env vars, hooks, permissions, autoCompactPrompt |
| `~/.claude/hooks/version-watch.sh` | Create: version detection hook |
| `~/.claude/hooks/on-permission-denied.sh` | Create: denial logging/retry hook |
| `~/.claude/commands/config-audit.md` | Create: audit slash command |
| `~/.claude/config-audit/features-manifest.json` | Create: known features registry |
