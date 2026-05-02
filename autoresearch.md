# Autoresearch: PR Merge Optimization

## Objective
Merge all 11 reopenable polish/feature PRs into main and achieve full CI green.
Each experiment = rebase + push branch + observe CI outcome + merge if green.

## Metrics
- **Primary**: merged_pr_count (count, higher is better)
- **Secondary**: ci_failure_count, merge_conflict_count

## How to Run
`./autoresearch.sh` — checks PR mergeability and CI status

## Files in Scope
- Branch heads: polish/*, feature/coherent-matter-precipitation
- CI workflows: .github/workflows/
- No source modifications expected (rebase-only operations)

## Constraints
- Every merge must pass CI: lint ✅ validate ✅ commit-lint ✅ ci-status ✅
- Use `gh pr merge --auto --squash --delete-branch`
- Never `gh pr merge --admin` unless CI is permanently stuck
- Commit conventional format for merge commits

## What's Been Tried
- PR #112: merged successfully (CI fix foundation)
- 11 remaining PRs: all show CONFLICTING after branch reopens
- Root cause: base branch main advanced past their fork points
