---
branch: polish/meta
base: polish/design-artifacts
commits: 2 (incremental) / 91 (vs main)
files_changed: 10 (incremental)
loc_delta: +1877 / -3 (incremental)
campaign: synthetic-sniffing-panda (2026-04-23)
campaign_plan: ~/.claude/plans/synthetic-sniffing-panda.md
campaign_retrospective: ~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md
---

# polish/meta — Cross-Repo Lint Patches + CLAUDE.md Sync

## Summary
Tail of the merge train: 4 cross-repo lint autofix patches (for sibling repos: `observer-patch-holography`, `geak`, `autoresearch-amd`, `A2UI`) shipped as research artifacts, plus a small CLAUDE.md update reflecting the post-campaign test/file counts. The cross-repo patches are NOT applied to this monorepo — they're proposals for sibling repos to apply themselves.

## Scope
**In scope (2 commits):**
- Wave 5C — `feat(cross-repo): generate lint autofix patches for 4 sibling repos`
- Wave 5E — `docs(claude): update test/file counts post-campaign`

**Out of scope:**
- Applying the patches to the sibling repos themselves (cross-repo PRs would need to be opened against each separately — see `research/patches/INDEX.md`)
- Documentation regeneration (MEMORY.md, vault, etc.) — not in this campaign

## Wave breakdown

### Wave 5C — Cross-repo lint patches (commit 94ebbdf46)
For each of 4 sibling repos, generates:
- `<repo>-lint-autofix.patch` — applyable patch (ruff + isort + bare-except cleanup)
- `<repo>-lint-report.md` — what changed and why

Plus `research/patches/INDEX.md` for navigation.

| Sibling repo | Patch file |
|---|---|
| `observer-patch-holography` | `research/patches/observer-patch-holography-lint-autofix.patch` |
| `geak` | `research/patches/geak-lint-autofix.patch` |
| `autoresearch-amd` | `research/patches/autoresearch-amd-lint-autofix.patch` (report only — patch may be empty if nothing actionable) |
| `A2UI` | `research/patches/A2UI-lint-autofix.patch` |

These are proposals to apply in the sibling repo's own checkout via `git apply <patch>`. They are NOT applied here.

Also includes `.pre-commit-config.yaml` modifications if any (verify in diff).

### Wave 5E — CLAUDE.md test/file count sync (commit 6ecf33321)
Updates CLAUDE.md numbers (test count, file count) to reflect the post-campaign reality after all the prior PRs land. 6-line diff.

## Key metrics
- **Cross-repo patches generated**: 4 (one per sibling repo)
- **Patches applied to this repo**: 0 (patches are proposals only)
- **CLAUDE.md numerical drift fixed**: 3 lines

## Test impact
- **No source/test changes.** Test counts unchanged.

## Files changed (categorized)

| File | Notes |
|---|---|
| `research/patches/INDEX.md` | Navigation for the 4 patches |
| `research/patches/observer-patch-holography-lint-autofix.patch` | Apply via `git -C ../observer-patch-holography apply <patch>` |
| `research/patches/observer-patch-holography-lint-report.md` | What the patch does and why |
| `research/patches/geak-lint-autofix.patch` + report | (same pattern) |
| `research/patches/autoresearch-amd-lint-report.md` | (report only, patch may be empty) |
| `research/patches/A2UI-lint-autofix.patch` + report | (same pattern) |
| `.pre-commit-config.yaml` | Pre-commit config tweaks (verify diff is small) |
| `CLAUDE.md` | Test/file count sync (6 lines) |

## Reviewer guide

**Read first:**
1. `research/patches/INDEX.md` — see what each patch claims to do
2. CLAUDE.md diff — verify the new numbers are correct

**Spot-check the patches** (optional):
```bash
# In a sibling-repo checkout, dry-run the patch:
git -C ~/path/to/observer-patch-holography apply --check ../cohezion/research/patches/observer-patch-holography-lint-autofix.patch
```

## Dependencies
- **Builds on `polish/design-artifacts`** for stack ordering only — no actual code dep. Could merge against main directly.
- **Tail of the stack** — nothing depends on this PR.

## Verification recipe
```bash
git checkout polish/meta
# Verify patches are syntactically valid:
for p in research/patches/*.patch; do
  echo "=== $p ==="
  head -3 "$p"
  # If sibling repo is checked out:
  # git -C ~/dev/<sibling> apply --check $(realpath $p)
done
# Verify CLAUDE.md still parses:
grep -E "^\| .* \| " CLAUDE.md | head -3
```

## Risks
- **Stale cross-repo patches**: if the sibling repos move, the patches become unapplyable. Date-stamp the report files; treat the patches as time-sensitive proposals.
- **CLAUDE.md drift**: the numbers will drift again as soon as more code lands. Consider adding a `make sync-claude-md` target to regenerate these from real counts.
- **Pre-commit config**: any change to `.pre-commit-config.yaml` should be flagged in review — these can break local commits across the team.

## Out of scope (deferred)
- Opening PRs against the 4 sibling repos to apply their patches
- Building automation to keep CLAUDE.md numbers in sync
- Sibling-repo patch verification in CI
