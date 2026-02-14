# Repository Root Cleanup Implementation Plan

Created: 2026-02-14
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)

## Summary

**Goal:** Clean up 198 loose markdown files, 50+ non-markdown artifacts, and stale directories from the repo root accumulated across sessions 40-57+. Archive markdown files to `docs/archive/` (committed to git), delete non-markdown clutter, add `.gitignore` patterns to prevent future accumulation.

**Architecture:** Sequential file operations with checkpoint commits after each task for safe rollback. No code changes to `src/` or `tests/`.

**Tech Stack:** Bash (file operations), git (staging removals + checkpoint commits), `.gitignore` patterns

## Scope

### In Scope

- Archive ~193 non-essential root `.md` files to `docs/archive/` (committed to git for audit trail)
- Delete ~50 non-markdown root artifacts (`.txt`, `.json`, `.sh`, `.service` files)
- Remove stale root directories (`cohezion-session-54/`, `TASKS_BACKUP_*/`, `TEAM_BACKUP_*/`, `kyutai-mcp-server-archive-*/`)
- Update `.gitignore` with patterns to prevent future session artifact accumulation
- Preserve essential root files (CLAUDE.md, README.md, CONTRIBUTING.md, CREDITS.md, CLA, config files)

### Out of Scope

- Changes to `src/`, `tests/`, `cloud-vault-mcp/`, or other code directories
- Refactoring or reorganizing the `docs/` directory itself (beyond adding `archive/`)
- Cleaning up files inside subdirectories (e.g., `cache/`, `data/`)
- Modifying any Python code or test files

## Prerequisites

- Git worktree created for isolated work
- No other sessions actively modifying root files
- **Pre-flight check:** Run `rg -l 'SESSION_|PHASE_|TASK_.*COMPLETION' tests/ src/` to identify any code references to root artifacts BEFORE archiving/deleting

## Context for Implementer

- **File counting:** Always use `find . -maxdepth 1 -name '*.md' | wc -l` (NOT `ls -1 *.md | wc -l` which may expand globs into subdirectories)
- **Essential root files to KEEP:** CLAUDE.md, README.md, CONTRIBUTING.md, CREDITS.md, CONTRIBUTOR_LICENSE_AGREEMENT.md, pyproject.toml, Makefile, .gitignore, .mcp.json, mcp_servers.json, docker-compose.yml, cloudbuild.yaml, pytest.ini, uv.lock, .pre-commit-config.yaml, .nvmrc, .env.sheets-research.example, model_registry.json
- **Key fact:** 104 of the 198 markdown files are git-tracked, 94 are untracked
- **Gotcha — modified tracked files:** Some tracked files have unstaged modifications. For these: (1) `cp -L file docs/archive/` FIRST to preserve working tree version, (2) then `git rm -f file` to remove from git. The `-L` flag dereferences any symlinks. The `-f` flag is needed because `git rm` blocks on modified files.
- **Checkpoint commits:** After each task, create a checkpoint commit. This provides atomic rollback — if any task fails, `git reset --hard` to the previous checkpoint.
- **Domain context:** These files accumulated from AI-assisted development sessions. The vault (`~/vaults/cohezion-vault/`) already captures decisions, experiments, and patterns — these root files are redundant.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Archive non-essential markdown files to docs/archive/
- [ ] Task 2: Delete non-markdown root clutter
- [ ] Task 3: Remove stale root directories
- [ ] Task 4: Update .gitignore with prevention patterns
- [ ] Task 5: Verify essential files preserved and repo health

**Total Tasks:** 5 | **Completed:** 1 | **Remaining:** 4

## Implementation Tasks

### Task 1: Archive Non-Essential Markdown Files

**Objective:** Move ~193 non-essential `.md` files from repo root to `docs/archive/`, preserving them in git for audit trail.

**Dependencies:** None

**Files:**

- Create: `docs/archive/` directory
- Move: All root `.md` files EXCEPT the essential keep list

**Key Decisions / Notes:**

