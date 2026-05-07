---
title: "Auto-merge ATTEMPTED on 6 polish PRs — BLOCKED by repo merge-method config"
date: 2026-04-23
campaign: synthetic-sniffing-panda Wave ψ7
status: AUTO-MERGE-BLOCKED-NEEDS-USER-DECISION
---

# Summary

**Phase 1 (drafts → ready): SUCCESS** — all 5 remaining drafts flipped.
**Phase 2 (auto-merge enable): FAILED** — repo only allows squash, agent scope only allowed `--merge`.

The 6 PRs are now ready-for-review and BLOCKED-on-CI, but auto-merge is NOT enabled. They will sit open until the user takes action.

# PR state after agent run

| PR  | Branch                       | Ready? | Auto-merge | mergeStateStatus | Base | Head Stack |
|-----|------------------------------|--------|------------|------------------|------|------------|
| #76 | `polish/code-quality`        | yes (ψ6) | NOT enabled | BLOCKED | main | parallel |
| #77 | `polish/refactors`           | yes (ψ7) | NOT enabled | BLOCKED | main | parallel |
| #78 | `polish/tests`               | yes (ψ7) | NOT enabled | BLOCKED | main | parallel |
| #79 | `polish/research-deep-think` | yes (ψ7) | NOT enabled | BLOCKED | main | parallel |
| #80 | `polish/design-artifacts`    | yes (ψ7) | NOT enabled | BLOCKED | main | parallel |
| #81 | `polish/meta`                | yes (ψ7) | NOT enabled | BLOCKED | main | parallel |

# Why auto-merge failed

```
$ gh pr merge 76 --merge --delete-branch --auto
GraphQL: Merge method merge commits are not allowed on this repository (enablePullRequestAutoMerge)
```

Repo `manderson240/cohezion` configuration:
```json
{"deleteBranchOnMerge": true,
 "mergeCommitAllowed": false,
 "rebaseMergeAllowed": false,
 "squashMergeAllowed": true,
 "viewerDefaultMergeMethod": "SQUASH"}
```

The repo only allows **squash**. The agent's authorization scope (per the user's auto-merge instructions) only permitted `--merge` (citing "stacked-branch safety per ψ6 rationale"), and explicitly DISALLOWED `--squash` and `--rebase`.

# Important: stacked-branch rationale doesn't apply here

All 6 PRs target `main` directly (verified via `baseRefName`). They are **parallel**, not stacked. The ψ6 rationale for `--merge` (preserve stacked branch base SHAs) does not apply.

If the user is willing to use squash-merge, auto-merge can be enabled trivially:
```bash
for pr in 76 77 78 79 80 81; do
  gh pr merge $pr --squash --delete-branch --auto
done
```

# What you (the user) need to decide

| Option | Action | Tradeoff |
|--------|--------|----------|
| **A** | Re-authorize agent for `--squash` (or run the loop yourself) | Each PR collapses to 1 commit on main. Loses per-commit history within each polish branch. |
| **B** | Allow merge commits at the repo level, then re-run `--merge` | Preserves history. Requires settings change at https://github.com/manderson240/cohezion/settings → "Pull Requests" → check "Allow merge commits". |
| **C** | Enable both squash AND merge at repo level, then user can pick per-PR | Most flexible. |
| **D** | Leave PRs sitting; merge each manually as CI clears | Slowest, but full control. |

# Hard-constraint adherence

- DID NOT use `--admin` (out of scope)
- DID NOT use `--squash` or `--rebase` (out of scope)
- DID NOT modify branch protection rulesets
- DID NOT touch CI workflows
- Stopped at first merge-config error rather than working around it

# Follow-up scheduled

- **Date:** 2026-04-30 09:03 local
- **Method 1 (primary):** CronCreate task `f77fd92c` (session-only — dies if this Claude session ends)
- **Method 2 (durable backup):** Recipe at `~/.claude/scheduled/2026-04-30-polish-campaign-followup.md`
- **What it will check:** PR merge status of #76–#81, test/ruff/mypy delta vs baseline (968p/86f/51e, 1022 ruff, 783 mypy), produces 200-word status update

# Files modified

- This worktree: `AUTO_MERGE_QUEUED.md` (new) — single new file, single commit on `worktree-synthetic-sniffing-panda` branch
- `~/.claude/scheduled/2026-04-30-polish-campaign-followup.md` (new, outside repo)

# Watch live

https://github.com/manderson240/cohezion/pulls?q=is%3Apr+is%3Aopen+head%3Apolish
