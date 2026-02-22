# Cohezion Workflow Engine - Clean-Room Implementation Plan

Created: 2026-02-21
Status: VERIFIED
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

**Goal:** Build an original CLI tool (`cohezion-engine`) and self-contained Claude Code rules/skills that replicate the *concepts* of spec-driven development, TDD enforcement, context continuation, and verification agents -- without copying any Pilot code. This is a clean-room reimplementation for internal use only.

**Architecture:** Python CLI using `click` (or `typer`) with JSON output, installed as `cz` command. Rules and skills live in the vault's `.claude/` directory. The engine provides session management, context tracking, worktree isolation, and plan lifecycle -- the rules/skills orchestrate Claude Code's behavior using these primitives.

**Tech Stack:** Python 3.12+, click/typer, standard library (pathlib, json, subprocess), pytest for testing. No compiled/obfuscated code -- fully open source for internal use.

## Scope

### In Scope

- CLI tool (`cz`) with subcommands: `context`, `session`, `worktree`, `plan`, `status`
- Context usage estimation (token counting from Claude Code's API)
- Session continuation files (write/read/clear)
- Git worktree creation, sync, cleanup, status
- Plan file lifecycle (register, status tracking)
- Self-contained Claude Code rules (no `pilot` binary references)
- Self-contained skills (spec, spec-plan, spec-implement, spec-verify)
- Hook scripts (context monitor, TDD enforcer, file checker)
- Verification agent prompts (plan-verifier, plan-challenger, spec-reviewer-compliance, spec-reviewer-quality)

### Out of Scope

- License management / activation (not needed for internal tool)
- Pilot Memory / observation system (separate MCP-based system, not part of this)
- Team vault / sx integration (separate tool, orthogonal)
- Statusline formatting (nice-to-have, defer)
- Worker service / bundled JS scripts (Pilot-specific architecture)
- Auto-update mechanism
- Web UI / viewer

## Prerequisites

- Python 3.12+ available via `uv`
- Claude Code CLI installed and configured
- Git installed with worktree support
- This vault repo checked out

## Context for Implementer

> This section is critical for cross-session continuity.

- **Clean-room constraint:** Do NOT read Pilot's source code (`~/.pilot/bin/pilot.cpython-312.so`, `~/.pilot/pilot/hooks/*.py`, `~/.pilot/pilot/scripts/*.cjs`, `~/.pilot/pilot/agents/*.md`). Implement from the *observable behavior* described in this plan and the *concepts* in the current rules files. The rules files describe what the system should DO, not how Pilot does it internally.
- **Project location:** The CLI tool lives at `/home/mike-anderson/vaults/cohezion-vault/tools/cohezion-engine/`
- **Installation:** Uses `uv` for dependency management, `pyproject.toml` for project config
- **Entry point:** `cz` command (short for cohezion-engine), installed via `uv pip install -e .`
- **Rules rewrite:** New rules go in `/home/mike-anderson/vaults/cohezion-vault/.claude/rules/` replacing references to `~/.pilot/bin/pilot` with `cz` commands
- **Skills rewrite:** New skills go in `/home/mike-anderson/vaults/cohezion-vault/.claude/skills/`
- **Hooks rewrite:** New hooks go in `/home/mike-anderson/vaults/cohezion-vault/.claude/hooks/`
- **Existing patterns:** Follow the Python conventions in the vault's `development-workflows.md` (black formatting, ruff linting, pytest testing)
- **JSON output:** All CLI commands support `--json` flag for machine-readable output. Human-readable output is the default.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Project scaffolding and CLI entry point
- [x] Task 2: Context estimation module
- [x] Task 3: Session management module
- [x] Task 4: Worktree management module
- [x] Task 5: Plan lifecycle module
- [x] Task 6: Hook scripts (context monitor, TDD enforcer, file checker)
- [x] Task 7: Self-contained rules rewrite
- [x] Task 8: Self-contained skills rewrite (spec workflow)
- [x] Task 9: Verification agent prompts
- [x] Task 10: Integration testing and CLI smoke tests

**Total Tasks:** 10 | **Completed:** 10 | **Remaining:** 0

## Implementation Tasks

### Task 1: Project Scaffolding and CLI Entry Point

**Objective:** Create the `cohezion-engine` Python project with CLI skeleton using click/typer, with `cz` as the entry point command.

**Dependencies:** None

**Files:**

- Create: `tools/cohezion-engine/pyproject.toml`
- Create: `tools/cohezion-engine/src/cohezion_engine/__init__.py`
- Create: `tools/cohezion-engine/src/cohezion_engine/cli.py`
- Create: `tools/cohezion-engine/src/cohezion_engine/config.py`
- Test: `tools/cohezion-engine/tests/test_cli.py`

**Key Decisions / Notes:**

- Use `click` for CLI framework (lightweight, well-documented, no compilation needed)
- Entry point: `cz` command with subcommands (`cz context`, `cz session`, `cz worktree`, `cz plan`, `cz status`)
- Config stored in `~/.cohezion-engine/` (session state, settings)
- All commands support `--json` flag for machine-readable output
- Use `uv` for project management (`uv init`, `uv add`)

**Definition of Done:**

- [ ] `cz --help` displays available subcommands
- [ ] `cz --version` shows version number
- [ ] `cz status --json` returns `{"version": "0.1.0", "config_dir": "..."}`
- [ ] Project installs cleanly via `uv pip install -e .`

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_cli.py -q`
- `cd tools/cohezion-engine && uv run cz --help`
- `cd tools/cohezion-engine && uv run cz status --json`

### Task 2: Context Estimation Module

**Objective:** Build a module that estimates Claude Code context usage by reading the current session's conversation JSONL file and summing token counts.

**Dependencies:** Task 1

**Files:**

- Create: `tools/cohezion-engine/src/cohezion_engine/context.py`
- Test: `tools/cohezion-engine/tests/test_context.py`
- Modify: `tools/cohezion-engine/src/cohezion_engine/cli.py` (add `cz context` subcommand)

**Key Decisions / Notes:**

- **No env var for token count exists.** Claude Code does NOT expose `CLAUDE_CODE_CONTEXT_TOKENS`. Instead, read the session JSONL file directly.
- **Session JSONL location:** `~/.claude/projects/<project-slug>/<session-uuid>.jsonl` where project-slug is the cwd path with `/` replaced by `-`. The most recently modified JSONL file in the project dir is the active session.
- **Token counting:** Sum `message.usage.input_tokens + message.usage.cache_creation_input_tokens + message.usage.cache_read_input_tokens` from each line where `message.role == "assistant"`. This gives cumulative tokens used.
- **Context limit:** 200,000 tokens (Claude Sonnet). Configurable via `~/.cohezion-engine/config.json`.
- **When run as a hook:** The JSONL has just been written (PostToolUse fires after the tool response is recorded), so the sum includes the latest turn.
- Output format: `{"status": "OK", "percentage": 47.0}` when < 80%, `{"status": "WARNING", "percentage": 85.0}` at 80-89%, `{"status": "CLEAR_NEEDED", "percentage": 92.0}` at 90%+
- Thresholds: 80% = warning, 90% = clear needed (configurable via config.json)

**Definition of Done:**

- [ ] `cz context --json` returns status with percentage
- [ ] Returns `CLEAR_NEEDED` when context exceeds 90% threshold
- [ ] Returns `WARNING` when context exceeds 80% threshold
- [ ] Handles missing/unreadable context data gracefully with error message

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_context.py -q`
- `cd tools/cohezion-engine && uv run cz context --json`

### Task 3: Session Management Module

**Objective:** Build session lifecycle management -- create sessions, write/read continuation files, trigger session clears.

**Dependencies:** Task 1

**Files:**

- Create: `tools/cohezion-engine/src/cohezion_engine/session.py`
- Test: `tools/cohezion-engine/tests/test_session.py`
- Modify: `tools/cohezion-engine/src/cohezion_engine/cli.py` (add `cz session` subcommands)

**Key Decisions / Notes:**

- Session ID: use `COHEZION_SESSION_ID` env var, fall back to PID-based ID
- Session directory: `~/.cohezion-engine/sessions/<session-id>/`
- Continuation file: `~/.cohezion-engine/sessions/<session-id>/continuation.md`
- `cz session send-clear <plan.md>` -- writes continuation marker to session dir, then sends a `/clear` instruction to Claude Code. Mechanism: write a trigger file that the user's terminal script picks up, OR write a message to Claude Code's IPC socket (`CLAUDE_CODE_SSE_PORT` env var exposes a WebSocket at `ws://localhost:<port>`). Primary approach: use the `CLAUDE_CODE_SSE_PORT` WebSocket to inject a `/clear` message programmatically.
- `cz session send-clear --general` -- same but without plan-specific continuation context
- **Implementation research task:** Before writing `send-clear`, prototype WebSocket injection: `python3 -c "import websocket; ws = websocket.create_connection('ws://localhost:$CLAUDE_CODE_SSE_PORT'); ..."` to confirm IPC capability. If WebSocket injection fails, fall back to writing a `.trigger` file and documenting a manual `/clear` step.
- `cz session status --json` -- shows current session info

**Definition of Done:**

- [ ] `cz session status --json` returns session ID and state
- [ ] Continuation files are written to the correct session directory
- [ ] `cz session send-clear` triggers Claude Code restart with continuation prompt
- [ ] Session directories are created on demand

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_session.py -q`
- `cd tools/cohezion-engine && uv run cz session status --json`

### Task 4: Worktree Management Module

**Objective:** Build git worktree isolation commands -- create, detect, diff, sync, cleanup, status.

**Dependencies:** Task 1

**Files:**

- Create: `tools/cohezion-engine/src/cohezion_engine/worktree.py`
- Test: `tools/cohezion-engine/tests/test_worktree.py`
- Modify: `tools/cohezion-engine/src/cohezion_engine/cli.py` (add `cz worktree` subcommands)

**Key Decisions / Notes:**

- Worktree location: `.worktrees/spec-<slug>-<hash>/` in the project root
- Branch naming: `spec/<slug>` (e.g., `spec/add-auth`)
- Slug derivation: plan filename without date prefix and `.md` extension
- `cz worktree create --json <slug>` -- creates worktree, checks for dirty working tree first
- `cz worktree detect --json <slug>` -- checks if worktree exists
- `cz worktree diff --json <slug>` -- lists changed files vs base branch
- `cz worktree sync --json <slug>` -- squash merge back to base branch
- `cz worktree cleanup --json <slug>` -- removes worktree directory and branch
- `cz worktree status --json` -- shows active worktree info
- Error handling: return `{"success": false, "error": "dirty", "detail": "..."}` for dirty working tree
- Uses `git worktree add/remove/list` under the hood

**Definition of Done:**

- [ ] `cz worktree create --json test-slug` creates worktree at `.worktrees/spec-test-slug-<hash>/`
- [ ] `cz worktree detect --json test-slug` returns `{"found": true/false, ...}`
- [ ] `cz worktree sync --json test-slug` performs squash merge and returns commit hash
- [ ] `cz worktree cleanup --json test-slug` removes worktree directory and branch
- [ ] Dirty working tree returns appropriate error JSON

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_worktree.py -q`
- `cd tools/cohezion-engine && uv run cz worktree status --json`

### Task 5: Plan Lifecycle Module

**Objective:** Build plan file registration and status tracking -- register plans with sessions, track status changes.

**Dependencies:** Task 1, Task 3

**Files:**

- Create: `tools/cohezion-engine/src/cohezion_engine/plan.py`
- Test: `tools/cohezion-engine/tests/test_plan.py`
- Modify: `tools/cohezion-engine/src/cohezion_engine/cli.py` (add `cz plan` subcommands)

**Key Decisions / Notes:**

- `cz plan register <path> <status>` -- associates plan with current session
- `cz plan status --json` -- shows current plan and its status
- Plan registration stored in session directory as `plan.json`
- Reads plan file frontmatter to extract Status, Approved, Iterations fields
- Status values: PENDING, COMPLETE, VERIFIED

**Definition of Done:**

- [ ] `cz plan register docs/plans/test.md PENDING` creates plan association
- [ ] `cz plan status --json` returns plan path and parsed frontmatter
- [ ] Plan status is persisted in session directory

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_plan.py -q`

### Task 6: Hook Scripts (Context Monitor, TDD Enforcer, File Checker)

**Objective:** Create original hook scripts that provide context monitoring, TDD enforcement, and file quality checks for Claude Code.

**Dependencies:** Task 2

**Files:**

- Create: `tools/cohezion-engine/src/cohezion_engine/hooks/context_monitor.py`
- Create: `tools/cohezion-engine/src/cohezion_engine/hooks/tdd_enforcer.py`
- Create: `tools/cohezion-engine/src/cohezion_engine/hooks/file_checker.py`
- Create: `tools/cohezion-engine/src/cohezion_engine/hooks/__init__.py`
- Create: `.claude/hooks/hooks.json` (or update existing)
- Test: `tools/cohezion-engine/tests/test_hooks.py`

**Key Decisions / Notes:**

- **Context monitor:** PostToolUse hook that checks context percentage and emits warnings at 80%/90%. Reads `TOOL_USE_ID`, `TOOL_NAME`, `TOOL_INPUT` from Claude Code hook environment. Outputs user-facing warnings.
- **TDD enforcer:** PostToolUse hook on Write/Edit that checks if production code was written without a corresponding test file change. Reads tool input to determine file paths. Warns if non-test file modified without test file in same session.
- **File checker:** PostToolUse hook on Write/Edit that checks file size (warn > 300 lines, error > 500 lines). Simple line-count check.
- Hook scripts read from stdin (Claude Code passes tool context as JSON) and output to stdout
- Hooks follow Claude Code's hook protocol: exit 0 = pass, exit 2 = block with message

**Definition of Done:**

- [ ] Context monitor outputs warning at 80% and CLEAR_NEEDED at 90%
- [ ] TDD enforcer warns when production code modified without test changes
- [ ] File checker warns on files exceeding 300 lines
- [ ] All hooks follow Claude Code hook protocol (stdin JSON, exit codes)
- [ ] hooks.json correctly references the new hook scripts

**Verify:**

- `cd tools/cohezion-engine && uv run pytest tests/test_hooks.py -q`

### Task 7: Self-Contained Rules Rewrite

**Objective:** Rewrite the Claude Code rules files to be self-contained, replacing all `~/.pilot/bin/pilot` references with `cz` commands.

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5

**Files:**

- Modify: `.claude/rules/context-continuation.md` (replace `pilot` → `cz`)
- Modify: `.claude/rules/workflow-enforcement.md` (replace `pilot` → `cz`)
- Modify: `.claude/rules/pilot-cli.md` → rename to `.claude/rules/cz-cli.md`
- Create: `.claude/rules/cz-cli.md` (new CLI reference for cohezion-engine)

**Key Decisions / Notes:**

- **Two-tier rules:** Global rules are at `~/.claude/rules/` (installed by Pilot, not ours to modify in-place). Project-scoped rules at `<vault>/.claude/rules/` can SHADOW global rules when they have the same filename. Write vault-scoped versions that shadow the global Pilot-referencing ones.
- **Files to shadow:** Only rules that reference `~/.pilot/` need shadowing: `context-continuation.md`, `workflow-enforcement.md`, `pilot-cli.md`
- **New vault-scoped file:** Create `.claude/rules/cz-cli.md` (vault-scoped) to document `cz` commands
- **Do NOT touch** `~/.claude/rules/*.md` (global Pilot files) -- they remain as installed
- The concepts stay the same; only tool references change in the vault-scoped rewrites:
  - `~/.pilot/bin/pilot check-context --json` → `cz context --json`
  - `~/.pilot/bin/pilot send-clear` → `cz session send-clear`
  - `~/.pilot/bin/pilot register-plan` → `cz plan register`
  - `~/.pilot/bin/pilot worktree *` → `cz worktree *`
  - `~/.pilot/sessions/$PILOT_SESSION_ID/` → `~/.cohezion-engine/sessions/$COHEZION_SESSION_ID/`
  - `PILOT_SESSION_ID` env var → `COHEZION_SESSION_ID`
- Keep all behavioral rules (TDD, verification, debugging, coding standards) as-is -- these are general engineering practices
- Do NOT create vault-scoped copies of rules that don't reference Pilot (e.g., `tdd-enforcement.md`, `coding-standards.md`, `systematic-debugging.md`)

**Definition of Done:**

- [ ] No remaining references to `~/.pilot/` in any rules file
- [ ] No remaining references to `PILOT_SESSION_ID` in any rules file
- [ ] New `cz-cli.md` documents all `cz` subcommands accurately
- [ ] All `cz` command references match actual CLI implementation from Tasks 1-5

**Verify:**

- `grep -r "pilot" .claude/rules/ | grep -v "autopilot\|copilot"` returns no matches
- `grep -r "PILOT_SESSION_ID" .claude/rules/` returns no matches

### Task 8: Self-Contained Skills Rewrite (Spec Workflow)

**Objective:** Write original skill files for the spec-driven development workflow (spec, spec-plan, spec-implement, spec-verify) that use `cz` commands instead of Pilot.

**Dependencies:** Task 7

**Files:**

- Create: `.claude/commands/spec.md`
- Create: `.claude/commands/spec-plan.md`
- Create: `.claude/commands/spec-implement.md`
- Create: `.claude/commands/spec-verify.md`
- Create: `.claude/commands/learn.md`
- Create: `.claude/commands/sync.md`
- Create: `.claude/commands/vault.md`

**Key Decisions / Notes:**

- **Skill format:** Claude Code skills are registered via plugin JSON. Place skills in `.claude/skills/<name>/SKILL.md` AND register each in `.claude/settings.json` under the skills plugin array. OR use the Claude Code commands format: `.claude/commands/<name>.md` for slash commands (simpler, no plugin registration needed).
- **Use commands format (simpler):** Create `.claude/commands/spec.md`, `.claude/commands/spec-plan.md`, etc. These become `/spec`, `/spec-plan` slash commands automatically when placed in `.claude/commands/`.
- Write these from scratch based on the *concepts* described in our rules files (spec-driven development, TDD loop, verification agents)
- Do NOT read or copy Pilot's skill files -- write original content
- The spec workflow follows the same conceptual phases: plan → implement → verify
- Reference `cz` CLI commands for all system interactions
- Skills should be self-documenting -- include all context an implementer needs

**Definition of Done:**

- [ ] `/spec` command dispatches to spec-plan, spec-implement, spec-verify based on plan status
- [ ] `/spec-plan` command defines exploration, planning, verification, approval flow
- [ ] `/spec-implement` command defines TDD loop for each task
- [ ] `/spec-verify` command defines testing, code review, execution verification
- [ ] No references to Pilot or `~/.pilot/` in any command file
- [ ] All command files are valid markdown and appear as Claude Code slash commands

**Verify:**

- `grep -r "pilot" .claude/commands/ | grep -v "autopilot\|copilot"` returns no matches
- All 7 command files exist in `.claude/commands/`

### Task 9: Verification Agent Prompts

**Objective:** Write original verification agent prompt files used by the spec workflow's paired review system.

**Dependencies:** Task 8

**Files:**

- Create: `.claude/agents/plan-verifier.md`
- Create: `.claude/agents/plan-challenger.md`
- Create: `.claude/agents/spec-reviewer-compliance.md`
- Create: `.claude/agents/spec-reviewer-quality.md`

**Key Decisions / Notes:**

- These are prompt files that define what each verification agent checks
- **plan-verifier:** Checks plan against user requirements, finds missing features, scope issues
- **plan-challenger:** Adversarial review -- challenges assumptions, finds failure modes, hidden dependencies
- **spec-reviewer-compliance:** Checks code implements plan correctly, all DoD criteria met
- **spec-reviewer-quality:** Checks code quality, test coverage, error handling, security
- Write original prompts based on the *purpose* of each role, not copying existing prompts
- Agent prompts include instructions on output format (JSON findings with severity levels)

**Definition of Done:**

- [ ] All four agent prompts exist and define clear review criteria
- [ ] Each agent has defined output format (JSON with findings array)
- [ ] No references to Pilot in agent prompts
- [ ] Agents cover complementary review aspects (no redundancy)

**Verify:**

- All four files exist in `.claude/agents/`
- `grep -r "pilot" .claude/agents/ | grep -v "autopilot\|copilot"` returns no matches

### Task 10: Integration Testing and CLI Smoke Tests

**Objective:** End-to-end tests verifying the full workflow works: CLI commands, hooks, and rule/skill coherence.

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6

**Files:**

- Create: `tools/cohezion-engine/tests/test_integration.py`
- Create: `tools/cohezion-engine/tests/conftest.py` (shared fixtures)

**Key Decisions / Notes:**

- Test the CLI end-to-end: `cz context`, `cz session`, `cz worktree`, `cz plan`
- Test hook scripts with mock Claude Code input
- Verify all rules files have no Pilot references
- Verify all skills files have no Pilot references
- Use temporary directories for session/worktree tests
- Test JSON output format matches expected schema

**Definition of Done:**

- [ ] `uv run pytest` passes with 0 failures
- [ ] CLI smoke tests verify all subcommands respond correctly
- [ ] Hook tests verify correct exit codes and output
- [ ] Integration test verifies worktree create → diff → sync → cleanup cycle
- [ ] Grep verification confirms no remaining Pilot references

**Verify:**

- `cd tools/cohezion-engine && uv run pytest -q`
- `grep -r "~/.pilot" .claude/rules/ .claude/skills/ .claude/agents/ .claude/hooks/` returns no matches

## Testing Strategy

- **Unit tests:** Each module (context, session, worktree, plan) tested independently with mocked filesystem/git
- **Integration tests:** Full CLI command tests using subprocess and temporary directories
- **Hook tests:** Mock Claude Code hook protocol (stdin JSON, exit codes)
- **Coherence tests:** Automated grep to verify no Pilot references remain
- **Manual verification:** Run `cz` commands in a real terminal to verify human-readable output

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Context JSONL format changes | Low | Med | Token sum from JSONL is stable; if fields change, degrade gracefully to "unknown" status |
| Clean-room violation (accidentally reading Pilot source) | Low | High | Explicit constraint in plan: never read `.so`, hook `.py`, agent `.md`, or `.cjs` files from Pilot |
| `cz session send-clear` mechanism unclear | Med | Med | Research Claude Code's `/clear` command behavior independently; implement as subprocess call |
| Worktree git operations fail on edge cases | Med | Low | Comprehensive error handling with JSON error responses; test with dirty working trees |
| Skills format incompatibility | Low | Med | Test skills with Claude Code's skill loader; follow official plugin documentation |

## Open Questions

- How does Claude Code's `/clear` command work programmatically? Can we trigger it via subprocess, or do we need a different mechanism for session restarts?
- ~~What environment variables does Claude Code expose for context token tracking?~~ **RESOLVED:** No env var exists. Context is read from session JSONL at `~/.claude/projects/<slug>/<session-uuid>.jsonl` by summing usage fields across assistant messages.
- Should we support the `sx` vault command integration, or is that a separate concern?

### Deferred Ideas

- Statusline formatting (`cz statusline`) -- nice-to-have, can add later
- Memory/observation system integration -- depends on existing MCP infrastructure
- Auto-update mechanism -- not needed for internal tool
- Web viewer for session history -- separate project