- **Essential files to KEEP at root (NEVER archive these):**
  - `CLAUDE.md` — Project instructions for Claude Code
  - `README.md` — Project readme
  - `CONTRIBUTING.md` — Contribution guidelines
  - `CREDITS.md` — Credits
  - `CONTRIBUTOR_LICENSE_AGREEMENT.md` — Legal
- **Safety gate:** Before ANY file operations, assert all 5 essential files exist. If any is missing, ABORT.
- **Pre-flight:** Run `find . -maxdepth 1 -type l -name '*.md'` to check for symlinks. Use `cp -L` (dereference) when copying.
- **Execution flow for EACH non-essential .md file:**
  1. `cp -L file docs/archive/` — preserve working tree version (dereferencing symlinks)
  2. If git-tracked: `git rm -f file` — remove from git (force needed for modified files)
  3. If untracked: `rm file` — simple remove
- **Checkpoint:** After all files archived, create commit: `git add docs/archive/ && git commit -m "chore: archive 193 session artifacts to docs/archive/"`

**Definition of Done:**

- [ ] `docs/archive/` directory exists with archived files
- [ ] Only 5 essential `.md` files remain at repo root
- [ ] No data loss — snapshot before/after confirms all non-essential files archived
- [ ] Checkpoint commit created

**Verify:**

- Before archiving: `find . -maxdepth 1 -name '*.md' -type f > /tmp/before-archive.txt` (baseline)
- After archiving: `find . -maxdepth 1 -name '*.md' -type f | sort` returns exactly 5 essential files
- `find docs/archive -name '*.md' -type f | wc -l` matches baseline minus 5
- Assert essential files NOT in archive: `ls docs/archive/CLAUDE.md 2>/dev/null` returns error
- `git log -1 --oneline` shows checkpoint commit

### Task 2: Delete Non-Markdown Root Clutter

**Objective:** Remove ~50 stale non-markdown artifacts from repo root that are session-specific or no longer needed.

**Dependencies:** Task 1 (sequential — checkpoint commit must exist first for rollback safety)

**Files:**

- Delete: Stale `.txt`, `.json`, `.sh`, `.service` files at root

**Key Decisions / Notes:**

- **Files to KEEP at root** (config/build files):
  - `pyproject.toml`, `Makefile`, `uv.lock`, `pytest.ini`
  - `.gitignore`, `.mcp.json`, `mcp_servers.json`
  - `docker-compose.yml`, `docker-compose.notebooks.yml`, `cloudbuild.yaml`
  - `.pre-commit-config.yaml`, `.nvmrc`, `.env.sheets-research.example`
  - `model_registry.json` — referenced by `src/cohezion/skills/cohezion_mcp.py` (KEEP)
- **Pre-flight reference check (MANDATORY before any deletion):**
  1. Build list of files to delete
  2. For each file: `rg -l '<filename>' src/ tests/` — if matches found, SKIP and report
  3. Only delete files with zero code references
- **Files to DELETE** (session artifacts, stale configs):
  - All `SESSION_*.txt` files
  - All `PHASE_*.txt` files
  - `TASK_7_MANIFEST.txt`
  - `cleanup_*.json`, `cleanup_*.sh` — old cleanup attempts
  - `PRUNING_CANDIDATES.json`, `SNAPSHOT.json`, `CROSS_TRACK_INTEGRATION.json`
  - `KNOWLEDGE_CORE.json`, `mission_checkpoint.json`, `surreal_insights.json`
  - `task_patterns.json`, `test_results.json`
  - `setup_*.sh` (setup_env.sh, setup_ipc.sh, setup_system.sh, setup_demogateway.sh)
  - `quick_setup.sh`, `toggle_display.sh`, `smart_loader.sh`
  - `validation_test_suite.sh`, `validation_test_suite_phase_c.sh`
  - `sheets-research-daemon.service`, `smart-loader.service`
  - `sprint-status.yaml`, `requirements_overnight.txt`
  - `opencode-*.json`, `local_reasoner_benchmark.json`
  - `model_registry_ascended.json`
  - Stale `.txt` files: `ARCHITECTURE_DIAGRAM.txt`, `debug_stderr.txt`, `DEPLOYMENT_READY.txt`, `ENFORCEMENT_VERIFICATION.txt`, `FINAL_METRICS_VERIFICATION.txt`, `FINAL_STATUS.txt`, `large_files.txt`, `STATUS_UPDATE_100.txt`, `verify_output.txt`
