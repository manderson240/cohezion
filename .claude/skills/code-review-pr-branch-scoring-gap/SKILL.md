---
name: code-review-pr-branch-scoring-gap
description: |
  Limitation of the multi-agent code-review pipeline: confidence scoring agents
  score legitimate issues as 0 when the file being reviewed ONLY EXISTS on the
  PR branch (i.e., is a new file added by the PR, not yet on main/base branch).
  Use when: (1) code review returns "no issues found" on a PR with many new files,
  (2) confidence scoring agents fail with "file not found" or return score 0 for
  CLAUDE.md compliance issues about new files, (3) reviewing PRs with large new
  modules or entirely new subsystems.
author: Claude Code
version: 1.0.0
---

# Code Review PR Branch Scoring Gap

## Problem

The `code-review:code-review` multi-agent pipeline has a systematic blind spot for
issues in files that only exist on the PR branch (new files). Legitimate bugs are
filtered out because the Haiku confidence scorers look at the base branch (main),
not the PR branch.

## How the Pipeline Works

1. **5 parallel Sonnet reviewers** — run with PR diff context, can see new files
2. **Haiku confidence scorers** — run independently to verify each issue with a
   0-100 confidence score (issues below 80 are filtered out)
3. **The gap**: The scoring agents verify issues by looking at files in the repo.
   For new files (added by the PR), the file doesn't exist on main/base branch.
   The scorer cannot find the file to verify the issue → scores it 0 → filtered out.

## Symptoms

- A PR adds a large new file (e.g., `evolution_training_bridge.py` with 800+ lines)
- Reviewers flag CLAUDE.md violations: file size limit exceeded (300 line rule),
  missing journey tracking, etc.
- Confidence scorers return score 0 for those exact issues: "could not verify file"
- Final review says "no issues found" even though real violations exist

## Real Example (Observed in PR #26)

PR added `src/cohezion/flume/group_evolution.py` (new file, large).
- Reviewer flagged: "File exceeds 300-line limit per CLAUDE.md"
- Scorer response: "File not found in repository. Score: 0."
- Result: filtered out, not reported in final comment

## Workaround

When reviewing PRs that introduce new files:

1. **Manually check new file sizes** after running code review:
   ```bash
   gh pr diff <PR_NUMBER> --name-only | xargs -I{} bash -c \
     'if gh api repos/:owner/:repo/contents/{}?ref=<BRANCH> &>/dev/null; then \
       echo "exists"; else echo "NEW: {}"; fi'
   ```

2. **Use `--ref` when fetching new files for manual review**:
   ```bash
   gh api repos/OWNER/REPO/contents/path/to/new/file.py?ref=BRANCH_NAME \
     --jq '.content' | base64 -d | wc -l
   ```

3. **Flag awareness in review output**: If code review returns no issues on a
   PR with many new files, manually verify CLAUDE.md compliance (file size,
   docstrings, imports) for the new files.

## Root Cause (Pipeline Architecture)

The 5 Sonnet reviewers are given PR diff context (they can see new files).
The Haiku confidence scorers are spawned independently without that context.
When a scorer reads `"File: src/cohezion/flume/group_evolution.py"` from a
reviewer's finding, it uses the Read/Glob/Bash tools against the checked-out
repo (base branch), where the file doesn't exist yet.

This is a known limitation of stateless sub-agents in multi-step pipelines.

## Files Most Affected

- New source files (entire new modules)
- Files moved/renamed (appear as "new" on the destination path)
- Generated files committed with the PR

## Files NOT Affected (scoring works correctly)

- Modified existing files (exist on base branch — scorer can read them)
- Deleted files (scorer can read them on base branch)
