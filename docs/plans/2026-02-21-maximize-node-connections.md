# Maximize Node Connections Implementation Plan

Created: 2026-02-21
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Maximize node connections in the Cohezion vault by making the linking system proactive instead of reactive. Add a Claude Code hook that surfaces link suggestions whenever a vault file is written or edited, and add new vault_linker subcommands to support single-file operations.

**Architecture:** PostToolUse hook on Write|Edit → shell script filters to vault .md files → calls `vault_linker suggest <file>` → suggestions appear in Claude's transcript. Uses existing VaultParser infrastructure for indexing. Shared `find_bidirectional_gaps()` function enables both suggest and analyze to detect missing reverse links.

**Tech Stack:** Python (vault_linker), Bash (hook script), jq (JSON parsing)

## Scope

### In Scope

- `suggest` subcommand: single-file link suggestions using full vault parse (~350ms)
- `inject-single` subcommand: surgical injection for one file (same indexing, one-file write)
- PostToolUse hook: surface suggestions after Write/Edit to vault .md files
- Bidirectional gap detection: shared function used by suggest + analyze
- Cooldown mechanism to prevent redundant suggestions during rapid edits

### Out of Scope

- Content keyword matching (tag overlap + bidirectional is sufficient for now)
- Batch re-analysis triggered by multiple file changes (manual `fix` covers this)
- Modifying the Obsidian plugin for link suggestions (separate concern)
- Persistent index caching (vault parse is fast enough at ~350ms; revisit if perf degrades)

## Prerequisites

- vault_linker tool is functional (`tools/vault_linker/`)
- `jq` is installed (for hook script JSON parsing)
- PyYAML is available for whichever Python runs vault_linker

## Context for Implementer

- **Patterns to follow:** Existing CLI pattern in `tools/vault_linker/__main__.py:14-46` (argparse subparsers). Follow `fix()` function structure at line 91 for new subcommands.
- **Conventions:** vault_linker functions return int exit codes. VaultParser builds `files_index` (dict of stem→metadata) and `link_graph` (dict of stem→set of linked stems). All vault file operations use `encoding='utf-8'`.
- **Key files:**
  - `tools/vault_linker/__main__.py` — CLI entry point, add new subcommands here
  - `tools/vault_linker/parser.py` — VaultParser with `walk_vault()` and `classify_broken_links()`
  - `tools/vault_linker/injector.py` — LinkInjector with `inject_links()` per-file
  - `tools/vault_linker/report.py` — ReportGenerator for analyze output
  - `.claude/settings.json` — Existing hooks config (PostToolUse entries)
  - `.claude/hooks/hooks.json` — Existing hooks metadata file (independent of new hook)
- **Gotchas:**
  - vault_linker is NOT installed in any venv — it requires `PYTHONPATH=tools` or `cd tools && python3 -m vault_linker`
  - Some vault files have invalid YAML that crashes `yaml.safe_load` — VaultParser handles this gracefully, but new code must too
  - VaultParser.EXCLUDE_DIRS = `{'.git', 'node_modules', '.obsidian', 'mcp-server', 'obsidian-plugin', '.claude', 'tools', 'htmlcov', 'docs', '.venv'}`
  - Hook stdin JSON for PostToolUse needs experimental verification (see Task 3)
- **Domain context:** The vault has ~666 .md files. `walk_vault()` parses all of them in ~350ms. Link graph tracks outgoing wiki-links per file. Tags are YAML arrays in frontmatter.

## Exploration Findings (Completed)

### Current State (from vault_linker analyze)
- **Total Files:** 666
- **Total Link Targets:** 801
- **Valid Links:** 448 (55%)
- **Broken Links:** 353 (44%) — 260 missing concepts, 91 external refs, 2 date-prefixed
- **Papers with null tags:** 2
- **Top broken:** `agent context` (27 refs), `mcp infrastructure architecture` (9 refs)

### Existing Infrastructure
1. **vault_linker tool** (`tools/vault_linker/`) — Python package with:
   - `parser.py` — VaultParser: walks vault, builds link graph, classifies broken links
   - `resolver.py` — LinkResolver: fuzzy matching for broken links (4 strategies, confidence-scored)
   - `tagger.py` — TagPopulator: generates tags from keywords + similar_papers inheritance
   - `stubgen.py` — StubGenerator: creates concept stubs for frequently-referenced broken links
   - `injector.py` — LinkInjector: adds Related Papers/Concepts sections based on tag overlap
   - `report.py` — ReportGenerator: vault health metrics
   - `__main__.py` — CLI with `analyze` and `fix` commands
   - Tests: `tools/tests/test_*.py` for each module