- **Checkpoint:** After deletion, commit: `git commit -am "chore: delete stale non-markdown root artifacts"`

**Definition of Done:**

- [ ] All stale `.txt`, `.json`, `.sh`, `.service` session artifacts removed from root
- [ ] Essential config files preserved (pyproject.toml, Makefile, docker-compose.yml, model_registry.json, etc.)
- [ ] No code in `src/` or `tests/` references any deleted file (verified BEFORE deletion)
- [ ] Checkpoint commit created

**Verify:**

- `find . -maxdepth 1 -name '*.txt' -type f | wc -l` returns 0
- `find . -maxdepth 1 -name '*.service' -type f | wc -l` returns 0
- `ls model_registry.json` — still exists (referenced by code)
- `rg -l 'cleanup_config\|PRUNING_CANDIDATES\|KNOWLEDGE_CORE' src/ tests/` returns no results
- `git log -1 --oneline` shows checkpoint commit

### Task 3: Remove Stale Root Directories

**Objective:** Remove directories at repo root that are session-specific backups or failed experiments.

**Dependencies:** Task 2 (sequential — checkpoint commit must exist first)

**Files:**

- Delete directories:
  - `cohezion-session-54/` — Old session worktree or stale directory
  - `TASKS_BACKUP_token-efficiency-phase-5b/` — Task backup from old session
  - `TEAM_BACKUP_token-efficiency-phase-5b/` — Team backup from old session
  - `kyutai-mcp-server-archive-failed-attempt/` — Failed experiment archive

**Key Decisions / Notes:**

- **Worktree check (MANDATORY first step):**
  1. Run `git worktree list` to see if `cohezion-session-54/` is registered
  2. If registered: `git worktree remove cohezion-session-54/` (try without force first)
  3. If not registered but directory exists: safe to `rm -rf`
  4. If `git worktree remove` fails with lock: `git worktree remove --force cohezion-session-54/`
  5. If still fails: `rm -rf cohezion-session-54/ && git worktree prune`
- Other directories: verify not git-tracked (`git ls-files <dir>`), then `rm -rf`
- **Checkpoint:** After removal, commit: `git commit -am "chore: remove stale root directories"`

**Definition of Done:**

- [ ] All 4 stale directories removed from repo root
- [ ] No broken git worktree references (`git worktree list` clean)
- [ ] No code references to deleted directories
- [ ] Checkpoint commit created

**Verify:**

- `ls -d cohezion-session-54/ TASKS_BACKUP_* TEAM_BACKUP_* kyutai-mcp-server-archive-* 2>/dev/null` returns nothing
- `git worktree list` shows only main worktree (and the spec worktree if active)
- `git log -1 --oneline` shows checkpoint commit

### Task 4: Update .gitignore with Prevention Patterns

**Objective:** Add `.gitignore` patterns to prevent future session artifact accumulation at repo root.

**Dependencies:** Task 3 (sequential — all cleanup must be done first)

**Files:**

- Modify: `.gitignore`

**Key Decisions / Notes:**

