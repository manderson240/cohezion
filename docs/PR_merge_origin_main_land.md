## What this lands

Integrates the long-lived `feat/adaptive-calibration-harness` branch (225 commits ahead of `main`) onto current `origin/main`, via a merge commit. Includes this session's surgical work: the `executor.py` latent-`NameError` fix, `recall_neurons` (closing the neurogenesis deposit→recall loop), two orphan-wiring fixes (`auto_generator`, `audio_telemetry`), the **Mellum-4b FIM specialist** (filling the last empty `Task` slot), plus research-feed / wiring-ledger / backlog docs.

## How conflicts were resolved

42 conflicts, resolved with **`-X ours`** (keep the feature branch's side on every conflicting hunk — this is a *land-the-branch* merge) while absorbing **all of main's non-conflicting advances** (ReflectiveDriver, AnomalyGate/ConservationFilter, SurpriseRouter, memory trust-hierarchy, Anthropic prompt-caching, skills-matrix reconcile). `103 files changed, +8354 / −239`.

Conflict set included invariant-sensitive files (`.claude/rules/harness.md`, `skill_registry.json`, 7 physics bridges) — `-X ours` keeps the harness-validated feature-branch versions.

> Note: the in-place merge was impossible in the dev environment (`scripts/` + `config/` are read-only ZFS mounts that `origin/main` modifies); performed in a writable git worktree on a side branch.

## Validation (against the merged tree)

- ✅ **Fast unit tests PASS**
- ✅ Calibrated-invariant checks PASS: validate PRIME skills, validate skill registry, H3 (safe-env)
- ✅ **Ruff debt 555 → 405** — the merge *reduced* lint errors (main's cleaner files); introduced none
- ⚠️ ruff-format / ruff-lint / mypy still report pre-existing branch debt (the branch was built with `--no-verify`) — not merge-induced

## Known pre-existing issue (NOT from this merge)

`research/posters/build_poster.py` carries a stale committed conflict marker (`>>>>>>> origin/polish/sigma-security-p1p2`) from older history — flagged for separate cleanup; it predates this branch's session work.

## Review guidance

Conflicts were auto-resolved toward the feature branch (`-X ours`). The highest-value files to spot-check are the invariant ones (`harness.md`, `skill_registry.json`, `physics/lenr.py` et al.) to confirm the feature-branch versions are the intended ones. Do **not** squash — the merge commit preserves both histories.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
