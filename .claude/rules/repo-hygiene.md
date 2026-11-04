# Repo Hygiene — what the 2026-11-04 root cleanup taught us (MANDATORY)

**Origin:** four root sweeps (2026-04-19, 2026-05-02, 2026-08-20, 2026-11-04). The first three
each regressed within weeks. The per-item ledger, with the commit that brought in each file, is
`docs/audits/ROOT_CLEANUP_2026-11-04.md`.

## Enforced by `root_health_guard.py`

`src/cohezion/governance/scripts/root_health_guard.py` reads the git index and fails on:

- a top-level name not in `ROOT_ALLOWLIST` (caught `satus/`, `.playwright-cli/`, `.claire/`)
- a zero-byte root file not in `ROOT_FLAG_FILES` (caught `EOF`, `package.json.harness-bak`)
- two tracked paths that differ only in case, at any depth (caught `docs/ARCHITECTURE.md` vs
  `docs/architecture.md`, which broke checkouts on macOS and Windows for nine months)

It runs, with `--self-test` first, in `.github/workflows/ci.yml`, `scripts/ci/automerge_guard.sh`
and the `root-health-guard` pre-commit hook. `tests/scripts/test_root_health_guard.py` fails if
any of those stops calling it. Adding a root entry is fine; it just has to be a reviewed edit to
`ROOT_ALLOWLIST`, in the group that says what kind of thing it is.

## The rules

1. **Never `git add -A` or `git add .` in an agent session.** Two commits (`9dce6ddd`,
   `66f5186d`) brought in most of the clutter, and neither message mentions those files. Stage
   explicit paths, then check `git diff --cached --name-only` before committing (see CLAUDE.md,
   Learning 363).
2. **Scratch goes in the session scratchpad, not the repo.** Agent tmp scripts
   (`.hermes-sessions/tmp_*.py`) and tool output written to cwd (`.playwright-cli/`) end up at
   the root.
3. **Ignoring is not untracking.** Adding a path to `.gitignore` after it's committed stops new
   files only. Run `git ls-files -ci --exclude-standard` in any sweep to list tracked files your
   ignore rules already cover, and `git rm --cached` the ones that are runtime output.
4. **Anchor root-only ignore patterns with a leading `/`.** `run_*.py` with no slash hid 88 real
   files under `scripts/` and `src/`. Before adding a pattern, check what it would hide with
   `git ls-files -ci --exclude-standard`.
5. **Untracking deletes the file on every other clone at the next pull.** Say so in the PR when
   you untrack anything someone might want to keep locally.
6. **Read a file before keeping it, and move, don't delete, anything with history or a consumer.** Two "experiments" moved in the first pass of this cleanup turned out to be 12-byte `placeholder` stubs. Archive superseded docs under
   `docs/archive/` with a date in the name, and record the move in the sweep's ledger with the
   origin commit and the lesson. Delete only empty, typo or runtime-output files.
7. **A guard nothing runs is dormant.** The 2026-04-19 guard said it "fails CI" and was never
   wired. Any new hygiene check gets a `--self-test`, a gate that runs it, and a test that the
   gate runs it (`verification-depth.md`, consumption over declaration).
8. **A collection error is not one failing test.** One import clash in
   `tests/scripts/test_producer_consumer_audit.py` stopped the whole integration step, which
   hid 217 failures across 14k tests. When a non-gating step reports "1 error", check how
   many tests it actually ran.