- Use specific number-prefixed patterns to avoid blocking legitimate future docs:
  - `SESSION_[0-9]*` instead of `SESSION_*` (won't block e.g. SESSION_GUIDELINES.md)
  - `PHASE_[0-9]*` instead of `PHASE_*`
- Do NOT gitignore `docs/archive/` — archived files are committed to git for audit trail
- Add comment explaining purpose and how to override (`!` prefix for exceptions)
- Block common session artifact patterns at root only

**Definition of Done:**

- [ ] `.gitignore` contains session artifact prevention patterns
- [ ] Patterns use specific number-prefix matching to avoid false positives
- [ ] New numbered session files at root are ignored by git
- [ ] `docs/archive/` is NOT gitignored (files are committed)

**Verify:**

- `echo "test" > SESSION_99_TEST.md && git check-ignore SESSION_99_TEST.md` returns the file (ignored)
- `echo "test" > PHASE_99_TEST.md && git check-ignore PHASE_99_TEST.md` returns the file (ignored)
- `echo "test" > SESSION_GUIDELINES.md && git check-ignore SESSION_GUIDELINES.md` returns nothing (NOT ignored)
- Clean up test files after verification

### Task 5: Verify Essential Files and Repo Health

**Objective:** Confirm all essential files are preserved, no broken references, and repo is in a clean state.

**Dependencies:** Tasks 1, 2, 3, 4

**Files:**

- Read-only verification across repo

**Key Decisions / Notes:**

- Verify all 5 essential `.md` files exist at root with expected content
- Run `uv run pytest tests/ -q` to confirm no tests broke
- Run `python -c "import cohezion"` to verify no import errors from deleted files
- Check `make lint-check` passes
- If CLAUDE.md was updated during cleanup (e.g., fixing broken links to archived docs), verify it has correct content — modifications during cleanup are acceptable

**Definition of Done:**

- [ ] Essential root files present: CLAUDE.md, README.md, CONTRIBUTING.md, CREDITS.md, CLA
- [ ] `uv run pytest tests/ -q` passes with no regressions
- [ ] `python -c "import cohezion"` succeeds
- [ ] `make lint-check` passes
- [ ] `git status` shows only expected changes

**Verify:**

- `ls CLAUDE.md README.md CONTRIBUTING.md CREDITS.md CONTRIBUTOR_LICENSE_AGREEMENT.md` — all exist
- `uv run pytest tests/ -q` — passes
- `python -c "import cohezion"` — no ImportError
- `make lint-check` — passes

## Testing Strategy

- **Pre-flight checks:** Grep `src/` and `tests/` for references to root artifacts BEFORE any archiving/deletion
- **Unit tests:** Not applicable (no code changes)
- **Integration tests:** `uv run pytest tests/ -q` to verify no tests reference deleted files
- **Import check:** `python -c "import cohezion"` to verify no broken imports
- **Manual verification:** File counts before/after, spot-check archive contents

## Runtime Environment

To verify the project still works after cleanup:

- **Tests:** `uv run pytest tests/ -q` (should pass ~2,854 tests)
- **Import check:** `python -c "import cohezion"` (should not raise ImportError)
- **API start:** `uv run uvicorn cohezion.api:app --reload` (port 8080, optional)
- **Lint:** `make lint-check` (should pass)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Test references deleted file | Low | Medium | Pre-flight: `rg -l '<filename>' tests/ src/` BEFORE deletion; if matches found, skip file and report |
| Essential file accidentally archived | Low | High | Assert all 5 essential files exist BEFORE archiving starts; archive script explicitly excludes keep-list; abort if any essential file would be moved |
| Modified tracked files lose data | Medium | High | For modified tracked files: `cp -L file docs/archive/` FIRST, then `git rm -f file`. The `-L` dereferences symlinks, `-f` handles modified files. Archive preserves working tree version. |
| Git worktree removal fails | Low | Low | Run `git worktree list` first; if listed try `git worktree remove`; if lock error use `--force`; if still fails `rm -rf` then `git worktree prune` |
| Partial task failure leaves broken state | Low | Medium | Checkpoint commits after each task. If any task fails, `git reset --hard` to previous checkpoint for clean rollback |
| Future sessions recreate clutter | Medium | Medium | `.gitignore` patterns `SESSION_[0-9]*`, `PHASE_[0-9]*`, `TASK_[0-9]*` block numbered session artifacts |

## Open Questions

- None — approach is straightforward file operations with safety checks

### Deferred Ideas

- Reorganize `docs/` directory structure (beyond adding `archive/`)
- Clean up files inside subdirectories (`cache/`, `data/`, `reports/`)
- Add pre-commit hook to enforce root file hygiene
