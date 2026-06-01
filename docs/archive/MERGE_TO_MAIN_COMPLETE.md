---
title: "Polish Campaign — Merge to Main BLOCKED"
date: 2026-04-23
campaign: synthetic-sniffing-panda Wave ψ6
status: BLOCKED
---

# Merge results

| PR | Branch | Status | Merge SHA | Time |
|---|---|---|---|---|
| #76 | polish/code-quality | BLOCKED — required-checks-stuck-queued | n/a | n/a |
| #77 | polish/refactors | NOT ATTEMPTED (stacked on #76) | n/a | n/a |
| #78 | polish/tests | NOT ATTEMPTED (stacked on #77) | n/a | n/a |
| #79 | polish/research-deep-think | NOT ATTEMPTED (stacked on #78) | n/a | n/a |
| #80 | polish/design-artifacts | NOT ATTEMPTED (stacked on #79) | n/a | n/a |
| #81 | polish/meta | NOT ATTEMPTED (stacked on #80) | n/a | n/a |

# Blocker

The `main` branch ruleset 12910460 requires four status checks before merge:

- `lint`
- `validate`
- `commit-lint`
- `ci-status`

These checks are jobs inside `.github/workflows/ci.yml` and `.github/workflows/commit-lint.yml`. Both workflows are stuck in `queued` status because the repo has only **one self-hosted runner** (`t30-runner`) and it is `busy=true`. The CI Pipeline run for PR #76 was created at `2026-04-24T12:28:09Z` and remained `queued` for 25+ minutes — six PRs each triggering ~10 workflows have saturated the single runner.

**`gh pr merge 76 --merge --delete-branch` failed with:**
> "Pull request manderson240/cohezion#76 is not mergeable: the base branch policy prohibits the merge."

The campaign brief explicitly disallows `--admin` (would bypass branch protection) and `--auto` would silently wait indefinitely without producing observable progress.

# What was actually done

1. Authenticated to GitHub (✓)
2. Listed all 6 PRs, confirmed all draft + targeting `main` (✓)
3. Inspected CI for each PR — all show `test (3.11)` failing (pre-existing baseline) and three (77/78/79) show CodeQL failing (CodeQL note: "Alerts not introduced by this pull request might have been detected because the code changes were too large" — pre-existing alerts in changed files, not new vulnerabilities)
4. Inspected branch protection — `Branch not protected` via legacy API; **ruleset 12910460** found via `repos/.../rules/branches/main` API — requires `lint`, `validate`, `commit-lint`, `ci-status`
5. Marked PR #76 as ready for review (✓)
6. Attempted `gh pr merge 76 --merge --delete-branch` → blocked by ruleset
7. Inspected runner pool: 1 runner online, busy
8. STOPPED per hard constraint "If ANY merge fails, STOP and report"

# Final main state (unchanged)

- main HEAD: `ffaf26888 feat(bmad): add BMAD-METHOD v6.3.0 skill definitions + scope playwright hook (#74)`
- Total commits added to main from this campaign: **0** (none merged)

# Local cleanup

Skipped — no PRs merged, no remote branches deleted.

# Follow-up needed (user action)

The user must choose one of:

**Option A — Wait for runner to drain.** Re-run merge attempt once `t30-runner` finishes its current backlog. With 6 stacked PRs × 4 required checks each, the runner needs to clear at least 4 jobs for PR #76 alone. Likely many hours to a day if runner is also processing other repo activity.

**Option B — Bypass ruleset for this campaign.** The user (as repo admin) can:
- Run `gh pr merge 76 --merge --delete-branch --admin` themselves (this auth path is forbidden to me by the campaign brief but available to the user)
- OR temporarily disable ruleset 12910460
- OR add additional self-hosted runners to drain the queue

**Option C — Use `--auto` flag.** `gh pr merge 76 --merge --delete-branch --auto` queues the merge to fire once required checks pass. This was not attempted because it requires waiting indefinitely with no observable progress, and the campaign brief expects deterministic per-PR outcomes.

# State left for resumption

- PR #76 is now in **ready** state (was draft) — this is irreversible without a human action; harmless
- PRs #77-#81 are still in **draft** state
- All polish/* branches still exist on remote
- `worktree-synthetic-sniffing-panda` branch is unchanged
- The `t30-runner` self-hosted runner exists and is online but saturated

# Verification recipe

```bash
# Re-check whether the queue has drained:
gh run list --branch polish/code-quality --limit 5 --json status,workflowName

# Re-check required checks once CI Pipeline completes:
gh pr checks 76 --required

# Once all 4 required checks (lint, validate, commit-lint, ci-status) are green:
gh pr merge 76 --merge --delete-branch
# Then proceed in order: 77, 78, 79, 80, 81 (each requires re-ready + waiting for green)
```

# Follow-up: 1-week-out cleanup agent

NOT scheduled because the campaign did not actually complete. Recommend scheduling AFTER the merges actually land (re-run this orchestrator once runner queue drains).
