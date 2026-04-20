# Repository Size Audit - 2026-04-07

## Summary
- **Total Pack Size**: 13.47 GiB
- **Total Objects**: 78,814
- **Largest Object**: 9.7 GB (`luma_speedrun_BACKUP_20260402_162540.tar.gz`)

## Top 10 Largest Blobs
1. **9.7 GB**: `luma_speedrun_BACKUP_20260402_162540.tar.gz` (blob 71cd947f...)
2. **4.2 GB**: `archive/worktrees/aimo/aimo.tar.gz` (blob 18e96648...)
3. **276 MB**: `archive/worktrees/amd-speedrun/amd-speedrun.tar.gz` (blob 761ed43f...)
4. **276 MB**: `archive/worktrees/luma-amd-speedrun/luma-amd-speedrun.tar.gz` (blob d303e6b7...)
5. **86 MB**: `archive/worktrees/genesis-engine/genesis-engine.bundle` (blob b2cc6c7c...)
6. **74 MB**: `archive/worktrees/aimo/aimo.bundle` (blob 9cd73e27...)
7. **72 MB**: `archive/worktrees/gemini-mcp-fix/gemini-mcp-fix.bundle` (blob 18308ce4...)
8. **72 MB**: `archive/worktrees/opus-mla/opus-mla.bundle` (blob 66000557...)
9. **72 MB**: `archive/worktrees/gemm/gemm.bundle` (blob 25ee6afa...)
10. **72 MB**: `archive/worktrees/amd-speedrun/luma-amd-speedrun.bundle` (blob 040e37af...)

## Major Patterns of Bloat
- **Backups/Archives**: Large `.tar.gz` files committed to the repository.
- **Git Bundles**: Numerous `.bundle` files in `archive/worktrees/`.
- **Large Metadata**: Many `full.jsonl` files in `.entire/metadata/` and other directories (30-40MB each).
- **Node Modules**: `cohezion-3d-graph-plugin/node_modules/@esbuild/linux-x64/bin/esbuild` (10MB) - should likely be ignored.

## Initial Cleanup Recommendations
1. **Remove Large Backups**: `luma_speedrun_BACKUP_...` and `aimo.tar.gz` must be removed from history using `git-filter-repo`.
2. **Purge Worktree Archives**: Remove all `.bundle` and `.tar.gz` files from `archive/worktrees/`.
3. **LFS Migration**: Move remaining large `.jsonl` and other binary blobs to Git LFS if they are still needed.
4. **.gitignore Audit**: Ensure `node_modules`, `*.tar.gz`, `*.bundle`, and `*.jsonl` (unless small) are properly ignored.

## .gitignore Gaps
- `*.tar.gz`: Many large backup archives found in history.
- `*.bundle`: Git bundles found in `archive/worktrees/`.
- `archive/worktrees/`: Entire directory seems to contain historical bloat.
- `node_modules/`: Should be ignored globally.
- Database artifacts at root: `*.sst`, `LOCK`, `LOG`, `MANIFEST-*`, `OPTIONS-*` (likely from a local SurrealDB instance running in the root).
- `agi_pid.txt`, `birdclef_pid.txt`, `nemotron_pid.txt`: Process IDs should not be tracked.
