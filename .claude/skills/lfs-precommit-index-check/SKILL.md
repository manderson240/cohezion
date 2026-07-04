---
name: lfs-precommit-index-check
description: |
  Fix for pre-commit hooks that falsely flag LFS-tracked files as missing pointers.
  Use when: (1) lfs-pointer-check pre-commit hook fails on files that ARE in .gitattributes,
  (2) "not an LFS pointer" error on CSV/binary files tracked via git lfs,
  (3) any hook reads file bytes to detect LFS pointers but always sees real content.
  Root cause: git lfs smudge filter expands pointer files to real content in the working tree.
  Solution: check the git INDEX (staging area) via `git cat-file blob :<path>`, not the filesystem.
author: Claude Code
version: 1.0.0
---

# LFS Pre-commit Index Check

## Problem

Pre-commit hooks that detect LFS pointers by reading working-tree bytes via `path.open("rb")`
always see the smudged (real) content — never the pointer — because the smudge filter runs
on checkout and keeps the working tree populated with real file content.

## Root Cause

The git LFS smudge filter is transparent: `git checkout` / `git add --renormalize` expand
pointers in the working tree automatically. By the time a pre-commit hook reads the file,
the bytes are real content, not the `version https://git-lfs.github.com/spec/v1\n...` pointer.

`git add --renormalize` does NOT help either — it re-runs the clean filter (pointer → LFS store)
but the working tree is still smudged. `git checkout -- <file>` re-runs smudge → same result.

## Solution

Read the **index** (staging area) via `git cat-file blob :<path>`:

```python
import subprocess

LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"

def is_lfs_pointer_in_index(path: str) -> bool:
    """Returns True if the staged version of `path` is an LFS pointer."""
    result = subprocess.run(
        ["git", "cat-file", "blob", f":{path}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return True  # not staged — nothing to check, treat as safe
    return result.stdout[:50].startswith(LFS_POINTER_MAGIC)
```

## What NOT to do

```python
# WRONG — always sees real content, never pointer bytes
def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as f:
        return f.read(50).startswith(LFS_POINTER_MAGIC)
```

## Verification

```bash
# Stage a file and inspect the index blob directly:
git cat-file blob :path/to/file.csv | head -c 100
# LFS-tracked file shows: version https://git-lfs.github.com/spec/v1
# Regular file shows: actual file content
```

## Applied In

`scripts/hooks/lfs_pointer_check.py` — fixed during BMAD v6.8.0 update (2026-06-16).
The hook previously false-failed on all `.csv` files tracked by git lfs because it read
working-tree bytes. The fix replaced `is_lfs_pointer(Path)` with `is_lfs_pointer_in_index(str)`.

## References

- Git LFS smudge/clean filters: https://git-lfs.com/
- `git cat-file blob :<path>` reads from the index, not the working tree