2. **Claude Code hooks** (`.claude/settings.json`):
   - Has existing PreToolUse/PostToolUse hooks for `track_session`, `Task`, `record_decision`, `record_outcome`, `TodoWrite`
   - No hooks currently trigger on Write/Edit for vault files
   - `.claude/hooks/hooks.json` exists separately — new hook shell script coexists independently

3. **Key gap:** Current system is entirely **reactive** — you must manually run `vault_linker fix`. Nothing happens automatically when notes are created or edited.

### Hook System Capabilities (from Context7)
- **PostToolUse** hooks can trigger on `Write|Edit` matcher
- Command-type hooks receive tool input via stdin JSON (`jq -r '.tool_input.file_path'`)
- Exit 0 = stdout shown in transcript; exit 2 = stderr fed back to Claude
- Can run shell scripts that invoke the vault_linker modules

## Design Decisions (Resolved)

### Hook Scope
**PostToolUse on `Write|Edit`, filtered in script to vault markdown files only.**

The hook script checks:
1. File extension is `.md`
2. File path is NOT in VaultParser.EXCLUDE_DIRS-aligned list (`.git`, `node_modules`, `.obsidian`, `mcp-server`, `obsidian-plugin`, `.claude`, `tools`, `htmlcov`, `docs`, `.venv`, `checkpoints`, `.worktrees`)

