# Specification: repo_size_fix_20260407

## Overview
The Cohezion repository has exceeded the 2GiB Git pack limit on GitHub, causing push failures. This track implements a systemic approach to repository optimization, including history cleanup, Git LFS migration, and enhanced `.gitignore` and branching strategies to ensure long-term repository health.

## Objectives
- Reduce repository pack size to < 500MB.
- Migrate large assets (> 50MB) and binary blobs to Git LFS.
- Implement a systemic maintenance process (scripts/automation) to prevent future size bloat.
- Review and optimize `.gitignore` and branching strategies to align with repository health goals.
- Ensure zero data loss through non-destructive history rewriting.

## Functional Requirements
- **History Rewriting**: Use `git-filter-repo` to remove unnecessarily large historical blobs (e.g., old model weights, large datasets) while preserving the integrity of the code history.
- **Git LFS Migration**: Identify all files exceeding 50MB and migrate them to Git LFS with full history preservation.
- **`.gitignore` Enhancement**: Audit and update `.gitignore` to prevent accidental inclusion of system logs, temporary artifacts, and large model outputs.
- **Branch Management Audit**: Review existing branches and provide a plan/script to prune merged or obsolete branches that contribute to repository bloat.
- **Automation**: Create a `repo_health` CLI utility (likely integrated with `cohezion`) to monitor pack size and alert on large file additions.

## Non-Functional Requirements
- **Safety**: Every history-altering operation must be verifiable and backed up before execution.
- **Performance**: Cleanup operations should be optimized for a 128GB RAM / 16-core CPU environment.
- **Traceability**: All maintenance operations must be logged in the `cohezion` Knowledge Graph.

## Acceptance Criteria
- [ ] Repository pack size is successfully reduced to < 500MB.
- [ ] Push to GitHub (remote) succeeds without size errors.
- [ ] Git LFS is correctly configured and tracked files are verified.
- [ ] `.gitignore` contains rules for all common "workslop" patterns identified in the audit.
- [ ] `repo_health` monitoring tool is functional and integrated.

## Out of Scope
- Complete restructuring of the `src/` directory (unless directly related to size optimization).
- Migration to a different VCS (e.g., SVN, Mercurial).
