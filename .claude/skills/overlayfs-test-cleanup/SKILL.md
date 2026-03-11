---
name: overlayfs-test-cleanup
description: |
  Fix for "Device or resource busy" (OSError errno 16) when shutil.rmtree
  fails to clean up test directories that contain OverlayFS mounts.
  Use when: (1) sandbox/container isolation tests fail in tearDown with
  "Device or resource busy", (2) shutil.rmtree raises OSError on a test dir,
  (3) tests pass individually but fail when the full suite runs (mount leak).
  Key insight: findmnt returncode=0 means mount FOUND, returncode=1 means NOT found.
author: Claude Code
version: 1.0.0
---

# OverlayFS Test Cleanup

## Problem

`shutil.rmtree()` raises `OSError: [Errno 16] Device or resource busy` when
a test directory contains active OverlayFS mounts. This typically appears in
tearDown methods of sandbox/container isolation tests.

## Context / Trigger Conditions

- Tests use OverlayFS (`overlayfs`, Docker layers, container isolation)
- `tearDown` calls `shutil.rmtree(self.test_dir)`
- Error: `OSError: [Errno 16] Device or resource busy`
- May only fail when tests run as a suite (prior test leaves mount active)

## Solution

Replace bare `shutil.rmtree()` calls in tearDown with a helper that:
1. Finds all active mounts under the directory using `findmnt`
2. Unmounts them in reverse order (deepest first)
3. Then safely removes the directory

```python
import os
import shutil
import subprocess

def _cleanup_dir(path: str) -> None:
    """Safely remove directory, unmounting any active OverlayFS mounts first."""
    if not os.path.exists(path):
        return
    # Find all mounts under path (submounts too)
    result = subprocess.run(
        ["findmnt", "--raw", "--noheadings", "-o", "TARGET", "--submounts", path],
        capture_output=True, text=True,
    )
    # Unmount in reverse order (deepest first)
    for mount_point in reversed(result.stdout.strip().split("\n")):
        if mount_point.strip():
            subprocess.run(["umount", mount_point.strip()], capture_output=True)
    shutil.rmtree(path, ignore_errors=True)
```

## Critical: Mock Behavior

When mocking `subprocess.run` in tests that verify cleanup behavior,
`findmnt` return codes have **counterintuitive semantics**:

| `returncode` | Meaning |
|---|---|
| `0` | Mount **found** (still active) |
| `1` | Mount **not found** (already cleaned up) |

A single blanket mock returning `returncode=0` will make `findmnt` appear to
always find an active mount — use a command-aware side_effect:

```python
def _side_effect(cmd, **kwargs):
    if isinstance(cmd, list) and "findmnt" in cmd:
        return MagicMock(returncode=1)  # 1 = not found = already clean
    return MagicMock(returncode=0)     # umount and other commands succeed

mock_run.side_effect = _side_effect
```

## Verification

After applying the helper, tearDown should clean up without errors.
Run the full test suite to verify no "Device or resource busy" errors remain:

```bash
uv run pytest tests/sandbox/ -v
```

## References

- `findmnt` man page: `man findmnt`
- `--submounts` flag lists all mounts under a path recursively
