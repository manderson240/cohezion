---
title: "Retrospective: cohezion-engine spec workflow (session 2026-02-22)"
date: 2026-02-22
status: accepted
tags: [decision, workflow, retrospective, spec-driven, compound-engineering]
aspect: thinker
neural:
  activation: 0.85
  stage: mature
  synapse_in: 5
  synapse_out: 10
---

## Context

First full end-to-end run of the cohezion-engine (`cz`) spec workflow, replacing Pilot. The session implemented Tasks 8-10 of the abstract-apply-pilot plan (Tasks 1-7 were from a prior session), ran full verification, and merged to `track-c`.

## What Worked

- **Worktree continuation** — detecting the existing worktree from a prior session worked cleanly
- **Verification agents in parallel** — background Task agents + polling for JSON output files is the right pattern; both agents finished before manual verification steps completed
- **62 tests passing** — TDD throughout produced solid coverage with no regressions
- **Coherence tests** — grep-based integration tests for "no pilot references" caught real issues during verification
- **`cz` replacing Pilot** — worktree create/detect/sync/cleanup all worked via the new CLI when Pilot trial expired

## What Didn't Work

### 1. Session ID never resolved in agent prompts
Skills passed `~/.cohezion-engine/sessions/<session-id>/` as a literal placeholder. Agents wrote findings to incorrect paths until the main session re-launched them with explicit paths.

**Fix:** Resolve session ID before constructing Task prompts:
```bash
SESSION_ID=$(cz session status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
```

### 2. Test command hardcoded to project-specific path
`spec-implement` and `spec-verify` hardcoded `cd tools/cohezion-engine && uv run pytest -q`. This makes the workflow unusable for non-Python projects or different directory structures.

**Fix:** Add a `## Runtime Environment` section to every plan with `test_command`, `lint_command`, and `type_check_command`. Skills read these from the plan.

### 3. No context checks during TDD loop
`cz context --json` returns UNKNOWN from subprocess shell (no active session JSONL). Context checks were effectively no-ops. At 90%+ the workflow would have lost work.

**Fix:** Add periodic context estimation via JSONL file discovery using the project slug approach. Also add explicit 80%/90% handoff instructions in the TDD loop.

### 4. spec-verify Step 3.4 was vault-specific
The grep verification step checked for pilot references — correct for this project but wrong for every other project.

**Fix:** Replace with "run the project's coherence tests" (from Runtime Environment section), or omit entirely.

### 5. Agent scope too broad
Agents were asked to read ALL changed files (38 files). Most findings were in 5-7 core files. Reading all files wastes tokens and dilutes focus.

**Fix:** Each Task in the plan lists its specific Files. Agents should read only files listed in each task's Files section, then expand if needed.

### 6. should_fix issues found in verification
8 should_fix issues found by agents — all valid, all fixed. But they could have been caught earlier:
- Broad exception handling (`except Exception`) — should be linting rule
- Unnecessary `importlib.reload()` — TDD enforcer hook could catch this
- `.gitignore` modified before success check — ordering issue

**Lesson:** The verification agents are doing work that hooks and linting should catch earlier in the loop.

## Decisions

### D1: Runtime Environment section in every plan
All future plans must include:
```markdown
## Runtime Environment
- **test_command:** `uv run pytest -q` (from project root)
- **lint_command:** `ruff check .`
- **type_check_command:** `basedpyright src`
- **project_root:** `tools/my-project/`
```

### D2: Explicit session ID resolution before agent Task calls
Skills must resolve the session ID to a concrete value before constructing agent prompts. Never pass `<session-id>` as a placeholder.

### D3: Context check cadence in TDD loop
After every 2-3 tasks (not just at 80%/90%), check context and document remaining work in continuation file if approaching threshold.

### D4: Scope-limited agents
Agent prompts should include the Files list from each plan task, directing agents to read those files first. Only expand scope if findings are insufficient.

### D5: Move coherence checks to project-specific tests
The "no old-CLI references" check belongs in the project's integration tests (as we did with `TestCoherenceChecks`), not in a generic skill step.

## Related

- [[multi-session-compound-engineering-workflow|Multi-Session Compound Engineering Workflow]] — the worktree isolation pattern exercised in this run
- [[2026-02-22-daily-cli-tool-update-via-systemd-timer|Daily CLI Tool Update via Systemd Timer]] — decided in the same session; motivation was keeping `cz` CLI current
- [[daily-cli-tool-update-with-version-comparison|Daily CLI Tool Update Pattern]] — pattern that operationalizes keeping CLI tools up to date
- [[compound-engineering|Compound Engineering]] — the framework this retrospective improves
- [[2026-02-22-asyncio-lock-in-init-not-class-level]] — async isolation fix that enabled 62 tests to pass in the same session
- [[2026-02-22-pytestmark-asyncio-module-level]] — module-level async marking fix discovered during same session's test healing
- [[2026-02-22-post-crash-venv-recovery-pytest-missing-despite-pyprojecttoml]] — venv recovery challenge encountered during this session's test run
- [[role-based-multi-agent-coordination]] — parallel verification agent pattern that this retrospective validates as effective
- [[workflow-orchestration]] — the `cz spec` workflow is the primary orchestration implementation this retrospective evaluates
- [[cohezion]] — this retrospective validates cohezion-engine as the replacement for the Pilot workflow CLI

## Next Steps for Compound Engineering

1. ~~Update spec workflow skills with the above fixes (D1-D5)~~ — **DONE** (were already incorporated during original implementation)
2. ~~Add `cz context` fallback~~ — **DONE** (2026-02-23): `context.py` now uses two-strategy JSONL discovery: cwd-slug first, then global most-recent scan. Eliminates UNKNOWN in subprocess/hook contexts.
3. Consider adding a `cz plan template` command that generates plans with the Runtime Environment section pre-filled
4. The TDD enforcer hook needs strengthening: detect and warn on `except Exception` pattern

## PILOT Removal (2026-02-23)

PILOT fully uninstalled:
- `~/.pilot/` deleted
- `~/.claude/mcp.json`: migrated context7, web-search, grep-mcp, web-fetch directly (mem-search lost — was PILOT-specific `.cjs`)
- `~/.claude/rules/pilot-cli.md` → deleted; replaced with `~/.claude/rules/cz-cli.md`
- `~/.claude/rules/workflow-enforcement.md`: all `~/.pilot/bin/pilot` and `pilot:*` refs replaced with `cz`
- `~/.claude/rules/context-continuation.md`: all `PILOT_SESSION_ID` and `~/.pilot/sessions/` refs replaced with `cz` equivalents
- `~/.claude/settings.json`: pilot MCP permissions → `mcp__context7__*` etc; `statusLine.command` → removed; `companyAnnouncements` → removed
- 62/62 tests passing after context fix
