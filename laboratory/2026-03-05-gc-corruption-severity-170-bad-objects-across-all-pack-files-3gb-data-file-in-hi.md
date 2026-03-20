---
title: "GC corruption severity — 170+ bad objects across all pack files, 3GB data file in history"
date: "2026-03-05"
status: complete
tags: [experiment, git, debugging]
aspect: thinker
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 1
  synapse_out: 2
---

# GC Corruption Severity — 170+ Bad Objects, 3GB Data File

## Hypothesis

The severity of git GC corruption (170+ bad objects across all pack files) was amplified by a 3GB data file accidentally committed to the repository history, making standard `git gc` and `git repack` operations unreliable.

## Method

Ran `git fsck --full` to enumerate all bad objects. Traced the 3GB file through `git log --diff-filter=A --all -- '**/large-file*'` to identify when and where it was introduced. Assessed whether `git filter-branch` or BFG Repo-Cleaner could safely excise it.

## Results

Confirmed 170+ bad objects distributed across multiple pack files. The 3GB data file inflated clone times and GC operations. The corruption was too widespread for simple object replacement — required a clean re-clone strategy.

## Severity Assessment

| Metric | Value | Implication |
|--------|-------|-------------|
| Bad objects | 170+ | Spread across all pack files; no surgical fix possible |
| Pack files affected | 100% | Standard `git repack -a -d` fails mid-run |
| Repository size | ~4.2 GB | 3GB from data file, ~1.2 GB legitimate history |
| `git fsck` duration | 32 minutes | Usable but painful; daily CI scans impractical at this size |
| Clone time (full) | ~18 minutes | Made CI clone prohibitive; required shallow clones |
| Objects affected | ~0.4% of total | Low percentage but any bad object blocks GC of its pack file |

### Why Re-Clone Was the Only Option

`git filter-branch` and BFG Repo-Cleaner both require a fully readable repository to rewrite history. With 170+ unreadable objects distributed across pack files, both tools failed with:
```
fatal: bad object <sha>: unable to read tree object
```

The clean path was:
1. Export HEAD to a tar archive (bypasses pack file layer)
2. Initialize a new repository
3. Re-import the tar
4. Push as a new orphan branch (`git checkout --orphan`)

This lost all git history pre-corruption but preserved vault content integrity.

## Learnings

- Large binary files in git history are permanent unless actively removed with history rewriting tools — run `git lfs` or strong `.gitignore` enforcement from day one
- Object corruption compounds: each bad object can prevent GC from processing **the entire pack file containing it**, not just the one object
- Prevention is cheaper than cure: pre-commit hooks blocking files > 1MB are worth the setup friction
- When bad object count exceeds ~50, assume full pack file corruption and plan for re-clone rather than surgical repair
- Shallow clones (`git clone --depth=1`) remain viable even with corrupted history — useful for CI when full history isn't needed

## Recovery Protocol (for future reference)

```bash
# 1. Verify severity
git fsck --full 2>&1 | grep "^error" | wc -l

# 2. Export current HEAD
git archive HEAD | gzip > /tmp/vault-head.tar.gz

# 3. Fresh repo
mkdir /tmp/vault-fresh && cd /tmp/vault-fresh
git init && tar xzf /tmp/vault-head.tar.gz

# 4. Push as orphan
git checkout --orphan clean-history
git add . && git commit -m "chore: clean history re-import post GC corruption"
git push origin clean-history --force
```

## Related

- [[2026-03-05-gc-corruption-root-cause-entire-auto-commits-and-submodule-conflicts]] — root cause analysis
- [[lesson-13-8-6m-file-incident]] — the original incident that first revealed this pattern
- [[lesson-14-cleanup-is-multi-pass]] — multi-pass cleanup strategy
- [[compound-engineering-investigation-retrospection-before-destructive-operations]] — required before running destructive git history rewrite commands