Directory exclusion is handled primarily by the `suggest` command itself (which reuses VaultParser's exclude logic). The hook only needs to check the `.md` extension as a fast pre-filter.

### Hook Action
**Report suggestions to stdout (exit 0) — Claude sees them in the transcript, no auto-modification.**

Rationale: Auto-injection on every save would be too aggressive and could corrupt in-progress notes. Instead, the hook surfaces suggestions as information Claude can act on. The user remains in control.

### Performance
- `suggest` uses `walk_vault()` (full vault parse, ~350ms). This is acceptable for a PostToolUse hook.
- Cooldown mechanism: hook checks a timestamp file. If last run was <30 seconds ago, exit immediately with no output. This prevents redundant suggestions during rapid multi-file edits.
- `inject-single` has the same indexing cost as `fix` (~350ms for `walk_vault()`). Its value is surgical: it writes only one file instead of all files. Marketing it as "fast" was inaccurate — it is "targeted".

### New CLI Subcommands
**`suggest <file>`** — Single-file analysis using full `walk_vault()`. Finds tag-overlapping files not already linked, plus bidirectional gaps (files that link TO target but aren't linked back). Outputs top 5 suggestions. If target file has no tags and no incoming links, outputs a helpful message instead of empty results.

**`inject-single <file>`** — Run full `injector.py` logic on one file only. Builds the vault index via `walk_vault()` then modifies only the target file. Provides a targeted path for "fix this file now" without writing every file in the vault.

### Shared Bidirectional Detection
`find_bidirectional_gaps(link_graph, target_stem)` function added to `parser.py`. Returns list of stems that link TO target but are not linked FROM target. Used by both `suggest` and `report.py`.

### Error Handling
Hook script wraps vault_linker invocation with error handling. On failure: log error to `/tmp/vault-link-suggest.log`, output nothing to stdout, exit 0. The suggest command itself catches all exceptions and exits cleanly.

## Progress Tracking

Done: 5 / Left: 0
- [x] Task 1: Add `suggest` subcommand with bidirectional detection
- [x] Task 2: Add `inject-single` subcommand
- [x] Task 3: Write hook shell script with cooldown
- [x] Task 4: Register hook in settings.json
- [x] Task 5: Add bidirectional gap section to analyze report

## Implementation Tasks

### Task 1: Add `suggest` subcommand and shared bidirectional function

**Objective:** Add a `suggest` subcommand to vault_linker that outputs link suggestions for a single file, and a shared `find_bidirectional_gaps()` function in parser.py.

**Dependencies:** None

**Files:**
- Modify: `tools/vault_linker/parser.py` — add `find_bidirectional_gaps(link_graph, target_stem)` method
- Modify: `tools/vault_linker/__main__.py` — add `suggest` subparser and `suggest_file()` function
- Create: `tools/tests/test_suggest.py` — tests for suggest command and bidirectional function

**Key Decisions / Notes:**
- `suggest_file()` calls `VaultParser.walk_vault()` for full index + link graph (~350ms, acceptable)
- Tag overlap: find files sharing ≥1 tag with target, not already linked in target's content
- Bidirectional gaps: use `find_bidirectional_gaps()` from parser.py
- Output format: `📎 Suggested links for <file>:\n  Tag overlap:\n  - [[concept-a]]\n  Bidirectional gaps:\n  - [[paper-b]] (links to you)`
- When target has no tags AND no incoming links: output `📎 No suggestions for <file> (no tags or incoming links yet)`
- Follow CLI pattern from `__main__.py:14-46` (argparse subparsers)
- The `find_bidirectional_gaps()` function goes in `parser.py` since it operates on the link_graph data structure that VaultParser builds
- Catch all exceptions in `suggest_file()` and exit cleanly (return 1, no traceback)

**Definition of Done:**
- [ ] `find_bidirectional_gaps(link_graph, target_stem)` returns correct gap list
- [ ] `vault_linker suggest <file>` outputs tag-overlap and bidirectional suggestions
- [ ] Files in EXCLUDE_DIRS are filtered from suggestions
- [ ] Files with no tags produce a helpful "no suggestions" message
- [ ] All tests pass: `PYTHONPATH=tools uv run pytest tools/tests/test_suggest.py -q`

**Verify:**
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools uv run pytest tools/tests/test_suggest.py -q`
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools python3 -m vault_linker suggest concepts/cs249r/workflow.md` — outputs sensible suggestions

### Task 2: Add `inject-single` subcommand

**Objective:** Add an `inject-single` subcommand that runs full injection logic on exactly one file.

**Dependencies:** None

**Files:**
- Modify: `tools/vault_linker/__main__.py` — add `inject-single` subparser and `inject_single()` function
- Create: `tools/tests/test_inject_single.py` — tests for inject-single command

**Key Decisions / Notes:**
- Calls `walk_vault()` for full index, then `LinkInjector.inject_links()` on one file only
- Supports `--dry-run` flag (print what would change, don't write)
- Value is surgical modification (one file write), not speed — indexing cost same as `fix`
- Follow `fix()` function structure at `__main__.py:91`
- Check `_is_read_only()` for the target file (skip daily/ files)

**Definition of Done:**
- [ ] `vault_linker inject-single <file>` injects Related sections into only the target file
- [ ] `--dry-run` flag shows changes without writing
- [ ] Read-only files (daily/) are rejected with a message
- [ ] All tests pass: `PYTHONPATH=tools uv run pytest tools/tests/test_inject_single.py -q`

**Verify:**
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools uv run pytest tools/tests/test_inject_single.py -q`
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools python3 -m vault_linker inject-single --dry-run patterns/predictive-throttling-via-12d-trajectory-velocity.md`

### Task 3: Write the hook shell script with cooldown

**Objective:** Create a PostToolUse hook script that calls `vault_linker suggest` on vault .md files with cooldown and error handling.

**Dependencies:** Task 1 (suggest command must exist)

**Files:**
- Create: `.claude/hooks/vault-link-suggest.sh` — hook shell script
- Create: `tools/tests/test_hook_script.sh` — smoke test for hook script

**Key Decisions / Notes:**
- **Step 0 — Verify JSON structure:** Before writing the final hook, create a temporary debug hook that dumps stdin to `/tmp/hook-debug.log`. Trigger it by editing a vault file. Inspect the actual JSON to confirm the key path (expected: `.tool_input.file_path`). Then build the real hook based on observed reality.
- Read `file_path` from stdin JSON using `jq -r '.tool_input.file_path'` (verify first!)
- Pre-filter: exit immediately if file doesn't end in `.md`
- Cooldown: check `/tmp/vault-link-suggest.last` timestamp. If less than 30 seconds old, exit 0 with no output. Update timestamp on each real run.
- Set `PYTHONPATH=/home/mike-anderson/vaults/cohezion-vault/tools` before invoking Python
- Wrap vault_linker invocation: on failure, log to `/tmp/vault-link-suggest.log`, output nothing, exit 0
- Script must be executable (`chmod +x`)
- Coexists with existing `.claude/hooks/hooks.json` (independent file)

**Definition of Done:**
- [ ] Hook script reads file_path from stdin JSON correctly (verified via debug step)
- [ ] Only fires on `.md` files
- [ ] Cooldown prevents firing within 30s of last run
- [ ] On vault_linker failure: logs error, outputs nothing, exits 0
- [ ] PYTHONPATH is set correctly (no ModuleNotFoundError)
- [ ] Smoke test passes: `echo '{"tool_input":{"file_path":"test.md"}}' | bash .claude/hooks/vault-link-suggest.sh`

**Verify:**
- `bash tools/tests/test_hook_script.sh` — smoke test passes
- Manual test: edit a vault .md file → hook fires → suggestions appear in transcript

### Task 4: Register the hook in `.claude/settings.json`

**Objective:** Add a PostToolUse entry matching `Write|Edit` that runs the hook script.

**Dependencies:** Task 3 (hook script must exist)

**Files:**
- Modify: `.claude/settings.json` — add PostToolUse Write|Edit entry

**Key Decisions / Notes:**
- Add to existing `PostToolUse` array in settings.json
- Matcher: `Write|Edit` (pipe-separated for both tools)
- Command: `bash /home/mike-anderson/vaults/cohezion-vault/.claude/hooks/vault-link-suggest.sh`
- Existing hooks remain unchanged

**Definition of Done:**
- [ ] `.claude/settings.json` has a PostToolUse entry for `Write|Edit`
- [ ] Existing hooks are not modified
- [ ] JSON is valid (parseable)

**Verify:**
- `python3 -c "import json; json.load(open('.claude/settings.json'))"` — valid JSON
- `jq '.hooks.PostToolUse[] | select(.matcher == "Write|Edit")' .claude/settings.json` — shows the new entry

### Task 5: Add bidirectional gap section to analyze report

**Objective:** Enhance `vault_linker analyze` output with a "Bidirectional Gaps" section showing files that would benefit from reverse links.

**Dependencies:** Task 1 (shared `find_bidirectional_gaps()` must exist in parser.py)

**Files:**
- Modify: `tools/vault_linker/report.py` — add bidirectional gap section to report output
- Modify: `tools/tests/test_report.py` (if exists) or create — tests for new section

**Key Decisions / Notes:**
- Uses `find_bidirectional_gaps()` from parser.py (added in Task 1)
- Report top 20 bidirectional gaps, sorted by number of missing reverse links
- Format: `## Bidirectional Gaps\n\n| File | Missing Reverse Links | Examples |\n...`
- This is the lowest-priority task — can be dropped if context runs low without losing core value

**Definition of Done:**
- [ ] `vault_linker analyze` includes a "Bidirectional Gaps" section
- [ ] Section shows top 20 files with most missing reverse links
- [ ] All existing analyze tests still pass
- [ ] New tests verify bidirectional section content

**Verify:**
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools uv run pytest tools/tests/ -q` — all tests pass
- `cd /home/mike-anderson/vaults/cohezion-vault && PYTHONPATH=tools python3 -m vault_linker analyze` — shows bidirectional gap section

## Testing Strategy

- **Unit tests:** Test `find_bidirectional_gaps()`, `suggest_file()`, `inject_single()` with fixture vaults (small temp directories with known .md files)
- **Integration tests:** Run suggest/inject-single against the real vault to verify output
- **Hook smoke test:** Pipe sample JSON to hook script, verify exit code and output
- **Manual verification:** Edit a vault file in Claude Code → hook fires → suggestions visible

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hook stdin JSON has unexpected structure | Medium | High (hook silently fails) | Debug hook step verifies actual JSON before building real hook |
| vault_linker crash during hook | Low | Medium (traceback in transcript) | Wrap invocation with error handling, silent exit on failure |
| Hook adds latency to every Write/Edit | Low | Medium (350ms per invocation) | 30-second cooldown prevents redundant runs during rapid edits |
| PYTHONPATH misconfiguration | Medium | High (ModuleNotFoundError) | Explicit PYTHONPATH in hook script, tested in smoke test |

## Open Questions

- None remaining — all design questions resolved

## Files to Create/Modify

| File | Change |
|------|--------|
| `tools/vault_linker/parser.py` | Add `find_bidirectional_gaps()` method |
| `tools/vault_linker/__main__.py` | Add `suggest` and `inject-single` subcommands |
| `tools/vault_linker/report.py` | Add bidirectional gap section to analyze |
| `tools/tests/test_suggest.py` | New: tests for suggest + bidirectional function |
| `tools/tests/test_inject_single.py` | New: tests for inject-single command |
| `.claude/hooks/vault-link-suggest.sh` | New: hook shell script with cooldown |
| `tools/tests/test_hook_script.sh` | New: smoke test for hook |
| `.claude/settings.json` | Add PostToolUse Write\|Edit hook |

**Total Tasks: 5 | Completed: 0 | Remaining: 5**
