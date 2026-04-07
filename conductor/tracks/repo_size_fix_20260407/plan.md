# Implementation Plan: repo_size_fix_20260407

## Phase 1: Audit and Analysis
1.  - [ ] Task: Audit repository for large blobs and historical artifacts.
    - [ ] Run `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$3 > 10000000' | sort -nrk 3` to identify large objects.
    - [ ] Document the findings in `research/repo_audit_20260407.md`.
2.  - [ ] Task: Audit existing `.gitignore` against common large-file patterns.
    - [ ] Compare current `.gitignore` with best practices for Python/ML/Node.js projects.
    - [ ] Identify gaps (e.g., `*.bin`, `*.pt`, `*.onnx`, large `*.json` or `*.csv`).
3.  - [ ] Task: Conductor - User Manual Verification 'Audit and Analysis' (Protocol in workflow.md).

## Phase 2: Safety and Backup
1.  - [ ] Task: Create a full local clone/backup of the current repository.
    - [ ] `git clone --mirror . ../cohezion_backup_20260407`
    - [ ] Verify the backup integrity.
2.  - [ ] Task: Conductor - User Manual Verification 'Safety and Backup' (Protocol in workflow.md).

## Phase 3: History Rewriting and Git LFS Migration
1.  - [ ] Task: Implement TDD for history rewriting verification.
    - [ ] Write tests to verify file content integrity after rewriting.
    - [ ] Write tests to verify Git LFS tracking for targeted file types.
2.  - [ ] Task: Execute `git-filter-repo` for history cleanup.
    - [ ] Remove identified large, obsolete blobs from the entire history.
    - [ ] Verify the repository integrity using `git fsck`.
3.  - [ ] Task: Migrate targeted files to Git LFS.
    - [ ] Use `git lfs migrate import --include="*.bin,*.pt,*.onnx,*.tar.gz"` (with proper patterns).
    - [ ] Verify LFS pointers are correctly created.
4.  - [ ] Task: Conductor - User Manual Verification 'History Rewriting and Git LFS Migration' (Protocol in workflow.md).

## Phase 4: `.gitignore` and Policy Implementation
1.  - [ ] Task: Update and refactor `.gitignore`.
    - [ ] Apply identified improvements.
    - [ ] Add rules to block known large-file patterns.
2.  - [ ] Task: Implement repository health monitoring utility.
    - [ ] Create `src/cohezion/maintenance/repo_health.py`.
    - [ ] Add functionality to check pack size and large file additions (via pre-commit hook).
3.  - [ ] Task: Conductor - User Manual Verification '.gitignore' and Policy Implementation' (Protocol in workflow.md).

## Phase 5: Final Verification and Push
1.  - [ ] Task: Verify final repository size and integrity.
    - [ ] `git count-objects -vH`.
    - [ ] `git verify-pack -v .git/objects/pack/pack-*.idx | sort -k 3 -n | tail -10`.
2.  - [ ] Task: Force-push to remote (with caution).
    - [ ] Coordinate with user before executing.
    - [ ] `git push origin --force --all && git push origin --force --tags`.
3.  - [ ] Task: Conductor - User Manual Verification 'Final Verification and Push' (Protocol in workflow.md).
